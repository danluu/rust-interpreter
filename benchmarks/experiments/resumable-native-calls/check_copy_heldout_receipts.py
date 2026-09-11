#!/usr/bin/env python3
"""Verify the exact receipt extension against all seven measured histories."""
from copy import deepcopy
import fcntl
import json
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).parent))
import assess_copy_heldout_receipts as subject

ROOT, gates = subject.ROOT, subject.gates


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        folder = ROOT / 'benchmarks/experiments/resumable-native-calls'
        adapter_path = folder / 'COPY-HELDOUTS-RECEIPT-ADAPTER.json'
        adapter = gates.read(adapter_path)
        subject.validate_adapter(adapter)
        gates.require(all(gates.sha(ROOT / name) == digest for name, digest in adapter['sources'].items()),
                      'adapter source changed')
        parent = gates.read(ROOT / subject.PARENT)
        amendment = gates.read(folder / 'COPY-HELDOUTS-RETRY-01.json')
        cases = subject.validate_amendment(amendment, parent)
        components, evidence, accepted = [], {}, []
        for case in cases:
            run = ROOT / 'results' / case['run_id']
            actual = gates.read(run / 'summary.json')['plan']
            subject.validate_corpus_plan(actual, parent, case)
            options = SimpleNamespace(run_id=case['run_id'], source_commit=subject.original.SOURCE,
                held_out=False, held_out_case=case['label'], copy_transitions=False)
            checked, evaluated = gates.evaluate(options)
            for name, value in [('final-verification.json', checked), ('gate-evaluation.json', evaluated)]:
                gates.require(gates.read(run / name) == value, 'existing per-case receipt changed')
                evidence[str((run / name).relative_to(ROOT))] = gates.sha(run / name)
            components.append((checked, evaluated))
            accepted.append(case['label'])
        rejected = []

        def reject(label, action):
            try:
                action()
            except RuntimeError:
                rejected.append(label)
            else:
                raise RuntimeError('invalid receipt accepted: ' + label)

        case = cases[0]
        actual = gates.read(ROOT / 'results' / case['run_id'] / 'summary.json')['plan']
        for value in [None, [], ['jobs'], ['native_jobs'], ['native_jobs', 'jobs'],
                      ['jobs', 'native_jobs', 'candidate_jobs'], ['jobs', 'jobs'], 'jobs,native_jobs']:
            altered = deepcopy(actual)
            altered['options']['_specified_job_counts'] = value
            reject('flag-list-' + repr(value), lambda: subject.validate_corpus_plan(altered, parent, case))
        for field in ['_specified_job_counts', 'native_jobs', 'candidate_tool_key']:
            altered = deepcopy(actual)
            del altered['options'][field]
            reject('missing-' + field, lambda: subject.validate_corpus_plan(altered, parent, case))
        for field, value in [('cycles', 4), ('jobs', 18), ('native_jobs', 4), ('candidate_jobs', 2),
            ('candidate_jit_resumable_calls', False), ('native_profile', 'repository'),
            ('minimum_free_gib', 0), ('unknown_option', True)]:
            altered = deepcopy(actual)
            altered['options'][field] = value
            reject('changed-' + field, lambda: subject.validate_corpus_plan(altered, parent, case))
        altered = deepcopy(actual)
        altered['frozen']['scripts/bench_e2e_workflow.py'] = '0' * 64
        reject('changed-frozen-source', lambda: subject.validate_corpus_plan(altered, parent, case))
        for field in ['schema_version', 'field', 'value', 'failure_report', 'failure_sha256',
                      'original_amendment_sha256']:
            altered_adapter = deepcopy(adapter)
            altered_adapter[field] = 'wrong'
            reject('adapter-' + field, lambda: subject.validate_adapter(altered_adapter))
        reject('incomplete-set', lambda: subject.combine(amendment, parent, components[:-1]))
        regressed = deepcopy(components)
        regressed[0][1]['evaluated'][0].update(median_paired_ratio=1.051, median_paired_cpu_ratio=1.06, passed=False)
        result = subject.combine(amendment, parent, regressed)
        gates.require(result['wall_regressions_above_5_percent'] == ['nushell-type-relations'] and
                      result['cpu_regressions_above_5_percent'] == ['nushell-type-relations'],
                      'original regression arithmetic changed')
        primaries = []
        for run, copy_mode in [('resumable-copy-original-e2e-01', False), ('resumable-copy-e2e-01', True)]:
            options = SimpleNamespace(run_id=run, source_commit=subject.original.SOURCE,
                held_out=False, held_out_case=None, copy_transitions=copy_mode)
            checked, evaluated = gates.evaluate(options)
            for name, value in [('final-verification.json', checked), ('gate-evaluation.json', evaluated)]:
                path = ROOT / 'results' / run / name
                gates.require(gates.read(path) == value, 'primary receipt changed')
                evidence[str(path.relative_to(ROOT))] = gates.sha(path)
            primaries.append(run)
        out = ROOT / 'results/copy-heldout-receipt-adapter-01'
        out.mkdir(exist_ok=False)
        result = dict(status='passed', actual_cases_verified=accepted, rejections=rejected,
            original_regression_preserved=True, primary_receipts_reproduced=primaries,
            benchmark_rerun=False, measurement_receipts_modified=False, evidence=evidence,
            adapter_plan_sha256=gates.sha(adapter_path), sources=adapter['sources'])
        (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
        (out / 'assessment.md').write_text(
            f'All seven actual corpus receipts and both primary comparisons reverify unchanged. '
            f'The adapter accepts only the exact parser-provenance list and rejects {len(rejected)} '
            'missing/changed fields, changed controls/sources and incomplete scope. '
            'The original regression arithmetic is preserved. No benchmark was rerun or receipt rewritten.\n')
        print(json.dumps(dict(status='passed', actual_cases=len(accepted), rejections=len(rejected), primaries=2)))


if __name__ == '__main__':
    main()
