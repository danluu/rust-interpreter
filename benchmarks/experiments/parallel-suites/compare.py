#!/usr/bin/env python3
"""Qualify isolated concurrency, then screen exactly one versus two workers."""
import argparse
import json
import os
from pathlib import Path
import re
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import capture, require_space, write_json as write
from workflow_measurements import child_usage, child_cpu_since


def counts(suite):
    return [{k: t[k] for k in ['name', 'function', 'instructions', 'peak_guest_memory']}
            for t in suite['tests']]


def screen_case(case, rows):
    pairs = []
    for pair in range(6):
        selected = {row['workers']: row for row in rows if row['pair'] == pair}
        assert set(selected) == {1, 2}
        a, b = selected[1], selected[2]
        wall = b['seconds'] / a['seconds']
        cpu = b['cpu']['total_seconds'] / a['cpu']['total_seconds']
        pairs.append(dict(pair=pair, wall_ratio=wall, cpu_ratio=cpu,
            wall_guard_excess=b['seconds']-a['seconds']-max(.05*a['seconds'], .010),
            cpu_guard_excess=b['cpu']['total_seconds']-a['cpu']['total_seconds']-
                max(.05*a['cpu']['total_seconds'], .010)))
    result = dict(case=case, pairs=pairs,
        median_wall_ratio=statistics.median(p['wall_ratio'] for p in pairs),
        median_cpu_ratio=statistics.median(p['cpu_ratio'] for p in pairs),
        median_wall_guard_excess=statistics.median(p['wall_guard_excess'] for p in pairs),
        median_cpu_guard_excess=statistics.median(p['cpu_guard_excess'] for p in pairs))
    result['passed'] = (result['median_wall_ratio'] <= .8 and result['median_cpu_ratio'] <= 1.2
        if case == 'token' else result['median_wall_guard_excess'] <= 0 and result['median_cpu_guard_excess'] <= 0)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['serial', 'screen'], required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    kinds = parser.add_mutually_exclusive_group()
    kinds.add_argument('--checked-addresses-candidate', action='store_true', help='qualify the 451-test checked-address runtime')
    kinds.add_argument('--scalar-copy-budget-candidate', action='store_true', help='qualify the 456-test scalar Copy and budget runtime')
    kinds.add_argument('--scalar-copy-operands-candidate', action='store_true', help='qualify the 441-test scalar Copy operand runtime')
    kinds.add_argument('--direct-operands-candidate', action='store_true', help='qualify the 433-test direct operand runtime')
    kinds.add_argument('--immediate-shifts-candidate', action='store_true', help='qualify the 432-test immediate shift runtime')
    kinds.add_argument('--memory-operands-candidate', action='store_true', help='qualify the 428-test memory-operand runtime')
    kinds.add_argument('--paired-registers-candidate', action='store_true', help='qualify the 421-test paired-register runtime')
    kinds.add_argument('--guarded-indirect-candidate', action='store_true', help='qualify the 424-test guarded indirect-call runtime')
    kinds.add_argument('--wide-bitwise-candidate', action='store_true', help='qualify the 419-test wide integer emitter')
    kinds.add_argument('--capacity-credit-candidate', action='store_true', help='qualify the 422-test capacity-credit runtime')
    kinds.add_argument('--main-integration-candidate', action='store_true', help='qualify the 418-test compiler/runtime integration')
    kinds.add_argument('--call-protocol-candidate', action='store_true', help='qualify the 395-test call-protocol runtime')
    kinds.add_argument('--composed-candidate', action='store_true',
                        help='qualify the composed runtime; no standalone speed screen')
    parser.add_argument('--selection-qualification', type=Path,
                        help='exact saved-test qualification for a rebuilt composed VM')
    args = parser.parse_args()
    runtime_candidate = args.checked_addresses_candidate or args.scalar_copy_budget_candidate or args.scalar_copy_operands_candidate or args.direct_operands_candidate or args.immediate_shifts_candidate or args.memory_operands_candidate or args.paired_registers_candidate or args.guarded_indirect_candidate or args.wide_bitwise_candidate or args.capacity_credit_candidate or args.composed_candidate or args.call_protocol_candidate or args.main_integration_candidate
    if runtime_candidate and args.selection_qualification is None:
        parser.error('a runtime candidate requires --selection-qualification')
    prefix = 'checked-addresses' if args.checked_addresses_candidate else 'scalar-copy-budget' if args.scalar_copy_budget_candidate else 'scalar-copy-operands' if args.scalar_copy_operands_candidate else 'direct-operands' if args.direct_operands_candidate else 'immediate-shifts' if args.immediate_shifts_candidate else 'memory-operands' if args.memory_operands_candidate else 'paired-registers' if args.paired_registers_candidate else 'guarded-indirect' if args.guarded_indirect_candidate else 'wide-bitwise' if args.wide_bitwise_candidate else 'call-capacity-credit' if args.capacity_credit_candidate else 'call-protocol-main' if args.main_integration_candidate else 'resumable-call-protocol' if args.call_protocol_candidate else 'composed-development' if args.composed_candidate else 'parallel-suites'
    assert not runtime_candidate or args.phase == 'serial'
    assert re.fullmatch(prefix + '-' + args.phase + r'-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8 if args.checked_addresses_candidate or args.scalar_copy_budget_candidate or args.scalar_copy_operands_candidate or args.direct_operands_candidate or args.immediate_shifts_candidate or args.memory_operands_candidate else 3.5)
        paths = [Path(__file__), Path(__file__).with_name('PLAN.md')]
        paths += [ROOT / 'scripts' / name for name in ['compare_saved_runtime.py', 'interpreter.py',
            'workspace_cache.py', 'workflow_io.py', 'workflow_measurements.py', 'suite_reports.py', 'native_suite.py']]
        builds = dict(candidate=args.build.resolve(strict=True),
                      retained=ROOT / ('results/parallel-suites-build-01/summary.json'
                          if runtime_candidate else 'results/selected-native-build-01/summary.json'))
        if args.checked_addresses_candidate:
            paths.append(ROOT / 'benchmarks/experiments/checked-addresses/PLAN.md')
        if args.scalar_copy_budget_candidate:
            paths.append(ROOT / 'benchmarks/experiments/scalar-copy-budget/PLAN.md')
        if args.scalar_copy_operands_candidate:
            paths.append(ROOT / 'benchmarks/experiments/scalar-copy-operands/PLAN.md')
        if args.direct_operands_candidate:
            paths.append(ROOT / 'benchmarks/experiments/direct-operands/PLAN.md')
        if args.immediate_shifts_candidate:
            paths.append(ROOT / 'benchmarks/experiments/immediate-shifts/PLAN.md')
        if args.memory_operands_candidate:
            paths.append(ROOT / 'benchmarks/experiments/memory-operands/PLAN.md')
        if args.paired_registers_candidate:
            paths.append(ROOT / 'benchmarks/experiments/paired-registers/PLAN.md')
        if args.guarded_indirect_candidate:
            paths.append(ROOT / 'benchmarks/experiments/guarded-indirect/PLAN.md')
        if args.wide_bitwise_candidate:
            paths.append(ROOT / 'benchmarks/experiments/wide-bitwise/PLAN.md')
        if args.capacity_credit_candidate:
            paths.append(ROOT / 'benchmarks/experiments/call-capacity-credit/PLAN.md')
        if args.main_integration_candidate:
            paths.append(ROOT / 'benchmarks/experiments/call-protocol-main/PLAN.md')
        if args.call_protocol_candidate:
            paths.append(ROOT / 'benchmarks/experiments/resumable-call-protocol/PLAN.md')
        if args.composed_candidate:
            paths.append(ROOT / 'benchmarks/experiments/composed-development/PLAN.md')
        vms, keys = {}, {}
        for mode, path in builds.items():
            build = json.loads(path.read_text())
            assert build['status'] == 'passed'
            candidate_tests = 451 if args.checked_addresses_candidate else 456 if args.scalar_copy_budget_candidate else 441 if args.scalar_copy_operands_candidate else 433 if args.direct_operands_candidate else 432 if args.immediate_shifts_candidate else 428 if args.memory_operands_candidate else 421 if args.paired_registers_candidate else 424 if args.guarded_indirect_candidate else 419 if args.wide_bitwise_candidate else 422 if args.capacity_credit_candidate else 418 if args.main_integration_candidate else 395 if args.call_protocol_candidate else 393
            expected = dict(passed=(candidate_tests if mode == 'candidate' else 365) if runtime_candidate
                            else (365 if mode == 'candidate' else 360), ignored=1)
            assert build['tests']['test-debug'] == build['tests']['test-release'] == expected
            directory, keys[mode] = installed_tools(build['tool_key'])
            vms[mode] = directory / 'rust-interp-vm'
            assert sha(vms[mode]) == build['binaries']['rust-interp-vm']
            paths += [path, vms[mode]]
        selected_path = (args.selection_qualification.resolve(strict=True)
                         if args.selection_qualification is not None else
                         ROOT / 'results' / (prefix + '-qualification-01') / 'summary.json')
        selected = json.loads(selected_path.read_text())
        assert selected['status'] == 'passed' and selected['commands'] == 7
        assert selected['vm_sha256'] == sha(vms['candidate']) and selected['exact_instructions_memory_and_entropy']
        paths.append(selected_path)
        if args.phase == 'screen':
            serial_path = ROOT / 'results/parallel-suites-serial-02/summary.json'
            serial = json.loads(serial_path.read_text())
            assert serial['status'] == 'passed' and serial['commands'] == 9
            assert serial['binaries']['candidate'] == sha(vms['candidate'])
            paths.append(serial_path)
        prior_path = ROOT / 'results/native-address-checks-screen-01/summary.json'
        prior = json.loads(prior_path.read_text())
        assert prior['status'] == 'passed' and prior['exact_per_test_counts_memory_and_entropy']
        plan_path = ROOT / prior['raw'] / 'plan.json'
        assert sha(plan_path) == prior['plan_sha256']
        prior_plan = json.loads(plan_path.read_text())
        paths += [prior_path, plan_path]
        inputs = prior_plan['inputs']
        assert {item['case'] for item in inputs} == {'token', 'folded', 'pgrust'}
        for item in inputs:
            artifact, catalog = Path(item['artifact']), Path(item['catalog'])
            for path in [artifact, catalog]:
                assert sha(path) == prior_plan['frozen'][str(path.relative_to(ROOT))]
            stream = item['streams'][0]
            assert sha(stream['tape']) == stream['sha256']
            # Bind the exact original native assertions, not merely VM success.
            native_path = artifact.parent / '6-native-suite.json'
            report_path = ROOT / 'results' / artifact.parent.name / 'summary.json'
            report = json.loads(report_path.read_text()); assert report['status'] == 'passed'
            records_path = ROOT / report['raw'] / 'records.json'
            assert sha(records_path) == report['records_sha256']
            rows = [r for r in json.loads(records_path.read_text()) if r['state'] == 6 and r['mode'] == 'native']
            assert len(rows) == 1
            native, _ = read_report(native_path, rows[0]['suite_sha256'])
            validate_report(native, item['names'], 'native', True)
            paths += [artifact, catalog, Path(stream['tape']), native_path, report_path, records_path]
        entropy_path = ROOT / 'results/fixed-frame-clear-entropy-check-01/summary.json'
        entropy = json.loads(entropy_path.read_text())
        assert entropy['status'] == 'passed' and entropy['commands'] == 17 and entropy['expected_rejections'] == 10
        library = ROOT / entropy['library']; assert sha(library) == entropy['library_sha256']
        paths += [entropy_path, library]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / args.run_id; work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, inputs=inputs,
            phase=args.phase, keys=keys, minimum_free_gib=8 if args.checked_addresses_candidate or args.scalar_copy_budget_candidate or args.scalar_copy_operands_candidate or args.direct_operands_candidate or args.immediate_shifts_candidate or args.memory_operands_candidate else 3, pairs=6 if args.phase == 'screen' else 0,
            normal_entropy_for_all_concurrent_runs=True, complete_workflow_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env['RUST_INTERP_VM_STATS'] = '1'
        records, cases = [], []
        for item in sorted(inputs, key=lambda i: ['token', 'folded', 'pgrust'].index(i['case'])):
            case, limits, reference = item['case'], item['limits'], item['streams'][0]
            if args.phase == 'serial':
                order = [(-1, 'retained', 1, True), (-1, 'candidate', 1, True), (-1, 'candidate', 2, False)]
            else:
                order = [(pair, 'candidate', workers, False) for pair in range(6)
                         for workers in ([1, 2] if pair % 2 == 0 else [2, 1])]
            for pair, mode, workers, replay in order:
                require_space(ROOT, 8 if args.checked_addresses_candidate or args.scalar_copy_budget_candidate or args.scalar_copy_operands_candidate or args.direct_operands_candidate or args.immediate_shifts_candidate or args.memory_operands_candidate else 3)
                suite_path = work / f'{case}-{pair}-{mode}-{workers}-suite.json'
                command = [str(vms[mode]), '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
                    '--isolated-batch', 'prepared', '--suite-report', str(suite_path), '--suite-catalog', item['catalog'],
                    '--instruction-limit', str(limits['instructions']), '--allocation-limit', str(limits['allocations'])]
                if mode == 'candidate': command += ['--suite-workers', str(workers)]
                command.append(item['artifact'])
                selected_env = dict(env)
                if replay:
                    assert workers == 1
                    selected_env.update(DYLD_INSERT_LIBRARIES=str(library), RUST_INTERP_ENTROPY_MODE='replay',
                                        RUST_INTERP_ENTROPY_TAPE=reference['tape'])
                before, started = child_usage(), time.perf_counter()
                child, stdout, stderr = capture(command, cwd=ROOT, env=selected_env,
                    receipt_path=work / 'active.json', receipt=dict(case=case, pair=pair, mode=mode, workers=workers))
                row = dict(case=case, pair=pair, mode=mode, workers=workers, entropy_replay=replay,
                    command=command, pid=child.pid, returncode=child.returncode, seconds=time.perf_counter()-started,
                    cpu=child_cpu_since(before), stdout=stdout, stderr=stderr)
                records.append(row); write(work / 'records.json', records)
                assert child.returncode == 0 and stdout == '0\n', stderr
                suite, digest = read_report(suite_path)
                validate_report(suite, item['names'], 'prepared', True)
                validate_runtime_limits(suite, limits['instructions'], limits['allocations'], required=True)
                observed = counts(suite)
                assert all(t['jit_declined_functions'] == 0 for t in suite['tests'])
                if mode == 'candidate':
                    assert suite['workers'] == suite['requested_workers'] == workers
                    assert all(0 <= t['worker'] < workers for t in suite['tests'])
                if replay:
                    entropy_counts = {k: int(v) for k, v in re.findall(r'\b(entropy_calls|entropy_bytes)=(\d+)\b', stderr)}
                    assert observed == reference['expected'] and entropy_counts == reference['entropy']
                elif case != 'token':
                    # Process-level entropy also includes host initialization.
                    # These controls must keep exact guest counters across the
                    # two independently recorded streams and normal OS input.
                    assert item['streams'][0]['expected'] == item['streams'][1]['expected']
                    assert observed == reference['expected']
                else:
                    assert [(t['name'], t['function']) for t in observed] == [(t['name'], t['function']) for t in reference['expected']]
                row.update(suite_sha256=digest, per_test=observed,
                    schedule=[dict(name=t['name'], worker=t.get('worker', 0), seconds=t['seconds']) for t in suite['tests']])
                write(work / 'records.json', records)
                print(case, pair, mode, workers, round(row['seconds'], 3), 'passed', flush=True)
            if args.phase == 'screen':
                cases.append(screen_case(case, [r for r in records if r['case'] == case]))
                write(work / 'cases.json', cases)
        assert all(sha(ROOT / p) == digest for p, digest in frozen.items())
        out = ROOT / 'results' / args.run_id; out.mkdir(exist_ok=False)
        result = dict(status='passed', phase=args.phase, commands=len(records), cases=cases,
            binaries={mode: sha(vm) for mode, vm in vms.items()}, native_assertion_outcomes_match=True,
            deterministic_controls_exact=True, concurrent_entropy='ordinary OS input; no process-global replay shim',
            complete_workflow_measurement=False, raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'))
        if args.phase == 'screen': result['runtime_screen_passed'] = all(c['passed'] for c in cases)
        write(out / 'summary.json', result)
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
