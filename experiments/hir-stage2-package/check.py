#!/usr/bin/env python3
"""Explicit in-place stage2 continuation after archived native HIR qualification."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
WORK = ROOT / '.work/hir-stage2-package-01'
NATIVE = Path('/Users/danluu/dev/rust-interp-hir-native-correctness-20260913')
NATIVE_SCRIPT = NATIVE / 'experiments/hir-native-correctness/check.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


native = load('stage2_native_prerequisite', NATIVE_SCRIPT)
package = load('stage2_package_adapter', HERE / 'package.py')
engine, old = native.engine, native.old
SOURCE, HOST = native.SOURCE, old.HOST
require, sha, write = engine.require, engine.sha, engine.write
ordinary = native.ordinary
SYSROOT = SOURCE / 'build' / HOST / 'stage2'
RUSTC = SYSROOT / 'bin/rustc'
CAPACITY = dict(initial_free_gib=24, capacity_stop_gib=9, running_floor_gib=8,
    original_fresh_compiler_gate_gib=36, historical_host_net_gib=8.925838,
    historical_net_is_peak_or_cap=False, new_stage2_units_and_hir_native_measured=False,
    retirement_credit_bytes=0, stop='retain all failure/capacity receipts; no automatic retry')
COMMANDS = {
    'stage2': ['./x', 'build', '--stage', '2', 'compiler/rustc', 'library', '--jobs', '2', '-vv'],
    'stage2-units': ['./x', 'test', '--stage', '2', 'compiler/rustc_ast_lowering', '--jobs', '2', '-vv'],
    'stage2-option': ['./x', 'test', '--stage', '2', 'compiler/rustc_interface', '--test-args',
                      'test_unstable_options_tracking_hash', '--jobs', '2', '-vv'],
    'stage2-partition': ['./x', 'test', '--stage', '2', 'tests/codegen-units/partitioning',
                        'tests/run-make/stable-cgu-partitioning', 'tests/run-make/stable-mono-cgu-partitioning',
                        '--jobs', '2', '-vv'],
    'stage2-hir': ['./x', 'test', '--stage', '2', 'tests/run-make/hir-body-cache-capture',
                  '--jobs', '2', '-vv', '--no-capture'],
    'dist': ['./x', 'dist', '--stage', '2', 'rustc-dev', 'rust-std', '--jobs', '2', '-vv'],
}
PROBES = [[str(RUSTC), '-vV'], [str(RUSTC), '--print', 'sysroot'], [str(RUSTC), '-Zhelp']]
ACTIONS = ['stage2', 'stage2-identity', 'stage2-units', 'stage2-option', 'stage2-partition',
           'stage2-hir', 'dist', 'package', 'package-identity', 'native15', 'strip6', 'complete']


def inputs():
    paths = [Path(__file__), HERE / 'package.py', HERE / 'README.md', ROOT / 'tests/test_hir_stage2_package.py',
             package.HERE / 'production-driver.py', package.HERE / 'package-owned.py',
             package.HERE / 'native-entry-controls.py', package.HERE / 'strip-controls.py',
             package.HERE / 'bootstrap-production-source-paths.toml', package.HERE / 'owned_stage.py',
             ROOT / 'experiments/hir-capture-upgrade/upgrade.py', package.legacy.OLD_COMPARISON]
    paths += sorted((ROOT / 'scripts').glob('*.py'))
    return {str(ordinary(p)): sha(p) for p in paths} | native.inputs()


def configurations():
    result = native.extra_configurations()
    dirs = [ROOT, SOURCE / 'build', SOURCE / 'compiler/rustc_ast_lowering',
            SOURCE / 'tests/codegen-units/partitioning', SOURCE / 'tests/run-make/stable-cgu-partitioning',
            SOURCE / 'tests/run-make/stable-mono-cgu-partitioning']
    for path in sorted({p / '.cargo' / n for d in dirs for p in [d, *d.parents] for n in ['config', 'config.toml']}):
        require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents)
                and (not path.exists() or path.is_file()), 'indirect Cargo configuration')
        result[str(path)] = sha(path) if path.exists() else None
    return result


def checked_native_terminal(row, plan, artifact_hash):
    require(row['status'] == 'passed' and row['stage'] == 'run'
            and row['owner'] == str(NATIVE) and row['expected_plan_sha256'] == plan['sha256']
            and row['source_revision'] == plan['value']['previous']['source']['revision']
            and row['capacity'] == native.CAPACITY and row['bootstrap_commands_passed'] == 3
            and row['actual_option_tests_passed'] == row['actual_native_runmake_passed'] == 1
            and row['required_units_prerequisite'] == 26 and row['final_artifacts_sha256'] == artifact_hash
            and row['started_at'] <= row['admitted_at'] <= row['finished_at'],
            'complete native success with actual verified hits is required')


def read_child(ref, parent, files):
    path = ordinary(ref['path'])
    require(path.is_relative_to(parent / 'commands') and sha(path) == ref['sha256'], 'native child binding changed')
    row = json.loads(path.read_bytes())
    require(row['status'] == 'finished' and row['returncode'] == 0 and row['command'] == ref['command'],
            'native child did not pass')
    files[str(path)] = sha(path)
    text = ''
    for name in ['stdout', 'stderr']:
        output = ordinary(path.parent / name)
        require(sha(output) == row[name + '_sha256'], 'native raw output changed')
        files[str(output)] = sha(output)
        text += output.read_text()
    return row, text


def previous(plan_path, digest, terminal_path, supervisor):
    plan_path, terminal_path = ordinary(plan_path), ordinary(terminal_path)
    require(plan_path.parent == NATIVE_SCRIPT.parent and terminal_path.is_relative_to(native.WORK / 'stages'),
            'native history must belong to the exact owned driver')
    frozen, (_, names) = native.inputs(), native.checkpoint()
    plan = native.load_plan(plan_path, digest, frozen, names)
    prior = plan['previous']
    require(native.history(prior['plan_sha256'], prior['terminal']) == prior, 'ReadyHit source/check/unit history changed')
    native.verify_references(prior)
    row = json.loads(terminal_path.read_bytes())
    final_path = ordinary(terminal_path.parent / 'final-artifacts.json')
    final = json.loads(final_path.read_bytes())
    checked_native_terminal(row, dict(value=plan, sha256=digest), sha(final_path))
    built_path = ordinary(terminal_path.parent / 'built-artifacts.json')
    built = json.loads(built_path.read_bytes())
    require(sha(built_path) == row['built_artifacts_sha256']
            and all(final['files'].get(p) == item for p, item in built['files'].items())
            and final['source_links'] == built['source_links'], 'native runtime association changed')
    files = {str(plan_path): digest, str(terminal_path): sha(terminal_path), str(final_path): sha(final_path),
             str(built_path): sha(built_path), **frozen}
    matched = []
    for ref in row['commands']:
        child, text = read_child(ref, terminal_path.parent, files)
        if child['command'] in [*native.COMMANDS.values(), *native.PROBES]:
            require(child['cwd'] == str(SOURCE) and child['environment'] == prior['old_plan']['environment'],
                    'native actual compiler route changed')
            matched.append((child['command'], text))
    expected = [native.COMMANDS['build'], *native.PROBES, native.COMMANDS['option'], native.COMMANDS['native']]
    require([cmd for cmd, _ in matched] == expected, 'native commands were replaced, missing or duplicated')
    require('commit-hash: ' + prior['source']['revision'] in matched[1][1]
            and matched[2][1].strip() == str(native.SYSROOT)
            and all(re.search(r'(?m)^\s*-Z\s+' + option + r'=', matched[3][1]) for option in
                    ['hir-body-cache-capture', 'hir-body-cache-reuse']), 'native actual compiler identity differs')
    native.checked_option(matched[4][1]); native.checked_native(matched[5][1])
    supervisor = Path(supervisor)
    require(supervisor.resolve(strict=True) == supervisor and supervisor.parent == NATIVE / '.work/experiments',
            'native outer supervisor must be task-owned')
    outer = json.loads(ordinary(supervisor / 'status.json').read_bytes())
    require(outer['status'] == 'finished' and outer['returncode'] == 0 and outer['child_pid'] == row['pid']
            and outer['owner'] == str(NATIVE) and sha(supervisor / 'plan.json') == outer['plan_sha256']
            and sha(supervisor / 'command.log') == outer['log_sha256'], 'native supervisor did not pass')
    launch = json.loads((supervisor / 'plan.json').read_bytes())
    argv = launch['command']
    require(launch['owner'] == str(NATIVE) and argv == outer['command']
            and '--plan' in argv and argv[argv.index('--plan') + 1] == str(plan_path)
            and '--plan-sha256' in argv and argv[argv.index('--plan-sha256') + 1] == digest
            and '--attempt' in argv and argv[argv.index('--attempt') + 1] == terminal_path.parent.name,
            'native outer command differs from the retained plan/attempt')
    for name in ['plan.json', 'status.json', 'command.log', 'supervisor.log']:
        files[str(ordinary(supervisor / name))] = sha(supervisor / name)
    references = [dict(paths=plan['archive_paths'], hashes=plan['archive_hashes'], required=plan['archive_required']),
                  *prior['historical_archives']]
    require(len(references) == 3 and references[0]['required'] == prior['files'] | prior['historical_source'],
            'complete ReadyHit/cold/failed archive chain required')
    return dict(plan_path=str(plan_path), plan_sha256=digest, terminal=str(terminal_path), supervisor=str(supervisor),
                files=files, source=prior['source'], old_plan=prior['old_plan'], old_plan_path=prior['old_plan_path'],
                stage1=final, historical_archives=references, historical_source=prior['historical_source'])


def verify_references(prior):
    for ref in prior['historical_archives']:
        require(all(sha(ordinary(p)) == h for p, h in ref['hashes'].items()), 'historical archive changed')
        p = ref['paths']
        engine.verify_archive(p['archive'], p['manifest'], p['summary'], ref['required'])


def load_plan(path, expected, frozen, names):
    require(re.fullmatch('[0-9a-f]{64}', expected or ''), 'reviewed stage2 plan digest required')
    data = ordinary(path).read_bytes()
    require(engine.digest(data) == expected, 'reviewed stage2 plan changed')
    plan = json.loads(data)
    require(plan['owner'] == str(ROOT) and plan['source'] == str(SOURCE) and plan['checkpoint'] == native.CHECKPOINT
            and plan['inputs'] == frozen and plan['required_units'] == names and plan['commands'] == COMMANDS
            and plan['probes'] == PROBES and plan['capacity'] == CAPACITY and plan['actions'] == ACTIONS
            and plan['canonical_lock'] == str(engine.CANONICAL_LOCK)
            and re.fullmatch('run-[0-9]+', plan['run_attempt']), 'fixed stage2 scope changed')
    return plan


def checked_partition(text):
    native.checked_result(text, 17)
    for name in ['stable-cgu-partitioning', 'stable-mono-cgu-partitioning']:
        require(len(re.findall(r'^test \[run-make\] tests/run-make/' + name + r' \.\.\. ok$', text, re.M)) == 1,
                'existing partition run-make did not pass: ' + name)
    require(len(re.findall(r'^test \[codegen-units\] tests/codegen-units/partitioning/.* \.\.\. ok$', text, re.M)) == 15,
            'all fifteen partitioning controls required')


def probe_identity(rows, sysroot, revision):
    require('commit-hash: ' + revision in rows[0]['stdout'] and rows[1]['stdout'].strip() == str(sysroot)
            and all(re.search(r'(?m)^\s*-Z\s+' + option + r'=', rows[2]['stdout']) for option in
                ['stable-cgu-partitioning', 'stable-mono-cgu-partitioning', 'hir-body-cache-capture', 'hir-body-cache-reuse']),
            'actual stage2 identity or all four capabilities differ')


def execute(args):
    require(re.fullmatch('(plan|run)-[0-9]+', args.attempt), 'fresh stage2 attempt required')
    output = WORK / 'stages' / args.attempt
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(schema_version=1, owner=str(ROOT), status='waiting', stage=args.stage, commands=[], stages={},
        pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
    write(output / 'receipt.json', receipt)
    try:
        with engine.workload_lock(engine.CANONICAL_LOCK, 600) as lock_fd:
            receipt.update(status='running', admitted_at=time.time(),
                           free_bytes_before=engine.disk(ROOT, 24 if args.stage == 'run' else 8))
            write(output / 'receipt.json', receipt)
            frozen, (_, names) = inputs(), native.checkpoint()
            if args.stage == 'plan':
                require(args.write_plan and args.write_plan.parent == HERE and args.write_plan.is_absolute()
                        and not args.write_plan.exists() and re.fullmatch('run-[0-9]+', args.run_attempt or ''),
                        'fresh owned plan and fixed run attempt required')
                require(not (WORK / 'stages' / args.run_attempt).exists(), 'run destination already exists')
                prior = previous(args.native_plan, args.native_plan_sha256, args.terminal, args.native_supervisor)
                archive_paths = {n: str(ordinary(getattr(args, n))) for n in ['archive', 'manifest', 'summary']}
                archive_hashes = {p: sha(p) for p in archive_paths.values()}
                plan = dict(schema_version=1, owner=str(ROOT), source=str(SOURCE), checkpoint=native.CHECKPOINT,
                    inputs=frozen, required_units=names, commands=COMMANDS, probes=PROBES, capacity=CAPACITY,
                    actions=ACTIONS, canonical_lock=str(engine.CANONICAL_LOCK), run_attempt=args.run_attempt,
                    previous=prior, archive_paths=archive_paths, archive_hashes=archive_hashes,
                    archive_required=prior['files'] | prior['historical_source'], configurations=configurations(),
                    rust_src_component=package.legacy.public_component(),
                    scope='in-place stage2/compiler checks/dist/package/native15/strip6 only; no installation or interpreter qualification')
            else:
                require(args.plan and args.plan.parent == HERE, 'owned reviewed stage2 plan required')
                plan = load_plan(args.plan, args.plan_sha256, frozen, names)
                require(args.attempt == plan['run_attempt'], 'run destination differs from reviewed plan')
                prior = plan['previous']
                require(previous(prior['plan_path'], prior['plan_sha256'], prior['terminal'], prior['supervisor']) == prior,
                        'native prerequisite changed')
            verify_references(prior)
            require(plan['archive_required'] == prior['files'] | prior['historical_source']
                    and all(sha(p) == h for p, h in plan['archive_hashes'].items()), 'native archive association changed')
            p = plan['archive_paths']; engine.verify_archive(p['archive'], p['manifest'], p['summary'], plan['archive_required'])
            require(native.artifacts() == prior['stage1'], 'native-qualified stage1 changed before continuation')
            def guard():
                require(inputs() == frozen and configurations() == plan['configurations']
                        and old.frozen_plan() == prior['old_plan']
                        and all(sha(p) == h for p, h in prior['files'].items())
                        and all(sha(p) == h for p, h in plan['archive_hashes'].items())
                        and all(sha(p) == h for ref in prior['historical_archives'] for p, h in ref['hashes'].items()),
                        'stage2 frozen input changed')
                if args.stage == 'run': require(sha(args.plan) == args.plan_sha256, 'reviewed plan changed during run')
                engine.disk(ROOT, 9)
            def command(argv, cwd=SOURCE, fds=()):
                argv = list(map(str, argv)); guard()
                if argv[0] == './x': old.verify_archives(old.ARCHIVES); old.verify_copied_archives()
                directory = output / 'commands' / f'{len(receipt["commands"]):03d}'
                ref = dict(path=str(directory / 'receipt.json'), command=argv)
                receipt['commands'].append(ref); write(output / 'receipt.json', receipt)
                try:
                    result = engine.run(argv, cwd=cwd, env=prior['old_plan']['environment'], out=directory,
                                        capacity_root=ROOT, pass_fds=fds)
                finally:
                    if (directory / 'receipt.json').exists():
                        ref['sha256'] = sha(directory / 'receipt.json'); write(output / 'receipt.json', receipt)
                guard()
                return dict(result, stdout=(directory / 'stdout').read_text(), stderr=(directory / 'stderr').read_text())
            def source_guard(): engine.source_guard(prior['source'], command, sha(prior['old_plan_path']))
            def save_stage(name, result, roots=()):
                row = dict(schema_version=1, status='passed', returncode=0, source_revision=prior['source']['revision'],
                    config_sha256=prior['source']['config_sha256'], command=result['command'],
                    child_receipt=receipt['commands'][-1], artifact_inventories={str(p): package.inventory(p,
                        source_checkout=SOURCE if p == SYSROOT else None) for p in roots},
                    artifact_source_links={str(SYSROOT): native.bootstrap_source_links(SYSROOT, SOURCE)} if SYSROOT in roots else {})
                path = output / (name + '.json'); write(path, row)
                receipt['stages'][name] = dict(path=str(path), sha256=sha(path)); write(output / 'receipt.json', receipt)
            source_guard(); old.verify_archives(old.ARCHIVES); old.verify_copied_archives()
            if args.stage == 'plan':
                write(args.write_plan, plan); receipt.update(plan=str(args.write_plan), plan_sha256=sha(args.write_plan))
            else:
                receipt.update(plan=str(args.plan), plan_sha256=args.plan_sha256, source_revision=prior['source']['revision'], capacity=CAPACITY)
                write(output / 'receipt.json', receipt)
                combined = command(['git', 'diff', '--binary', package.legacy.UPSTREAM, prior['source']['revision'], '--'])
                (output / 'combined-upstream.patch').write_text(combined['stdout'])
                for name, argv in COMMANDS.items():
                    result = command(argv); text = result['stdout'] + result['stderr']
                    if name == 'stage2-units':
                        engine.checked_tests(text, names, []); native.checked_result(text, 26, unfiltered=True)
                    elif name == 'stage2-option': native.checked_option(text)
                    elif name == 'stage2-partition': checked_partition(text)
                    elif name == 'stage2-hir': native.checked_native(text)
                    roots = ([SOURCE / 'build/tmp/tarball' / n / HOST / 'image' for n in ['rustc-dev', 'rust-std']]
                             if name == 'dist' else [SYSROOT])
                    save_stage(name, result, roots); source_guard()
                    if name == 'stage2': probe_identity([command(p) for p in PROBES], SYSROOT, prior['source']['revision'])
                package_refs = package.compose(command, output, receipt['stages'], prior['source'], plan['rust_src_component'], lock_fd)
                receipt['package'] = package_refs; write(output / 'receipt.json', receipt)
                prefix = output / 'packaged-stage2-01'
                probe_identity([command([str(prefix / 'bin/rustc'), *p[1:]], cwd=ROOT) for p in PROBES], prefix, prior['source']['revision'])
                for name, script, count in [('native15', 'native-entry-controls.py', 15), ('strip6', 'strip-controls.py', 6)]:
                    command([sys.executable, package.HERE / script, '--compiler', prefix / 'bin/rustc',
                        '--package-provenance', package_refs['provenance']['path'], '--receipt', output / name,
                        '--partitioning-policy', 'stable-mono-cgu', '--lock-fd', str(lock_fd), '--lock-wait-seconds', '600'],
                        cwd=ROOT, fds=(lock_fd,))
                    result_path = output / name / 'result.json'; result = json.loads(result_path.read_bytes())
                    require(result['status'] == 'passed' and len(result['commands']) == count
                            and all(c['returncode'] == 0 for c in result['commands']), 'packaged native/strip controls failed')
                    receipt['stages'][name] = dict(path=str(result_path), sha256=sha(result_path))
                source_guard()
                p = json.loads(Path(package_refs['package_receipt']['path']).read_bytes())
                require({n: r['sha256'] for n, r in package.inventory(prefix).items()} == p['files'], 'package changed during controls')
                receipt.update(required_units_passed=26, option_tests_passed=1, partition_tests_passed=17,
                    hir_native_runmake_passed=1, actual_verified_hits=True, package_native_commands=15, strip_commands=6,
                    package_complete=True, installed=False, interpreter_tools_built=False, performance_qualified=False)
            guard(); old.verify_archives(old.ARCHIVES); old.verify_copied_archives()
            receipt.update(status='passed', finished_at=time.time(), free_bytes_after=engine.disk(ROOT))
            write(output / 'receipt.json', receipt)
    except BaseException as error:
        receipt.update(status='failed', error=repr(error), finished_at=time.time(), free_bytes_after=shutil.disk_usage(ROOT).free)
        write(output / 'receipt.json', receipt); raise


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('stage', choices=['plan', 'run']); p.add_argument('--attempt', required=True)
    p.add_argument('--write-plan', type=Path); p.add_argument('--run-attempt')
    for name in ['native-plan', 'terminal', 'native-supervisor', 'archive', 'manifest', 'summary', 'plan']:
        p.add_argument('--' + name, type=Path)
    p.add_argument('--native-plan-sha256'); p.add_argument('--plan-sha256')
    execute(p.parse_args())

if __name__ == '__main__': main()
