#!/usr/bin/env python3
"""Verify the fixed worker cold histories and their predeclared completion bounds."""
import argparse
import fcntl
from fractions import Fraction
import json
from pathlib import Path
from statistics import median
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_repeated_workflow import require, verify
from workflow_io import write_json
from assess_worker_warm import read, sha, receipt, checked_primary, TOOL, VM, EXPORTER, STD, PINS

ORDERS = ['native,baseline,candidate', 'candidate,baseline,native', 'baseline,candidate,native',
          'native,candidate,baseline', 'candidate,native,baseline', 'baseline,native,candidate']


def median_lower_bound(known):
    require(1 <= len(known) <= 6 and all(isinstance(value, Fraction) and value > 0 for value in known),
            'cold bound requires one through six positive exact ratios')
    return median([*known, *([Fraction(0)] * (6 - len(known)))])


def checked_cold(index):
    name = f'worker-count-nushell-cold-{index:02d}'
    expected = receipt('worker-count-nushell-qualification-01')
    expected[expected.index('--run-id') + 1] = name
    expected += ['--initial-mode-order', ORDERS[index - 1]]
    require(receipt(name) == expected, 'cold command differs from qualified recipe')
    out = ROOT / 'results' / name
    report = read(out / 'summary.json')
    require(report['project'] == 'nushell' and report['workflow'] == 'nushell-generic-list' and
            report['revision'] == PINS['nushell'] and report['cycles'] == 1 and len(report['edits']) == 1 and
            report['raw'] == '.work/runs/' + name, 'unexpected cold workflow')
    settings = dict(engine='jit', tool_key=TOOL, jit_persistent_registers=False,
        jit_resumable_calls=False, inline_leaves=True, jit_native_calls=False,
        jit_native_call_stubs=False, trap_unsupported_calls=False,
        run_try_callbacks=False, guest_rustflags=[], vm_sha256=VM, exporter_sha256=EXPORTER)
    require(report['tool_builds'] == dict(baseline=settings, candidate=settings) and
            report['custom_build_jobs'] == dict(baseline=4, candidate=18) and
            report['native_control'] == dict(profile='o0-incremental', jobs=18, test_threads='default', rustflags=[]) and
            report['std_mir']['key'] == STD, 'cold tool/worker settings differ')
    installed = ROOT / '.work/interpreter-tools' / TOOL
    binaries = {'rust-interp-vm': VM, 'rust-interp-mir-export': EXPORTER}
    require(read(installed / 'ready.json') == binaries and
            all(sha(installed / name) == digest for name, digest in binaries.items()), 'installed tools changed')
    require(len(report['scripts_sha256']) == 11 and
            all(sha(ROOT / path) == digest for path, digest in report['scripts_sha256'].items()),
            'frozen cold inputs changed')
    verified = verify(report)
    require(verified == read(out / 'verification.json') and verified['commands'] == 9 and
            verified['check_commands'] == 3 and verified['exact_artifact_hashes_verified'] == 6,
            'cold workflow verification differs')
    raw = ROOT / report['raw']
    rows = read(raw / 'records.json')
    traces = [call['launch']['compiler_wrapper'] for row in rows if row['mode'] != 'native' for call in row['calls']]
    require(traces == [dict(name='rust-interp-mir-export', sha256=EXPORTER)] * 6, 'cold wrapper traces differ')
    relative = read(raw / 'case.json')['case']['file']
    source = ROOT / '.work/sources/nushell'
    original = subprocess.check_output(['git', '-C', str(source), 'show', PINS['nushell'] + ':' + relative])
    require((source / relative).read_bytes() == original and subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == PINS['nushell'], 'source not restored')
    cold = {row['mode']: dict(wall_seconds=row['seconds'], cpu_seconds=row['cpu_seconds'])
            for row in rows if row['phase'] == 'cold'}
    ratios = {kind: Fraction(str(cold['candidate'][kind + '_seconds'])) /
              Fraction(str(cold['baseline'][kind + '_seconds'])) for kind in ['wall', 'cpu']}
    return out, dict(run=name, initial_mode_order=ORDERS[index - 1], cold=cold,
        ratios={kind: dict(value=float(value), exact_fraction=str(value)) for kind, value in ratios.items()},
        verification=verified, source_revision=PINS['nushell'], source_restored=True,
        frozen_input_hashes=11, compiler_wrapper_traces=6, report_sha256=sha(out / 'summary.json'),
        records_sha256=sha(raw / 'records.json'), assessor_sha256=sha(Path(__file__)))


def decision(count):
    observations = []
    for index in range(1, count + 1):
        out, result = checked_cold(index)
        require(result == read(out / 'cold-observation.json'), 'stored cold observation differs')
        observations.append(result)
    warm = [checked_primary(project)[1] for project in ['pgrust', 'nushell']]
    remaining = 6 - count
    bounds = {}
    for kind, threshold in [('wall', Fraction(9, 10)), ('cpu', Fraction(11, 10))]:
        known = [Fraction(row['ratios'][kind]['exact_fraction']) for row in observations]
        lower = median_lower_bound(known)
        bounds[kind] = dict(minimum_possible_six_sample_median=float(lower), exact_fraction=str(lower),
            threshold=float(threshold), impossible_to_pass=lower > threshold)
    warm_pass = all(w['warm_wall_guard_passed'] and w['cpu_guard_passed'] for w in warm)
    failure = not warm_pass or any(b['impossible_to_pass'] for b in bounds.values())
    unstarted = []
    if remaining and failure:
        for index in range(count + 1, 7):
            name = f'worker-count-nushell-cold-{index:02d}'
            require(all(not (ROOT / parent / name).exists() for parent in
                        ['results', '.work/runs', '.work/experiments']), 'a remaining cold history was already started')
            unstarted.append(name)
    return dict(status=('six cold histories verified' if remaining == 0 else
                        'incomplete; deterministic failure bound' if failure else 'incomplete; continue fixed histories'),
        completed_cold_histories=count, planned_cold_histories=6, observations=observations,
        warm=[dict(project=w['project'], ratios=w['ratios'], warm_wall_guard_passed=w['warm_wall_guard_passed'],
                   cpu_guard_passed=w['cpu_guard_passed'], report_sha256=w['report_sha256']) for w in warm],
        bounds=bounds, warm_guards_passed=warm_pass, unstarted_for_futility=unstarted,
        eligible_for_held_out_checks=remaining == 0 and not failure, retained=False,
        assessor_sha256=sha(Path(__file__)),
        note='Zero padding is a mathematical lower bound, never a missing measurement. Only the original-source cold command of each named history enters the cold criterion. Qualification and warm anchors are excluded. No early acceptance or additional trials; held-out checks remain required if all six histories pass.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--index', type=int, choices=range(1, 7))
    action.add_argument('--decision-through', type=int, choices=range(1, 7))
    args = parser.parse_args()
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.index:
            out, result = checked_cold(args.index)
            target = out / 'cold-observation.json'
        else:
            result = decision(args.decision_through)
            out = ROOT / 'results' / f'worker-count-cold-decision-through-{args.decision_through:02d}'
            out.mkdir(exist_ok=False)
            target = out / 'summary.json'
        require(not target.exists(), 'assessment already exists')
        write_json(target, result)
        print(json.dumps({key: result[key] for key in ['run', 'ratios', 'status', 'bounds', 'eligible_for_held_out_checks']
                          if key in result}))


if __name__ == '__main__':
    main()
