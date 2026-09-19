#!/usr/bin/env python3
"""Normally wait one prepared screen supervisor; acquire no workload lock."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
PYTHON = '/opt/homebrew/bin/python3'
SUPERVISOR = R/'scripts/supervise_experiment.py'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(reference):
    require(type(reference) is dict and set(reference) == {'path', 'sha256'}
            and re.fullmatch('[0-9a-f]{64}', reference['sha256']), 'exact saved reference required')
    path = Path(reference['path'])
    require(path.resolve(strict=True) == path and path.is_file() and path.stat().st_size <= 32*2**20,
            'bounded ordinary saved input required')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == reference['sha256'], 'saved input changed')
    return json.loads(raw)


def ref(path):
    return dict(path=str(path), sha256=sha(path))


def write(path, value):
    with path.open('w') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    require(Path.cwd() == R and sys.dont_write_bytecode and not sys.flags.optimize,
            'screen parent requires Python -B and R cwd')
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--history', choices=['ab', 'aa'], required=True)
    parser.add_argument('--launch-sha256', required=True)
    parser.add_argument('--sources-sha256', required=True)
    args = parser.parse_args()
    source_ref = dict(path=str(HERE/'sources.json'), sha256=args.sources_sha256)
    sources = read(source_ref)
    launch_ref = dict(path=str(HERE/'packet-01'/('launch-'+args.history+'.json')), sha256=args.launch_sha256)
    launch = read(launch_ref)
    name = 'hir-options-hash-ruff-screen-'+args.history+'-03'
    outer = R/'.work/experiments'/(name+'-supervisor')
    work = R/'.work'/(name+'-observer')
    execution = R/'.work'/(name+'-execution')
    require(not os.path.lexists(execution), 'fresh screen parent execution required')
    require(launch['cwd'] == str(R) and launch['plan']['path'] == str(outer/'plan.json'),
            'prepared launch route differs')
    outer_plan = read(launch['plan'])
    require(set(outer_plan) == {'owner', 'command', 'supervisor_sha256'}
            and outer_plan['owner'] == str(R)
            and outer_plan['supervisor_sha256'] == sources['files'][str(SUPERVISOR)] == sha(SUPERVISOR),
            'ordinary supervisor source or three-field plan differs')
    command = outer_plan['command']
    require(command[:3] == [PYTHON, '-B', str(HERE/'observe.py')]
            and len(command[3:]) % 2 == 0, 'fixed observer command required')
    pairs = list(zip(command[3::2], command[4::2], strict=True))
    flags = dict(pairs)
    expected = {'--history', '--plan-sha256', '--inputs-sha256', '--sources-sha256'}
    if args.history == 'aa':
        expected |= {'--previous', '--previous-sha256'}
    require(len(flags) == len(pairs) and set(flags) == expected and flags['--history'] == args.history
            and flags['--sources-sha256'] == args.sources_sha256, 'observer argument binding differs')
    plan_ref = dict(path=str(HERE/'packet-01/plan.json'), sha256=flags['--plan-sha256'])
    plan = read(plan_ref)
    read(dict(path=str(HERE/'packet-01/inputs.json'), sha256=flags['--inputs-sha256']))
    h = plan['histories'][args.history]
    require(plan['order'] == ['ab', 'aa'] and plan['sources'] == source_ref
            and h['observer'] == str(work) and h['outer'] == str(outer)
            and launch['environment'] == h['environment'], 'exact prepared history/environment differs')
    argv = [PYTHON, '-B', str(SUPERVISOR), '--supervise', str(outer/'plan.json')]
    require(launch['argv'] == argv, 'direct supervisor invocation differs')
    require(not os.path.lexists(outer/'status.json') and not os.path.lexists(work),
            'history already started')
    # Observer authenticates all124 sources before running either ordinary child.
    # The separate parent is externally source-pinned and records its own bytes.
    execution.mkdir()
    record = dict(status='starting', history=args.history, parent_pid=os.getpid(),
        parent_parent_pid=os.getppid(), started_at=time.time(), source_sha256=sha(__file__),
        command=argv, cwd=str(R), environment=launch['environment'], launch=launch_ref,
        sources=source_ref, plan=plan_ref, outer_plan=launch['plan'], signals=0, retries=0,
        supervisor_may_be_live=True, controller_may_be_live=True,
        resource_policy='Inherited sampled disk observation; no CPU, wall-time or memory cap.')
    write(execution/'record.json', record)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    tick = time.perf_counter()
    with (execution/'stdout').open('xb') as stdout, (execution/'stderr').open('xb') as stderr:
        child = subprocess.Popen(argv, cwd=R, env=launch['environment'], stdin=subprocess.DEVNULL,
                                 stdout=stdout, stderr=stderr)
        try:
            record.update(pid=child.pid, child_started_at=time.time())
            write(execution/'record.json', record)
        finally:
            code = child.wait()
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    user, system = after.ru_utime-before.ru_utime, after.ru_stime-before.ru_stime
    record.update(status='finished', returncode=code, finished_at=time.time(), supervisor_may_be_live=False,
        session_wall_seconds=time.perf_counter()-tick,
        child_cpu=dict(user_seconds=user, system_seconds=system, total_seconds=user+system),
        session_scope='Direct supervisor through OS wait, including admission queues, runner, verification and observer overhead; not a separately measured setup phase.',
        stdout_sha256=sha(execution/'stdout'), stderr_sha256=sha(execution/'stderr'))
    write(execution/'record.json', record)  # Save known OS closure before decoding any terminal JSON.
    status = read(ref(outer/'status.json'))
    closed = (status['status'] == 'finished' and status['supervisor_pid'] == child.pid
        and status['supervisor_parent_pid'] == os.getpid() and status['plan_sha256'] == launch['plan']['sha256']
        and status['command'] == command and status['log_sha256'] == sha(outer/'command.log'))
    record['outer'] = ref(outer/'status.json')
    if closed:
        record.update(controller_may_be_live=False, controller_returncode=status['returncode'])
    write(execution/'record.json', record)
    if not closed or code != 0 or status['returncode'] != 0:
        raise SystemExit(1)
    receipt_ref = ref(work/'receipt.json')
    receipt = read(receipt_ref)
    require(receipt['status'] == 'passed' and receipt['history'] == args.history and receipt['plan'] == plan_ref
            and receipt['pid'] == status['child_pid'] and receipt['parent_pid'] == child.pid
            and record['started_at'] <= status['started_at'] <= receipt['started_at']
            <= receipt['finished_at'] <= status['finished_at'] <= record['finished_at']
            and 'error' not in receipt, 'observer did not pass inside this normal parent wait')
    require(receipt['result']['path'] == str(work/'result.json'), 'observer result route differs')
    result = read(receipt['result'])
    require(result['status'] == 'passed' and result['history'] == args.history and result['plan'] == plan_ref,
            'observer result differs')
    record.update(observer=receipt_ref, result=receipt['result'], observer_verified=True)
    write(execution/'record.json', record)
    print(json.dumps(ref(execution/'record.json'), sort_keys=True))


if __name__ == '__main__':
    main()
