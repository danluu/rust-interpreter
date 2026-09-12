#!/usr/bin/env python3
"""Native control calibration on real edits; original commands remain primary."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time

from native_results import libtest_summary, residual_seconds

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from workflow_controls import native_command, native_environment
from workflow_cases import WORKFLOW_VARIANTS
from workflow_io import SourceEdit, capture, require_space, write_json as write
from workflow_measurements import source_states, child_usage, child_cpu_since

PRESETS = ['repository', 'line-tables-only', 'none']
TOOLCHAIN = 'nightly-2026-09-08'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def environment(preset):
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or name in [
            'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
            'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR',
            'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR', 'RUST_TEST_THREADS']:
            env.pop(name)
    env = native_environment(env, 'o0-incremental', [])
    env['CARGO_TERM_COLOR'] = 'never'
    for profile in ['DEV', 'TEST']:
        env[f'CARGO_PROFILE_{profile}_BUILD_OVERRIDE_OPT_LEVEL'] = '0'
        if preset != 'repository':
            env[f'CARGO_PROFILE_{profile}_DEBUG'] = '0' if preset == 'none' else preset
            env[f'CARGO_PROFILE_{profile}_SPLIT_DEBUGINFO'] = 'unpacked'
    return env


def choose(samples):
    """Calibration uses edits 1–3; later samples cannot enter this decision."""
    rows = {(r['preset'], r['state']): r for r in samples if 1 <= r['state'] <= 3}
    require(len(rows) == 9, 'incomplete calibration')
    ratios = {p: statistics.median(rows[p, s]['seconds'] / rows['repository', s]['seconds']
                                  for s in [1, 2, 3]) for p in PRESETS[1:]}
    eligible = [p for p in PRESETS[1:] if ratios[p] <= .92]
    selected = min(eligible, key=lambda p: ratios[p]) if eligible else None
    if selected and 'line-tables-only' in eligible and ratios['line-tables-only'] <= ratios[selected] * 1.03:
        selected = 'line-tables-only'
    return dict(selected=selected, paired_median_wall_ratios=ratios,
                minimum_improvement=.08, line_preference_tolerance=.03,
                calibration_states=[1, 2, 3], confirmation_states=[4, 5])


def invoke(work, label, command, source, env):
    require_space(ROOT, 8)
    usage = child_usage()
    start = time.perf_counter()
    child, stdout, stderr = capture(command, cwd=source, env=env,
        receipt_path=work / 'child.json', receipt=dict(label=label))
    seconds = time.perf_counter() - start
    cpu = child_cpu_since(usage)
    row = dict(label=label, command=command, pid=child.pid, parent_pid=os.getpid(),
               seconds=seconds, cpu=cpu, returncode=child.returncode, load=os.getloadavg())
    for stream, contents in [('stdout', stdout), ('stderr', stderr)]:
        path = work / (label + '.' + stream)
        path.write_text(contents)
        row[stream] = str(path.relative_to(ROOT))
        row[stream + '_sha256'] = sha(path)
    return row, stdout, stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'native-tuned-calibration-\d{2}', args.run_id), 'invalid run id')
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
    write(work / 'status.json', status)
    try:
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            source = ROOT / '.work/sources/fre'
            case = WORKFLOW_VARIANTS['fre', 'token-phrase-allocation']
            marker = read(source / '.rust-interp-owned.json')
            pin = read(ROOT / 'benchmarks/corpus.json')['projects']['fre']['revision']
            require(marker['owner'] == str(ROOT) and marker['revision'] == pin, 'source ownership differs')
            require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == pin and
                not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(), 'source pin changed')
            reference_path = ROOT / 'results/parked-budget-e2e-token-phrase-native-archive-01/plan.json'
            reference_size = sum(g['bytes'] for g in read(reference_path)['manifest']['groups'])
            needed = 8 * 1024**3 + 16 * 1024**2 + (reference_size * 3 * 120 + 99) // 100
            free = shutil.disk_usage(ROOT).free
            write(work / 'admission.json', dict(required=needed, observed=free,
                historical_unique_cache_bytes=reference_size, reference_sha256=sha(reference_path)))
            require(free >= needed, 'three fresh targets do not fit; no source edit started')
            paths = [Path(__file__), HERE / 'PLAN.md', HERE / 'native_results.py',
                ROOT / 'scripts/workflow_controls.py', ROOT / 'scripts/workflow_cases.py',
                ROOT / 'scripts/workflow_io.py', ROOT / 'scripts/workflow_measurements.py',
                ROOT / 'benchmarks/corpus.json', ROOT / 'results/native-effective-profiles-02/summary.json']
            frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
            profiles = next(p['profiles'] for p in read(paths[-1])['projects'] if p['project'] == 'fre')
            envs = {p: environment(p) for p in PRESETS}
            write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, source_pin=pin,
                presets=PRESETS, jobs=18, test_threads='default', profiles=profiles,
                environment_overrides={p: {k: v for k, v in env.items() if k.startswith('CARGO_PROFILE_')}
                                       for p, env in envs.items()},
                source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()))
            for preset in PRESETS:
                command = native_command(TOOLCHAIN, source / 'Cargo.toml', case['package'],
                    work / preset, 18, 'default', [])
                command = command[:command.index('--')] + ['--no-run', '--unit-graph', '-Z', 'unstable-options']
                record, stdout, _ = invoke(work, 'profile-' + preset, command, source, envs[preset])
                require(record['returncode'] == 0, 'effective profile query failed')
                graph = json.loads(stdout)
                require(len(graph['roots']) == 1, 'unexpected Cargo roots')
                require(graph['units'][graph['roots'][0]]['profile'] == profiles[preset], 'effective native profile changed')
            file = source / case['file']
            original = file.read_bytes()
            samples = list(source_states(original.decode(), case, 1, PRESETS, True))
            require(len(samples) == 7, 'expected five real edits')
            (work / 'original.rs').write_bytes(original)
            records = []
            previous = {p: None for p in PRESETS}
            decision = None
            status.update(status='running')
            write(work / 'status.json', status)
            with SourceEdit(file, original) as edit:
                for sample in samples:
                    edit.replace(sample['source'])
                    digest = sha(file)
                    for preset in sample['modes']:
                        require(previous[preset] != digest, 'unchanged source is not an edit benchmark')
                        label = f"state-{sample['state']}-{preset}"
                        command = native_command(TOOLCHAIN, source / 'Cargo.toml', case['package'],
                            work / preset, 18, 'default', case['tests'])
                        row, stdout, stderr = invoke(work, label, command, source, envs[preset])
                        row.update(preset=preset, state=sample['state'], phase=sample['phase'],
                            source_sha256=digest, previous_source_sha256=previous[preset])
                        success = sample['state'] != -1
                        records.append(row)
                        write(work / 'records.json', records)
                        require((row['returncode'] == 0) == success, 'original assertion outcome differs')
                        suite = libtest_summary(stdout, selected=len(case['tests']), success=success)
                        require('Compiling ' + case['package'] in stderr, 'edited crate did not compile')
                        row.update(suite=suite, non_suite_seconds=residual_seconds(row['seconds'], suite))
                        build = re.findall(r'^\s*Finished `test` profile .* in ([0-9.]+)s\s*$', stderr, re.M)
                        require(len(build) == 1, 'missing Cargo build duration')
                        row['cargo_reported_build_seconds'] = float(build[0])
                        if sample['state'] > 0:
                            binaries = re.findall(r'^\s*Running unittests .* \((.*)\)\s*$', stderr, re.M)
                            require(len(binaries) == 1, 'expected one library test executable')
                            binary = Path(binaries[0])
                            require(binary.is_file() and binary.resolve().is_relative_to(work / preset), 'executable outside owned Cargo target')
                            repeat, repeat_out, _ = invoke(work, label + '-repeat',
                                [str(binary), '--exact', *case['tests']], source, envs[preset])
                            require(repeat['returncode'] == 0, 'diagnostic repeat failed')
                            repeat['suite'] = libtest_summary(repeat_out, selected=len(case['tests']))
                            repeat['binary_sha256'] = sha(binary)
                            row['diagnostic_repeat'] = repeat
                        previous[preset] = digest
                        write(work / 'records.json', records)
                        print(preset, sample['state'], round(row['seconds'], 3), flush=True)
                    if sample['state'] == 3:
                        decision = choose(records)
                        write(work / 'calibration.json', decision)
                        print('calibration', decision, flush=True)
            require(file.read_bytes() == original and not subprocess.check_output(
                ['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(), 'source restoration differs')
            require(all(sha(ROOT / p) == h for p, h in frozen.items()), 'frozen experiment inputs changed')
            require(len(records) == 21 and sum('diagnostic_repeat' in r for r in records) == 15, 'incomplete native history')
            selected = decision['selected']
            index = {(r['preset'], r['state']): r for r in records}
            confirmation = [dict(state=s, wall_ratio=index[selected, s]['seconds'] / index['repository', s]['seconds'],
                cpu_ratio=index[selected, s]['cpu']['total_seconds'] / index['repository', s]['cpu']['total_seconds'])
                for s in [4, 5]] if selected else []
            confirmed = bool(confirmation) and all(p['wall_ratio'] < 1 for p in confirmation) and statistics.median(p['wall_ratio'] for p in confirmation) <= .95
            decision.update(confirmation=confirmation, status='confirmed-for-next-workflows' if confirmed else 'inconclusive')
            out = ROOT / 'results' / args.run_id
            out.mkdir(exist_ok=False)
            medians = {}
            for p in PRESETS:
                rows = [r for r in records if r['preset'] == p and r['state'] > 0]
                medians[p] = dict(command=statistics.median(r['seconds'] for r in rows),
                    cpu=statistics.median(r['cpu']['total_seconds'] for r in rows),
                    cargo_reported_build=statistics.median(r['cargo_reported_build_seconds'] for r in rows),
                    suite_rounded=statistics.median(r['suite']['rounded_seconds'] for r in rows),
                    repeated_process=statistics.median(r['diagnostic_repeat']['seconds'] for r in rows))
            write(out / 'summary.json', dict(status='passed', raw=str(work.relative_to(ROOT)),
                records_sha256=sha(work / 'records.json'), plan_sha256=sha(work / 'plan.json'),
                source_restored=True, original_assertions=True, wrong_edits_rejected=3,
                complete_cargo_commands=21, edited_cargo_commands=15, diagnostic_repeats=15,
                median_seconds=medians, cold_seconds={p: index[p, 0]['seconds'] for p in PRESETS},
                decision=decision, profiles=profiles,
                note='Choice frozen after edits 1–3. Edits 4–5 are confirmation. Diagnostic binary repeats are separate executions, never subtracted from primary Cargo commands. This calibrates a native control, not a custom-engine comparison.'))
            status.update(status='finished', returncode=0, finished_at=time.time())
            write(work / 'status.json', status)
            print(decision, flush=True)
    except BaseException as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(work / 'status.json', status)
        raise


if __name__ == '__main__':
    main()
