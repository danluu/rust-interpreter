#!/usr/bin/env python3
"""Verify each fixed cold history, then assess the six-sample wrapper gate."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
from statistics import median
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_repeated_workflow import require, verify
from workflow_io import write_json

ORDERS = ['native,baseline,candidate', 'candidate,baseline,native', 'baseline,candidate,native',
          'native,candidate,baseline', 'candidate,native,baseline', 'baseline,native,candidate']
WRAPPERS = {
    'baseline': dict(name='rust-interp-mir-export', sha256='64d7102e21ae5017564076d40781c1c9f5e05cf62bff7abefb6f8519fd0fb317'),
    'candidate': dict(name='rust-interp-rustc-wrapper', sha256='ba366dd3b4815e4ddb25d130c5d1f861396bc24c3f99cf960bb7433618d29f35'),
}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_run(index):
    name = f'lightweight-wrapper-nushell-cold-{index:02d}'
    out = ROOT / 'results' / name
    report = read(out / 'summary.json')
    raw = ROOT / report['raw']
    require(report['raw'] == '.work/runs/' + name and report['project'] == 'nushell' and
            report['workflow'] == 'nushell-generic-list' and report['cycles'] == 1, 'unexpected cold case')
    qualification = ROOT / '.work/experiments/lightweight-wrapper-nushell-qualification-01'
    seed = read(qualification / 'status.json')
    require(seed['status'] == 'finished' and seed['returncode'] == 0 and
            seed['owner'] == str(ROOT) and seed['plan_sha256'] == sha(qualification / 'plan.json'),
            'qualification command provenance differs')
    expected = read(qualification / 'plan.json')['command']
    require(expected == seed['command'], 'qualification command changed')
    expected[expected.index('--run-id') + 1] = name
    expected += ['--initial-mode-order', ORDERS[index - 1]]
    experiment = ROOT / '.work/experiments' / name
    status = read(experiment / 'status.json')
    require(status['status'] == 'finished' and status['returncode'] == 0 and
            status['owner'] == str(ROOT) and status['cwd'] == str(ROOT) and
            status['command'] == read(experiment / 'plan.json')['command'] == expected and
            status['plan_sha256'] == sha(experiment / 'plan.json') and
            status['log_sha256'] == sha(experiment / 'command.log'), 'cold execution provenance differs')
    verified = verify(report)
    require(verified == read(out / 'verification.json') and verified['commands'] == 9 and
            verified['check_commands'] == 3 and verified['exact_artifact_hashes_verified'] == 6,
            'cold workflow verification differs')
    require(len(report['scripts_sha256']) == 10 and
            all(sha(ROOT / p) == h for p, h in report['scripts_sha256'].items()), 'frozen cold inputs changed')
    rows = read(raw / 'records.json')
    traces = 0
    for row in rows:
        if row['mode'] != 'native':
            for call in row['calls']:
                require(call['launch']['compiler_wrapper'] == WRAPPERS[row['mode']], 'compiler wrapper differs')
                traces += 1
    require(traces == 6, 'unexpected wrapper trace count')
    case = read(raw / 'case.json')
    relative = case['case']['file']
    source = ROOT / '.work/sources/nushell'
    original = subprocess.check_output(['git', '-C', str(source), 'show', report['revision'] + ':' + relative])
    require((source / relative).read_bytes() == original and
            subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == report['revision'],
            'pinned source is not restored')
    frozen = dict(status='verified', frozen_input_hashes=len(report['scripts_sha256']),
        compiler_wrapper_traces=traces, source_pin=report['revision'], source_restoration=True,
        restored_source_sha256=hashlib.sha256(original).hexdigest(), restored_source_file=relative,
        initial_mode_order=report['initial_mode_order'], sources=report['scripts_sha256'])
    cold = {row['mode']: dict(wall_seconds=row['seconds'], cpu_seconds=row['cpu_seconds'])
            for row in rows if row['phase'] == 'cold'}
    result = dict(run=name, initial_mode_order=ORDERS[index - 1], cold=cold,
        wall_ratio=cold['candidate']['wall_seconds'] / cold['baseline']['wall_seconds'],
        cpu_ratio=cold['candidate']['cpu_seconds'] / cold['baseline']['cpu_seconds'],
        edited_seconds=report['median_seconds'], verification=verified,
        report_sha256=sha(out / 'summary.json'), records_sha256=sha(raw / 'records.json'))
    return out, frozen, result


def assess(args):
    if args.index:
        out, frozen, result = checked_run(args.index)
        require(not (out / 'frozen-inputs.json').exists() and not (out / 'assessment.md').exists(), 'cold assessment exists')
        write_json(out / 'frozen-inputs.json', frozen)
        write_json(out / 'cold-observation.json', dict(result, assessor_sha256=sha(Path(__file__))))
        lines = [f'# Balanced cold history {args.index} of six', '',
            'All nine primary commands, three independent checks, six paired artifacts,',
            'ten frozen input hashes and six wrapper traces verify. The pinned source is',
            'restored byte-for-byte. Original fourteen tests and wrong-edit controls pass.', '',
            f"Initial order: `{result['initial_mode_order']}`.", '',
            '| Cold mode | Wall seconds | Child CPU seconds |', '| --- | ---: | ---: |']
        for mode in ['native', 'baseline', 'candidate']:
            r = result['cold'][mode]
            lines.append(f"| {mode} | {r['wall_seconds']:.3f} | {r['cpu_seconds']:.3f} |")
        lines += ['', f"Candidate/baseline cold ratios: **{result['wall_ratio']:.10f} wall**, **{result['cpu_ratio']:.10f} CPU**.",
            'This is one predeclared sample, not a retention decision. All six histories',
            'and the original cold/warm criteria remain required. Edited observations in',
            'this run are not added to the completed fifteen-cycle warm comparisons.', '',
            'Tools remain 78e60cdd/c341296c with identical VM, ordinary JIT, matched leaf',
            'inlining and std-MIR. Native uses eighteen jobs/O0/incremental/default test',
            'concurrency; custom uses four jobs. Cold excludes installation, downloads',
            'and prebuilt std-MIR setup. No OS caches were cleared or other work controlled.', '',
            '[Full precision and provenance](cold-observation.json), [workflow checks](verification.json),',
            'and [frozen inputs/source restoration](frozen-inputs.json) are preserved.']
        (out / 'assessment.md').write_text('\n'.join(lines) + '\n')
        print(json.dumps(dict(run=result['run'], wall_ratio=result['wall_ratio'], cpu_ratio=result['cpu_ratio'])))
        return
    # All six reports must exist and verify before any aggregate is published.
    runs = []
    for index in range(1, 7):
        out, frozen, result = checked_run(index)
        require(read(out / 'frozen-inputs.json') == frozen, 'stored cold source evidence differs')
        runs.append(result)
    warm = []
    for project in ['pgrust', 'nushell']:
        path = ROOT / 'results' / f'lightweight-wrapper-{project}-repeated-01' / 'summary.json'
        report = read(path)
        stored = read(path.with_name('verification.json'))
        reference = read(ROOT / 'results' / f'lightweight-wrapper-{project}-qualification-01' / 'summary.json') if stored['reference_bytecode'] is not None else None
        require(verify(report, reference) == stored and report['cycles'] == 15,
                'warm comparison verification differs')
        pairs = report['comparison']['pairs']
        warm.append(dict(project=project, pairs=len(pairs), report_sha256=sha(path),
            wall_ratio=median(p['candidate_seconds'] / p['baseline_seconds'] for p in pairs)))
    ratio = median(r['wall_ratio'] for r in runs)
    cold_pass = ratio <= .95
    warm_pass = all(w['wall_ratio'] <= 1.05 for w in warm)
    out = ROOT / 'results/lightweight-wrapper-cold-comparison-01'
    out.mkdir(exist_ok=False)
    write_json(out / 'summary.json', dict(status='six cold histories and warm controls verified',
        runs=runs, warm=warm, median_cold_wall_ratio=ratio,
        median_cold_cpu_ratio=median(r['cpu_ratio'] for r in runs),
        cold_improvement_gate_passed=cold_pass, warm_regression_guard_passed=warm_pass,
        eligible_for_held_out_checks=cold_pass and warm_pass, retained=False,
        assessor_sha256=sha(Path(__file__)),
        note='Cold improvement must be at least5%; no median paired warm regression over5%. Qualification/anchor cold samples are excluded. Held-out checks are still required before retention; failed gates do not trigger additional wrapper trials.'))
    print(json.dumps(dict(cold_wall_ratio=ratio, cold_pass=cold_pass, warm_pass=warm_pass,
                          held_out_eligible=cold_pass and warm_pass)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--index', type=int, choices=range(1, 7))
    action.add_argument('--all', action='store_true')
    args = parser.parse_args()
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assess(args)


if __name__ == '__main__':
    main()
