#!/usr/bin/env python3
"""Build one checked compiler, then diagnose its existing capture path once."""
import argparse
from collections import Counter
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
WORK = ROOT / '.work/hir-diagnostic-native-01'
UPGRADE = Path('/Users/danluu/dev/rust-interp-hir-fixture-env-upgrade-20260913')
UPGRADE_WORK = UPGRADE / '.work/hir-fixture-env-upgrade-01'
UPGRADE_PLAN = UPGRADE / 'experiments/hir-fixture-env-upgrade/planned-upgrade-01.json'
UPGRADE_PLAN_SHA = '5d79e14e09d124dac64afcb24a5ddf9037fbaf1ab59ccb48f7a66b45bfec507f'
SOURCE_REVISION = '0bc623ee4860082df9d1d2216aefad9abb42990d'
SOURCE_RECORD_SHA = 'bd53da0a1d70e560a362699ef7c789fab303e18da25dee669b28996529388ec0'
CURRENT_ARCHIVE_SHA = 'eb4f4157bc0c1e35d44f6364b6be0e315ce02e7c853d6a3c24b96b59f2bf0985'
CURRENT_SUMMARY_SHA = 'b0c1ddfe9eaee7e227fa0a4a3ac5c20210339eacaf7e6e4d577ead4a91deb7b1'
CURRENT_MANIFEST_SHA = '45440f7da06f325914fa20b1307e8967493f86fe39c8cff5a6c871af8c742c7d'
spec = importlib.util.spec_from_file_location('diagnostic_phase_upgrade', ROOT / 'experiments/hir-fixture-env-upgrade/upgrade.py')
upgrade = importlib.util.module_from_spec(spec); sys.modules[spec.name] = upgrade; spec.loader.exec_module(upgrade)
native, engine = upgrade.native, upgrade.engine
old = engine.old
SOURCE, SYSROOT, RUSTC = engine.SOURCE, native.SYSROOT, native.RUSTC
CHECKPOINT, CONFIG_SHA = upgrade.CHECKPOINT, native.CONFIG_SHA
ordinary, require, sha, write = native.ordinary, engine.require, engine.sha, engine.write
checked_result = native.checked_result
BUILD = list(native.COMMANDS['build'])
PROBES = native.PROBES
CAPACITY = dict(initial_free_gib=16, capacity_stop_gib=9, running_floor_gib=8,
    interpretation='One sequence admission; existing net-space observations are not peak upper bounds or reuse credit',
    full_stage2_package_gate_gib=36)
ARCHIVE_CHAIN = [upgrade.PREVIOUS_ARCHIVE_SHA, upgrade.FAILURE_HASHES['archive'],
                 native.COLD_ARCHIVE_SHA, native.FAILED_ARCHIVE_SHA]
FIXTURE_NAME = 'tests/run-make/hir-body-cache-capture/fixture.rs'
BODY_PHASES = ['current', 'capture', 'validation', 'preparation', 'cold-audit', 'post-audit-exit']
REPORT_STATES = {'rejected-entry', 'rejected-normalized-entry', 'rejected-effects', 'tree-write-unavailable',
    'cold-tree-and-journal-after-stock-lowering', 'same-tree-and-journal-after-stock-lowering',
    'changed-tree-or-journal-after-stock-lowering', *('rejected-body-tree-' + p for p in BODY_PHASES)}


def inputs():
    return {**upgrade.inputs(), **{str(ordinary(p)): sha(p) for p in
        [Path(__file__), HERE / 'README.md', ROOT / 'tests/test_hir_diagnostic_native.py']}}


def configurations():
    paths = set(map(Path, native.extra_configurations()))
    for directory in [ROOT, WORK, WORK / 'fixture']:
        paths.update(p / '.cargo' / name for p in [directory, *directory.parents] for name in ['config', 'config.toml'])
    result = {}
    for path in sorted(paths):
        require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents)
                and (not path.exists() or path.is_file()), 'unexpected diagnostic Cargo configuration')
        result[str(path)] = sha(path) if path.exists() else None
    return result


def compile_command(app):
    return [str(RUSTC), '-L', str(app), 'input.rs', '--crate-name', 'body_journal_test',
        '-o', 'body_journal_test', '-Cmetadata=body_journal_test', '-Cincremental=cache-on',
        '-Zhir-body-cache-capture=true', '-Cdebuginfo=2', '--edition=2024', '-Zincremental-info',
        '--target=' + old.HOST]


def observations(stderr):
    """Retain actual records, including rejection/no-record results; never qualify hits."""
    lines = [line for line in stderr.splitlines() if line.startswith(('[hir-body-capture]', '[hir-body-reuse]'))]
    counts = Counter()
    number = r'(0|[1-9][0-9]*)'
    pattern = (r'\[hir-body-capture\] (?P<name>[a-zA-Z_][a-zA-Z_0-9]*) (?P<state>[a-z-]+) '
        + r'S=' + number + r' E=' + number + r' events=' + number
        + r' cache_hits=0 body_codec=1 prepared_values=1 cold_materialization_audit=1 hit_materializer=0 '
        + r'body_bytes=' + number + r' body_ast=' + number + r' param_ast=' + number
        + r' trait_entries=' + number + r' trait_candidates=' + number + r' external_refs=' + number)
    for line in lines:
        match = re.fullmatch(pattern, line)
        require(match is not None and match['state'] in REPORT_STATES,
                'unexpected or malformed actual capture diagnostic')
        require(0 <= int(match[3]) <= int(match[4]) <= 0xFFFF_FF00, 'invalid diagnostic ItemLocalId range')
        counts[match['state']] += 1
    return dict(raw_records=lines, records=len(lines), state_counts=dict(sorted(counts.items())),
                no_records=not lines, native_qualified=False, executed_native_binary=False)


def history(terminal_path):
    """Read the completed phase-checkpoint history, never its predecessor reader."""
    plan_hash = UPGRADE_PLAN_SHA
    require(re.fullmatch('[0-9a-f]{64}', plan_hash or '') and sha(ordinary(UPGRADE_PLAN)) == plan_hash,
            'reviewed phase-checkpoint plan digest required')
    plan = json.loads(UPGRADE_PLAN.read_bytes())
    state_path, completed_path = UPGRADE_WORK / 'source.json', UPGRADE_WORK / 'completed.json'
    require(sha(ordinary(state_path)) == SOURCE_RECORD_SHA, 'actual phase source receipt changed')
    state = json.loads(state_path.read_bytes())
    require(state['revision'] == SOURCE_REVISION and state['parent'] == upgrade.PREVIOUS_REVISION,
            'actual phase source commit or parent changed')
    completed = json.loads(ordinary(completed_path).read_bytes())
    manifest, names = upgrade.checkpoint()
    require(plan['owner'] == str(UPGRADE) and plan['source'] == str(SOURCE)
            and plan['checkpoint'] == CHECKPOINT and plan['commands'] == old.COMMANDS
            and plan['stages'] == ['apply', 'check', 'unit']
            and sorted([*plan['old_tests'], *plan['added_tests']]) == names
            and state['plan_sha256'] == plan_hash and state['config_sha256'] == CONFIG_SHA
            and set(completed) == {'apply', 'check', 'unit'}, 'phase-checkpoint check/unit source history is incomplete')
    require(state['parent'] == plan['previous']['source']['revision']
            and all(state['files'].get(name) == dict(kind='file', sha256=row['after_sha256'])
                    for name, row in manifest['files'].items()), 'phase-checkpoint source does not match the frozen patch')
    references = [dict(paths=plan['archive_paths'], hashes=plan['archive_hashes'], required=plan['archive_required']),
                  *plan['previous']['historical_archives']]
    require(len(references) == 4, 'four separate predecessor archives required')
    for ref, expected in zip(references, ARCHIVE_CHAIN, strict=True):
        require(ref['hashes'][ref['paths']['archive']] == expected and ref['required']
                and set(ref['hashes']) == set(ref['paths'].values()), 'fixed predecessor archive identity changed')
    archive_inputs = {r['paths']['archive']: r['hashes'][r['paths']['archive']] for r in references}
    require(all(plan['inputs'].get(p) in (None, h) for p,h in archive_inputs.items()),
            'plan archive input disagrees with explicit reference')
    text_inputs = {p:h for p,h in plan['inputs'].items() if p not in archive_inputs}
    files = {str(UPGRADE_PLAN): plan_hash, str(state_path): sha(state_path), str(completed_path): sha(completed_path),
             str(ordinary(plan['delta'])): plan['delta_sha256'], **text_inputs}
    stages = {name: ordinary(ref['path']) for name, ref in completed.items()}
    require(ordinary(terminal_path) == stages['unit'], 'terminal must be the completed phase-checkpoint unit receipt')
    stages = {'plan': ordinary(Path(plan['delta']).parent / 'receipt.json'), **stages}
    last_finish = 0
    for name in ['plan', 'apply', 'check', 'unit']:
        stage_path = stages[name]
        require(stage_path.is_relative_to(UPGRADE_WORK / 'stages')
                and (name == 'plan' or sha(stage_path) == completed[name]['sha256']),
                'phase-checkpoint completion association changed')
        row = json.loads(stage_path.read_bytes())
        require(row['owner'] == str(UPGRADE) and row['stage'] == name and row['status'] == 'passed'
                and row['plan_sha256'] == plan_hash
                and (name == 'plan' or row['source_record_sha256'] == sha(state_path)),
                'phase-checkpoint stage did not pass against this exact source')
        require(row['started_at'] <= row['admitted_at'] <= row['finished_at']
                and row['admitted_at'] >= last_finish, 'phase-checkpoint stage order changed')
        last_finish = row['finished_at']
        attempt = re.fullmatch(re.escape(name) + r'-(\d+)', stage_path.parent.name)
        require(attempt is not None, 'unknown phase-checkpoint stage attempt')
        supervisor = UPGRADE / '.work/experiments' / ('hir-fixture-env-upgrade-' + name + '-supervisor-' + attempt[1])
        status_path = ordinary(supervisor / 'status.json')
        status = json.loads(status_path.read_bytes())
        require(status['status'] == 'finished' and status['returncode'] == 0 and status['child_pid'] == row['pid']
                and sha(supervisor / 'plan.json') == status['plan_sha256']
                and sha(supervisor / 'command.log') == status['log_sha256'], 'phase-checkpoint outer supervisor changed')
        for part in ['status.json', 'plan.json', 'command.log', 'supervisor.log']:
            files[str(ordinary(supervisor / part))] = sha(supervisor / part)
        files[str(stage_path)] = sha(stage_path)
        matched = []
        for ref in row['commands']:
            path = ordinary(ref['path'])
            require(path.is_relative_to(stage_path.parent / 'commands') and sha(path) == ref['sha256'],
                    'phase-checkpoint child association changed')
            child = json.loads(path.read_bytes())
            require(child['status'] == 'finished' and child['returncode'] == 0
                    and child['command'] == ref['command'], 'phase-checkpoint child failed or changed')
            files[str(path)] = sha(path)
            text = ''
            for output in ['stdout', 'stderr']:
                output_path = ordinary(path.parent / output)
                require(sha(output_path) == child[output + '_sha256'], 'phase-checkpoint raw output changed')
                files[str(output_path)] = sha(output_path)
                text += output_path.read_text()
            if name in old.COMMANDS and child['command'] == old.COMMANDS[name]:
                require(child['cwd'] == str(SOURCE) and child['environment'] == plan['previous']['old_plan']['environment'],
                        'phase-checkpoint compiler invocation route or environment changed')
                matched.append(text)
        if name in old.COMMANDS:
            require(len(matched) == 1, 'exactly one selected phase-checkpoint compiler command required')
            if name == 'unit':
                engine.checked_tests(matched[0], names, [])
                checked_result(matched[0], 26, unfiltered=True)
    require(all(sha(ordinary(p)) == h for p, h in files.items()), 'frozen phase-checkpoint history input changed')
    require(references[0]['required'] == (plan['previous']['files'] | plan['previous']['historical_source']),
            'immediate ReadyHit324 payload proof changed')
    old_plan = plan['previous']['old_plan']
    require(old.frozen_plan() == old_plan, 'original bootstrap/seed/environment recipe changed')
    return dict(plan_sha256=plan_hash, source=state, terminal=str(terminal_path), files=files,
                old_plan=old_plan, old_plan_path=plan['previous']['old_plan_path'], historical_archives=references,
                historical_source={str(SOURCE / p): row['after_sha256'] for p, row in manifest['files'].items()})


def current_archive(paths, prior):
    hashes = {paths[k]: expected for k, expected in [('archive', CURRENT_ARCHIVE_SHA),
              ('manifest', CURRENT_MANIFEST_SHA), ('summary', CURRENT_SUMMARY_SHA)]}
    require(all(sha(ordinary(p)) == h for p, h in hashes.items()), 'actual phase-checkpoint archive changed')
    required = prior['files'] | prior['historical_source']
    engine.verify_archive(paths['archive'], paths['manifest'], paths['summary'], required)
    return hashes, required


def load_plan(path, expected, frozen, names):
    require(re.fullmatch('[0-9a-f]{64}', expected or ''), 'reviewed diagnostic plan SHA256 required')
    payload = ordinary(path).read_bytes()
    require(engine.digest(payload) == expected, 'reviewed diagnostic plan changed')
    plan = json.loads(payload)
    require(plan['owner'] == str(ROOT) and plan['source'] == str(SOURCE) and plan['checkpoint'] == CHECKPOINT
            and plan['inputs'] == frozen and plan['required_units'] == names and plan['build'] == BUILD
            and plan['probes'] == PROBES and plan['compile_command'] == compile_command(WORK / 'fixture')
            and plan['capacity'] == CAPACITY and plan['canonical_lock'] == str(engine.CANONICAL_LOCK)
            and plan['diagnostic_only'] is True and plan['native_qualified'] is False
            and plan['executed_native_binary'] is False, 'fixed diagnostic contract changed')
    return plan


def execute(args):
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.attempt), 'fresh owned attempt required')
    output = WORK / 'stages' / args.attempt
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(schema_version=1, owner=str(ROOT), stage=args.stage, status='waiting', pid=os.getpid(),
        parent_pid=os.getppid(), started_at=time.time(), commands=[], diagnostic_only=True,
        native_qualified=False, executed_native_binary=False, canonical_lock=str(engine.CANONICAL_LOCK),
        lock_wait_seconds=600, capacity=CAPACITY)
    write(output / 'receipt.json', receipt)
    try:
        with engine.workload_lock(engine.CANONICAL_LOCK, 600):
            receipt.update(status='running', admitted_at=time.time(),
                           free_bytes_before=engine.disk(ROOT, 16 if args.stage == 'run' else 8))
            write(output / 'receipt.json', receipt)
            frozen, (_, names) = inputs(), upgrade.checkpoint()
            if args.stage == 'plan':
                require(args.write_plan and args.write_plan.is_absolute() and args.write_plan.parent == HERE
                        and not args.write_plan.exists() and not (WORK / 'fixture').exists(), 'fresh owned plan/work required')
                prior = history(args.terminal)
                paths = {k: str(ordinary(getattr(args, k))) for k in ['archive', 'manifest', 'summary']}
                hashes, required = current_archive(paths, prior)
                plan = dict(schema_version=1, owner=str(ROOT), source=str(SOURCE), checkpoint=CHECKPOINT,
                    inputs=frozen, required_units=names, build=BUILD, probes=PROBES,
                    compile_command=compile_command(WORK / 'fixture'), capacity=CAPACITY,
                    canonical_lock=str(engine.CANONICAL_LOCK), previous=prior, configurations=configurations(),
                    archive_paths=paths, archive_hashes=hashes, archive_required=required,
                    diagnostic_only=True, native_qualified=False, executed_native_binary=False)
            else:
                require(args.plan and args.plan.parent == HERE, 'diagnostic plan must belong to this worktree')
                plan = load_plan(args.plan, args.plan_sha256, frozen, names)
                prior = plan['previous']
                require(history(prior['terminal']) == prior, 'phase-checkpoint prerequisite changed')
                hashes, required = current_archive(plan['archive_paths'], prior)
                require(hashes == plan['archive_hashes'] and required == plan['archive_required'], 'archive proof changed')
            native.verify_references(prior)
            env = prior['old_plan']['environment']
            require('RUSTC_FORCE_RUSTC_VERSION' not in env, 'diagnostic requires exact original environment without override')
            fixture = ordinary(SOURCE / FIXTURE_NAME)
            fixture_sha = prior['source']['files'][FIXTURE_NAME]['sha256']
            require(sha(fixture) == fixture_sha, 'exact checked fixture changed')
            artifacts = None
            app = WORK / 'fixture'
            def guard():
                require(inputs() == frozen and configurations() == plan['configurations']
                        and old.frozen_plan() == prior['old_plan'] and sha(fixture) == fixture_sha
                        and all(sha(ordinary(p)) == h for p, h in prior['files'].items())
                        and all(sha(ordinary(p)) == h for p, h in plan['archive_hashes'].items())
                        and all(sha(ordinary(p)) == h for ref in prior['historical_archives']
                                for p, h in ref['hashes'].items()), 'frozen diagnostic prerequisite changed')
                if args.stage == 'run':
                    require(sha(args.plan) == args.plan_sha256, 'reviewed plan changed during run')
                if app.exists():
                    require(app.resolve(strict=True) == app and sha(ordinary(app / 'input.rs')) == fixture_sha,
                            'owned diagnostic source changed')
                if artifacts is not None:
                    require(native.artifacts() == artifacts, 'built compiler/native std changed during diagnostic')
                engine.disk(ROOT, 9)
            def command(argv, cwd=SOURCE):
                guard()
                if argv[0] == './x':
                    old.verify_archives(old.ARCHIVES); old.verify_copied_archives()
                folder = output / 'commands' / f'{len(receipt["commands"]):03d}'
                ref = dict(path=str(folder / 'receipt.json'), command=list(map(str, argv)))
                receipt['commands'].append(ref); write(output / 'receipt.json', receipt)
                try:
                    result = engine.run(argv, cwd=cwd, env=env, out=folder, capacity_root=ROOT)
                finally:
                    if (folder / 'receipt.json').exists():
                        ref['sha256'] = sha(folder / 'receipt.json'); write(output / 'receipt.json', receipt)
                guard()
                return dict(result, stdout=(folder / 'stdout').read_text(), stderr=(folder / 'stderr').read_text())
            def source_guard():
                engine.source_guard(prior['source'], command, sha(prior['old_plan_path']))
            source_guard()
            old.verify_archives(old.ARCHIVES); old.verify_copied_archives()
            if args.stage == 'plan':
                write(args.write_plan, plan)
                receipt.update(plan=str(args.write_plan), plan_sha256=sha(args.write_plan))
            else:
                receipt.update(plan=str(args.plan), expected_plan_sha256=args.plan_sha256,
                               source_revision=prior['source']['revision'], required_units_prerequisite=26)
                write(output / 'receipt.json', receipt)
                require(not app.exists(), 'diagnostic fixture/cache destination must be fresh')
                command(BUILD)
                source_guard()
                artifacts = native.artifacts()
                write(output / 'built-artifacts.json', artifacts)
                probes = [command(argv) for argv in PROBES]
                require('commit-hash: ' + SOURCE_REVISION in probes[0]['stdout']
                        and probes[1]['stdout'].strip() == str(SYSROOT)
                        and all(re.search(r'(?m)^\s*-Z\s+' + flag + r'=', probes[2]['stdout'])
                                for flag in ['hir-body-cache-capture', 'hir-body-cache-reuse']),
                        'actual compiler source/sysroot/capability mismatch')
                app.mkdir(exist_ok=False)
                (app / 'input.rs').write_bytes(fixture.read_bytes())
                try:
                    actual = command(plan['compile_command'], app)
                    observation = observations(actual['stderr'])
                    write(output / 'observations.json', observation)
                    ref = next(r for r in receipt['commands'] if r['command'] == plan['compile_command'])
                    receipt.update(compiler_command=ref, compiler_returncode=actual['returncode'],
                        observation_sha256=sha(output / 'observations.json'), observation=observation,
                        fixture_sha256=sha(app / 'input.rs'), output_binary_sha256=sha(ordinary(app / 'body_journal_test')))
                finally:
                    source_guard()
                    final = native.artifacts()
                    write(output / 'final-artifacts.json', final)
                    require(final == artifacts, 'compiler/native std changed during final probe')
                    receipt.update(built_artifacts_sha256=sha(output / 'built-artifacts.json'),
                        final_artifacts_sha256=sha(output / 'final-artifacts.json'))
                    write(output / 'receipt.json', receipt)
                receipt.update(bootstrap_commands_passed=1, identity_probes_passed=3, direct_compiler_commands_passed=1)
            guard()
            old.verify_archives(old.ARCHIVES); old.verify_copied_archives()
            receipt.update(status='passed' if args.stage == 'plan' else 'diagnostic-completed',
                           finished_at=time.time(), free_bytes_after=engine.disk(ROOT))
            write(output / 'receipt.json', receipt)
    except BaseException as error:
        receipt.update(status='failed', error=repr(error), finished_at=time.time(),
                       free_bytes_after=shutil.disk_usage(ROOT).free)
        write(output / 'receipt.json', receipt)
        raise


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=['plan', 'run'])
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--write-plan', type=Path)
    parser.add_argument('--terminal', type=Path)
    for name in ['archive', 'manifest', 'summary', 'plan']:
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--plan-sha256')
    execute(parser.parse_args())

if __name__ == '__main__':
    main()
