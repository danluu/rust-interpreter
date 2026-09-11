#!/usr/bin/env python3
"""Verify repeated edit measurements; output only counts and hashes, including for private cases."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import time

from workflow_measurements import initial_modes, mode_order
from workflow_jobs import recorded_build_jobs, verify_command_jobs

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read(path):
    return json.loads(path.read_text())


def verify(report, reference=None):
    require(report['schema_version'] == 2, 'unsupported workflow schema')
    job_counts = (recorded_build_jobs(report)
                  if 'build_jobs' in report and 'native_control' in report else None)
    require('custom_build_jobs' not in report or job_counts is not None,
            'custom worker receipt lacks shared/native controls')
    rows = read(ROOT / report['raw'] / 'records.json')
    if 'case_file' in report:
        from workflow_case_file import verify_snapshot
        verify_snapshot(ROOT, report, rows)
    transitions = read(ROOT / report['raw'] / 'source-transitions.json')
    cycles = report['cycles']
    edits = len(report['edits'])
    states = [0, -1, *range(1, edits + 1)]
    custom_modes = ['baseline', 'candidate'] if 'comparison' in report else ['interpreter', 'jit']
    modes = ['native', *custom_modes]
    scheduled_modes = initial_modes(modes, report.get('initial_mode_order'))
    expected_orders = [dict(cycle=c, state=s,
        phase=('cold' if c == 0 else 'anchor') if s == 0 else ('wrong-edit' if s == -1 else 'edit'),
        modes=mode_order(scheduled_modes, c, s, 'comparison' in report))
        for c in range(cycles) for s in states]
    require(report['mode_orders'] == expected_orders, 'recorded mode schedule differs')
    require([(r['cycle'], r['state'], r['mode']) for r in rows] ==
        [(o['cycle'], o['state'], m) for o in expected_orders for m in o['modes']], 'command order differs from schedule')
    expected = {(c, s, m) for c in range(cycles) for s in states for m in modes}
    actual = [(r['cycle'], r['state'], r['mode']) for r in rows]
    require(len(set(actual)) == len(actual) and set(actual) == expected, 'missing or duplicate samples')
    require(report['test_source_unchanged'] and report['wrong_production_edit_rejected'], 'source/test controls failed')
    require(len(transitions) == cycles * len(states), 'missing source transitions')
    require(all(t['content_changed'] for t in transitions if t['phase'] != 'cold'), 'unchanged warm sample')
    previous = dict.fromkeys(modes)
    artifacts = {}
    paths = set()
    for row in rows:
        cycle, state, mode = row['cycle'], row['state'], row['mode']
        phase = ('cold' if cycle == 0 else 'anchor') if state == 0 else ('wrong-edit' if state == -1 else 'edit')
        require(row['phase'] == phase, 'incorrect cold/anchor/edit label')
        require(row['previous_source_sha256'] == previous[mode], 'source history mismatch')
        if phase != 'cold':
            require(previous[mode] != row['source_sha256'], 'mode rebuilt unchanged source')
        previous[mode] = row['source_sha256']
        require(row['seconds'] > 0 and row['cpu_seconds'] > 0, 'invalid timing')
        cpu = sum(c['cpu']['user_seconds'] + c['cpu']['system_seconds'] for c in row['calls'])
        require(abs(cpu - row['cpu_seconds']) < 1e-8, 'CPU total does not match child calls')
        require(all((c['returncode'] == 0) == (state != -1) for c in row['calls']), 'unexpected command result')
        if job_counts is not None:
            for call in row['calls']:
                verify_command_jobs(call['command'], job_counts[mode])
        if mode != 'native':
            settings = report.get('tool_builds', {}).get(mode, {})
            for field, flag in [('jit_native_calls', '--jit-native-calls'),
                                ('jit_native_call_stubs', '--jit-native-call-stubs'),
                                ('jit_persistent_registers', '--jit-persistent-registers'),
                                ('jit_resumable_calls', '--jit-resumable-calls')]:
                if field in settings:
                    for call in row['calls']:
                        require((flag in call['command']) == settings[field], 'recorded runtime option differs')
                        require(call['launch'].get(field, False) == settings[field], 'launched runtime option differs')
            require(len(row['artifacts']) == 1, 'expected one batched artifact')
            artifact = row['artifacts'][0]
            path = artifact['path']
            require(path not in paths, 'repeated artifact path was overwritten')
            paths.add(path)
            digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            require(digest == artifact['sha256'], 'artifact hash mismatch')
            artifacts[cycle, state, mode] = digest
    for c in range(cycles):
        for s in states:
            selected = [r for r in rows if r['cycle'] == c and r['state'] == s]
            require(len({r['source_sha256'] for r in selected}) == 1, 'paired sources differ')
            require(all(r['tests'] == selected[0]['tests'] for r in selected), 'paired test selections differ')
            require(artifacts[c, s, custom_modes[0]] == artifacts[c, s, custom_modes[1]], 'paired bytecode differs')
    for s in states:
        require(len({r['source_sha256'] for r in rows if r['state'] == s}) == 1, 'repeated source state differs')
    if cycles == 3:
        for s in range(1, edits + 1):
            orders = [o['modes'] for o in report['mode_orders'] if o['state'] == s]
            for m in modes:
                require(sorted(o.index(m) for o in orders) == [0, 1, 2], 'unbalanced mode positions')
    if 'comparison' in report:
        require(len(report['comparison']['pairs']) == cycles * edits, 'missing edited pairs')
    require(len(report['cycle_anchor_seconds']) == cycles - 1, 'incorrect anchor count')
    require(report['cold_success_seconds'] == {r['mode']: r['seconds'] for r in rows if r['phase'] == 'cold'}, 'cold results contain warm anchors')
    cross_cycle = [{"state": s, "sha256_by_cycle": [artifacts[c, s, custom_modes[1]] for c in range(cycles)]} for s in states]
    check_count = 0
    if report.get('check_floor') is not None:
        checks = read(ROOT / report['raw'] / 'check-records.json')
        keys = [(c['cycle'], c['state']) for c in checks]
        require(len(set(keys)) == len(keys) and set(keys) == {(c, s) for c in range(cycles) for s in states}, 'missing/duplicate check controls')
        check_count = len(checks)
        control = report['native_control']
        encoded = '\x1f'.join(control['rustflags']) or None
        previous = None
        for check in checks:
            group = [r for r in rows if r['cycle'] == check['cycle'] and r['state'] == check['state']]
            require(check['returncode'] == 0 and all(r['source_sha256'] == check['source_sha256'] for r in group), 'check/source mismatch')
            require(check['previous_source_sha256'] == previous, 'check source history mismatch')
            if check['phase'] != 'cold':
                require(previous != check['source_sha256'], 'unchanged check control')
            previous = check['source_sha256']
            require(check['phase'] == group[0]['phase'], 'check phase mismatch')
            require(check['seconds'] > 0 and check['cpu_seconds'] > 0 and abs(check['cpu_seconds'] - check['cpu']['total_seconds']) < 1e-8, 'invalid check timing')
            command = check['command']
            require(command[2] == 'check' and '--profile' in command and command[command.index('--profile') + 1] == 'test' and '--' not in command, 'check did not select the non-executing test target')
            verify_command_jobs(command, control['jobs'])
            require('test result:' not in check['stdout'], 'check unexpectedly executed tests')
        for row in rows:
            for call in row['calls']:
                require(call.get('encoded_rustflags') == (encoded if row['mode'] == 'native' else None), 'native flags missing or leaked to custom engines')
                command = call['command']
                if row['mode'] == 'native':
                    actual = [a for a in command if a.startswith('--test-threads=')]
                    expected = [] if control['test_threads'] == 'default' else ['--test-threads=' + control['test_threads']]
                    require(actual == expected, 'test concurrency differs')
    history = None
    if reference:
        old = read(ROOT / reference['raw'] / 'records.json')
        require(report['case_sha256'] == reference['case_sha256'], 'reference case differs')
        comparisons = []
        for row in rows:
            matching = [r for r in old if r['state'] == row['state'] and r['mode'] == row['mode']]
            require(len(matching) == 1, 'reference must contain one cycle')
            prior = matching[0]
            require(prior['source_sha256'] == row['source_sha256'] and prior['tests'] == row['tests'], 'reference source/tests differ')
            if row['mode'] != 'native':
                comparisons.append(artifacts[row['cycle'], row['state'], row['mode']] == prior['artifacts'][0]['sha256'])
        history = dict(identical=sum(comparisons), different=len(comparisons) - sum(comparisons))
    return dict(schema_version=1, measurement_controls_verified=True,
        commands=len(rows), cycles=cycles, edited_pairs=cycles * edits,
        check_commands=check_count, explicit_controls_verified=bool(check_count),
        exact_artifact_hashes_verified=len(paths), paired_bytecode_identical=True,
        cross_cycle_bytecode_identical=all(len(set(x['sha256_by_cycle'])) == 1 for x in cross_cycle),
        cross_cycle_artifacts=cross_cycle, reference_bytecode=history,
        cross_cycle_semantic_equivalence_proven=False,
        note='Control verification does not imply identical compilation across cache histories or a performance claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--wait-for-lock', type=int, default=0, help='wait up to this many seconds for other task work to finish')
    args = parser.parse_args()
    if not 0 <= args.wait_for_lock <= 3600:
        parser.error('wait-for-lock must be 0..3600')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        deadline = time.monotonic() + args.wait_for_lock
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.5)
        result = verify(read(args.report), read(args.reference) if args.reference else None)
        with args.report.with_name('verification.json').open('x') as output:
            json.dump(result, output, indent=2)
            output.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
