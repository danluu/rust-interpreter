#!/usr/bin/env python3
"""Qualify only the declared recovery mapping, reserve and owned monitor."""
import ast
import copy
import fcntl
import json
import os
import sys
import time

from build_relocation import ROOT, HERE, PARENT, read, write, sha, require
from check_comparison import expected_tools
from heldout_controls import case
from heldout_recovery import (ORIGINAL, RETRY, RUNNER, QUALIFICATION, run_id, command,
    stop_evidence, admission_estimate, recovery_receipts, SpaceMonitor, CADENCE)
from report_heldouts import collect


def fixture(label):
    work, experiment = ROOT/'.work'/ORIGINAL, ROOT/'.work/experiments'/ORIGINAL
    launch, supervisor = (read(experiment/n) for n in ['plan.json', 'status.json'])
    plan, controller = (read(work/n) for n in ['plan.json', 'status.json'])
    launch['command'] = ['python3', RUNNER, '--case', label]
    supervisor.update(command=launch['command'].copy(), returncode=0, started_at=1, finished_at=9)
    controller.update(status='finished', child_returncode=0, command=command(label),
        started_at=2, child_started_at=4, child_finished_at=6, monitor_finished_at=7,
        finished_at=8, passed=True)
    needed, _ = admission_estimate(label)
    plan.update(command=command(label), case=case(label),
        admission=dict(label=label, checked_at=3, observed_free_bytes=needed['minimum_free_bytes'],
            estimate=needed, passed=True),
        recovery=dict(original_run=ORIGINAL, retry_run=RETRY, excluded_partial_pairs=5,
            predecessor=('aggregate-relocation-heldout-01-nushell-type-relations' if label=='ruff' else RETRY)))
    rows = [dict(sequence=i, time=t, monotonic=t, pid=controller['pid'],
        child_pid=controller['child_pid'], thread_id=17, cadence_seconds=CADENCE,
        event='sample' if i==0 else 'stopped', free_bytes=1024) for i, t in enumerate([4.1, 6.1])]
    return [launch, supervisor, plan, controller, rows]


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        evidence = stop_evidence()
        actual, bound = collect('nushell-type-relations')
        evidence.update(bound)
        # Evaluate the unchanged original runner's command expression separately.
        assignments = [n for n in ast.walk(ast.parse((HERE/'run_heldout.py').read_text()))
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id=='command' for t in n.targets)]
        require(len(assignments)==1, 'original command template differs')
        template = compile(ast.Expression(assignments[0].value), '<original command>', 'eval')
        for label in ['ruff', 'nushell']:
            expected = eval(template, dict(sys=sys, ROOT=ROOT, run=run_id(label), c=case(label),
                tools=expected_tools(), PARENT=PARENT))
            require(command(label)==expected, 'amended command differs from original template')
            recovery_receipts(label, *fixture(label))
        changes = [
            ('running supervisor', [1,'status'], 'running'),
            ('failed supervisor', [1,'returncode'], 1),
            ('wrong owner', [1,'owner'], '/other'),
            ('wrong cwd', [1,'cwd'], '/other'),
            ('old launch', [0,'command',1], 'benchmarks/experiments/aggregate-byte-writes/run_heldout.py'),
            ('incomplete controller', [3,'status'], 'running'),
            ('workflow failed', [3,'child_returncode'], 1),
            ('wrong controller pid', [3,'pid'], -1),
            ('wrong parent', [3,'parent_pid'], -1),
            ('wrong workflow run', [3,'command',3], ORIGINAL),
            ('wrong case', [2,'case'], {}),
            ('false admission', [2,'admission','passed'], False),
            ('insufficient reserve', [2,'admission','observed_free_bytes'], 0),
            ('omitted extra reserve', [2,'admission','estimate','retry_extra_reserve_bytes'], 0),
            ('expired admission', [2,'admission','checked_at'], -100),
            ('future admission', [2,'admission','checked_at'], 5),
            ('old predecessor', [2,'recovery','predecessor'], ORIGINAL),
            ('pool partial pairs', [2,'recovery','excluded_partial_pairs'], 0),
            ('child before controller', [3,'child_started_at'], 1),
            ('monitor still running', [4,1,'event'], 'sample'),
            ('monitor wrong owner', [4,0,'pid'], -1),
            ('monitor wrong child', [4,0,'child_pid'], -1),
            ('monitor other thread', [4,1,'thread_id'], 19),
            ('monitor different cadence', [4,0,'cadence_seconds'], .1),
            ('monitor invalid space', [4,0,'free_bytes'], -1),
            ('monitor nonfinite time', [4,0,'time'], float('nan')),
            ('monitor bad sequence', [4,1,'sequence'], 4),
            ('monitor reversed clock', [4,1,'monotonic'], 1),
            ('monitor early stop', [4,1,'time'], 5),
            ('monitor after controller', [3,'monitor_finished_at'], 10),
        ]
        rejected = []
        for name, keys, value in changes:
            changed = fixture('ruff')
            node = changed
            for key in keys[:-1]:
                node = node[key]
            node[keys[-1]] = value
            try:
                recovery_receipts('ruff', *changed)
            except RuntimeError:
                rejected.append(name)
            else:
                raise RuntimeError('accepted invalid receipt: '+name)
        completed_failure = fixture('ruff')
        completed_failure[3]['passed'] = False
        recovery_receipts('ruff', *completed_failure)
        directory = ROOT/'.work/aggregate-relocation-recovery-controls-01'
        directory.mkdir(exist_ok=False)
        monitor = SpaceMonitor(directory/'monitor.jsonl', os.getpid(), cadence=.01, sample=lambda: 123)
        monitor.start()
        time.sleep(.035)
        monitor.stop()
        rows = [json.loads(line) for line in monitor.path.read_text().splitlines()]
        require(not monitor.thread.is_alive() and len(rows)>=2 and rows[-1]['event']=='stopped' and
            all(r['free_bytes']==123 for r in rows), 'owned monitor failed to stop/publish')
        def failed_sample():
            raise OSError('injected statvfs failure')
        failed = SpaceMonitor(directory/'failed-monitor.jsonl', os.getpid(), sample=failed_sample)
        failed.start()
        try:
            failed.stop()
        except RuntimeError:
            require(not failed.thread.is_alive() and 'injected statvfs failure' in failed.error,
                'monitor failure did not propagate after join')
        else:
            raise RuntimeError('monitor failure was ignored')
        for path in [HERE/n for n in ['heldout_recovery.py','run_heldout_recovery.py',
                'report_heldout_recovery.py','check_heldout_recovery.py','HELDOUT-RETRY-NEXT.md',
                'report_heldouts.py','run_heldout.py']] + [monitor.path, failed.path]:
            evidence[str(path.relative_to(ROOT))] = sha(path)
        QUALIFICATION.parent.mkdir(exist_ok=False)
        write(QUALIFICATION, dict(status='passed', actual_case=actual, rejected=rejected,
            command_templates=2, completed_performance_failure_accepted=True,
            monitor_lifecycle_passed=True, monitor_error_propagated=True,
            original_partial_pairs_excluded=5, evidence=evidence, performance_measurement=False))
        print(dict(status='passed', rejected=len(rejected), command_templates=2, monitor_cases=2))


if __name__ == '__main__':
    main()
