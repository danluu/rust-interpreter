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
NATIVE = Path('/Users/danluu/dev/rust-interp-hir-arena-native-20260913')
NATIVE_SCRIPT = NATIVE / 'experiments/hir-native-correctness/check.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


native = load('stage2_native_prerequisite', NATIVE_SCRIPT)
package = load('stage2_package_adapter', HERE / 'package.py')
qualified = load('stage2_qualified_native', HERE / 'qualified_native.py')
recipe = load('stage2_complete_recipe', HERE / 'recipe.py')
CHECKPOINT = qualified.CHECKPOINT
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
           'stage2-hir', 'stage2-hir-direct', 'dist', 'package', 'package-identity', 'native15', 'strip6', 'complete']


def inputs():
    paths = [Path(__file__), HERE / 'package.py', HERE / 'qualified_native.py', HERE / 'recipe.py', HERE / 'README.md',
             *sorted((HERE / 'inputs').iterdir()), ROOT / 'tests/test_hir_stage2_package.py',
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


def recipe_contract(stage):
    build = SOURCE / 'build' / HOST
    sysroot = build / ('stage' + str(stage))
    return dict(source=str(SOURCE), host=HOST, stage=stage, sysroot=str(sysroot),
        compiler=str(sysroot / 'bin/rustc'), compiletest=str(build / 'stage1-tools-bin/compiletest'),
        recipe=str(build / 'test/run-make/hir-body-cache-capture/rmake'))


def previous(plan_path, digest, terminal_path, supervisor, archive):
    return qualified.previous(native, recipe, archive, plan_path, digest, terminal_path, supervisor, recipe_contract(1))


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
    require(plan['owner'] == str(ROOT) and plan['source'] == str(SOURCE) and plan['checkpoint'] == CHECKPOINT
            and plan['inputs'] == frozen and plan['required_units'] == names and plan['commands'] == COMMANDS
            and plan['probes'] == PROBES and plan['capacity'] == CAPACITY and plan['actions'] == ACTIONS
            and plan['canonical_lock'] == str(engine.CANONICAL_LOCK) and plan['stage2_recipe'] == recipe_contract(2)
            and re.fullmatch('run-[0-9]+', plan['run_attempt'])
            and plan['direct_recipe_cwd'] == str(WORK/'stages'/plan['run_attempt']/'stage2-hir-direct/rmake_out'),
            'fixed stage2 scope changed')
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
            frozen, (_, names) = inputs(), qualified.checkpoint(native)
            if args.stage == 'plan':
                require(args.write_plan and args.write_plan.parent == HERE and args.write_plan.is_absolute()
                        and not args.write_plan.exists() and re.fullmatch('run-[0-9]+', args.run_attempt or ''),
                        'fresh owned plan and fixed run attempt required')
                require(not (WORK / 'stages' / args.run_attempt).exists(), 'run destination already exists')
                archive_paths = {n: str(ordinary(getattr(args, n))) for n in ['archive', 'manifest', 'summary']}
                archive = qualified.Archive(native, archive_paths)
                prior = previous(args.native_plan, args.native_plan_sha256, args.terminal, args.native_supervisor, archive)
                archive_hashes = archive.hashes
                plan = dict(schema_version=1, owner=str(ROOT), source=str(SOURCE), checkpoint=CHECKPOINT, stage2_recipe=recipe_contract(2),
                    inputs=frozen, required_units=names, commands=COMMANDS, probes=PROBES, capacity=CAPACITY,
                    actions=ACTIONS, canonical_lock=str(engine.CANONICAL_LOCK), run_attempt=args.run_attempt,
                    direct_recipe_cwd=str(WORK/'stages'/args.run_attempt/'stage2-hir-direct/rmake_out'),
                    previous=prior, archive_paths=archive_paths, archive_hashes=archive_hashes,
                    archive_required=prior['files'] | prior['historical_source'], configurations=configurations(),
                    rust_src_component=package.legacy.public_component(),
                    scope='in-place stage2/compiler checks/dist/package/native15/strip6 only; no installation or interpreter qualification')
            else:
                require(args.plan and args.plan.parent == HERE, 'owned reviewed stage2 plan required')
                plan = load_plan(args.plan, args.plan_sha256, frozen, names)
                require(args.attempt == plan['run_attempt'], 'run destination differs from reviewed plan')
                prior = plan['previous']
                archive = qualified.Archive(native, plan['archive_paths'])
                require(previous(prior['plan_path'], prior['plan_sha256'], prior['terminal'], prior['supervisor'], archive) == prior,
                        'native prerequisite changed')
            verify_references(prior)
            require(plan['archive_required'] == prior['files'] | prior['historical_source']
                    and all(sha(p) == h for p, h in plan['archive_hashes'].items()), 'native archive association changed')
            p = plan['archive_paths']; engine.verify_archive(p['archive'], p['manifest'], p['summary'], plan['archive_required'])
            require(native.artifacts() == prior['stage1'], 'native-qualified stage1 changed before continuation')
            def guard():
                archive.guard()
                require(inputs() == frozen and configurations() == plan['configurations']
                        and old.frozen_plan() == prior['old_plan']
                        and prior['archived_qualification_hashes'] == archive.hashes
                        and all(sha(p) == h for p, h in plan['archive_hashes'].items())
                        and all(sha(p) == h for ref in prior['historical_archives'] for p, h in ref['hashes'].items()),
                        'stage2 frozen input changed')
                if args.stage == 'run': require(sha(args.plan) == args.plan_sha256, 'reviewed plan changed during run')
                engine.disk(ROOT, 9)
            def command(argv, cwd=SOURCE, fds=(), env=None):
                argv = list(map(str, argv)); guard()
                if argv[0] == './x': old.verify_archives(old.ARCHIVES); old.verify_copied_archives()
                directory = output / 'commands' / f'{len(receipt["commands"]):03d}'
                ref = dict(path=str(directory / 'receipt.json'), command=argv)
                receipt['commands'].append(ref); write(output / 'receipt.json', receipt)
                try:
                    result = engine.run(argv, cwd=cwd, env=env if env is not None else prior['old_plan']['environment'], out=directory,
                                        capacity_root=ROOT, pass_fds=fds)
                finally:
                    if (directory / 'receipt.json').exists():
                        ref['sha256'] = sha(directory / 'receipt.json'); write(output / 'receipt.json', receipt)
                guard()
                return dict(result, stdout=(directory / 'stdout').read_text(), stderr=(directory / 'stderr').read_text())
            def source_guard(): engine.source_guard(prior['source'], command, sha(prior['old_plan_path']))
            def direct_recipe(compiletest_result):
                contract = plan['stage2_recipe']
                route = recipe.recipe_environment(compiletest_result['stdout'] + compiletest_result['stderr'],
                                                  prior['old_plan']['environment'], contract)
                parent = output/'stage2-hir-direct'; parent.mkdir(exist_ok=False)
                cwd = Path(plan['direct_recipe_cwd']); cwd.mkdir(exist_ok=False)
                fixture = SOURCE/'tests/run-make/hir-body-cache-capture/fixture.rs'
                expected_fixture = prior['source']['files'][str(fixture.relative_to(SOURCE))]['sha256']
                require(sha(ordinary(fixture)) == expected_fixture, 'actual stage2 fixture changed')
                shutil.copyfile(fixture, cwd/'fixture.rs')
                def runtime():
                    stage2 = dict(files=package.inventory(SYSROOT,source_checkout=SOURCE),
                                  source_links=native.bootstrap_source_links(SYSROOT,SOURCE))
                    roots = [Path(p) for p in route['environment']['DYLD_LIBRARY_PATH'].split(':')]
                    files = {}
                    for root in roots:
                        require(root.is_dir() and root.resolve(strict=True) == root, 'stage2 recipe runtime root changed')
                        for p in root.rglob('*'):
                            require(not p.is_symlink(), 'stage2 recipe dependency symlink')
                            if p.is_dir(): continue
                            files[str(ordinary(p))] = sha(p)
                    for p in [Path(contract['recipe']),Path(contract['compiletest']),
                              Path(route['options']['--run-make-support-rlib'][0])]:
                        files[str(ordinary(p))] = sha(p)
                    return dict(stage2=stage2,other_files=files)
                before = runtime(); write(parent/'runtime-before.json',before)
                write(parent/'route.json',route)
                direct_result = command([contract['recipe']],cwd=cwd,env=route['environment'])
                direct_ref = dict(receipt['commands'][-1])
                observations = recipe.checked_replay(direct_result['stdout']+direct_result['stderr'])
                require(sha(cwd/'fixture.rs') == sha(cwd/'input.rs') == expected_fixture,
                        'complete stage2 recipe did not restore source')
                after = runtime(); require(after == before, 'stage2 recipe/compiler/support bytes changed')
                write(parent/'runtime-after.json',after);write(parent/'observations.json',observations)
                value = dict(status='passed',returncode=0,source_revision=prior['source']['revision'],
                    command=[contract['recipe']],cwd=str(cwd),child_receipt=direct_ref,
                    actual_complete_recipe=True,observations=observations,
                    evidence={str(parent/name):sha(parent/name) for name in
                        ['runtime-before.json','runtime-after.json','route.json','observations.json']})
                write(parent/'result.json',value)
                return dict(path=str(parent/'result.json'),sha256=sha(parent/'result.json'))
            def save_stage(name, result, roots=(), extra=None, child_ref=None):
                row = dict(schema_version=1, status='passed', returncode=0, source_revision=prior['source']['revision'],
                    config_sha256=prior['source']['config_sha256'], command=result['command'],
                    child_receipt=child_ref or receipt['commands'][-1], artifact_inventories={str(p): package.inventory(p,
                        source_checkout=SOURCE if p == SYSROOT else None) for p in roots},
                    artifact_source_links={str(SYSROOT): native.bootstrap_source_links(SYSROOT, SOURCE)} if SYSROOT in roots else {})
                if extra is not None: row['direct_recipe'] = extra
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
                    result = command(argv); bootstrap_ref = dict(receipt['commands'][-1])
                    text = result['stdout'] + result['stderr']
                    if name == 'stage2-units':
                        engine.checked_tests(text, names, []); native.checked_result(text, len(names), unfiltered=True)
                    elif name == 'stage2-option': native.checked_option(text)
                    elif name == 'stage2-partition': checked_partition(text)
                    elif name == 'stage2-hir':
                        # Keep the original complete run-make pass; compiletest
                        # may abbreviate its raw output even with --no-capture.
                        native.checked_result(text, 1)
                        require(len(re.findall(r'^test \[run-make\] tests/run-make/hir-body-cache-capture \.\.\.', text, re.M)) == 1,
                                'stage2 run-make did not execute exactly once')
                        direct = direct_recipe(result)
                        receipt['stage2_hir_direct'] = direct; receipt['stages']['stage2-hir-direct'] = direct
                        write(output / 'receipt.json', receipt)
                    roots = ([SOURCE / 'build/tmp/tarball' / n / HOST / 'image' for n in ['rustc-dev', 'rust-std']]
                             if name == 'dist' else [SYSROOT])
                    save_stage(name, result, roots, extra=direct if name == 'stage2-hir' else None,
                               child_ref=bootstrap_ref); source_guard()
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
                receipt.update(required_units_passed=len(names), option_tests_passed=1, partition_tests_passed=17,
                    hir_native_runmake_passed=1, hir_native_direct_recipe_passed=1, actual_verified_hits=True, package_native_commands=15, strip_commands=6,
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
