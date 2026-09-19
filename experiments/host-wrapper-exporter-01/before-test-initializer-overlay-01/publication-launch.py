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
SOURCES_SHA = '210246de7c9ced7a2640b67e7d44261777afa2bf8f0d3157165324c010099d71'
BUILD_SOURCES_SHA = '1bd9e2e16c030f1fe0b5c95bb01ae869bc4be39791d64775753bb3376fe02d59'
FRONTEND_SOURCES_SHA = 'baf35df088745b3de78288e65dd223b08eaca719abf5d5ca9889414d7bf901ee'
PUBLICATION_SOURCES_SHA = 'e4f88f77dbb34ff7167234767c9b48ceee8a54ee1886b396622024e60839909f'


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
