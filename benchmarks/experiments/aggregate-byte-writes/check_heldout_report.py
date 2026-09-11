#!/usr/bin/env python3
"""Qualify aggregate receipt checks against the first real held-out history."""
import copy
import fcntl
from pathlib import Path

from report_heldouts import ROOT, HERE, read, write, sha, require, collect, receipt_controls


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        label = 'nushell-type-relations'
        result, evidence = collect(label)
        run = 'aggregate-relocation-heldout-01-' + label
        work, experiment = ROOT/'.work'/run, ROOT/'.work/experiments'/run
        inputs = [read(experiment/'plan.json'), read(experiment/'status.json'),
                  read(work/'plan.json'), read(work/'status.json')]
        mutations = [
            ('running supervisor', 1, 'status', 'running'),
            ('failed supervisor', 1, 'returncode', 1),
            ('other owner', 1, 'owner', '/another-workspace'),
            ('other cwd', 1, 'cwd', '/another-workspace'),
            ('other launch', 0, 'command', ['python3', 'other.py']),
            ('incomplete controller', 3, 'status', 'running'),
            ('failed workflow', 3, 'child_returncode', 1),
            ('wrong controller pid', 3, 'pid', -1),
            ('wrong parent pid', 3, 'parent_pid', -1),
            ('wrong workflow command', 3, 'command', ['python3', 'other.py']),
            ('wrong case', 2, 'case', {}),
            ('failed admission', 2, 'admission', dict(label=label, passed=False)),
            ('wrong admission case', 2, 'admission', dict(label='ruff', passed=True)),
            ('child before parent', 3, 'child_started_at', 0),
            ('child after controller finish', 3, 'child_finished_at', inputs[1]['finished_at']+1),
        ]
        rejected = []
        for name, index, key, value in mutations:
            changed = copy.deepcopy(inputs)
            changed[index][key] = value
            try:
                receipt_controls(label, *changed)
            except RuntimeError:
                rejected.append(name)
            else:
                raise RuntimeError('accepted invalid receipt: ' + name)
        # A completed performance failure must remain reportable, not disappear
        # as an infrastructure rejection. The actual gate is recomputed by collect.
        changed = copy.deepcopy(inputs)
        changed[3]['passed'] = False
        receipt_controls(label, *changed)
        for path in [Path(__file__), HERE/'report_heldouts.py', HERE/'heldout_controls.py',
                     HERE/'verify_heldouts.py']:
            evidence[str(path.relative_to(ROOT))] = sha(path)
        out = ROOT/'results/aggregate-relocation-heldout-report-check-01'
        out.mkdir(exist_ok=False)
        write(out/'summary.json', dict(status='passed', actual_case=result, rejected=rejected,
            completed_performance_failure_accepted=True, evidence=evidence,
            performance_measurement=False))
        print(dict(status='passed', actual_cases=1, rejected=len(rejected)))


if __name__ == '__main__':
    main()
