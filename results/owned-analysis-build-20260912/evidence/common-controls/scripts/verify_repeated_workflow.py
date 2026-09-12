#!/usr/bin/env python3
"""Verify repeated edit measurements; output only counts and hashes, including for private cases."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import statistics
import time

from workflow_measurements import initial_modes, mode_order
from workflow_jobs import recorded_build_jobs, verify_command_jobs
from bench_e2e_workflow import build_metrics, cache_workspace, guest_test_failure

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read(path):
    return json.loads(path.read_text())


def verify_entry_catalog(root, artifact, launch, names, suite=None):
    """Bind a retained catalog to its launch, bytecode and executed identities."""
    present = 'entry_catalog' in artifact
    require(present == ('entry_catalog_path' in launch) == ('entry_catalog_sha256' in launch),
            'catalog launch or snapshot receipt is missing')
    if not present:
        require(suite is None or suite.get('entry_source', 'legacy batch descriptor') == 'legacy batch descriptor',
                'catalog execution lacks retained evidence')
        return
    item = artifact['entry_catalog']
    path = root / item['path']
    require(path == Path(str(root / artifact['path']) + '.entries.json') and not path.is_symlink(),
            'catalog snapshot is outside its artifact')
    require(path.is_file() and 0 < path.stat().st_size <= 8 * 1024 * 1024, 'invalid catalog snapshot size')
    payload = path.read_bytes()
    require(hashlib.sha256(payload).hexdigest() == item['sha256'], 'catalog snapshot changed')
    catalog = json.loads(payload)
    require(catalog['artifact_sha256'] == artifact['sha256'] and
            [e['name'] for e in catalog['entries']] == names, 'catalog artifact or test selection differs')
    require(launch['entry_catalog_sha256'] == item['sha256'] and
            launch['entry_catalog_path'] == launch['artifact_path'] + '.entries.json', 'launched catalog differs')
    if suite is not None:
        require(suite['entry_source'] == 'artifact-bound catalog' and
                [(e['name'], e['function']) for e in catalog['entries']] ==
                [(t['name'], t['function']) for t in suite['tests']],
                'executed entry identities differ from the catalog')


def verify(report, reference=None, *, compiler_flags=None):
    """Verify runtime comparisons by default; explicitly bind compiler changes.

    A compiler comparison must supply its expected per-mode flags separately
    from the measured receipt. It uses identical tools/runtime options and
    retains every artifact hash, but does not require the artifacts to match.
    The ordinary CLI and all runtime callers keep the strict default.
    """
    require(report['schema_version'] == 2, 'unsupported workflow schema')
    if compiler_flags is not None:
        require(isinstance(compiler_flags, dict) and set(compiler_flags) == {'baseline', 'candidate'},
                'compiler comparison requires explicit flags for both modes')
        require(all(isinstance(flags, list) and flags and
                    all(isinstance(flag, str) and flag and not any(c.isspace() for c in flag)
                        for flag in flags) for flags in compiler_flags.values()) and
                compiler_flags['baseline'] != compiler_flags['candidate'], 'invalid compiler comparison flags')
        require('comparison' in report and not report['comparison']['identical_bytecode_required'],
                'compiler comparison cannot waive a required artifact match')
        builds = report['tool_builds']
        require(all(builds[mode]['guest_rustflags'] == compiler_flags[mode] for mode in compiler_flags),
                'compiler flags differ from the independent expectation')
        require({k: v for k, v in builds['baseline'].items() if k != 'guest_rustflags'} ==
                {k: v for k, v in builds['candidate'].items() if k != 'guest_rustflags'},
                'compiler comparison changed tools or runtime options')
    job_counts = (recorded_build_jobs(report)
                  if 'build_jobs' in report and 'native_control' in report else None)
    require('custom_build_jobs' not in report or job_counts is not None,
            'custom worker receipt lacks shared/native controls')
    measuring_build = 'build_metrics' in report
    restoring = 'restored_original' in report
    aa_control = report.get('aa_control', False)
    controlled_caches = measuring_build or aa_control
    if measuring_build:
        require('comparison' in report and report['batch'], 'build metrics require a batched paired comparison')
    if restoring:
        require('comparison' in report and report['batch'], 'restoration verification requires a batched paired comparison')
    if aa_control:
        require('comparison' in report and report['batch'] and job_counts is not None and not report.get('compare_isolated_batches'),
                'A/A control requires identical batched paired jobs/settings')
        require(report['tool_builds']['baseline'] == report['tool_builds']['candidate'] and
                job_counts['baseline'] == job_counts['candidate'], 'A/A tools or settings differ')
        require(report['comparison']['baseline_tool_key'] == report['comparison']['candidate_tool_key'] ==
                report['tool_builds']['baseline']['tool_key'], 'A/A tool keys differ')
    if controlled_caches:
        require(set(report['cache_namespaces']) == set(report['cache_workspaces']) == {'baseline', 'candidate'},
                'missing isolated comparison caches')
        namespaces = report['cache_namespaces']
        require(all(namespaces[m] == Path(report['raw']).name + ':' + m for m in namespaces) and
                len(set(report['cache_workspaces'].values())) == 2, 'comparison caches are not isolated')
    rows = read(ROOT / report['raw'] / 'records.json')
    if 'case_file' in report:
        from workflow_case_file import verify_snapshot
        # The existing case verifier reconstructs its declared edit history.
        # The optional final restoration is checked against that verified
        # original below, without changing historical case-file schemas.
        case_report = dict(report, mode_orders=report['mode_orders'][:-1]) if restoring else report
        case_rows = [r for r in rows if r['state'] != -2] if restoring else rows
        verify_snapshot(ROOT, case_report, case_rows)
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
    if restoring:
        expected_orders.append(dict(cycle=cycles,state=-2,phase='restored-original',
            modes=mode_order(scheduled_modes,cycles,-2,'comparison' in report)))
    require(report['mode_orders'] == expected_orders, 'recorded mode schedule differs')
    require([(r['cycle'], r['state'], r['mode']) for r in rows] ==
        [(o['cycle'], o['state'], m) for o in expected_orders for m in o['modes']], 'command order differs from schedule')
    expected = {(o['cycle'],o['state'],m) for o in expected_orders for m in modes}
    actual = [(r['cycle'], r['state'], r['mode']) for r in rows]
    require(len(set(actual)) == len(actual) and set(actual) == expected, 'missing or duplicate samples')
    require(report['test_source_unchanged'] and report['wrong_production_edit_rejected'], 'source/test controls failed')
    require(len(transitions) == len(expected_orders), 'missing source transitions')
    if restoring:
        original = rows[0]['source_sha256']
        require(report['restored_original'] == dict(verified=True,source_sha256=original,
            cycle=cycles,state=-2,commands=len(modes),excluded_from_edited_medians=True), 'invalid restoration receipt')
        require(transitions[-1]['cycle'] == cycles and transitions[-1]['state'] == -2 and
                transitions[-1]['phase'] == 'restored-original' and transitions[-1]['source_sha256'] == original,
                'restoration transition does not return to original source')
    require(all(t['content_changed'] for t in transitions if t['phase'] != 'cold'), 'unchanged warm sample')
    previous = dict.fromkeys(modes)
    artifacts = {}
    suites = {}
    paths = set()
    for row in rows:
        cycle, state, mode = row['cycle'], row['state'], row['mode']
        phase = 'restored-original' if restoring and state == -2 else (('cold' if cycle == 0 else 'anchor') if state == 0 else ('wrong-edit' if state == -1 else 'edit'))
        require(row['phase'] == phase, 'incorrect cold/anchor/edit label')
        require(row['previous_source_sha256'] == previous[mode], 'source history mismatch')
        if phase != 'cold':
            require(previous[mode] != row['source_sha256'], 'mode rebuilt unchanged source')
        previous[mode] = row['source_sha256']
        require(row['seconds'] > 0 and row['cpu_seconds'] > 0, 'invalid timing')
        cpu = sum(c['cpu']['user_seconds'] + c['cpu']['system_seconds'] for c in row['calls'])
        require(abs(cpu - row['cpu_seconds']) < 1e-8, 'CPU total does not match child calls')
        require(all((c['returncode'] == 0) == (state != -1) for c in row['calls']), 'unexpected command result')
        if measuring_build or restoring or aa_control:
            package = report['build_controls']['package']
            prefix = ('Compiling ' if mode == 'native' else 'Checking ') + package + ' '
            require(any(line.strip().startswith(prefix) for call in row['calls'] for line in call['stderr'].splitlines()),
                    'controlled source was not freshly compiled')
            if state == -1 and not report.get('compare_isolated_batches'):
                call = row['calls'][-1]
                if mode == 'native':
                    require('test result: FAILED.' in call['stdout'] and
                            any(f'test {test} ... FAILED' in call['stdout'] for test in row['tests']),
                            'wrong edit was not rejected by a native test body')
                else:
                    require(guest_test_failure(call['stderr']), 'wrong edit did not reach a guest assertion')
            elif not report.get('compare_isolated_batches'):
                require(all(call['stdout'].strip() == '0' for call in row['calls']) if mode != 'native' else
                        f"{len(row['tests'])} passed" in row['calls'][0]['stdout'], 'successful test output differs')
            if phase == 'restored-original':
                require(row['source_sha256'] == original, 'final build did not use original source')
        if job_counts is not None:
            for call in row['calls']:
                verify_command_jobs(call['command'], job_counts[mode])
        if report.get('compare_isolated_batches'):
            from suite_reports import read_report, validate_report, validate_runtime_limits
            suite_mode = 'native' if mode == 'native' else 'fresh' if mode == 'baseline' else 'prepared'
            item = row['suite_report']
            path = ROOT / item['path']
            require(path.resolve().is_relative_to((ROOT / report['raw'] / 'suites' / mode).resolve()),
                    'suite report outside this mode')
            suite, _ = read_report(path, item['sha256'])
            suites[cycle, state, mode] = validate_report(suite, row['tests'], suite_mode, state != -1)
            require(len(row['calls']) == 1, 'isolated suite must execute in one complete command')
            call = row['calls'][0]
            command = call['command']
            require(command.count('--suite-report') == 1 and command[command.index('--suite-report')+1] == str(path),
                    'command selected another report')
            if mode == 'native':
                require(Path(command[1]).resolve() == ROOT / 'scripts/native_suite.py', 'native isolation runner differs')
                verify_command_jobs(suite['build']['command'], job_counts[mode])
                require(suite['build']['returncode'] == 0, 'native suite did not build')
                for test in suite['tests']:
                    require(test['command'] == [suite['executable'], '--exact', test['name'], '--test-threads=1'],
                            'native test process did not select its exact body')
            else:
                validate_runtime_limits(suite,report.get('instruction_limit'),report.get('allocation_limit'))
                require(command.count('--isolated-batch') == 1 and command[command.index('--isolated-batch')+1] == suite_mode,
                        'isolated mode differs from command')
                require(call['launch']['isolated_batch'] == suite_mode and
                        call['launch']['suite_report_sha256'] == item['sha256'] and
                        call['launch']['suite_report_path'] == str(path), 'launched suite differs')
        if mode != 'native':
            settings = report.get('tool_builds', {}).get(mode, {})
            if controlled_caches or restoring:
                for call in row['calls']:
                    launches = [json.loads(line.split('rust-interp-launch: ',1)[1]) for line in call['stderr'].splitlines()
                                if line.startswith('rust-interp-launch: ')]
                    require(launches == [call['launch']], 'launch receipt differs from command stderr')
                    require(call['launch']['tool_key'] == settings['tool_key'], 'executed tool differs')
                    if controlled_caches:
                        scope = ROOT / '.work/interpreter-workspaces' / settings['tool_key']
                        workspace = cache_workspace(call['command'],call['launch']['artifact_path'],scope,namespaces[mode])
                        require(workspace == report['cache_workspaces'][mode], 'executed cache workspace differs')
                if measuring_build:
                    measured = [build_metrics(call['launch']) for call in row['calls']]
                    for field in measured[0]:
                        require(row[field] == sum(value[field] for value in measured), 'sample build metrics differ from launch receipts')
            if compiler_flags is not None:
                require(all(call.get('rustflags') == ' '.join(compiler_flags[mode]) and
                            call['launch']['tool_key'] == settings['tool_key'] for call in row['calls']),
                        'executed compiler flags or tool differ')
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
            if controlled_caches or restoring:
                require(len(row['calls']) == 1 and row['calls'][0]['launch']['artifact_sha256'] == digest and
                        row['calls'][0]['launch']['artifact_bytes'] == (ROOT / path).stat().st_size,
                        'snapshot differs from the executed artifact receipt')
            verify_entry_catalog(ROOT, artifact, row['calls'][0]['launch'], row['tests'],
                                 suite if report.get('compare_isolated_batches') else None)
            artifacts[cycle, state, mode] = digest
    paired_identical = True
    for order in expected_orders:
        c,s = order['cycle'],order['state']
        selected = [r for r in rows if r['cycle'] == c and r['state'] == s]
        require(len({r['source_sha256'] for r in selected}) == 1, 'paired sources differ')
        require(all(r['tests'] == selected[0]['tests'] for r in selected), 'paired test selections differ')
        if report.get('compare_isolated_batches'):
            require(suites[c, s, modes[0]] == suites[c, s, modes[1]] == suites[c, s, modes[2]],
                    'isolated test outcomes differ between native/fresh/prepared')
        identical = artifacts[c, s, custom_modes[0]] == artifacts[c, s, custom_modes[1]]
        paired_identical &= identical
        if compiler_flags is None:
            require(identical, 'paired bytecode differs')
    for s in states:
        require(len({r['source_sha256'] for r in rows if r['state'] == s}) == 1, 'repeated source state differs')
    if cycles == 3:
        for s in range(1, edits + 1):
            orders = [o['modes'] for o in report['mode_orders'] if o['state'] == s]
            for m in modes:
                require(sorted(o.index(m) for o in orders) == [0, 1, 2], 'unbalanced mode positions')
    if 'comparison' in report:
        require(len(report['comparison']['pairs']) == cycles * edits, 'missing edited pairs')
    if measuring_build:
        expected_pairs = [(c,s) for c in range(cycles) for s in range(1,edits+1)]
        require([(p['cycle'],p['state']) for p in report['comparison']['pairs']] == expected_pairs,
                'build pairs include a control or omit an edit')
        for pair in report['comparison']['pairs']:
            selected = {r['mode']:r for r in rows if (r['cycle'],r['state']) == (pair['cycle'],pair['state'])}
            for mode in ['baseline','candidate']:
                for field in ['build_to_ready_seconds','build_to_ready_cpu_seconds','cargo_cpu_seconds']:
                    require(pair[mode+'_'+field] == selected[mode][field], 'paired build timing differs from commands')
            for field in ['build_to_ready_seconds','build_to_ready_cpu_seconds']:
                difference = field.removesuffix('_seconds')+'_difference_seconds'
                require(pair[difference] == selected['candidate'][field]-selected['baseline'][field], 'paired build difference differs')
        for mode in ['baseline','candidate']:
            selected = [r for r in rows if r['mode'] == mode and r['state'] > 0]
            require(report['build_metrics']['median_seconds'][mode] == statistics.median(r['build_to_ready_seconds'] for r in selected) and
                    report['build_metrics']['median_cpu_seconds'][mode] == statistics.median(r['build_to_ready_cpu_seconds'] for r in selected),
                    'build medians include controls or differ from edited samples')
    if restoring:
        for mode in modes:
            selected = [r for r in rows if r['mode'] == mode and r['state'] > 0]
            require(report['median_seconds'][mode] == statistics.median(r['seconds'] for r in selected) and
                    report['median_cpu_seconds'][mode] == statistics.median(r['cpu_seconds'] for r in selected),
                    'edited command medians include restoration or other controls')
    require(len(report['cycle_anchor_seconds']) == cycles - 1, 'incorrect anchor count')
    require(report['cold_success_seconds'] == {r['mode']: r['seconds'] for r in rows if r['phase'] == 'cold'}, 'cold results contain warm anchors')
    cross_cycle = [{"state": s, "sha256_by_cycle": [artifacts[c, s, custom_modes[1]] for c in range(cycles)]} for s in states]
    check_count = 0
    if report.get('check_floor') is not None:
        checks = read(ROOT / report['raw'] / 'check-records.json')
        keys = [(c['cycle'], c['state']) for c in checks]
        require(len(set(keys)) == len(keys) and set(keys) == {(o['cycle'],o['state']) for o in expected_orders}, 'missing/duplicate check controls')
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
    result = dict(schema_version=1, measurement_controls_verified=True,
        commands=len(rows), cycles=cycles, edited_pairs=cycles * edits,
        check_commands=check_count, explicit_controls_verified=bool(check_count),
        exact_artifact_hashes_verified=len(paths), paired_bytecode_identical=paired_identical,
        cross_cycle_bytecode_identical=all(len(set(x['sha256_by_cycle'])) == 1 for x in cross_cycle),
        cross_cycle_artifacts=cross_cycle, reference_bytecode=history,
        cross_cycle_semantic_equivalence_proven=False,
        note='Control verification does not imply identical compilation across cache histories or a performance claim.')
    if compiler_flags is not None:
        result['compiler_comparison'] = dict(expected_guest_flags=compiler_flags,
            identical_tools_and_runtime_options=True, bytecode_equivalence_proven=False)
    if measuring_build:result['build_to_ready_metrics_verified']=True
    if restoring:result['restored_original_build_and_execution_verified']=True
    if aa_control:result['identical_build_isolated_caches_verified']=True
    return result


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
