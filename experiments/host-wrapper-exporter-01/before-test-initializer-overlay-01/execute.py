#!/usr/bin/env python3
"""Normally wait the existing supervisor and retain its exact phase invocation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HERE = ROOT/'experiments/host-wrapper-exporter-01'
SUPERVISOR_SHA = '019608c2d37fcecb55ed436fafe3753498bfe11e1a1805a46ae49a59c7d6a1b2'
SOURCES_SHA = '210246de7c9ced7a2640b67e7d44261777afa2bf8f0d3157165324c010099d71'
BUILD_SOURCES_SHA = '1bd9e2e16c030f1fe0b5c95bb01ae869bc4be39791d64775753bb3376fe02d59'


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
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('phase', choices=['metadata', 'build', 'frontend'])
    parser.add_argument('--launch-sha256', required=True)
    parser.add_argument('--metadata-receipt-sha256')
    parser.add_argument('--frontend-sources-sha256')
    parser.add_argument('--build-receipt-sha256')
    parser.add_argument('--built-tools-sha256')
    args = parser.parse_args()
    launch = read(HERE/'packet-01/launch.json', args.launch_sha256)
    inputs = read(launch['inputs']['path'], launch['inputs']['sha256'])
    plan = read(launch['plan']['path'], launch['plan']['sha256'])
    assert inputs['plan'] == launch['plan'] and launch['environment'] == plan['launch_environment']
    assert launch['cwd'] == str(X) and Path.cwd() == X
    command = list(launch['command'])
    if args.phase in ('build', 'frontend'):
        assert args.metadata_receipt_sha256
        prior = read(X/'.work/host-wrapper-exporter-metadata-01/receipt.json', args.metadata_receipt_sha256)
        assert prior['status'] == 'passed' and prior['phase'] == 'metadata'
        command = ['/opt/homebrew/bin/python3', '-B', str(HERE/(args.phase+'.py')),
            '--inputs-sha256', launch['inputs']['sha256'], '--sources-sha256', SOURCES_SHA,
            '--build-sources-sha256', BUILD_SOURCES_SHA,
            '--metadata-receipt-sha256', args.metadata_receipt_sha256]
        if args.phase == 'frontend':
            assert args.frontend_sources_sha256 and args.build_receipt_sha256 and args.built_tools_sha256
            command += ['--frontend-sources-sha256', args.frontend_sources_sha256,
                        '--build-receipt-sha256', args.build_receipt_sha256,
                        '--built-tools-sha256', args.built_tools_sha256]
    else:
        assert args.metadata_receipt_sha256 is None
    if args.phase != 'frontend':
        assert args.frontend_sources_sha256 is args.build_receipt_sha256 is args.built_tools_sha256 is None
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
        resource_policy='Ordinary jobs=2 and sampled disk guards; no CPU, wall-time or memory cap.')
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
