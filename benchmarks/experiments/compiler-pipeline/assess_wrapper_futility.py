#!/usr/bin/env python3
"""Verify whether the unfinished six-history wrapper gate is unreachable."""
import fcntl
from fractions import Fraction
from pathlib import Path
from statistics import median

from assess_wrapper_cold import ROOT, checked_run, read, sha
from verify_repeated_workflow import require, verify
from workflow_io import write_json


def assess():
    out = ROOT / 'results/lightweight-wrapper-cold-futility-01'
    require(not out.exists(), 'futility assessment already exists')
    protocol = ROOT / 'benchmarks/experiments/compiler-pipeline/REPEATED.md'
    require('All runs remain separate cache histories.' in protocol.read_text() and
            'Use all six within-run candidate/baseline wall ratios' in protocol.read_text(),
            'original six-history protocol is missing')
    runs, ratios = [], []
    for index in range(1, 5):
        path, frozen, result = checked_run(index)
        require(read(path / 'frozen-inputs.json') == frozen, 'stored source verification differs')
        cold = result['cold']
        # Use exact rational arithmetic on the recorded decimal durations.
        ratio = (Fraction(str(cold['candidate']['wall_seconds'])) /
                 Fraction(str(cold['baseline']['wall_seconds'])))
        require(ratio > 0, 'invalid observed cold ratio')
        ratios.append(ratio)
        runs.append(dict(result, exact_decimal_duration_ratio=str(ratio)))
    unexecuted = []
    for index in [5, 6]:
        name = f'lightweight-wrapper-nushell-cold-{index:02d}'
        require(all(not (ROOT / prefix / name).exists()
                    for prefix in ['results', '.work/runs', '.work/experiments']),
                'a remaining cold history already has execution evidence')
        unexecuted.append(name)

    # Two unknown ratios can occupy at most two positions below the known ones.
    # Thus the third/fourth of six values cannot fall below the two smallest
    # known ratios. Zero is a conservative mathematical bound, not a sample.
    smallest = sorted(ratios)[:2]
    lower_bound = sum(smallest) / 2
    require(lower_bound == median([Fraction(0), Fraction(0), *ratios]),
            'median lower-bound calculation disagrees')
    require(lower_bound > Fraction(95, 100), 'remaining measurements could still pass the cold gate')

    warm = []
    for project in ['pgrust', 'nushell']:
        path = ROOT / 'results' / f'lightweight-wrapper-{project}-repeated-01' / 'summary.json'
        report, stored = read(path), read(path.with_name('verification.json'))
        reference = (read(ROOT / 'results' / f'lightweight-wrapper-{project}-qualification-01' / 'summary.json')
                     if stored['reference_bytecode'] is not None else None)
        require(verify(report, reference) == stored and report['cycles'] == 15,
                'warm comparison verification differs')
        rows = read(ROOT / report['raw'] / 'records.json')
        values = {(r['cycle'], r['state'], r['mode']): r for r in rows if r['state'] > 0}
        ratios_from_records = []
        for pair in report['comparison']['pairs']:
            candidate = values[pair['cycle'], pair['state'], 'candidate']
            baseline = values[pair['cycle'], pair['state'], 'baseline']
            require(pair['candidate_seconds'] == candidate['seconds'] and
                    pair['baseline_seconds'] == baseline['seconds'], 'warm pair differs from raw commands')
            ratios_from_records.append(candidate['seconds'] / baseline['seconds'])
        require(len(ratios_from_records) == 15, 'unexpected warm pair count')
        warm.append(dict(project=project, pairs=15, wall_ratio=median(ratios_from_records),
                         report_sha256=sha(path), verification=stored))

    result = dict(
        status='cold gate mathematically unreachable; original six-history protocol incomplete',
        originally_required_cold_histories=6, verified_cold_histories=4,
        unexecuted_histories=unexecuted, original_six_history_protocol_completed=False,
        runs=runs, warm=warm, required_maximum_median_wall_ratio='19/20',
        minimum_possible_six_history_median_wall_ratio=float(lower_bound),
        exact_lower_bound=str(lower_bound),
        maximum_possible_six_history_improvement_percent=float(100 * (1 - lower_bound)),
        measured_six_history_median=None, cold_gate_unreachable=True,
        warm_regression_guard_passed=all(w['wall_ratio'] <= 1.05 for w in warm),
        eligible_for_held_out_checks=False, retained=False,
        original_protocol_sha256=sha(protocol), assessor_sha256=sha(Path(__file__)),
        cold_verifier_sha256=sha(Path(__file__).with_name('assess_wrapper_cold.py')),
        decision='Stop the two unstarted wrapper histories for deterministic futility; preserve all observations.',
        note='This stopping rule was not predeclared. The protocol is amended openly to avoid measurements '
             'that cannot change rejection under its existing gate. No six-sample estimate, missing timings, '
             'significance claim or relaxed threshold is reported. The unbounded development goal remains active.')
    out.mkdir()
    write_json(out / 'summary.json', result)
    (out / 'assessment.md').write_text(
        '# Stop the wrapper comparison for deterministic futility\n\n'
        'All four completed cold histories verify, as do both fifteen-cycle warm\n'
        'comparisons. Cold histories 05 and 06 have no run, experiment or result\n'
        'directories and have not started. The original six-history protocol is\n'
        '**incomplete**. A futility stopping rule was not predeclared; this report\n'
        'records the amendment and preserves the original observations and gate.\n\n'
        'For any two additional nonnegative candidate/baseline ratios, the third\n'
        'and fourth values of the sorted six cannot be smaller than the two\n'
        'smallest known values. Therefore their average is a lower bound on the\n'
        f'six-sample median: **{float(lower_bound):.10f}**, or at most\n'
        f'**{float(100 * (1 - lower_bound)):.4f}% improvement**. The required ratio\n'
        'is at most 0.95 (at least 5% improvement). No outcomes of the remaining\n'
        'two histories can make that criterion pass. Arithmetic uses exact\n'
        'fractions of the recorded decimal durations. Zero padding is a bound\n'
        'calculation, not fabricated benchmark data.\n\n'
        'The wrapper remains experimental and does not proceed to its conditional\n'
        'held-out checks. Its measured warm improvements remain reported. Stop\n'
        'the two unstarted histories and proceed to the independently specified\n'
        'worker-count experiment, with the same established tool in both arms.\n'
        'No measured six-history median or completed original protocol is claimed.\n\n'
        '[Full precision, observations and verification](summary.json).\n')
    print(f'cold gate unreachable: lower bound {float(lower_bound):.10f} > 0.95; '
          'four histories verified, two unexecuted')


if __name__ == '__main__':
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assess()
