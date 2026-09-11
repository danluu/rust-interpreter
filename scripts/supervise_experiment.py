#!/usr/bin/env python3
"""Keep one recorded local experiment running if the launching client disconnects."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, record):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(record, indent=2) + '\n')
    temp.replace(path)


def identity(pid):
    return subprocess.run(['ps', '-p', str(pid), '-o', 'pid,ppid,lstart,tty,command'],
                          capture_output=True, text=True).stdout


def supervise(path):
    path = path.resolve()
    if not path.is_relative_to(ROOT / '.work/experiments'):
        raise RuntimeError('unexpected experiment directory')
    plan = json.loads(path.read_text())
    if plan['owner'] != str(ROOT) or plan['supervisor_sha256'] != sha(Path(__file__)):
        raise RuntimeError('experiment owner or supervisor source changed')
    work = path.parent
    receipt = work / 'status.json'
    if receipt.exists():
        raise RuntimeError('experiment already started')
    record = dict(status='starting', owner=str(ROOT), command=plan['command'], cwd=str(ROOT),
        supervisor_pid=os.getpid(), supervisor_parent_pid=os.getppid(),
        supervisor_identity=identity(os.getpid()), started_at=time.time(), plan_sha256=sha(path))
    write(receipt, record)
    try:
        with (work / 'command.log').open('x') as log:
            child = subprocess.Popen(plan['command'], cwd=ROOT, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT)
            record.update(status='running', child_pid=child.pid,
                          child_identity=identity(child.pid), child_started_at=time.time())
            write(receipt, record)
            code = child.wait()
        record.update(status='finished', returncode=code, finished_at=time.time(),
                      log_sha256=sha(work / 'command.log'))
        write(receipt, record)
    except BaseException as error:
        # Record an interrupted supervisor without signaling the child or any
        # other process. Its liveness must be inspected separately on recovery.
        record.update(status='supervisor failed', error=repr(error), finished_at=time.time())
        write(receipt, record)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id')
    parser.add_argument('--supervise', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.supervise:
        supervise(args.supervise)
        return
    if not args.run_id or Path(args.run_id).name != args.run_id or args.run_id in ['.', '..']:
        parser.error('run-id must be a directory name')
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('supply a command after --')
    work = ROOT / '.work/experiments' / args.run_id
    work.mkdir(parents=True, exist_ok=False)
    plan = work / 'plan.json'
    write(plan, dict(owner=str(ROOT), command=command, supervisor_sha256=sha(Path(__file__))))
    with (work / 'supervisor.log').open('x') as log:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--supervise', str(plan)],
            cwd=ROOT, start_new_session=True, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    print(json.dumps(dict(supervisor_pid=process.pid, directory=str(work), identity=identity(process.pid))))


if __name__ == '__main__':
    main()
