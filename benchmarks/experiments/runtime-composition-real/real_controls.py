"""Qualify saved selected tests and one/two-worker suites after primary admission."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import capture, require_space, write_json as write


def counts(suite):
    return [{k: t[k] for k in ['name', 'function', 'instructions', 'peak_guest_memory']}
            for t in suite['tests']]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--screen', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'runtime-composition-real-controls-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 10)
        build_path = args.build.resolve(strict=True)
        screen_path = args.screen.resolve(strict=True)
        build = json.loads(build_path.read_text())
        screen = json.loads(screen_path.read_text())
        assert build['status'] == screen['status'] == 'passed'
        assert build['tests'] == {'test-debug': 666, 'test-release': 666}
        assert screen['commands'] == 40 and screen['gate_passed'] and screen['source_restored']
        assert screen['tool_keys']['candidate'] == build['tool_key']
        tools, key = installed_tools(build['tool_key'])
        vm = tools / 'rust-interp-vm'
        adopted,control_key=installed_tools(build['matched_control']['tool_key'])
        assert control_key=='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
        assert all(sha(adopted/n)==h for n,h in build['matched_control']['binaries'].items())
        for proof in [build_path,screen_path]:
            closed=json.loads(proof.with_name('closure.json').read_text())
            if proof==screen_path:assert closed['performance_gate_passed'] and not closed['parked']
            else:assert closed['status']=='closed' and sha(proof)==closed['summary_sha256']
        assert all(sha(tools / name) == digest for name, digest in build['binaries'].items())
        paths = [Path(__file__), Path(__file__).with_name('FULL-CONTROLS.md'), build_path, screen_path]
        paths += [t / name for t in [tools,adopted] for name in build['binaries']]
        paths += [build_path.with_name('closure.json'),screen_path.with_name('closure.json')]
        paths += [ROOT / 'scripts' / name for name in
                  ['compare_saved_runtime.py', 'interpreter.py', 'suite_reports.py', 'workflow_io.py']]

        # Keep the established seven selected-test entropy streams and native
        # assertion bindings. No old guest command or mutable source is rerun.
        selected_path = ROOT / 'results/suite-profiling-real-01/summary.json'
        selected = json.loads(selected_path.read_text())
        assert selected['status'] == 'passed' and selected['exact_logical_counts_and_entropy']
        selected_raw = ROOT / '.work/suite-profiling-real-01'
        selected_rows_path = selected_raw / 'records.json'
        assert sha(selected_rows_path) == selected['records_sha256']
        selected_rows = json.loads(selected_rows_path.read_text())
        paths += [selected_path, selected_rows_path]
        selections = []
        for case in selected['profiles']:
            artifact, catalog = ROOT / case['artifact'], ROOT / case['catalog']
            tape = selected_raw / (str(case['index']) + '.tape')
            profile = selected_raw / (str(case['index']) + '-profile.json')
            assert sha(artifact) == case['artifact_sha256'] and sha(catalog) == case['catalog_sha256']
            assert sha(profile) == case['profile_sha256']
            prior, = [r for r in selected_rows if r['index'] == case['index'] and r['mode'] == 'profile']
            assert sha(tape) == prior['tape_sha256']
            paths += [artifact, catalog, tape, profile]
            selections.append((case, artifact, catalog, tape))
        assert len(selections) == 7

        serial_path = ROOT / 'results/guarded-ranges-serial-01/summary.json'
        serial = json.loads(serial_path.read_text())
        assert serial['status'] == 'passed' and serial['commands'] == 9
        assert serial['native_assertion_outcomes_match'] and serial['deterministic_controls_exact']
        serial_raw = ROOT / serial['raw']
        serial_plan_path, serial_rows_path = serial_raw / 'plan.json', serial_raw / 'records.json'
        assert sha(serial_plan_path) == serial['plan_sha256'] and sha(serial_rows_path) == serial['records_sha256']
        serial_plan = json.loads(serial_plan_path.read_text())
        serial_rows = json.loads(serial_rows_path.read_text())
        paths += [serial_path, serial_plan_path, serial_rows_path]
        suites = serial_plan['inputs']
        assert {i['case'] for i in suites} == {'token', 'folded', 'pgrust'}
        for item in suites:
            artifact, catalog = Path(item['artifact']), Path(item['catalog'])
            stream = item['streams'][0]
            for path in [artifact, catalog, Path(stream['tape'])]:
                assert sha(path) == serial_plan['frozen'][str(path.relative_to(ROOT))]
                paths.append(path)
            assert sha(stream['tape']) == stream['sha256']
            prior, = [r for r in serial_rows if r['case'] == item['case'] and r['mode'] == 'candidate' and r['workers'] == 1]
            assert prior['returncode'] == 0 and prior['entropy_replay'] and prior['per_test'] == stream['expected']
            prior_suite_path = Path(prior['command'][prior['command'].index('--suite-report') + 1])
            prior_suite, _ = read_report(prior_suite_path, prior['suite_sha256'])
            assert counts(prior_suite) == stream['expected']
            validate_report(prior_suite, item['names'], 'prepared', True)
            paths.append(prior_suite_path)
            # Revalidate the retained native reference, rather than treating a
            # zero guest exit status as sufficient assertion evidence.
            native_path = artifact.parent / '6-native-suite.json'
            native_proof_path = ROOT / 'results' / artifact.parent.name / 'summary.json'
            native_proof = json.loads(native_proof_path.read_text())
            assert native_proof['status'] == 'passed'
            native_rows_path = ROOT / native_proof['raw'] / 'records.json'
            assert sha(native_rows_path) == native_proof['records_sha256']
            native_row, = [r for r in json.loads(native_rows_path.read_text()) if r['state'] == 6 and r['mode'] == 'native']
            native, _ = read_report(native_path, native_row['suite_sha256'])
            validate_report(native, item['names'], 'native', True)
            paths += [native_path, native_proof_path, native_rows_path]

        entropy_path = ROOT / 'results/fixed-frame-clear-entropy-check-01/summary.json'
        entropy = json.loads(entropy_path.read_text())
        assert entropy['status'] == 'passed' and entropy['commands'] == 17 and entropy['expected_rejections'] == 10
        library = ROOT / entropy['library']
        assert sha(library) == entropy['library_sha256']
        paths += [entropy_path, library]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(), frozen=frozen, commands=26, tool_key=key, fresh_baseline_commands=13,
            initial_gib=10, minimum_child_gib=8, selected_tests=7, prepared_suites=6, jit_scalar_calls=True,
            native_reference_suites=3, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env['RUST_INTERP_VM_STATS'] = '1'
        rows = []

        def invoke(label, command, tape=None):
            require_space(ROOT, 8)
            selected_env = dict(env)
            if tape is not None:
                selected_env.update(DYLD_INSERT_LIBRARIES=str(library), RUST_INTERP_ENTROPY_MODE='replay',
                                    RUST_INTERP_ENTROPY_TAPE=str(tape))
            command = list(map(str, command))
            child, out, err = capture(command, cwd=ROOT, env=selected_env,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            row = dict(label=label, command=command, pid=child.pid, returncode=child.returncode,
                       stdout=out, stderr=err, entropy_replay=tape is not None)
            rows.append(row)
            write(work / 'records.json', rows)
            assert child.returncode == 0 and out == '0\n', err
            return row

        selected_expected={};suite_expected={};entropy_expected={}
        for mode,selected_vm in [('control',adopted/'rust-interp-vm'),('candidate',vm)]:
            flags=['--jit-indirect-calls'] if mode=='candidate' else []
            for case, artifact, catalog, tape in selections:
                row = invoke(mode+'-selected-' + str(case['index']), [selected_vm, '--engine', 'jit', '--jit-resumable-calls',
                    '--jit-persistent-registers', '--jit-scalar-calls', *flags, '--select-test', case['name'], '--suite-catalog', catalog,
                    '--instruction-limit', str(case['limits']['instructions']),
                    '--allocation-limit', str(case['limits']['allocations']), artifact], tape)
                selection, = [json.loads(line.split(': ', 1)[1]) for line in row['stderr'].splitlines()
                              if line.startswith('rust-interp-test-selection: ')]
                assert selection == case['selection']
                stats = {k: int(v) for k, v in re.findall(r'\b([a-z_]+)=(\d+)\b', row['stderr'])}
                observed={k:stats[k] for k in ['instructions','peak_guest_memory','jit_declined_functions','entropy_calls','entropy_bytes']}
                assert observed['jit_declined_functions']==0
                if mode=='control':selected_expected[case['index']]=observed
                assert observed==selected_expected[case['index']]
                row.update(mode=mode,selection=selection, statistics=stats, exact_current_reference_statistics=selected_expected[case['index']])
                write(work / 'records.json', rows)
                print(row['label'], 'PASS', flush=True)
            for item in sorted(suites, key=lambda i: ['token', 'folded', 'pgrust'].index(i['case'])):
                reference = item['streams'][0];limits = item['limits']
                for workers in [1, 2]:
                    label = mode+'-'+item['case'] + '-workers-' + str(workers)
                    suite_path = work / (label + '-suite.json')
                    row = invoke(label, [selected_vm, '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers', '--jit-scalar-calls', *flags,
                        '--isolated-batch', 'prepared', '--suite-report', suite_path, '--suite-catalog', item['catalog'],
                        '--instruction-limit', str(limits['instructions']), '--allocation-limit', str(limits['allocations']),
                        '--suite-workers', str(workers), item['artifact']], reference['tape'] if workers == 1 else None)
                    suite, digest = read_report(suite_path)
                    validate_report(suite, item['names'], 'prepared', True)
                    validate_runtime_limits(suite, limits['instructions'], limits['allocations'], required=True)
                    assert suite['workers'] == suite['requested_workers'] == workers
                    assert all(0 <= t['worker'] < workers and t['jit_declined_functions'] == 0 for t in suite['tests'])
                    observed = counts(suite);index=(item['case'],workers)
                    if mode=='control':suite_expected[index]=observed
                    if workers == 1:
                        entropy_counts = {k: int(v) for k, v in re.findall(r'\b(entropy_calls|entropy_bytes)=(\d+)\b', row['stderr'])}
                        if mode=='control':entropy_expected[index]=entropy_counts
                        assert observed==suite_expected[index] and entropy_counts==entropy_expected[index]==reference['entropy']
                    elif item['case'] != 'token':
                        assert observed==suite_expected[index]==suite_expected[item['case'],1]
                    else:
                        assert [(t['name'], t['function']) for t in observed] == [(t['name'], t['function']) for t in reference['expected']]
                    row.update(mode=mode,suite_sha256=digest, per_test=observed, workers=workers)
                    write(work / 'records.json', rows)
                    print(label, 'PASS', flush=True)
        assert len(rows) == 26 and all(sha(ROOT / p) == h for p, h in frozen.items())
        result = ROOT / 'results' / args.run_id
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', commands=26, fresh_baseline_commands=13, matched_control_key=control_key, jit_indirect_calls=True, selected_tests=7, prepared_suites=6, jit_scalar_calls=True,
            tool_key=key, vm_sha256=sha(vm), native_assertion_outcomes_match=True,
            deterministic_controls_exact=True, concurrent_entropy='ordinary OS, no replay shim',
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            records_sha256=sha(work / 'records.json'), performance_measurement=False))


if __name__ == '__main__':
    main()
