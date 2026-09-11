#!/usr/bin/env python3
"""Reverify the seven fixed histories without pooling their performance gates."""
import fcntl
from pathlib import Path

from build_relocation import ROOT, HERE, read, write, sha, require
from heldout_controls import ORDER, case, assess


def receipt_controls(label, launch, supervisor, plan, controller):
    expected = ['benchmarks/experiments/aggregate-byte-writes/run_heldout.py', '--case', label]
    require(supervisor['status'] == 'finished' and supervisor['returncode'] == 0 and
            supervisor['owner'] == supervisor['cwd'] == launch['owner'] == str(ROOT),
            'supervisor is incomplete or belongs to another workspace')
    require(supervisor['command'] == launch['command'] and
            supervisor['command'][1:] == expected, 'supervisor command differs')
    require(controller['status'] == 'finished' and controller['child_returncode'] == 0 and
            controller['pid'] == supervisor['child_pid'] and
            controller['parent_pid'] == supervisor['supervisor_pid'],
            'controller completion or parentage differs')
    require(controller['command'] == plan['command'] and
            controller['command'][1:3] == [str(ROOT/'scripts/bench_e2e_workflow.py'), '--run-id'] and
            controller['command'][3] == 'aggregate-relocation-heldout-01-' + label,
            'workflow command differs')
    require(plan['case'] == case(label) and plan['admission']['label'] == label and
            plan['admission']['passed'] is True, 'case or admission differs')
    require(supervisor['started_at'] <= controller['started_at'] <=
            controller['child_started_at'] <= controller['child_finished_at'] <=
            controller['finished_at'] <= supervisor['finished_at'],
            'execution timestamps are out of order')


def collect(label):
    run = 'aggregate-relocation-heldout-01-' + label
    work = ROOT/'.work'/run
    experiment = ROOT/'.work/experiments'/run
    out = ROOT/'results'/run
    launch, supervisor = (read(experiment/n) for n in ['plan.json', 'status.json'])
    plan, controller = (read(work/n) for n in ['plan.json', 'status.json'])
    receipt_controls(label, launch, supervisor, plan, controller)
    require(supervisor['plan_sha256'] == sha(experiment/'plan.json') and
            supervisor['log_sha256'] == sha(experiment/'command.log'),
            'supervisor evidence differs')
    report, recorded = (read(out/n) for n in ['summary.json', 'relocation-assessment.json'])
    result = assess(report, case(label))
    require(recorded['label'] == label and recorded['expected_tools'] == plan['expected_tools'] and
            all(recorded[k] == v for k, v in result.items()) and
            controller['passed'] == result['passed'], 'recorded assessment differs')
    evidence = dict(plan['frozen'])
    for path, digest in recorded['evidence'].items():
        require(path not in evidence or evidence[path] == digest, 'conflicting evidence')
        evidence[path] = digest
    require(all(sha(ROOT/p) == h for p, h in evidence.items()), 'frozen evidence changed')
    for directory, names in [(work, ['plan.json', 'status.json', 'admission.json']),
                             (experiment, ['plan.json', 'status.json', 'command.log']),
                             (out, ['summary.json', 'relocation-assessment.json'])]:
        for name in names:
            path = directory/name
            evidence[str(path.relative_to(ROOT))] = sha(path)
    # Publish aggregate measurements only, including for the private adapter.
    return dict(label=label, run_id=run, **{k: result[k] for k in [
        'passed', 'wall_ratio', 'cpu_ratio', 'median_seconds', 'median_cpu_seconds']}), evidence


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        qualification = ROOT/'results/aggregate-relocation-heldout-report-check-01/summary.json'
        checked = read(qualification)
        require(checked['status'] == 'passed' and len(checked['rejected']) == 15 and
                checked['completed_performance_failure_accepted'] is True and
                all(sha(ROOT/p) == h for p, h in checked['evidence'].items()),
                'aggregate receipt qualification is missing or changed')
        cases, evidence = [], {str(qualification.relative_to(ROOT)): sha(qualification)}
        for label in ORDER:
            result, bound = collect(label)
            for path, digest in bound.items():
                require(path not in evidence or evidence[path] == digest, 'conflicting case evidence')
                evidence[path] = digest
            cases.append(result)
        passed = all(c['passed'] for c in cases)
        for path in [Path(__file__), HERE/'heldout_controls.py', HERE/'verify_heldouts.py',
                     HERE/'QUALIFICATION-NEXT.md']:
            evidence[str(path.relative_to(ROOT))] = sha(path)
        result = dict(status='all seven histories verified', heldout_gates_passed=passed,
            production_retained=False, primary_commands=441, check_commands=147,
            edited_pairs=105, artifacts=294, cases=cases, evidence=evidence)
        out = ROOT/'results/aggregate-relocation-heldout-01'
        out.mkdir(exist_ok=False)
        write(out/'summary.json', result)
        lines = ['# Aggregate relocation: seven held-out edit benchmarks', '',
            '| Case | Paired wall change | Paired CPU change | Native | Control | Candidate | Gate |',
            '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
        for c in cases:
            m = c['median_seconds']
            lines.append(f"| {c['label']} | {(c['wall_ratio']-1)*100:+.2f}% | "
                f"{(c['cpu_ratio']-1)*100:+.2f}% | {m['native']:.3f}s | {m['baseline']:.3f}s | "
                f"{m['candidate']:.3f}s | {'pass' if c['passed'] else 'fail'} |")
        lines += ['', ('All seven fixed wall/CPU guards pass.' if passed else
            'At least one fixed wall/CPU guard fails. Do not adopt this candidate.'), '',
            'All 588 commands, 105 real-edit pairs and 294 artifacts verify. Compiler checking, '
            'original assertions, wrong-edit rejection, source restoration and native/check controls '
            'are retained. Counts are bookkeeping; performance is not pooled across cases. '
            'Three cycles on a shared host are descriptive. Setup and target-cache-cold commands '
            'are separate. These selected workflows do not establish full-suite Rust support.', '']
        (out/'assessment.md').write_text('\n'.join(lines))
        print(dict(heldout_gates_passed=passed, commands=588, edited_pairs=105, artifacts=294))


if __name__ == '__main__':
    main()
