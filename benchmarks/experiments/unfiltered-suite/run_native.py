#!/usr/bin/env python3
"""First actual unfiltered native command and a historical body-coverage join."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/tuned-native'))
from timing import environment, invoke, read, require, sha
from native_results import SUMMARY, libtest_summary
from workflow_io import SourceEdit, write_json as write
from workflow_measurements import source_states
from workflow_cases import WORKFLOW_VARIANTS

RUN = 'fre-unfiltered-native-01'


def main():
    work = ROOT / '.work' / RUN
    work.mkdir(exist_ok=False)
    status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
    write(work / 'status.json', status)
    try:
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            calibration = ROOT / '.work/native-tuned-calibration-01'
            terminal = read(calibration / 'status.json')
            require(terminal['status'] == 'finished' and terminal['returncode'] == 0, 'native target still active')
            target = calibration / 'repository'
            old_plan = read(calibration / 'plan.json')
            require(old_plan['owner'] == str(ROOT) and target.is_dir(), 'native cache ownership differs')
            require(shutil.disk_usage(ROOT).free >= 8 * 1024**3 + 256 * 1024**2, 'native library growth margin unavailable')
            source = ROOT / '.work/sources/fre'
            marker = read(source / '.rust-interp-owned.json')
            require(marker['owner'] == str(ROOT) and marker['revision'] == old_plan['source_pin'], 'source ownership changed')
            require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == marker['revision'] and
                not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(), 'source changed')
            case = WORKFLOW_VARIANTS['fre', 'token-phrase-allocation']
            file = source / case['file']
            original = file.read_bytes()
            samples = list(source_states(original.decode(), case, 1, ['a', 'b', 'c'], True))[:3]
            (work / 'original.rs').write_bytes(original)
            command = ['cargo', '+nightly-2026-09-08', 'test', '--manifest-path', str(source / 'Cargo.toml'),
                       '--package', 'fre-kernels', '--locked', '--offline', '--jobs', '18', '--target-dir', str(target)]
            inputs = [Path(__file__), Path(__file__).with_name('PLAN.md'),
                ROOT / 'benchmarks/experiments/tuned-native/timing.py', ROOT / 'benchmarks/experiments/tuned-native/native_results.py',
                ROOT / 'scripts/workflow_io.py', ROOT / 'scripts/workflow_measurements.py', ROOT / 'scripts/workflow_cases.py',
                ROOT / 'scripts/workflow_controls.py',
                calibration / 'plan.json', ROOT / 'results/aggregate-relocation-fre-01/summary.json']
            frozen = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
            write(work / 'plan.json', dict(owner=str(ROOT), source_pin=marker['revision'], frozen=frozen,
                command=command, source_states=[s['state'] for s in samples], warm_reused_cache=True,
                source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()))
            records = []
            status.update(status='running')
            write(work / 'status.json', status)
            with SourceEdit(file, original) as edit:
                for sample in samples:
                    edit.replace(sample['source'])
                    row, stdout, stderr = invoke(work, 'state-' + str(sample['state']), command, source, environment('repository'))
                    row.update(state=sample['state'], phase='warm-anchor' if sample['state'] == 0 else sample['phase'], source_sha256=sha(file))
                    records.append(row)
                    write(work / 'records.json', records)
                    success = sample['state'] != -1
                    require((row['returncode'] == 0) == success, 'unfiltered command assertion outcome differs')
                    summaries = [libtest_summary(m.group(0), success=success) for m in SUMMARY.finditer(stdout)]
                    require(summaries, 'no full native test summaries')
                    require(all(s['filtered'] == 0 for s in summaries), 'native test filtering appeared')
                    unit_names = re.findall(r'^test (\S+) \.\.\. (ok|FAILED|ignored)(?:,.*)?$', stdout, re.M)
                    require(unit_names and len({name for name, _ in unit_names}) == len(unit_names), 'ambiguous native unit inventory')
                    require('Compiling fre-kernels' in stderr, 'changed native package did not compile')
                    row.update(summaries=summaries, unit_outcomes=dict(unit_names))
                    write(work / 'records.json', records)
                    print(sample['state'], round(row['seconds'], 3), summaries, flush=True)
            require(file.read_bytes() == original and not subprocess.check_output(
                ['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(), 'source restoration differs')
            history = read(inputs[-1])
            require(history['status'] == 'passed' and history['revision'] == marker['revision'], 'historical replay provenance differs')
            bodies = {}
            for batch in history['records']:
                replay = read(ROOT / batch['replay'])
                path = ROOT / replay['raw'] / 'results.json'
                require(sha(path) == batch['evidence'][str(path.relative_to(ROOT))], 'historical outcomes changed')
                for r in read(path):
                    require(r['entry'] not in bodies, 'duplicate historical body')
                    bodies[r['entry']] = r['status']
            native_names = records[0]['unit_outcomes']
            joined = dict(native_only=sorted(set(native_names) - set(bodies)), custom_only=sorted(set(bodies) - set(native_names)),
                historical_custom_ignored=[n for n, outcome in bodies.items() if outcome == 'ignored'],
                historical_custom_unsupported={n: outcome for n, outcome in bodies.items() if outcome not in ['passed', 'ignored']})
            write(work / 'coverage.json', dict(native_original=native_names, historical_custom=bodies, **joined))
            require(all(sha(ROOT / p) == h for p, h in frozen.items()), 'experiment inputs changed')
            out = ROOT / 'results' / RUN
            out.mkdir(exist_ok=False)
            write(out / 'summary.json', dict(status='passed', raw=str(work.relative_to(ROOT)),
                records_sha256=sha(work / 'records.json'), coverage_sha256=sha(work / 'coverage.json'),
                native_commands=3, source_restored=True, original_tests_unchanged=True,
                original=records[0]['summaries'], wrong_edit=records[1]['summaries'], real_edit=records[2]['summaries'],
                real_edit_command_seconds=records[2]['seconds'], real_edit_cpu=records[2]['cpu'],
                warm_anchor_seconds=records[0]['seconds'],
                historical_custom=dict(report=str(inputs[-1].relative_to(ROOT)), tool_key=history['tool_key'], counts=history['counts']),
                inventory_difference=joined,
                note='Actual unfiltered Cargo command, including default doc tests. Reused native cache; initial source restoration is a warm anchor. Custom coverage is historical body evidence, not an edited custom suite timing or libtest qualification.'))
            status.update(status='finished', returncode=0, finished_at=time.time())
            write(work / 'status.json', status)
    except BaseException as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(work / 'status.json', status)
        raise


if __name__ == '__main__':
    main()
