#!/usr/bin/env python3
"""Qualify unchanged primary gates, complete-set checks and an optional real case."""
import argparse
import copy
import fcntl
import json
from pathlib import Path
from statistics import median
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent))
import assess_separate_heldouts as separate
gates = separate.gates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--case-run', help='completed excluded pgrust corpus used for actual single-case qualification')
    args = parser.parse_args()
    gates.require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid run ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        evidence, reproduced = {}, []
        for run, copy_mode in [('resumable-copy-original-e2e-01', False), ('resumable-copy-e2e-01', True)]:
            options = SimpleNamespace(run_id=run, source_commit=separate.SOURCE,
                held_out=False, held_out_case=None, copy_transitions=copy_mode)
            checked, result = gates.evaluate(options)
            for name, value in [('final-verification.json', checked), ('gate-evaluation.json', result)]:
                path = ROOT / 'results' / run / name
                gates.require(gates.read(path) == value, 'historical primary receipt differs')
                evidence[str(path.relative_to(ROOT))] = gates.sha(path)
            reproduced.append(dict(run_id=run, counts=checked['counts'], gates_identical=True))
        near_misses = []
        for run in ['resumable-bulk-e2e-01', 'resumable-bulk-e2e-02']:
            path = ROOT / 'results' / (run + '-token-phrase') / 'summary.json'
            report = gates.read(path)
            ratio = median(p['candidate_seconds'] / p['baseline_seconds'] for p in report['comparison']['pairs'])
            gate_path = ROOT / 'results' / run / 'gate-evaluation.json'
            row = next(r for r in gates.read(gate_path)['evaluated'] if r['workload'] == 'token-phrase')
            gates.require(row['median_paired_ratio'] == ratio and ratio > .8 and row['passed'] is False,
                          'historical near-miss arithmetic changed')
            near_misses.append(dict(run_id=run, ratio=ratio, passed=False, arithmetic_only=True))
            evidence[str(path.relative_to(ROOT))] = gates.sha(path)
            evidence[str(gate_path.relative_to(ROOT))] = gates.sha(gate_path)
        plan = dict(schema_version=1, owner=str(ROOT), run_id='resumable-copy-heldout-01',
                    source_commit=separate.SOURCE, options=copy.deepcopy(separate.OPTIONS))
        plan['cases'] = [dict(label=label, run_id=plan['run_id'] + f'-case-{i:02}') for i, label in enumerate(separate.ORDER, 1)]
        counts = dict(primary_commands=63, check_commands=21, edited_pairs=15, artifacts=42)
        components = []
        for label in separate.ORDER:
            row = dict(workload=label, target_max_ratio=1.05, median_paired_ratio=1.0, median_paired_cpu_ratio=1.0, passed=True)
            components.append((dict(counts=counts.copy()), dict(held_out_case=label, held_out_workflows_run=False,
                retained=False, source_commit=separate.SOURCE, tool_key=separate.KEY, baseline_tool_key=gates.BASELINE,
                evaluated=[row])))
        gates.require(separate.combine(plan, components)['held_out_wall_checks_passed'], 'complete fixture did not pass')
        regressed = copy.deepcopy(components)
        regressed[0][1]['evaluated'][0].update(median_paired_ratio=1.051, passed=False)
        gates.require(not separate.combine(plan, regressed)['held_out_wall_checks_passed'], 'regression was discarded')
        rejected = []
        def reject(label, operation):
            try:
                operation()
            except RuntimeError:
                rejected.append(label)
            else:
                raise RuntimeError('accepted invalid separate qualification: ' + label)
        for length in range(7):
            reject('incomplete-set-' + str(length), lambda length=length: separate.combine(plan, components[:length]))
        reject('duplicate-extra-case', lambda: separate.combine(plan, components + components[:1]))
        for key, value in [('source_commit', 'wrong'), ('run_id', 'wrong'), ('owner', '/wrong'),
                           ('cases', plan['cases'][::-1])]:
            altered = {**plan, key: value}
            reject('plan-' + key, lambda altered=altered: separate.combine(altered, components))
        for key in separate.OPTIONS:
            altered = copy.deepcopy(plan); altered['options'][key] = 'wrong'
            reject('control-' + key, lambda altered=altered: separate.combine(altered, components))
        for field, value in [('held_out_workflows_run', True), ('held_out_case', 'wrong'),
                             ('retained', True), ('tool_key', 'wrong'), ('baseline_tool_key', 'wrong')]:
            altered = copy.deepcopy(components); altered[0][1][field] = value
            reject('component-' + field, lambda altered=altered: separate.combine(plan, altered))
        altered = copy.deepcopy(components); altered[0][0]['counts']['artifacts'] -= 1
        reject('missing-artifact-count', lambda: separate.combine(plan, altered))
        for all_cases, single, copy_mode in [(True, 'pgrust', False), (False, 'pgrust', True), (False, 'wrong', False)]:
            options = SimpleNamespace(run_id='resumable-copy-original-e2e-01', source_commit=separate.SOURCE,
                held_out=all_cases, held_out_case=single, copy_transitions=copy_mode)
            reject('incompatible-gate-options-' + str(len(rejected)), lambda options=options: gates.evaluate(options))
        actual = None
        if args.case_run:
            gates.require(args.case_run == 'resumable-copy-heldout-qualification-01', 'unexpected qualification corpus')
            options = SimpleNamespace(run_id=args.case_run, source_commit=separate.SOURCE,
                held_out=False, held_out_case='pgrust', copy_transitions=False)
            checked, result = gates.evaluate(options)
            gates.require(checked['counts'] == counts and result['held_out_case'] == 'pgrust' and
                          result['held_out_workflows_run'] is False, 'actual case scope differs')
            for name, value in [('final-verification.json', checked), ('gate-evaluation.json', result)]:
                path = ROOT / 'results' / args.case_run / name
                gates.require(gates.read(path) == value, 'actual case receipt differs')
                evidence[str(path.relative_to(ROOT))] = gates.sha(path)
            actual = dict(run_id=args.case_run, counts=checked['counts'], qualification_only=True,
                          all_seven_claimed=False)
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        paths = [Path(__file__), Path(separate.__file__), Path(gates.__file__)]
        result = dict(status='passed', historical_primaries=reproduced, historical_near_miss_arithmetic=near_misses,
            complete_set_fixture_passed=True, regression_fixture_retained=True, rejected=rejected,
            actual_single_case=actual, sources={str(p.relative_to(ROOT)): gates.sha(p) for p in paths},
            evidence=evidence, performance_measurement=False)
        (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(dict(status='passed', historical_primaries=2, rejections=len(rejected), actual_case=actual)))


if __name__ == '__main__':
    main()
