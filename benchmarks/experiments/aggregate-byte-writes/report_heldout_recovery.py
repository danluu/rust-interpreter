#!/usr/bin/env python3
"""Collect actual amended histories and retain the excluded partial history."""
import fcntl
import json
from pathlib import Path

from build_relocation import ROOT, HERE, read, write, sha, require
from heldout_controls import ORDER, case, assess
from heldout_recovery import run_id, recovery_receipts, stop_evidence, QUALIFICATION
from report_heldouts import collect


def collect_recovered(label):
    run = run_id(label)
    work, experiment, out = ROOT/'.work'/run, ROOT/'.work/experiments'/run, ROOT/'results'/run
    launch, supervisor = (read(experiment/n) for n in ['plan.json', 'status.json'])
    plan, controller = (read(work/n) for n in ['plan.json', 'status.json'])
    rows = [json.loads(line) for line in (work/'free-space.jsonl').read_text().splitlines()]
    recovery_receipts(label, launch, supervisor, plan, controller, rows)
    require(supervisor['plan_sha256'] == sha(experiment/'plan.json') and
            supervisor['log_sha256'] == sha(experiment/'command.log'), 'supervisor evidence differs')
    report, recorded = (read(out/n) for n in ['summary.json', 'relocation-assessment.json'])
    require(report['raw'] == '.work/runs/'+run, 'report is from another history')
    result = assess(report, case(label))
    require(recorded['label'] == label and recorded['expected_tools'] == plan['expected_tools'] and
            all(recorded[k] == v for k, v in result.items()) and
            controller['passed'] == result['passed'], 'recorded assessment differs')
    evidence = stop_evidence()
    for mapping in [plan['frozen'], recorded['evidence']]:
        for path, digest in mapping.items():
            require(path not in evidence or evidence[path] == digest, 'conflicting evidence')
            evidence[path] = digest
    require(all(sha(ROOT/p) == h for p, h in evidence.items()), 'frozen recovery evidence changed')
    for directory, names in [(work, ['plan.json', 'status.json', 'admission.json', 'free-space.jsonl']),
            (experiment, ['plan.json', 'status.json', 'command.log']),
            (out, ['summary.json', 'relocation-assessment.json'])]:
        for name in names:
            path = directory/name
            evidence[str(path.relative_to(ROOT))] = sha(path)
    return dict(label=label, run_id=run, **{k: result[k] for k in [
        'passed', 'wall_ratio', 'cpu_ratio', 'median_seconds', 'median_cpu_seconds']},
        space_samples=len(rows), minimum_observed_free_bytes=min(r['free_bytes'] for r in rows)), evidence


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        qualified = read(QUALIFICATION)
        require(qualified['status'] == 'passed' and
                all(sha(ROOT/p) == h for p, h in qualified['evidence'].items()), 'recovery unqualified')
        cases, evidence = [], stop_evidence()
        evidence[str(QUALIFICATION.relative_to(ROOT))] = sha(QUALIFICATION)
        for label in ORDER:
            result, bound = collect_recovered(label) if label in ['ruff', 'nushell'] else collect(label)
            for path, digest in bound.items():
                require(path not in evidence or evidence[path] == digest, 'conflicting case evidence')
                evidence[path] = digest
            cases.append(result)
        passed = all(c['passed'] for c in cases)
        out = ROOT/'results/aggregate-relocation-heldout-recovery-01'
        out.mkdir(exist_ok=False)
        write(out/'summary.json', dict(status='all seven histories verified',
            heldout_gates_passed=passed, production_retained=False, primary_commands=441,
            check_commands=147, edited_pairs=105, artifacts=294, cases=cases, evidence=evidence,
            excluded_partial_history='results/aggregate-relocation-ruff-stop-01/summary.json'))
        lines = ['# Aggregate relocation: complete held-outs', '',
            '| Case | Paired wall | Paired CPU | Native | Control | Candidate | Gate |',
            '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
        for c in cases:
            m = c['median_seconds']
            lines.append(f"| {c['label']} | {(c['wall_ratio']-1)*100:+.2f}% | "
                f"{(c['cpu_ratio']-1)*100:+.2f}% | {m['native']:.3f}s | {m['baseline']:.3f}s | "
                f"{m['candidate']:.3f}s | {'pass' if c['passed'] else 'fail'} |")
        lines += ['', 'All 588 commands, 105 real-edit pairs and 294 artifacts verify. '
            'Each case keeps its own fixed 5% wall and CPU guards. The original Ruff '
            'disk-guard stop remains preserved and excluded; the distinct complete retry '
            'supplies its fifteen pairs. Source restoration, original assertions and wrong-edit '
            'checks remain mandatory. Three cycles on a shared host are descriptive. '
            'Target-cache-cold setup is separate; these selected workflows do not establish '
            'full-suite support. Private results contain aggregate measurements only.', '',
            'All held-out guards pass.' if passed else 'A held-out guard fails. Do not adopt.', '']
        (out/'assessment.md').write_text('\n'.join(lines))
        print(dict(heldout_gates_passed=passed, commands=588, edited_pairs=105))


if __name__ == '__main__':
    main()
