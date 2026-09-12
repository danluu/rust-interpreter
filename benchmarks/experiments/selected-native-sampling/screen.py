#!/usr/bin/env python3
"""Screen the split-arena VM on current prepared suites and two recorded inputs."""
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
from workflow_io import capture, require_space, write_json as write
from workflow_measurements import child_usage, child_cpu_since
from suite_reports import read_report, validate_report, validate_runtime_limits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'native-address-checks-screen-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 3.5)
        builds = dict(baseline=ROOT / 'results/selected-native-build-01/summary.json',
                      candidate=args.build.resolve(strict=True))
        paths = [Path(__file__), Path(__file__).with_name('ADDRESS-CHECKS.md'), *builds.values()]
        paths += [ROOT / 'scripts' / name for name in ['compare_saved_runtime.py', 'interpreter.py',
            'workspace_cache.py', 'workflow_io.py', 'workflow_measurements.py', 'suite_reports.py', 'native_suite.py']]
        vms = {}
        for mode, path in builds.items():
            build = json.loads(path.read_text())
            assert build['status'] == 'passed'
            assert all(build['tests'][profile] == dict(passed=360 if mode == 'baseline' else 363, ignored=1)
                       for profile in ['test-debug', 'test-release'])
            directory, _ = installed_tools(build['tool_key'])
            vms[mode] = directory / 'rust-interp-vm'
            assert sha(vms[mode]) == build['binaries']['rust-interp-vm']
            paths.append(vms[mode])
        qualification_path = ROOT / 'results/fixed-frame-clear-entropy-check-01/summary.json'
        qualification = json.loads(qualification_path.read_text())
        assert qualification['status'] == 'passed' and qualification['commands'] == 17 and qualification['expected_rejections'] == 10
        library = ROOT / qualification['library']
        assert sha(library) == qualification['library_sha256']
        paths += [qualification_path, library]
        inputs = {}
        for number in ['01', '02']:
            report_path = ROOT / 'results' / ('constant-specialize-replay-' + number) / 'summary.json'
            report = json.loads(report_path.read_text())
            assert report['status'] == 'passed' and all(c['exact_entropy_replay'] for c in report['cases'])
            old_work = ROOT / report['raw']
            plan_path, records_path = old_work / 'plan.json', old_work / 'records.json'
            assert sha(plan_path) == report['plan_sha256'] and sha(records_path) == report['records_sha256']
            plan = json.loads(plan_path.read_text())
            records = json.loads(records_path.read_text())
            paths += [report_path, plan_path, records_path]
            for item in plan['inputs']:
                case = item['case']
                artifact, catalog = Path(item['artifacts']['baseline']), Path(item['catalog'])
                assert sha(artifact) == plan['frozen'][str(artifact.relative_to(ROOT))]
                assert sha(catalog) == plan['frozen'][str(catalog.relative_to(ROOT))]
                base = dict(case=case, artifact=str(artifact), catalog=str(catalog), names=item['names'], limits=item['limits'])
                entry = inputs.setdefault(case, dict(**base, streams=[]))
                assert {k: entry[k] for k in base} == base
                rows = [r for r in records if r['case'] == case and r['mode'] == 'baseline' and r['pair'] == -1]
                assert len(rows) == 1 and rows[0]['returncode'] == 0
                row = rows[0]
                tape = old_work / (case + '.tape')
                assert sha(tape) == row['tape_sha256']
                suite_path = old_work / (case + '--1-baseline-suite.json')
                suite, _ = read_report(suite_path, row['suite_sha256'])
                validate_report(suite, item['names'], 'prepared', True)
                validate_runtime_limits(suite, item['limits']['instructions'], item['limits']['allocations'], required=True)
                expected = [{k: t[k] for k in ['name', 'function', 'instructions', 'peak_guest_memory']} for t in suite['tests']]
                entry['streams'].append(dict(tape=str(tape), sha256=sha(tape), entropy=row['entropy'], expected=expected))
                paths += [artifact, catalog, tape, suite_path]
        assert set(inputs) == {'token', 'folded', 'pgrust'} and all(len(i['streams']) == 2 for i in inputs.values())
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, inputs=list(inputs.values()),
            binaries={mode: str(vm) for mode, vm in vms.items()}, pairs=6, measured_streams=[0, 1, 1, 0, 0, 1],
            minimum_free_gib=3, scope='Prepared-suite saved-artifact runtime including startup; no export or changed-source compilation.'))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library), RUST_INTERP_ENTROPY_MODE='replay', RUST_INTERP_VM_STATS='1')
        records, cases = [], []
        for case in ['token', 'folded', 'pgrust']:
            item = inputs[case]
            for pair in range(-1, 6):
                stream = 0 if pair < 0 else [0, 1, 1, 0, 0, 1][pair]
                reference = item['streams'][stream]
                for mode in (['baseline', 'candidate'] if pair % 2 == 0 else ['candidate', 'baseline']):
                    require_space(ROOT, 3)
                    suite_path = work / f'{case}-{pair}-{mode}-suite.json'
                    command = [str(vms[mode]), '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
                        '--isolated-batch', 'prepared', '--suite-report', str(suite_path), '--suite-catalog', item['catalog'],
                        '--instruction-limit', str(item['limits']['instructions']), '--allocation-limit', str(item['limits']['allocations']), item['artifact']]
                    before, started = child_usage(), time.perf_counter()
                    child, stdout, stderr = capture(command, cwd=ROOT, env=dict(env, RUST_INTERP_ENTROPY_TAPE=reference['tape']),
                        receipt_path=work / 'active.json', receipt=dict(case=case, mode=mode, pair=pair, stream=stream))
                    row = dict(case=case, mode=mode, pair=pair, stream=stream, command=command, pid=child.pid,
                        returncode=child.returncode, seconds=time.perf_counter()-started, cpu=child_cpu_since(before), stdout=stdout, stderr=stderr)
                    records.append(row)
                    write(work / 'records.json', records)
                    assert child.returncode == 0 and stdout == '0\n', stderr
                    suite, digest = read_report(suite_path)
                    validate_report(suite, item['names'], 'prepared', True)
                    validate_runtime_limits(suite, item['limits']['instructions'], item['limits']['allocations'], required=True)
                    observed = [{k: t[k] for k in ['name', 'function', 'instructions', 'peak_guest_memory']} for t in suite['tests']]
                    entropy = {k: int(v) for k, v in re.findall(r'\b(entropy_calls|entropy_bytes)=(\d+)\b', stderr)}
                    assert observed == reference['expected'] and entropy == reference['entropy']
                    assert sha(reference['tape']) == reference['sha256']
                    assert all(t['jit_declined_functions'] == 0 for t in suite['tests'])
                    row.update(suite_sha256=digest, entropy=entropy, instructions=sum(t['instructions'] for t in observed))
                    write(work / 'records.json', records)
                    print(case, pair, mode, round(row['seconds'], 3), 'passed', flush=True)
            pairs = []
            for pair in range(6):
                selected = {r['mode']: r for r in records if r['case'] == case and r['pair'] == pair}
                pairs.append(dict(pair=pair, stream=selected['baseline']['stream'],
                    wall_ratio=selected['candidate']['seconds']/selected['baseline']['seconds'],
                    cpu_ratio=selected['candidate']['cpu']['total_seconds']/selected['baseline']['cpu']['total_seconds']))
            cases.append(dict(case=case, tests=len(item['names']), pairs=pairs,
                median_wall_ratio=statistics.median(p['wall_ratio'] for p in pairs),
                median_cpu_ratio=statistics.median(p['cpu_ratio'] for p in pairs)))
            write(work / 'cases.json', cases)
        assert all(sha(ROOT / p) == digest for p, digest in frozen.items())
        primary = cases[0]
        gate = primary['median_wall_ratio'] <= .90 and primary['median_cpu_ratio'] < 1
        gate = gate and all(c['median_wall_ratio'] <= 1.05 and c['median_cpu_ratio'] <= 1.05 for c in cases[1:])
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', runtime_screen_passed=gate, commands=len(records), cases=cases,
            exact_per_test_counts_memory_and_entropy=True, source_inputs_unchanged=True, new_entropy_recordings=0,
            complete_workflow_measurement=False, runtime_binaries={mode: sha(vm) for mode, vm in vms.items()},
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json')))
        print('runtime_screen_passed', gate, flush=True)


if __name__ == '__main__':
    main()
