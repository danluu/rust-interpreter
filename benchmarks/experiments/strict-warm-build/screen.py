#!/usr/bin/env python3
"""Fresh Nushell compiler-cache screen; never a final 0.5-second qualification."""
import argparse
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, lock_wait_seconds
from interpreter import TOOLCHAIN, installed_tools, require_export_option
from std_mir import FLAGS as STD_FLAGS, POLICY as STD_POLICY, stamp
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_cases import WORKFLOW_VARIANTS
from workflow_io import SourceEdit, capture, require_space, write_json
from workflow_measurements import child_usage, child_cpu_since, source_states

MODES = ['baseline', 'candidate', 'duplicate']
CASE = WORKFLOW_VARIANTS['nushell', 'type-relations']
INSTRUCTIONS, ALLOCATIONS = 100_000_000_000, 150_000
JOBS, SUITE_WORKERS, MINIMUM_GIB = 4, 2, 8


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_input_hash(path):
    """Freeze a tracked link itself, including directory and dangling fixtures."""
    path = Path(path)
    if path.is_symlink():
        data = b'symlink\0' + os.fsencode(os.readlink(path))
    else:
        require(path.is_file(), 'frozen input is not a file or symlink: ' + str(path))
        data = b'file\0' + path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def protocol_states(original, case=CASE):
    """Each of five cumulative valid edits is new in every arm's cache."""
    states = list(source_states(original.decode(), case, 1, MODES, True))
    require(len(case['edits']) == 5 and len(states) == 7, 'expected five real edits')
    recovery = dict(states[0], phase='recovery', label='compiled-original-after-wrong-edit')
    final = dict(states[0], phase='restoration', label='compiled-final-restoration')
    states = [states[0], states[1], recovery, *states[2:], final]
    # Controls use a Latin square; the remaining six rows use every permutation.
    orders = [MODES, MODES[1:] + MODES[:1], MODES[2:] + MODES[:2]]
    orders += list(itertools.permutations(MODES))
    seen = set()
    require(len(states) == len(orders), 'source/order count differs')
    for index, (state, order) in enumerate(zip(states, orders)):
        state.update(index=index, modes=list(order))
        if state['phase'] == 'edit':
            digest = hashlib.sha256(state['source']).hexdigest()
            require(digest not in seen, 'an edited source revision was already compiled')
        seen.add(hashlib.sha256(state['source']).hexdigest())
    return states


def environment():
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
           and k not in {'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                         'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR',
                         'CARGO_BUILD_TARGET', 'RUST_TEST_THREADS'}}
    require(not any(k.startswith(('LD_', 'DYLD_')) for k in env),
            'dynamic-loader overrides are outside this screen')
    env.update(CARGO_TERM_COLOR='never', RUST_INTERP_LAUNCH_STATS='1')
    return env


def validate_std_ready(path, env):
    """Read-only setup verification; never invoke the std-MIR builder."""
    path = path.absolute()
    require(path.resolve(strict=True) == path and path.name == 'ready.json', 'invalid std readiness path')
    require(path.parent.parent == ROOT / '.work/std-mir', 'std MIR must be owned by this checkout')
    ready = json.loads(path.read_bytes())
    identity = ready['identity']
    require(ready['owner'] == str(ROOT) and identity['policy'] == STD_POLICY
            and identity['flags'] == STD_FLAGS, 'std ownership or policy differs')
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    require(path.parent.name == key, 'std MIR identity differs from its directory')
    rustup = Path(env.get('RUSTUP_HOME', str(Path.home() / '.rustup')))
    toolchain = (rustup / 'toolchains' / (TOOLCHAIN + '-' + identity['target'])).resolve(strict=True)
    rustc = toolchain / 'bin/rustc'
    require(rustc.is_file(), 'pinned rustc is not installed; setup is required')
    compiler = subprocess.check_output([str(rustc), '-vV'], env=env, text=True)
    require(compiler == identity['compiler'], 'prepared std MIR uses a different compiler')
    require(sha(toolchain / 'lib/rustlib/src/rust/library/Cargo.lock') == identity['lock_sha256'],
            'prepared std MIR uses a different standard-library lockfile')
    artifacts = {}
    for name, proof in ready['artifacts'].items():
        artifact = path.parent / name
        require(artifact.resolve(strict=True) == artifact and artifact.is_relative_to(path.parent),
                'std artifact escapes its directory or follows a symlink')
        require(stamp(artifact) == proof['stamp'] and sha(artifact) == proof['sha256'],
                'prepared std MIR artifact changed')
        artifacts[str(artifact)] = proof
    require(artifacts, 'prepared std MIR has no artifacts')
    for crate in ['core', 'alloc', 'std', 'test', 'proc_macro']:
        matches = list((path.parent / 'sysroot/lib/rustlib' / identity['target'] / 'lib').glob('lib' + crate + '-*.rmeta'))
        require(len(matches) == 1 and str(matches[0]) in artifacts, 'missing prepared std crate ' + crate)
    return dict(path=str(path), sha256=sha(path), key=key, artifacts=artifacts,
                compiler=compiler, rustc=str(rustc), rustc_sha256=sha(rustc))


def validate_source(source):
    require(source.resolve(strict=True) == source and source.is_dir(), 'source must be an ordinary owned directory')
    revision = json.loads((ROOT / 'benchmarks/corpus.json').read_bytes())['projects']['nushell']['revision']
    marker = source / '.rust-interp-owned.json'
    owner = json.loads(marker.read_bytes())
    require(not marker.is_symlink() and owner['owner'] == str(ROOT) and owner['revision'] == revision,
            'Nushell snapshot ownership or revision differs')
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == revision,
            'Nushell snapshot HEAD differs')
    require(not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip(),
            'Nushell snapshot has tracked changes')
    changed = source / CASE['file']
    require(changed.resolve(strict=True) == changed and changed.is_file(), 'edited source follows a symlink')
    original = subprocess.check_output(['git', 'show', revision + ':' + CASE['file']], cwd=source)
    require(changed.read_bytes() == original, 'production source differs from pinned revision')
    return revision, marker, changed, original


def command_for(mode, key, source, work, sample, names=CASE['tests']):
    require(mode in MODES, 'unknown screen arm')
    command = [sys.executable, ROOT / 'scripts/interpreter.py', '--manifest-path', source / 'Cargo.toml',
        '--package', CASE['package'], '--jobs', str(JOBS), '--tool-key', key,
        '--cache-namespace', work.name + ':' + mode, '--workspace-cache-root', work / 'caches' / mode,
        '--query-cache-retention', 'demand' if mode == 'candidate' else 'off',
        '--test-body', '--std-mir', '--engine', 'jit', '--jit-resumable-calls',
        '--jit-persistent-registers', '--inline-leaves', '--trap-unsupported-calls', '--run-try-callbacks',
        '--function-cache', 'auto', '--toolchain-lookup', 'cached', '--isolated-batch', 'prepared',
        '--suite-workers', str(SUITE_WORKERS), '--suite-report', work / 'suites' / f"{sample['index']}-{mode}.json",
        '--instruction-limit', str(INSTRUCTIONS), '--allocation-limit', str(ALLOCATIONS)]
    return list(map(str, [*command, *[arg for name in names for arg in ['--entry', name]]]))


def measure_command(command, **kwargs):
    before = child_usage()
    started = time.perf_counter()
    child, stdout, stderr = capture(command, **kwargs)
    elapsed = time.perf_counter() - started
    cpu = child_cpu_since(before)
    require(math.isfinite(elapsed) and elapsed > 0, 'invalid complete-command wall time')
    require(all(math.isfinite(v) and v >= 0 for v in cpu.values())
            and cpu['total_seconds'] > 0, 'invalid complete-command CPU time')
    return child, stdout, stderr, elapsed, cpu


def checked_launch(stderr, mode, key, success, suite_path, cache_parent):
    launches = [json.loads(line.removeprefix('rust-interp-launch: ')) for line in stderr.splitlines()
                if line.startswith('rust-interp-launch: ')]
    require(len(launches) == 1, 'expected exactly one completed launcher report')
    launch = launches[0]
    expected = dict(tool_key=key, engine='jit', function_cache='auto', borrowck_cache='off',
        query_cache_retention='demand' if mode == 'candidate' else 'off',
        jit_persistent_registers=True, jit_resumable_calls=True, inline_leaves=True,
        trap_unsupported_calls=True, run_try_callbacks=True, isolated_batch='prepared',
        suite_workers_requested=SUITE_WORKERS)
    require(all(launch.get(k) == v for k, v in expected.items()), 'launcher settings differ')
    require(launch['toolchain_lookup']['mode'] == 'cached'
            and launch['toolchain_lookup']['outcome'] in {'miss', 'hit'}, 'cached toolchain lookup unavailable')
    for field in ['launcher_seconds', 'cargo_seconds', 'execution_seconds']:
        value = launch[field]
        require(type(value) in (int, float) and math.isfinite(value) and value > 0, 'invalid launcher duration')
    workspace = Path(launch['workspace_path'])
    artifact = Path(launch['artifact_path'])
    require(workspace.resolve(strict=True) == workspace and workspace.is_relative_to(cache_parent),
            'launcher workspace is outside its fresh arm cache')
    require(artifact.resolve(strict=True) == artifact and artifact.is_relative_to(workspace / 'target'),
            'selected artifact is outside the actual Cargo target')
    require(sha(artifact) == launch['artifact_sha256'] and artifact.stat().st_size == launch['artifact_bytes'],
            'executed artifact differs from launcher provenance')
    suite, suite_sha = read_report(suite_path, launch['suite_report_sha256'])
    outcomes = validate_report(suite, CASE['tests'], 'prepared', success)
    validate_runtime_limits(suite, INSTRUCTIONS, ALLOCATIONS, required=True)
    require(suite['workers'] == suite['requested_workers'] == SUITE_WORKERS, 'suite worker count differs')
    catalog = Path(launch['entry_catalog_path'])
    require(catalog == Path(str(artifact) + '.entries.json') and not catalog.is_symlink()
            and sha(catalog) == launch['entry_catalog_sha256'], 'entry catalog provenance differs')
    entries = json.loads(catalog.read_bytes())['entries']
    require([e['name'] for e in entries] == CASE['tests']
            and [e['function'] for e in entries] == [t['function'] for t in suite['tests']],
            'entry catalog and suite selection differ')
    require('Checking ' + CASE['package'] in stderr, 'Cargo did not report checking the changed package')
    require(sum(line.startswith('rust-interp-export: ') for line in stderr.splitlines()) == 1,
            'expected one selected test export')
    return launch, outcomes, [artifact, catalog, Path(launch['call_report_path'])], suite_sha


def assessment(rows):
    require(len(rows) == 27 and all(row.get('validated') for row in rows), 'screen is incomplete')
    pairs = []
    for index in range(3, 8):
        selected = {r['mode']: r for r in rows if r['index'] == index}
        require(set(selected) == set(MODES), 'missing edited arm')
        a, b, duplicate = (selected[m] for m in MODES)
        pairs.append(dict(index=index, label=a['label'], source_sha256=a['source_sha256'],
            baseline_seconds=a['seconds'], candidate_seconds=b['seconds'], duplicate_seconds=duplicate['seconds'],
            difference_seconds=b['seconds'] - a['seconds'], aa_difference_seconds=duplicate['seconds'] - a['seconds'],
            wall_ratio=b['seconds'] / a['seconds'], aa_wall_ratio=duplicate['seconds'] / a['seconds'],
            cpu_ratio=b['cpu']['total_seconds'] / a['cpu']['total_seconds'],
            aa_cpu_ratio=duplicate['cpu']['total_seconds'] / a['cpu']['total_seconds']))
    return dict(status='passed', kind='mechanism-screen', final_qualification=False,
        commands=len(rows), edited_pairs=len(pairs), pairs=pairs,
        complete_command_median_seconds={m: statistics.median(r['seconds'] for r in rows
            if r['phase'] == 'edit' and r['mode'] == m) for m in MODES},
        median_paired_wall_ratio=statistics.median(p['wall_ratio'] for p in pairs),
        median_paired_cpu_ratio=statistics.median(p['cpu_ratio'] for p in pairs),
        maximum_aa_wall_deviation=max(abs(p['aa_wall_ratio'] - 1) for p in pairs),
        all_five_screen_commands_below_0_5=all(p['candidate_seconds'] < .5 for p in pairs),
        target_claim='screen only; no final latency or generalization claim',
        whole_session_command_seconds={m: sum(r['seconds'] for r in rows if r['mode'] == m) for m in MODES})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--baseline-tool-key', required=True)
    parser.add_argument('--candidate-tool-key', required=True)
    parser.add_argument('--std-mir-ready', type=Path, required=True)
    parser.add_argument('--lock-wait-seconds', type=lock_wait_seconds, default=45)
    args = parser.parse_args()
    require(__debug__, 'run Python without -O')
    require(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid run ID')
    require(args.baseline_tool_key != args.candidate_tool_key, 'screen requires distinct tool identities')
    source = args.source.absolute()
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    rows, transitions, workspaces = [], [], {}
    changed, original = None, None
    try:
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            acquire_lock(lock, args.lock_wait_seconds)
            require_space(work, MINIMUM_GIB)
            env = environment()
            std = validate_std_ready(args.std_mir_ready, env)
            revision, marker, changed, original = validate_source(source)
            states = protocol_states(original)
            keys = dict(baseline=args.baseline_tool_key, candidate=args.candidate_tool_key,
                        duplicate=args.baseline_tool_key)
            tools = {m: installed_tools(key)[0] for m, key in keys.items()}
            manifests = {m: json.loads((tool / 'ready.json').read_bytes()) for m, tool in tools.items()}
            require(len({proof['rust-interp-vm'] for proof in manifests.values()}) == 1,
                    'compiler-cache screen requires identical VM binaries')
            for mode, tool in tools.items():
                for option in ['entry-catalog', 'function-cache-auto', 'inline-leaves',
                               'trap-unsupported-calls', 'run-try-callbacks']:
                    require_export_option(tool, keys[mode], option)
            require_export_option(tools['candidate'], keys['candidate'], 'query-cache-retention')
            for directory in [work / 'artifacts', work / 'suites', work / 'receipts',
                              *[work / 'caches' / m for m in MODES]]:
                directory.mkdir(parents=True, exist_ok=False)
            paths = [Path(__file__).resolve(), Path(__file__).with_name('PROTOCOL.md'), marker,
                     ROOT / 'benchmarks/corpus.json', Path(std['path'])]
            paths += sorted((ROOT / 'scripts').glob('*.py'))
            paths += [p for tool in set(tools.values()) for p in tool.iterdir() if p.is_file()]
            tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0')
            paths += [source / name for name in tracked if name and source / name != changed]
            frozen = {str(p): frozen_input_hash(p) for p in paths}
            plan = dict(schema_version=1, kind='mechanism-screen', owner=str(ROOT), project='nushell',
                workflow='type-relations', revision=revision, source=str(source), case=CASE,
                original_source_sha256=hashlib.sha256(original).hexdigest(), frozen=frozen, std_mir=std,
                tools=keys, binaries=manifests, cargo_jobs=JOBS, suite_workers=SUITE_WORKERS,
                guest_rustflags=[], profile_overrides={}, instruction_limit=INSTRUCTIONS,
                allocation_limit=ALLOCATIONS, minimum_free_gib=MINIMUM_GIB,
                environment_sha256=hashlib.sha256(json.dumps(env, sort_keys=True).encode()).hexdigest(),
                states=[{k: v for k, v in s.items() if k != 'source'} | {
                    'source_sha256': hashlib.sha256(s['source']).hexdigest()} for s in states],
                timing='wall around capture, including launcher, Cargo, VM, tests and receipt I/O; waited-for child CPU',
                controls='original; wrong production edit; compiled recovery; five new cumulative edits; compiled final restoration',
                final_qualification=False, retry='none; failures retained, no sample replacement')
            write_json(work / 'plan.json', plan)
            previous = dict.fromkeys(MODES)

            def verify_inputs(expected):
                require(changed.read_bytes() == expected and not changed.is_symlink(), 'production source changed')
                require(all(frozen_input_hash(p) == digest for p, digest in frozen.items()), 'frozen source, tool or harness changed')
                require(all(stamp(Path(p)) == proof['stamp'] for p, proof in std['artifacts'].items()),
                        'prepared standard-library artifact changed')
                current = subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0')
                require(current == tracked, 'tracked source inventory changed')
                require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == revision,
                        'source revision changed during screen')

            def snapshot(path):
                require(path.is_file() and not path.is_symlink(), 'missing or linked artifact')
                payload = path.read_bytes()
                digest = hashlib.sha256(payload).hexdigest()
                target = work / 'artifacts' / (digest + path.suffix)
                if target.exists():
                    require(target.read_bytes() == payload, 'artifact snapshot collision')
                else:
                    with target.open('xb') as output:
                        output.write(payload)
                return dict(path=str(target.relative_to(ROOT)), sha256=digest, bytes=len(payload))

            def invoke(mode, sample):
                verify_inputs(sample['source'])
                digest = sha(changed)
                require(previous[mode] != digest, 'unchanged command entered screen')
                command = command_for(mode, keys[mode], source, work, sample)
                suite_path = work / 'suites' / f"{sample['index']}-{mode}.json"
                free = shutil.disk_usage(work).free
                require_space(work, MINIMUM_GIB)
                child, stdout, stderr, elapsed, cpu = measure_command(command, cwd=source, env=env,
                    receipt_path=work / 'receipts' / f"{sample['index']}-{mode}.json",
                    receipt=dict(index=sample['index'], phase=sample['phase'], mode=mode,
                                 source_sha256=digest, tool_key=keys[mode]))
                row = dict(index=sample['index'], phase=sample['phase'], label=sample['label'], mode=mode,
                    command=command, pid=child.pid, seconds=elapsed,
                    cpu=cpu, returncode=child.returncode, stdout=stdout, stderr=stderr,
                    source_sha256=digest, previous_source_sha256=previous[mode], free_bytes=free)
                rows.append(row)
                write_json(work / 'records.json', rows)
                verify_inputs(sample['source'])
                success = sample['phase'] != 'wrong-edit'
                require((child.returncode == 0) == success, 'wrong-edit/passing exit status differs')
                launch, outcomes, artifacts, suite_sha = checked_launch(
                    stderr, mode, keys[mode], success, suite_path, work / 'caches' / mode)
                workspace = launch['workspace_path']
                require(workspaces.get(mode, workspace) == workspace, 'arm workspace changed')
                workspaces[mode] = workspace
                require(len(set(workspaces.values())) == len(workspaces), 'arms share actual Cargo workspace')
                row.update(launch=launch, outcomes=outcomes, suite_sha256=suite_sha,
                           artifacts=[snapshot(p) for p in artifacts], validated=True)
                previous[mode] = digest
                write_json(work / 'records.json', rows)
                print(sample['index'], sample['phase'], mode, f"{row['seconds']:.6f}s", flush=True)
                return row

            def run_state(sample):
                write_json(work / 'transitions.json', transitions)
                selected = {mode: invoke(mode, sample) for mode in sample['modes']}
                require(len({json.dumps(r['outcomes']) for r in selected.values()}) == 1,
                        'test outcomes differ between arms')
                require(len({r['stdout'] for r in selected.values()}) == 1, 'program outputs differ between arms')
                for slot in [0, 1]:
                    require(len({r['artifacts'][slot]['sha256'] for r in selected.values()}) == 1,
                            'executed bytecode or entry catalogs differ between arms')

            with SourceEdit(changed, original) as edit:
                for sample in states[:-1]:
                    transitions.append(dict(index=sample['index'], before=sha(changed),
                        after=hashlib.sha256(sample['source']).hexdigest()))
                    edit.replace(sample['source'])
                    run_state(sample)
            # This compilation is outside SourceEdit: its restored source really
            # is the source left on disk after the context exits.
            transitions.append(dict(index=states[-1]['index'], phase='restoration', after=sha(changed)))
            run_state(states[-1])
            verify_inputs(original)
            summary = assessment(rows)
            summary.update(raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
                records_sha256=sha(work / 'records.json'), source_restored=True, cache_workspaces=workspaces)
            write_json(work / 'summary.json', summary)
    except BaseException as error:
        try:
            restored = changed is not None and original is not None and not changed.is_symlink() and changed.read_bytes() == original
        except OSError:
            restored = False
        failure = dict(status='failed', kind='mechanism-screen', final_qualification=False,
            commands=len(rows), error_type=type(error).__name__, error=str(error), source_restored=restored)
        try:
            write_json(work / 'summary.json', failure)
        except OSError as receipt_error:
            print('Cannot retain failure summary: ' + str(receipt_error), file=sys.stderr)
            print(json.dumps(failure), file=sys.stderr)
        raise


if __name__ == '__main__':
    main()
