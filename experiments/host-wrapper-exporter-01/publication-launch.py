#!/usr/bin/env python3
"""Normally wait the existing supervisor for the separately bound publication phase."""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
import subprocess
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HERE = ROOT/'experiments/host-wrapper-exporter-01'
SUPERVISOR_SHA = '019608c2d37fcecb55ed436fafe3753498bfe11e1a1805a46ae49a59c7d6a1b2'
SOURCES_SHA = '4e17ba1f0be6548ea3875322a1216c56e5bfb857ca99d57278e18925632cfeb3'
BUILD_SOURCES_SHA = '190a4e56c5083d595f91b3e3bac7ac6e8c8c883bfc32befe49b31473a99e58e1'
FRONTEND_SOURCES_SHA = '9d8490fd749d92c9dc38c506e9e399fd8bd3073a8496bde4d23204f2d330d0b4'
PUBLICATION_SOURCES_SHA = '94a9faf5250e108dd3bd4014b219c1dd347548bc47f979a71782eb5d5decbb25'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path, expected):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError('Reviewed input changed: '+str(path))
    return json.loads(data)


def write(path, value, exclusive=False):
    with path.open('x' if exclusive else 'w') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    if not sys.dont_write_bytecode or sys.flags.optimize or Path.cwd() != X:
        raise RuntimeError('Publication launcher requires Python -B and original X cwd')
    parser = argparse.ArgumentParser(__doc__)
    for name in ('launch-sha256', 'metadata-receipt-sha256', 'build-receipt-sha256',
                 'built-tools-sha256', 'frontend-receipt-sha256'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    if not all(re.fullmatch('[0-9a-f]{64}', value) for value in vars(args).values()):
        raise RuntimeError('Exact actual receipt digests required')
    args.phase = 'publication'
    args.frontend_sources_sha256 = FRONTEND_SOURCES_SHA
    launch = read(HERE/'packet-01/launch.json', args.launch_sha256)
    inputs = read(launch['inputs']['path'], launch['inputs']['sha256'])
    plan = read(launch['plan']['path'], launch['plan']['sha256'])
    assert inputs['plan'] == launch['plan'] and launch['environment'] == plan['launch_environment']
    assert launch['cwd'] == str(X)
    read(HERE/'publication-sources.json', PUBLICATION_SOURCES_SHA)
    for phase in ('metadata', 'build', 'frontend'):
        prior = read(X/'.work'/('host-wrapper-exporter-'+phase+'-01')/'receipt.json',
                     getattr(args, phase+'_receipt_sha256'))
        assert prior['status'] == 'passed' and prior['phase'] == phase and 'error' not in prior
    read(X/'.work/host-wrapper-exporter-build-01/built-tools.json', args.built_tools_sha256)
    command = ['/opt/homebrew/bin/python3', '-B', str(HERE/'publish.py'),
        '--inputs-sha256', launch['inputs']['sha256'], '--sources-sha256', SOURCES_SHA,
        '--build-sources-sha256', BUILD_SOURCES_SHA, '--frontend-sources-sha256', FRONTEND_SOURCES_SHA,
        '--publication-sources-sha256', PUBLICATION_SOURCES_SHA,
        '--metadata-receipt-sha256', args.metadata_receipt_sha256,
        '--build-receipt-sha256', args.build_receipt_sha256,
        '--built-tools-sha256', args.built_tools_sha256,
        '--frontend-receipt-sha256', args.frontend_receipt_sha256]
    supervisor = X/'scripts/supervise_experiment.py'
    assert sha(supervisor) == SUPERVISOR_SHA
    outer = X/'.work/experiments'/('host-wrapper-exporter-'+args.phase+'-supervisor-01')
    execution = ROOT/'.work'/('host-wrapper-exporter-'+args.phase+'-execution-01')
    assert not outer.exists() and not execution.exists()
    outer.mkdir(); execution.mkdir()
    outer_plan = dict(owner=str(X), command=command, supervisor_sha256=SUPERVISOR_SHA)
    write(outer/'plan.json', outer_plan, exclusive=True)
    argv = ['/opt/homebrew/bin/python3', '-B', str(supervisor), '--supervise', str(outer/'plan.json')]
    record = dict(status='starting', parent_pid=os.getpid(), started_at=time.time(), phase=args.phase,
        source_sha256=sha(__file__), command=argv, cwd=str(X), environment=launch['environment'],
        outer_plan_sha256=sha(outer/'plan.json'), launch_sha256=args.launch_sha256,
        metadata_receipt_sha256=args.metadata_receipt_sha256, signals=0, retries=0,
        frontend_sources_sha256=args.frontend_sources_sha256,
        build_receipt_sha256=args.build_receipt_sha256, built_tools_sha256=args.built_tools_sha256,
        frontend_receipt_sha256=args.frontend_receipt_sha256, publication_sources_sha256=PUBLICATION_SOURCES_SHA,
        resource_policy='Four publication children and sampled disk guards; no CPU, wall-time or memory cap.')
    write(execution/'record.json', record)
    with (execution/'stdout').open('xb') as stdout, (execution/'stderr').open('xb') as stderr:
        child = subprocess.Popen(argv, cwd=X, env=launch['environment'], stdin=subprocess.DEVNULL,
                                 stdout=stdout, stderr=stderr)
        try:
            record.update(pid=child.pid, child_started_at=time.time())
            write(execution/'record.json', record)
        finally:
            code = child.wait()
    record.update(status='finished', returncode=code, finished_at=time.time(), supervisor_may_be_live=False,
                  stdout_sha256=sha(execution/'stdout'), stderr_sha256=sha(execution/'stderr'))
    write(execution/'record.json', record)  # Persist known OS wait before decoding the outer terminal.
    status = json.loads((outer/'status.json').read_text())
    record.update(outer_status_sha256=sha(outer/'status.json'), controller_may_be_live=True)
    closed = (status['status'] == 'finished' and status['supervisor_pid'] == child.pid
        and status['supervisor_parent_pid'] == os.getpid() and status['plan_sha256'] == record['outer_plan_sha256']
        and status['command'] == command and status['log_sha256'] == sha(outer/'command.log'))
    if closed:
        record.update(controller_may_be_live=False, controller_returncode=status['returncode'])
    write(execution/'record.json', record)
    print(json.dumps(record, sort_keys=True))
    if not closed or code != 0 or status['returncode'] != 0:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
