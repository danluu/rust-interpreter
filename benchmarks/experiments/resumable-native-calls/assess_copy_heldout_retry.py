#!/usr/bin/env python3
"""Apply one explicit infrastructure retry while preserving all original gates."""
import argparse
from copy import deepcopy
import fcntl
import json
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).parent))
import assess_separate_heldouts as original

ROOT, gates = original.ROOT, original.gates
PARENT = 'benchmarks/experiments/resumable-native-calls/COPY-HELDOUTS.json'
PARENT_SHA = 'b12c33cc81f00558aebb03e104a9cb901fdb272417bf70b0124f2c13ec4a2e11'
FAILURE = 'results/resumable-copy-heldout-01-case-01-stop/summary.json'
FAILURE_SHA = '30f3e9ce848af9225cd5a945ccb38fe6271972d74a7f7e59cbd1bff575326eb8'
RETRY = 'resumable-copy-heldout-01-case-01-retry-01'
ADMISSION = 'results/' + RETRY + '-preflight/summary.json'
MINIMUM_FREE = 27906753093
SOURCES = {
    'benchmarks/experiments/resumable-native-calls/assess_copy_heldout_retry.py',
    'benchmarks/experiments/resumable-native-calls/check_copy_heldout_retry.py',
    'benchmarks/experiments/resumable-native-calls/preflight_copy_heldout_retry.py',
    'scripts/workflow_space.py',
}


def validate_amendment(amendment, parent):
    cases = deepcopy(original.validate_plan(parent))
    replacement = dict(label='nushell-type-relations', original_run_id=cases[0]['run_id'], retry_run_id=RETRY)
    gates.require(set(amendment) == {'schema_version', 'owner', 'parent_plan', 'parent_plan_sha256',
        'stopped_history', 'stopped_history_sha256', 'replacement', 'admission_report',
        'minimum_retry_free_bytes', 'output_run_id', 'sources'}, 'unknown retry amendment fields')
    gates.require(amendment['schema_version'] == 1 and amendment['owner'] == str(ROOT) and
        amendment['parent_plan'] == PARENT and amendment['parent_plan_sha256'] == PARENT_SHA and
        amendment['stopped_history'] == FAILURE and amendment['stopped_history_sha256'] == FAILURE_SHA and
        amendment['replacement'] == replacement and amendment['admission_report'] == ADMISSION and
        amendment['minimum_retry_free_bytes'] == MINIMUM_FREE and
        amendment['output_run_id'] == 'resumable-copy-heldout-recovery-01',
        'retry amendment changes more than the one declared infrastructure retry')
    gates.require(set(amendment['sources']) == SOURCES and
        all(isinstance(value, str) and len(value) == 64 and set(value) <= set('0123456789abcdef')
            for value in amendment['sources'].values()), 'retry estimator or evaluator binding is missing')
    cases[0]['run_id'] = RETRY
    return cases


def validate_admission(admission, start_time):
    gates.require(admission['owner'] == str(ROOT) and admission['run_id'] == RETRY + '-preflight' and
        admission['case'] == 'nushell-type-relations' and admission['status'] == 'space admission passed' and
        admission['passed'] is True and admission['benchmark_started'] is False and
        admission['compiler_caches_modified'] is False and
        admission['estimate']['minimum_free_bytes'] == MINIMUM_FREE and
        admission['estimate']['command_floor_bytes'] == 8 * 1024**3 and
        admission['observed_free_bytes'] >= MINIMUM_FREE and admission['additional_bytes_required'] == 0 and
        admission['checked_at'] <= start_time <= admission['checked_at'] + 60,
        'retry lacks a recent successful admission with the original running floor')


def combine(amendment, parent, components):
    cases = validate_amendment(amendment, parent)
    # The original complete-set checks and all wall/CPU arithmetic are reused.
    result = original.combine(parent, components)
    for row, actual in zip(result['workflows'], cases):
        row['original_run_id'] = row['run_id']
        row['run_id'] = actual['run_id']
    result.update(status='all seven histories verified after one declared infrastructure retry',
        infrastructure_retry=amendment['replacement'], interrupted_history=FAILURE,
        excluded_partial_counts=dict(primary_commands=5, check_commands=1, artifacts=4, edited_pairs=0))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--amendment', type=Path, required=True)
    parser.add_argument('--amendment-sha256', required=True)
    args = parser.parse_args()
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = args.amendment.resolve()
        gates.require(path.is_relative_to(ROOT / 'benchmarks') and gates.sha(path) == args.amendment_sha256,
                      'retry amendment path or hash changed')
        amendment, parent = gates.read(path), gates.read(ROOT / PARENT)
        cases = validate_amendment(amendment, parent)
        bound = {PARENT: PARENT_SHA, FAILURE: FAILURE_SHA, str(path.relative_to(ROOT)): args.amendment_sha256,
            **parent['frozen'], **parent['evaluation_sources'], **parent['prerequisites'], **amendment['sources']}
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
            gates.require(corpus['plan']['options'] == dict(parent['options'], run_id=case['run_id'], only=[case['label']]) and
                          corpus['plan']['frozen'] == parent['frozen'], 'retry changed benchmark controls or sources')
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
