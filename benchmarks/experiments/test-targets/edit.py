#!/usr/bin/env python3
"""Real library edits through an integration target, with native/check controls."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/tuned-native'))
from timing import environment, invoke, read, require, sha
from native_results import libtest_summary
from workflow_io import SourceEdit, write_json as write
from workflow_measurements import mode_order

def end_greedy_edits(original):
    text = original.decode()
    begin = text.index('    pub fn end_greedy_class_literal_prospective(')
    end = text.index('    /// Transactionally retain the suffix', begin)
    body = text[begin:end]
    changes = [
        ('swap-pure-empty-checks', 'if class.is_empty() || suffix_bytes == 0 {', 'if suffix_bytes == 0 || class.is_empty() {'),
        ('commute-checked-items', 'let items = suffix_bytes.checked_add(1)', 'let items = 1usize.checked_add(suffix_bytes)'),
        ('commute-checked-payload', 'let payload_bytes = suffix_bytes\n            .checked_add(size_of::<ByteMask>())',
         'let payload_bytes = size_of::<ByteMask>()\n            .checked_add(suffix_bytes)'),
        ('commute-checked-work', '.and_then(|work| work.checked_add(1))', '.and_then(|work| 1usize.checked_add(work))'),
        ('infer-checked-conversion', '.and_then(|work| u64::try_from(work).ok())', '.and_then(|work| work.try_into().ok())'),
    ]
    combine = lambda b: (text[:begin] + b + text[end:]).encode()
    wrong = body.replace('suffix_bytes == 0', 'suffix_bytes != 0')
    require(wrong != body and body.count('suffix_bytes == 0') == 1, 'negative edit is ambiguous')
    states = [(0, 'warm-anchor', original), (-1, 'reject-valid-nonempty-suffix', combine(wrong))]
    for index, (label, before, after) in enumerate(changes, 1):
        require(body.count(before) == 1, 'production edit is ambiguous: ' + label)
        body = body.replace(before, after)
        states.append((index, label, combine(body)))
    require(len({payload for _, _, payload in states}) == 7, 'source states are not distinct')
    return states


def es8_edits(original):
    text = original.decode()
    begin = text.index('    fn preflight_with_run_scanner(')
    end = text.index('\nimpl DispatchedForwardAnchoredPlan', begin)
    body = text[begin:end]
    changes = [
        ('reverse-prefilter-comparison', 'let uses_prefilter = window_bytes >= RANGE_BLOCK;',
         'let uses_prefilter = RANGE_BLOCK <= window_bytes;'),
        ('swap-pure-scanner-checks', 'if bitset_scanner.is_some() && window_bytes != 0 {',
         'if window_bytes != 0 && bitset_scanner.is_some() {'),
        ('commute-prefix-bound', 'window_bytes\n                .checked_add(rescan_margin)',
         'rescan_margin\n                .checked_add(window_bytes)'),
        ('commute-suffix-minimum', 'self.suffix.len().min(window_bytes)',
         'window_bytes.min(self.suffix.len())'),
        ('commute-examined-bound', 'prefilter_bytes_upper_bound\n            .checked_add(prefix_bytes_upper_bound)',
         'prefix_bytes_upper_bound\n            .checked_add(prefilter_bytes_upper_bound)'),
    ]
    combine = lambda b: (text[:begin] + b + text[end:]).encode()
    require(body.count('window_bytes.saturating_sub(1)') == 1, 'negative edit is ambiguous')
    states = [(0, 'warm-anchor', original), (-1, 'underreport-prefilter-bound',
              combine(body.replace('window_bytes.saturating_sub(1)', 'window_bytes.saturating_sub(2)')))]
    for index, (label, before, after) in enumerate(changes, 1):
        require(body.count(before) == 1, 'production edit is ambiguous: ' + label)
        body = body.replace(before, after)
        states.append((index, label, combine(body)))
    require(len({payload for _, _, payload in states}) == 7, 'source states are not distinct')
    return states


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['end-greedy', 'es8'], default='end-greedy')
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'fre-integration-[a-z0-9-]+-\d{2}', args.run_id), 'invalid run id')
    target, source_name, make_edits = {
        'end-greedy': ('end_greedy_class_literal', 'fixed_absolute_domain.rs', end_greedy_edits),
        'es8': ('es8i_semantic_proof', 'forward_anchored.rs', es8_edits),
    }[args.case]
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    (work / 'artifacts').mkdir()
    status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
    write(work / 'status.json', status)
    try:
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            coverage = read(ROOT / 'results/fre-integration-targets-02/summary.json')
            require(coverage['status'] == 'passed' and coverage['original_tests_passed'] == 52 and
                read(ROOT / '.work/experiments/fre-integration-targets-02/status.json')['status'] == 'finished', 'coverage not complete')
            source = ROOT / '.work/sources/fre'
            marker = read(source / '.rust-interp-owned.json')
            require(marker['owner'] == str(ROOT) and marker['revision'] == read(ROOT / 'benchmarks/corpus.json')['projects']['fre']['revision'], 'source pin differs')
            require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == marker['revision'] and not
                subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(), 'source changed')
            file = source / 'crates/fre-kernels/src' / source_name
            original = file.read_bytes()
            states = make_edits(original)
            (work / 'original.rs').write_bytes(original)
            test_source = source / 'crates/fre-kernels/tests' / (target + '.rs')
            native_target = ROOT / '.work/native-tuned-calibration-01/repository'
            check_run = ROOT / '.work/runs/aggregate-relocation-e2e-01-token-phrase'
            check_target = check_run / 'check'
            require(check_target.is_dir() and read(check_run / 'active-command.json')['status'] == 'finished', 'check cache unavailable')
            require(all(Path(r['command'][r['command'].index('--target-dir') + 1]) == check_target for r in read(check_run / 'check-records.json')), 'check-cache provenance differs')
            require(shutil.disk_usage(ROOT).free >= 8 * 1024**3 + 512 * 1024**2, 'edit/priming growth margin unavailable')
            previous = next(r for r in read(ROOT / coverage['raw'] / 'records.json') if r['target'] == target)
            native = previous['native']['command']
            require(native[native.index('--target-dir') + 1] == str(native_target), 'native cache changed')
            custom = previous['custom']['command']
            custom[1] = str(ROOT / 'scripts/interpreter.py')
            check = ['cargo', '+nightly-2026-09-08', 'check', '--manifest-path', str(source / 'Cargo.toml'), '--package', 'fre-kernels',
                '--test', target, '--profile', 'test', '--locked', '--offline', '--jobs', '18', '--target-dir', str(check_target)]
            env = environment('repository')
            guest_env = dict(env, RUST_INTERP_LAUNCH_STATS='1', RUSTFLAGS='-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240')
            commands = dict(native=native, custom=custom, check=check)
            paths = [Path(__file__), HERE / ('ES8.md' if args.case == 'es8' else 'EDIT.md'), ROOT / 'scripts/interpreter.py',
                test_source, ROOT / 'results/fre-integration-targets-02/summary.json', ROOT / 'scripts/workflow_io.py',
                ROOT / 'scripts/workflow_measurements.py', ROOT / 'scripts/workflow_controls.py', ROOT / 'benchmarks/experiments/tuned-native/timing.py']
            frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
            source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
            write(work / 'plan.json', dict(owner=str(ROOT), source_commit=source_commit, tool_key=coverage['tool_key'],
                source_pin=marker['revision'], frozen=frozen, commands=commands, source_states=[dict(state=s, label=l) for s, l, _ in states],
                jobs=18, native_test_threads='default', warm_reused_caches=True, case=args.case, target=target,
                pilot_target_wall_ratio=.90, note='Five real production edits; original assertions unchanged. Anchor excluded. CPU reported. No retention decision from this one-cycle pilot.'))
            records = []
            status.update(status='running')
            write(work / 'status.json', status)
            def run_state(state, label):
                digest = sha(file)
                for mode in mode_order(['native', 'custom', 'check'], 0, 6 if state == 'restored' else state, True):
                    row, stdout, stderr = invoke(work, str(state) + '-' + mode, commands[mode], source, guest_env if mode == 'custom' else env)
                    row.update(state=state, mode=mode, edit=label, source_sha256=digest)
                    records.append(row)
                    write(work / 'records.json', records)
                    success = state != -1 or mode == 'check'
                    require((row['returncode'] == 0) == success, 'unexpected assertion outcome: ' + str(state) + '/' + mode)
                    if mode == 'native':
                        row['suite'] = libtest_summary(stdout, selected=previous['tests'], success=success)
                    elif mode == 'custom':
                        require((stdout.strip() == '0') == success, 'unexpected VM result')
                        launches = [json.loads(line.split(': ', 1)[1]) for line in stderr.splitlines() if line.startswith('rust-interp-launch: ')]
                        require(len(launches) == 1, 'missing custom stage/identity record')
                        row['launch'] = launches[0]
                        artifact = Path(row['launch']['artifact_path'])
                        snapshot = work / 'artifacts' / (str(state) + '.rbc')
                        require(sha(artifact) == row['launch']['artifact_sha256'], 'executed bytecode changed')
                        subprocess.run(['cp', '-c', str(artifact), str(snapshot)], check=True)
                        require(sha(snapshot) == row['launch']['artifact_sha256'], 'snapshot differs')
                        row['snapshot'] = str(snapshot.relative_to(ROOT))
                    if state != 0:
                        require(('Compiling ' if mode == 'native' else 'Checking ') + 'fre-kernels' in stderr, 'production edit was not rebuilt')
                    write(work / 'records.json', records)
                    print(state, mode, round(row['seconds'], 3), flush=True)
            with SourceEdit(file, original) as edit:
                for state, label, payload in states:
                    edit.replace(payload)
                    run_state(state, label)
            require(file.read_bytes() == original and not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(), 'source restoration differs')
            run_state('restored', 'original-after-restoration')
            require(all(sha(ROOT / p) == h for p, h in frozen.items()), 'experiment inputs changed')
            require(len(records) == 24, 'incomplete edit history and restoration controls')
            index = {(r['mode'], r['state']): r for r in records}
            pairs = [dict(state=s, wall_ratio=index['custom', s]['seconds'] / index['native', s]['seconds'],
                cpu_ratio=index['custom', s]['cpu']['total_seconds'] / index['native', s]['cpu']['total_seconds']) for s in range(1, 6)]
            medians = {m: statistics.median(index[m, s]['seconds'] for s in range(1, 6)) for m in commands}
            out = ROOT / 'results' / args.run_id
            out.mkdir(exist_ok=False)
            write(out / 'summary.json', dict(status='passed', raw=str(work.relative_to(ROOT)), source_commit=source_commit,
                tool_key=coverage['tool_key'], commands=24, edited_pairs=5, artifacts=8, source_restored=True,
                case=args.case, target=target, tests=previous['tests'], restoration_recompiled_all_modes=True,
                original_assertions_passed=True, wrong_edit_rejected_by_native_and_custom=True, check_accepts_well_typed_wrong_logic=True,
                median_seconds=medians, pairs=pairs, paired_median_wall_ratio=statistics.median(p['wall_ratio'] for p in pairs),
                paired_median_cpu_ratio=statistics.median(p['cpu_ratio'] for p in pairs),
                pilot_target_met=statistics.median(p['wall_ratio'] for p in pairs) <= .90,
                records_sha256=sha(work / 'records.json'), frozen=frozen,
                note='Actual production-library edits through one integration target. Five edited pairs, warm primed/reused caches, 18 jobs, native repository debuginfo/O0/incremental/default threads. Pilot only; no cold or whole-suite claim.'))
            status.update(status='finished', returncode=0, finished_at=time.time())
            write(work / 'status.json', status)
    except BaseException as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(work / 'status.json', status)
        raise


if __name__ == '__main__':
    main()
