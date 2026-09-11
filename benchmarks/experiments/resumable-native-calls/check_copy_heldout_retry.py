#!/usr/bin/env python3
"""Qualify one retry substitution, unchanged gates, and mandatory admission."""
import argparse
from copy import deepcopy
import fcntl
import json
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).parent))
import assess_copy_heldout_retry as retry

ROOT, gates, original = retry.ROOT, retry.gates, retry.original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    gates.require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid run ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = ROOT / 'benchmarks/experiments/resumable-native-calls/COPY-HELDOUTS-RETRY-01.json'
        amendment, parent = gates.read(path), gates.read(ROOT / retry.PARENT)
        gates.require(gates.sha(ROOT / retry.PARENT) == retry.PARENT_SHA and
                      gates.sha(ROOT / retry.FAILURE) == retry.FAILURE_SHA, 'original plan or stop assessment changed')
        gates.require(all(gates.sha(ROOT / name) == digest for name, digest in amendment['sources'].items()),
                      'retry code differs from the declared amendment')
        counts = dict(primary_commands=63, check_commands=21, edited_pairs=15, artifacts=42)
        components = []
        for label in original.ORDER:
            row = dict(workload=label, target_max_ratio=1.05, median_paired_ratio=1.0,
                       median_paired_cpu_ratio=1.0, passed=True)
            components.append((dict(counts=counts.copy()), dict(held_out_case=label, held_out_workflows_run=False,
                retained=False, source_commit=original.SOURCE, tool_key=original.KEY,
                baseline_tool_key=gates.BASELINE, evaluated=[row])))
        before, after = original.combine(parent, components), retry.combine(amendment, parent, components)
        gates.require(before['counts'] == after['counts'] and
            [r['evaluation'] for r in before['workflows']] == [r['evaluation'] for r in after['workflows']] and
            after['workflows'][0]['run_id'] == retry.RETRY and
            [r['run_id'] for r in after['workflows'][1:]] == [r['run_id'] for r in before['workflows'][1:]],
            'retry changed complete-set arithmetic or another case identity')
        regressed = deepcopy(components)
        regressed[0][1]['evaluated'][0].update(median_paired_ratio=1.051, median_paired_cpu_ratio=1.06, passed=False)
        result = retry.combine(amendment, parent, regressed)
        gates.require(result['wall_regressions_above_5_percent'] == ['nushell-type-relations'] and
                      result['cpu_regressions_above_5_percent'] == ['nushell-type-relations'],
                      'retry discarded a regression')
        rejected = []

        def reject(label, callback):
            try:
                callback()
            except RuntimeError:
                rejected.append(label)
            else:
                raise RuntimeError('accepted invalid retry: ' + label)

        for count in range(7):
            reject('incomplete-' + str(count), lambda: retry.combine(amendment, parent, components[:count]))
        reject('extra-case', lambda: retry.combine(amendment, parent, components + components[:1]))
        for key in ['owner', 'parent_plan', 'parent_plan_sha256', 'stopped_history', 'stopped_history_sha256',
                    'admission_report', 'output_run_id', 'minimum_retry_free_bytes']:
            changed = deepcopy(amendment)
            changed[key] = 'wrong'
            reject('amendment-' + key, lambda: retry.validate_amendment(changed, parent))
        for key in ['label', 'original_run_id', 'retry_run_id']:
            changed = deepcopy(amendment)
            changed['replacement'][key] = 'another-case'
            reject('replacement-' + key, lambda: retry.validate_amendment(changed, parent))
        changed = deepcopy(amendment)
        changed['sources'] = {}
        reject('unbound-evaluators', lambda: retry.validate_amendment(changed, parent))
        changed = deepcopy(parent)
        changed['options']['cycles'] = 4
        reject('extra-repetitions', lambda: retry.validate_amendment(amendment, changed))
        admission = dict(owner=str(ROOT), run_id=retry.RETRY + '-preflight', case='nushell-type-relations',
            status='space admission passed', passed=True, benchmark_started=False, compiler_caches_modified=False,
            estimate=dict(minimum_free_bytes=retry.MINIMUM_FREE, command_floor_bytes=8 * 1024**3),
            observed_free_bytes=retry.MINIMUM_FREE, additional_bytes_required=0, checked_at=1000.0)
        retry.validate_admission(admission, 1000.0)
        retry.validate_admission(admission, 1060.0)
        reject('stale-admission', lambda: retry.validate_admission(admission, 1060.001))
        reject('future-admission', lambda: retry.validate_admission(admission, 999.999))
        for key, value in [('passed', False), ('benchmark_started', True), ('compiler_caches_modified', True),
                           ('observed_free_bytes', retry.MINIMUM_FREE - 1), ('additional_bytes_required', 1)]:
            changed = deepcopy(admission)
            changed[key] = value
            reject('admission-' + key, lambda: retry.validate_admission(changed, 1001.0))
        changed = deepcopy(admission)
        changed['estimate']['command_floor_bytes'] = 0
        reject('omitted-running-floor', lambda: retry.validate_admission(changed, 1001.0))
        reproduced = []
        evidence = {str(path.relative_to(ROOT)): gates.sha(path)}
        for run, copy_mode in [('resumable-copy-original-e2e-01', False), ('resumable-copy-e2e-01', True)]:
            options = SimpleNamespace(run_id=run, source_commit=original.SOURCE,
                held_out=False, held_out_case=None, copy_transitions=copy_mode)
            checked, evaluated = gates.evaluate(options)
            for name, value in [('final-verification.json', checked), ('gate-evaluation.json', evaluated)]:
                report = ROOT / 'results' / run / name
                gates.require(gates.read(report) == value, 'original primary gate changed')
                evidence[str(report.relative_to(ROOT))] = gates.sha(report)
            reproduced.append(dict(run_id=run, counts=checked['counts'], identical=True))
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        (out / 'summary.json').write_text(json.dumps(dict(status='passed', complete_set_fixture_passed=True,
            regression_fixture_retained=True, exact_admission_boundary_checked=True, rejected=rejected,
            historical_primary_receipts=reproduced, evidence=evidence, sources=amendment['sources'],
            performance_measurement=False), indent=2) + '\n')
        (out / 'assessment.md').write_text(
            'The single Nushell retry substitution preserves all seven cases and their arithmetic. '
            'A regression remains a regression, and both existing primary gate receipts reproduce exactly. '
            f'{len(rejected)} incomplete sets, changed controls/identities and invalid admissions are rejected. '
            'The exact 60-second admission boundary is checked. No new benchmark was run.\n')
        print(json.dumps(dict(status='passed', rejections=len(rejected), historical_primaries=2)))


if __name__ == '__main__':
    main()
