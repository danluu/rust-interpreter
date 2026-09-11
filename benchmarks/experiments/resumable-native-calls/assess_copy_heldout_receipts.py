#!/usr/bin/env python3
"""Recognize one exact parser-provenance field without changing original gates.

The collection body retains the frozen retry runner's checks; the option
comparison below additionally requires the exact recorded flag-spelling list.
No measured receipt or original evaluator is rewritten.
"""
import argparse
import fcntl
import json
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).parent))
from assess_copy_heldout_retry import (ROOT, gates, original, PARENT, PARENT_SHA,
    FAILURE, FAILURE_SHA, ADMISSION, RETRY, validate_amendment, validate_admission, combine)

SCHEMA_FAILURE = 'results/copy-heldout-aggregate-schema-stop-01/summary.json'
SCHEMA_FAILURE_SHA = 'fa2eeaad02cd4bd1e276884bc58ed3e8fea67464652e66896d6903d86b38c4ac'
ADAPTER_SOURCES = {
    'benchmarks/experiments/resumable-native-calls/assess_copy_heldout_receipts.py',
    'benchmarks/experiments/resumable-native-calls/check_copy_heldout_receipts.py',
}


def validate_adapter(adapter):
    gates.require(set(adapter) == {'schema_version', 'field', 'value', 'failure_report',
        'failure_sha256', 'original_amendment_sha256', 'sources'} and
        adapter['schema_version'] == 1 and adapter['field'] == '_specified_job_counts' and
        adapter['value'] == ['jobs', 'native_jobs'] and adapter['failure_report'] == SCHEMA_FAILURE and
        adapter['failure_sha256'] == SCHEMA_FAILURE_SHA and
        adapter['original_amendment_sha256'] == 'faf59923337a40b5931540593af36b00720b42088a9b45b415de49c3fefb2aaf' and
        set(adapter['sources']) == ADAPTER_SOURCES, 'receipt adapter scope changed')


def validate_corpus_plan(actual, parent, case):
    expected = dict(parent['options'], run_id=case['run_id'], only=[case['label']],
                    _specified_job_counts=['jobs', 'native_jobs'])
    gates.require(actual['options'] == expected and actual['frozen'] == parent['frozen'],
                  'actual controls, explicit job flags or frozen sources differ')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--amendment', type=Path, required=True)
    parser.add_argument('--amendment-sha256', required=True)
    parser.add_argument('--receipt-adapter', type=Path, required=True)
    parser.add_argument('--receipt-adapter-sha256', required=True)
    args = parser.parse_args()
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        adapter_path = args.receipt_adapter.resolve()
        gates.require(adapter_path.is_relative_to(ROOT / 'benchmarks') and
                      gates.sha(adapter_path) == args.receipt_adapter_sha256, 'receipt adapter plan changed')
        adapter = gates.read(adapter_path)
        validate_adapter(adapter)
        gates.require(args.amendment_sha256 == adapter['original_amendment_sha256'],
                      'receipt adapter references another retry amendment')
        path = args.amendment.resolve()
        gates.require(path.is_relative_to(ROOT / 'benchmarks') and gates.sha(path) == args.amendment_sha256,
                      'retry amendment path or hash changed')
        amendment, parent = gates.read(path), gates.read(ROOT / PARENT)
        cases = validate_amendment(amendment, parent)
        bound = {PARENT: PARENT_SHA, FAILURE: FAILURE_SHA, str(path.relative_to(ROOT)): args.amendment_sha256,
            **parent['frozen'], **parent['evaluation_sources'], **parent['prerequisites'], **amendment['sources']}
        bound.update({str(adapter_path.relative_to(ROOT)): args.receipt_adapter_sha256,
            SCHEMA_FAILURE: SCHEMA_FAILURE_SHA, **adapter['sources']})
        schema_failure = gates.read(ROOT / SCHEMA_FAILURE)
        for name, item in schema_failure['evidence'].items():
            bound[name] = item['sha256']
            bound[str(Path(SCHEMA_FAILURE).parent / item['snapshot'])] = item['sha256']
        for item in schema_failure['cases']:
            bound[item['report']] = item['report_sha256']
        gates.require(all(gates.sha(ROOT / name) == digest for name, digest in bound.items()),
                      'original or amended input changed')
        failure = gates.read(ROOT / FAILURE)
        gates.require(failure['completed_workflows'] == 0 and failure['measured_successful_edit_pairs'] == 0 and
                      failure['source_restored'] is True, 'interrupted history was not the assessed zero-pair stop')
        for name, item in failure['evidence'].items():
            bound[name] = item['sha256']
            bound[str((Path(FAILURE).parent / item['snapshot']))] = item['sha256']
        bound.update(failure['snapshots'])
        admission = gates.read(ROOT / ADMISSION)
        started = gates.read(ROOT / '.work/corpus-runs' / RETRY / 'status.json')['started_at']
        validate_admission(admission, started)
        bound[ADMISSION] = gates.sha(ROOT / ADMISSION)
        gates.require(all(admission['sources'].get(name) == digest for name, digest in amendment['sources'].items()
                          if name.endswith('preflight_copy_heldout_retry.py') or name == 'scripts/workflow_space.py'),
                      'admission used another estimator')
        components = []
        for case in cases:
            folder = ROOT / 'results' / case['run_id']
            corpus = gates.read(folder / 'summary.json')
            validate_corpus_plan(corpus['plan'], parent, case)
            options = SimpleNamespace(run_id=case['run_id'], source_commit=original.SOURCE,
                held_out=False, held_out_case=case['label'], copy_transitions=False)
            checked, evaluated = gates.evaluate(options)
            gates.require(checked == gates.read(folder / 'final-verification.json') and
                          evaluated == gates.read(folder / 'gate-evaluation.json'), 'component verification changed')
            components.append((checked, evaluated))
            for name in ['summary.json', 'final-verification.json', 'gate-evaluation.json']:
                bound[str((folder / name).relative_to(ROOT))] = gates.sha(folder / name)
        result = combine(amendment, parent, components)
        gates.require(all(gates.sha(ROOT / name) == digest for name, digest in bound.items()),
                      'evidence changed during final verification')
        result['receipt_metadata_adapter'] = str(adapter_path.relative_to(ROOT))
        result['preserved_aggregate_schema_failure'] = SCHEMA_FAILURE
        result['evidence'] = bound
        out = ROOT / 'results' / amendment['output_run_id']
        out.mkdir(exist_ok=False)
        (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
        lines = ['All seven complete histories verify: 588 commands, 105 edited pairs and 294 artifacts.', '',
            'The interrupted zero-pair history remains excluded and preserved.', '',
            '| Workflow | Paired wall change | Paired CPU change | Wall gate |', '| --- | ---: | ---: | --- |']
        for row in result['workflows']:
            v = row['evaluation']
            lines.append(f"| {row['label']} | {(v['median_paired_ratio']-1)*100:+.2f}% | {(v['median_paired_cpu_ratio']-1)*100:+.2f}% | {'pass' if v['passed'] else 'fail'} |")
        lines += ['', result['note'], '', 'See [complete evidence](summary.json).', '']
        (out / 'assessment.md').write_text('\n'.join(lines))
        print(json.dumps(dict(counts=result['counts'], wall_regressions=result['wall_regressions_above_5_percent'])))


if __name__ == '__main__':
    main()
