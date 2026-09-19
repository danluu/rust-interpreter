#!/usr/bin/env python3
"""Normally wait the existing supervisor for the prepared strict Ruff history."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
PACKET = A/'experiments/runtime-application-admission/ruff-options-hash-strict-01/plan'
OUTER = A/'.work/experiments/ruff-options-hash-strict-supervisor-01'
OUT = ROOT/'.work/ruff-options-hash-strict-execution-01'
LAUNCH_SHA = '6b4a063a36e881d8e29acce1d2e3bf48c838cd48feea0a4dced83a929dfa8334'
SUPERVISOR_SHA = '019608c2d37fcecb55ed436fafe3753498bfe11e1a1805a46ae49a59c7d6a1b2'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path, digest):
    payload = Path(path).read_bytes()
    if hashlib.sha256(payload).hexdigest() != digest:
        raise RuntimeError('Prepared input changed: '+str(path))
    return json.loads(payload)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


def main():
    assert Path.cwd() == A and sys.dont_write_bytecode and not sys.flags.optimize
    launch = read(PACKET/'launch.json', LAUNCH_SHA)
    plan = read(launch['plan']['path'], launch['plan']['sha256'])
    read(launch['source_freeze']['path'], launch['source_freeze']['sha256'])
    assert sha(launch['helper']['path']) == launch['helper']['sha256']
    assert launch['cwd'] == launch['owner'] == str(A)
    assert launch['environment'] == plan['launch_environment']
    assert len(plan['commands']) == launch['expected_children'] == 16
    supervisor = A/'scripts/supervise_experiment.py'
    assert sha(supervisor) == SUPERVISOR_SHA
    original_prefix = ['/opt/homebrew/bin/python3', '-B', str(supervisor),
                       '--run-id', OUTER.name, '--']
    assert launch['command'][:6] == original_prefix
    command = launch['command'][6:]
    assert command == ['/opt/homebrew/bin/python3', '-B', launch['helper']['path'],
        '--plan', launch['plan']['path'], '--freeze', launch['source_freeze']['path'],
        '--freeze-sha256', launch['source_freeze']['sha256']]
    assert not os.path.lexists(OUTER) and not os.path.lexists(OUT)
    OUTER.mkdir(); OUT.mkdir()
    write(OUTER/'plan.json', dict(owner=str(A), command=command, supervisor_sha256=SUPERVISOR_SHA))
    argv = ['/opt/homebrew/bin/python3', '-B', str(supervisor), '--supervise', str(OUTER/'plan.json')]
    record = dict(status='starting', parent_pid=os.getpid(), started_at=time.time(),
        source_sha256=sha(__file__), command=argv, cwd=str(A), environment=launch['environment'],
        launch_sha256=LAUNCH_SHA, outer_plan_sha256=sha(OUTER/'plan.json'), signals=0, retries=0,
        transport='Direct ordinary supervisor with normally waited parent; controller owns canonical lock.',
        performance_measurement=False)
    write(OUT/'record.json', record)
    with (OUT/'stdout').open('xb') as stdout, (OUT/'stderr').open('xb') as stderr:
        child = subprocess.Popen(argv, cwd=A, env=launch['environment'], stdin=subprocess.DEVNULL,
                                 stdout=stdout, stderr=stderr)
        try:
            record.update(pid=child.pid, child_started_at=time.time())
            write(OUT/'record.json', record)
        finally:
            code = child.wait()
    record.update(status='finished', returncode=code, finished_at=time.time(), supervisor_may_be_live=False,
                  stdout_sha256=sha(OUT/'stdout'), stderr_sha256=sha(OUT/'stderr'))
    write(OUT/'record.json', record)
    status = json.loads((OUTER/'status.json').read_bytes())
    record.update(outer_status_sha256=sha(OUTER/'status.json'), controller_may_be_live=True)
    closed = (status['status'] == 'finished' and status['supervisor_pid'] == child.pid
        and status['supervisor_parent_pid'] == os.getpid() and status['plan_sha256'] == record['outer_plan_sha256']
        and status['command'] == command and status['log_sha256'] == sha(OUTER/'command.log'))
    if closed:
        record.update(controller_may_be_live=False, controller_returncode=status['returncode'])
    write(OUT/'record.json', record)
    print(json.dumps(record, sort_keys=True))
    if not closed or code != 0 or status['returncode'] != 0:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
