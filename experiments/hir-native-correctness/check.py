#!/usr/bin/env python3
"""Limited native correctness of an archived, checked ReadyHit compiler source."""
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
WORK = ROOT / '.work/hir-native-correctness-01'
READY = Path('/Users/danluu/dev/rust-interp-hir-ready-hit-upgrade-20260913')
READY_WORK = READY / '.work/hir-ready-hit-upgrade-01'
READY_PLAN = READY / 'experiments/hir-ready-hit-upgrade/planned-upgrade-01.json'
CHECKPOINT = '5cd6acd3f50912cec5fb29375b130afa70506703'
PATCH_SHA = 'cca094ebc73f6cc7da9ea1660669a436a6900e5d9c307550435dbcd8784410f4'
SOURCE_IDENTITY = '50ecfb157fd227791b2dbb196c6c795d8c999a37017fed3be938c672a8a85818'
COLD_ARCHIVE_SHA = '55061f25443157ef7ea125a1cad8920ce18d895f9c6f9a99d480df804b188f73'
FAILED_ARCHIVE_SHA = '53a8fa2fab9504a8dbef7a44fbe26bf094a254bf8443f0cda43c9fe35eacaf54'
CONFIG_SHA = '71b495da8fc35ca1321322f56065eb149ecd82fa3c8ff7ef4d4c10ec53f0df9b'
ENGINE = ROOT / 'experiments/hir-capture-upgrade/upgrade.py'
spec = importlib.util.spec_from_file_location('hir_native_engine', ENGINE)
engine = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = engine
spec.loader.exec_module(engine)
from owned_stage import bootstrap_source_links, inventory
old = engine.old
SOURCE = engine.SOURCE
SYSROOT = SOURCE / 'build' / old.HOST / 'stage1'
RUSTC = SYSROOT / 'bin/rustc'
require, sha, write = engine.require, engine.sha, engine.write
COMMANDS = {
    'build': ['./x', 'build', '--stage', '1', 'compiler/rustc', 'library', '--jobs', '2', '-vv'],
    'option': ['./x', 'test', '--stage', '1', 'compiler/rustc_interface', '--test-args',
               'test_unstable_options_tracking_hash', '--jobs', '2', '-vv'],
    'native': ['./x', 'test', '--stage', '1', 'tests/run-make/hir-body-cache-capture', '--jobs', '2', '-vv', '--no-capture'],
}
PROBES = [[str(RUSTC), '-vV'], [str(RUSTC), '--print', 'sysroot'], [str(RUSTC), '-Zhelp']]
CAPACITY = dict(initial_free_gib=16, capacity_stop_gib=9, running_floor_gib=8,
    analogous_host_net_gib=[3.548553, 0.846394, 2.450684],
    interpretation='Host free-space observations; not isolated allocation or peak upper bounds; no reuse credit',
    full_stage2_package_gate_gib=36)


def ordinary(path):
    path = Path(path)
    require(path.is_absolute() and path.is_file() and path.resolve(strict=True) == path
            and not path.is_symlink(), 'expected ordinary absolute file: ' + str(path))
    return path


def checkpoint():
    origins = json.loads((HERE / 'inputs/origin.json').read_bytes())
    require(set(origins) == {'capture.patch', 'patch.json', 'checkpoint-README.md'}, 'checkpoint input set changed')
    for name, row in origins.items():
        require(row['git_revision'] == CHECKPOINT and sha(HERE / 'inputs' / name) == row['sha256'],
                'immutable ReadyHit snapshot changed')
    patch = HERE / 'inputs/capture.patch'
    manifest = json.loads((HERE / 'inputs/patch.json').read_bytes())
    require(sha(patch) == manifest['patch_sha256'] == PATCH_SHA
            and manifest['source_identity'] == SOURCE_IDENTITY and manifest['base_commit'] == old.BASE
            and len(manifest['files']) == 25 and manifest['actual_cache_hit_path'] is True
            and manifest['cached_body_materialization'] is True, 'wrong ReadyHit checkpoint')
    names = re.findall(r'^\+\s*#\[test\]\n\+\s*fn ([a-z0-9_]+)', patch.read_text(), re.M)
    require(len(names) == len(set(names)) == 26 and set(old.REQUIRED_TESTS) <= set(names),
            'all twenty-six ReadyHit units are required')
    return manifest, sorted(names)


def inputs():
    paths = [Path(__file__), HERE / 'README.md', ROOT / 'tests/test_hir_native_correctness.py', ENGINE,
             ROOT / 'experiments/stable-cgu/owned_stage.py', ROOT / 'scripts/supervise_experiment.py',
             *sorted((HERE / 'inputs').iterdir())]
    return {str(ordinary(p)): sha(p) for p in paths}


def checked_result(text, count, *, unfiltered=False):
    rows = re.findall(r'^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;', text, re.M)
    require(rows and sum(int(p) for p, _, _, _, _ in rows) == count
            and all(int(f) == int(i) == int(m) == 0 and (not unfiltered or int(x) == 0)
                    for _, f, i, m, x in rows), 'actual test count or outcome differs')


def checked_option(text):
    require(len(re.findall(r'^test tests::test_unstable_options_tracking_hash \.\.\. ok$', text, re.M)) == 1,
            'actual tracked-option test did not pass exactly once')
    checked_result(text, 1)


def checked_native(text):
    require(len(re.findall(r'^test \[run-make\] tests/run-make/hir-body-cache-capture \.\.\.', text, re.M)) == 1,
            'actual ReadyHit native run-make did not run exactly once')
    checked_result(text, 1)
    hits = re.findall(r'(?m)^\[hir-body-reuse\][^\n]*$', text)
    require(hits, 'no actual verified cache hit in retained native output')
    for line in hits:
        hit = re.fullmatch(r'\[hir-body-reuse\] [a-z0-9_]+ hit cache_hits=1 '
                          r'verify_tree=1 verify_journal=1 verify_poststate=1 '
                          r'S=(0|[1-9][0-9]*) E=(0|[1-9][0-9]*)', line)
        # Pinned ItemLocalId::INVALID is 0xFFFF_FF00. E is exclusive and
        # may equal INVALID; every allocated ID in [S, E) must precede it.
        require(hit is not None and 0 < int(hit[1]) < int(hit[2]) <= 0xFFFF_FF00,
                'malformed verified cache hit or invalid ItemLocalId range')


def history(plan_hash, terminal_path):
    """Read the completed ReadyHit history, never its cold predecessor reader."""
    require(re.fullmatch('[0-9a-f]{64}', plan_hash or '') and sha(ordinary(READY_PLAN)) == plan_hash,
            'reviewed ReadyHit plan digest required')
    plan = json.loads(READY_PLAN.read_bytes())
    state_path, completed_path = READY_WORK / 'source.json', READY_WORK / 'completed.json'
    state = json.loads(ordinary(state_path).read_bytes())
    completed = json.loads(ordinary(completed_path).read_bytes())
    manifest, names = checkpoint()
    require(plan['owner'] == str(READY) and plan['source'] == str(SOURCE)
            and plan['checkpoint'] == CHECKPOINT and plan['commands'] == old.COMMANDS
            and plan['stages'] == ['apply', 'check', 'unit']
            and sorted([*plan['old_tests'], *plan['added_tests']]) == names
            and state['plan_sha256'] == plan_hash and state['config_sha256'] == CONFIG_SHA
            and set(completed) == {'apply', 'check', 'unit'}, 'ReadyHit check/unit source history is incomplete')
    require(state['parent'] == plan['previous']['source']['revision']
            and all(state['files'].get(name) == dict(kind='file', sha256=row['after_sha256'])
                    for name, row in manifest['files'].items()), 'ReadyHit source does not match the frozen patch')
    files = {str(READY_PLAN): plan_hash, str(state_path): sha(state_path), str(completed_path): sha(completed_path),
             str(ordinary(plan['delta'])): plan['delta_sha256'], **plan['inputs']}
    stages = {name: ordinary(ref['path']) for name, ref in completed.items()}
    require(ordinary(terminal_path) == stages['unit'], 'terminal must be the completed ReadyHit unit receipt')
    stages = {'plan': ordinary(Path(plan['delta']).parent / 'receipt.json'), **stages}
    last_finish = 0
    for name in ['plan', 'apply', 'check', 'unit']:
        stage_path = stages[name]
        require(stage_path.is_relative_to(READY_WORK / 'stages')
                and (name == 'plan' or sha(stage_path) == completed[name]['sha256']),
                'ReadyHit completion association changed')
        row = json.loads(stage_path.read_bytes())
        require(row['owner'] == str(READY) and row['stage'] == name and row['status'] == 'passed'
                and row['plan_sha256'] == plan_hash
                and (name == 'plan' or row['source_record_sha256'] == sha(state_path)),
                'ReadyHit stage did not pass against this exact source')
        require(row['started_at'] <= row['admitted_at'] <= row['finished_at']
                and row['admitted_at'] >= last_finish, 'ReadyHit stage order changed')
        last_finish = row['finished_at']
        attempt = re.fullmatch(re.escape(name) + r'-(\d+)', stage_path.parent.name)
        require(attempt is not None, 'unknown ReadyHit stage attempt')
        supervisor = READY / '.work/experiments' / ('hir-ready-hit-upgrade-' + name + '-supervisor-' + attempt[1])
        status_path = ordinary(supervisor / 'status.json')
        status = json.loads(status_path.read_bytes())
        require(status['status'] == 'finished' and status['returncode'] == 0 and status['child_pid'] == row['pid']
                and sha(supervisor / 'plan.json') == status['plan_sha256']
                and sha(supervisor / 'command.log') == status['log_sha256'], 'ReadyHit outer supervisor changed')
        for part in ['status.json', 'plan.json', 'command.log', 'supervisor.log']:
            files[str(ordinary(supervisor / part))] = sha(supervisor / part)
        files[str(stage_path)] = sha(stage_path)
        matched = []
        for ref in row['commands']:
            path = ordinary(ref['path'])
            require(path.is_relative_to(stage_path.parent / 'commands') and sha(path) == ref['sha256'],
                    'ReadyHit child association changed')
            child = json.loads(path.read_bytes())
            require(child['status'] == 'finished' and child['returncode'] == 0
                    and child['command'] == ref['command'], 'ReadyHit child failed or changed')
            files[str(path)] = sha(path)
            text = ''
            for output in ['stdout', 'stderr']:
                output_path = ordinary(path.parent / output)
                require(sha(output_path) == child[output + '_sha256'], 'ReadyHit raw output changed')
                files[str(output_path)] = sha(output_path)
                text += output_path.read_text()
            if name in old.COMMANDS and child['command'] == old.COMMANDS[name]:
                require(child['cwd'] == str(SOURCE) and child['environment'] == plan['previous']['old_plan']['environment'],
                        'ReadyHit compiler invocation route or environment changed')
                matched.append(text)
        if name in old.COMMANDS:
            require(len(matched) == 1, 'exactly one selected ReadyHit compiler command required')
            if name == 'unit':
                engine.checked_tests(matched[0], names, [])
                checked_result(matched[0], 26, unfiltered=True)
    require(all(sha(ordinary(p)) == h for p, h in files.items()), 'frozen ReadyHit history input changed')
    references = [dict(paths=plan['archive_paths'], hashes=plan['archive_hashes'], required=plan['archive_required']),
                  *plan['previous']['historical_archives']]
    require(len(references) == 2 and references[0]['required'] ==
            (plan['previous']['files'] | plan['previous']['historical_source']),
            'separate immediate cold and failed-predecessor archive proofs required')
    for ref, expected in zip(references, [COLD_ARCHIVE_SHA, FAILED_ARCHIVE_SHA], strict=True):
        require(ref['hashes'][ref['paths']['archive']] == expected and ref['required']
                and set(ref['hashes']) == set(ref['paths'].values()), 'fixed historical archive identity changed')
    old_plan = plan['previous']['old_plan']
    require(old.frozen_plan() == old_plan, 'original bootstrap/seed/environment recipe changed')
    return dict(plan_sha256=plan_hash, source=state, terminal=str(terminal_path), files=files,
                old_plan=old_plan, old_plan_path=plan['previous']['old_plan_path'], historical_archives=references,
                historical_source={str(SOURCE / p): row['after_sha256'] for p, row in manifest['files'].items()})


def verify_references(prior):
    for ref in prior['historical_archives']:
        require(all(sha(ordinary(p)) == h for p, h in ref['hashes'].items()), 'referenced historical archive changed')
        paths = ref['paths']
        engine.verify_archive(paths['archive'], paths['manifest'], paths['summary'], ref['required'])


def extra_configurations():
    dirs = [ROOT, SOURCE / 'compiler/rustc_interface', SOURCE / 'src/tools/compiletest',
            SOURCE / 'src/tools/run-make-support', SOURCE / 'src/tools/rustdoc',
            SOURCE / 'tests/run-make/hir-body-cache-capture', SOURCE / 'library']
    paths = {p / '.cargo' / name for d in dirs for p in [d, *d.parents] for name in ['config', 'config.toml']}
    values = {}
    for p in sorted(paths):
        require(not p.is_symlink() and not any(x.is_symlink() for x in p.parents)
                and (not p.exists() or p.is_file()), 'unexpected native-scope Cargo configuration')
        values[str(p)] = sha(p) if p.exists() else None
    return values


def load_plan(path, expected, frozen, names):
    require(re.fullmatch('[0-9a-f]{64}', expected or ''), 'reviewed native plan SHA256 required')
    data = ordinary(path).read_bytes()
    require(engine.digest(data) == expected, 'reviewed native plan changed')
    plan = json.loads(data)
    require(plan['owner'] == str(ROOT) and plan['source'] == str(SOURCE) and plan['checkpoint'] == CHECKPOINT
            and plan['inputs'] == frozen and plan['required_units'] == names and plan['commands'] == COMMANDS
            and plan['probes'] == PROBES and plan['capacity'] == CAPACITY
            and plan['canonical_lock'] == str(engine.CANONICAL_LOCK), 'fixed native plan contract changed')
    return plan


def artifacts():
    files = inventory(SYSROOT, source_checkout=SOURCE)
    require('bin/rustc' in files and any(p.startswith('lib/librustc_driver-') for p in files),
            'stage1 compiler runtime missing')
    prefix = 'lib/rustlib/' + old.HOST + '/lib/'
    for crate in ['core', 'alloc', 'std', 'test', 'proc_macro']:
        require(any(p.startswith(prefix + 'lib' + crate + '-') and p.endswith('.rlib') for p in files),
                'native stage1 standard library missing: ' + crate)
    return dict(files=files, source_links=bootstrap_source_links(SYSROOT, SOURCE))


def execute(args):
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.attempt), 'invalid fresh native attempt')
    output = WORK / 'stages' / args.attempt
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(schema_version=1, owner=str(ROOT), status='waiting', stage=args.stage,
        pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), commands=[])
    write(output / 'receipt.json', receipt)
    try:
        with engine.workload_lock(engine.CANONICAL_LOCK, 600):
            receipt.update(status='running', admitted_at=time.time(),
                           free_bytes_before=engine.disk(ROOT, 16 if args.stage == 'run' else 8))
            write(output / 'receipt.json', receipt)
            frozen, (_, names) = inputs(), checkpoint()
            if args.stage == 'plan':
                require(args.write_plan and args.write_plan.is_absolute() and args.write_plan.parent == HERE
                        and not args.write_plan.exists(), 'fresh owned plan destination required')
                prior = history(args.ready_plan_sha256, args.terminal)
                verify_references(prior)
                archive_paths = {n: str(ordinary(getattr(args, n))) for n in ['archive', 'manifest', 'summary']}
                archive_hashes = {p: sha(p) for p in archive_paths.values()}
                required = prior['files'] | prior['historical_source']
                engine.verify_archive(archive_paths['archive'], archive_paths['manifest'], archive_paths['summary'], required)
                plan = dict(schema_version=1, owner=str(ROOT), source=str(SOURCE), checkpoint=CHECKPOINT,
                    inputs=frozen, required_units=names, commands=COMMANDS, probes=PROBES, capacity=CAPACITY,
                    canonical_lock=str(engine.CANONICAL_LOCK), previous=prior, archive_paths=archive_paths,
                    archive_hashes=archive_hashes, archive_required=required, configurations=extra_configurations())
            else:
                require(args.plan and args.plan.parent == HERE, 'native plan must belong to this experiment')
                plan = load_plan(args.plan, args.plan_sha256, frozen, names)
                prior = plan['previous']
                require(history(prior['plan_sha256'], prior['terminal']) == prior, 'ReadyHit prerequisite changed')
                verify_references(prior)
                require(plan['archive_required'] == (prior['files'] | prior['historical_source']),
                        'immediate ReadyHit archive required-member map changed')
                require(all(sha(p) == h for p, h in plan['archive_hashes'].items()), 'ReadyHit archive changed')
                engine.verify_archive(**dict(archive=plan['archive_paths']['archive'],
                    manifest_path=plan['archive_paths']['manifest'], summary_path=plan['archive_paths']['summary'],
                    required=plan['archive_required']))
            def guard():
                require(inputs() == frozen and extra_configurations() == plan['configurations']
                        and old.frozen_plan() == prior['old_plan']
                        and all(sha(p) == h for p, h in prior['files'].items())
                        and all(sha(p) == h for p, h in plan['archive_hashes'].items())
                        and all(sha(p) == h for ref in prior['historical_archives']
                                for p, h in ref['hashes'].items()), 'native frozen input changed')
                if args.stage == 'run':
                    require(sha(args.plan) == args.plan_sha256, 'reviewed plan changed during native sequence')
                engine.disk(ROOT, 9)
            def command(argv, cwd=SOURCE):
                guard()
                if argv[0] == './x':
                    old.verify_archives(old.ARCHIVES)
                    old.verify_copied_archives()
                directory = output / 'commands' / f'{len(receipt["commands"]):03d}'
                ref = dict(path=str(directory / 'receipt.json'), command=list(map(str, argv)))
                receipt['commands'].append(ref)
                write(output / 'receipt.json', receipt)
                try:
                    result = engine.run(argv, cwd=cwd, env=prior['old_plan']['environment'],
                                        out=directory, capacity_root=ROOT)
                finally:
                    if (directory / 'receipt.json').exists():
                        ref['sha256'] = sha(directory / 'receipt.json')
                        write(output / 'receipt.json', receipt)
                guard()
                return dict(result, stdout=(directory / 'stdout').read_text(), stderr=(directory / 'stderr').read_text())
            def source_guard():
                engine.source_guard(prior['source'], command, sha(prior['old_plan_path']))
            source_guard()
            old.verify_archives(old.ARCHIVES)
            old.verify_copied_archives()
            if args.stage == 'plan':
                write(args.write_plan, plan)
                receipt.update(plan=str(args.write_plan), plan_sha256=sha(args.write_plan))
            else:
                receipt.update(plan=str(args.plan), expected_plan_sha256=args.plan_sha256,
                               source_revision=prior['source']['revision'], capacity=CAPACITY)
                write(output / 'receipt.json', receipt)
                command(COMMANDS['build'])
                source_guard()
                built = artifacts()
                write(output / 'built-artifacts.json', built)
                probes = [command(argv) for argv in PROBES]
                require('commit-hash: ' + prior['source']['revision'] in probes[0]['stdout']
                        and probes[1]['stdout'].strip() == str(SYSROOT)
                        and all(re.search(r'(?m)^\s*-Z\s+' + option + r'=', probes[2]['stdout'])
                                for option in ['hir-body-cache-capture', 'hir-body-cache-reuse']),
                        'actual stage1 identity or required capabilities differ')
                option = command(COMMANDS['option'])
                checked_option(option['stdout'] + option['stderr'])
                source_guard()
                native = command(COMMANDS['native'])
                checked_native(native['stdout'] + native['stderr'])
                source_guard()
                final = artifacts()
                require(all(final['files'].get(p) == v for p, v in built['files'].items())
                        and final['source_links'] == built['source_links'], 'tested compiler/std bytes changed')
                write(output / 'final-artifacts.json', final)
                receipt.update(bootstrap_commands_passed=3, actual_option_tests_passed=1,
                    actual_native_runmake_passed=1, required_units_prerequisite=26,
                    built_artifacts_sha256=sha(output / 'built-artifacts.json'),
                    final_artifacts_sha256=sha(output / 'final-artifacts.json'))
            guard()
            old.verify_archives(old.ARCHIVES)
            old.verify_copied_archives()
            receipt.update(status='passed', finished_at=time.time(), free_bytes_after=engine.disk(ROOT))
            write(output / 'receipt.json', receipt)
    except BaseException as error:
        receipt.update(status='failed', error=repr(error), finished_at=time.time(),
                       free_bytes_after=shutil.disk_usage(ROOT).free)
        write(output / 'receipt.json', receipt)
        raise


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('stage', choices=['plan', 'run'])
    p.add_argument('--attempt', required=True)
    p.add_argument('--write-plan', type=Path)
    p.add_argument('--ready-plan-sha256')
    p.add_argument('--terminal', type=Path)
    for name in ['archive', 'manifest', 'summary', 'plan']:
        p.add_argument('--' + name, type=Path)
    p.add_argument('--plan-sha256')
    execute(p.parse_args())


if __name__ == '__main__':
    main()
