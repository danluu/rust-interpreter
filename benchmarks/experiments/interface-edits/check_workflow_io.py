#!/usr/bin/env python3
"""Inject disk-write failures; verify restoration and waited-for child lifetimes."""
import argparse
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import workflow_io as io
import supervise_experiment as supervisor


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def full():
    return OSError(errno.ENOSPC, 'injected full disk')


class PartialWrite:
    def __init__(self, fd, mode):
        self.file = os.fdopen(fd, mode)

    def __enter__(self):
        return self

    def write(self, payload):
        self.file.write(payload[:3])
        raise full()

    def __exit__(self, *args):
        self.file.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['.', '..'], 'invalid run ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    passed = []
    with tempfile.TemporaryDirectory(prefix='workflow-io-', dir=ROOT / '.work') as folder:
        directory = Path(folder)
        source = directory / 'source.rs'
        original = b'original source\n'
        edited = b'edited source\n'
        source.write_bytes(original)
        source.chmod(0o644)
        with io.SourceEdit(source, original) as guard:
            guard.replace(edited)
            require(source.read_bytes() == edited, 'mutation missing')
        require(source.read_bytes() == original and source.stat().st_mode & 0o777 == 0o644, 'normal restore differs')
        passed.append('successful source lifecycle preserves bytes and mode')

        with patch.object(io.tempfile, 'mkstemp', wraps=tempfile.mkstemp) as allocation:
            try:
                with io.SourceEdit(source, original) as guard:
                    guard.replace(edited)
                    allocation.side_effect = full()
                    raise full()
            except OSError as error:
                require(error.errno == errno.ENOSPC, 'wrong injected failure')
        require(source.read_bytes() == original, 'failed to restore with new allocations unavailable')
        passed.append('body ENOSPC restores using already staged bytes')

        real_fdopen = os.fdopen
        def partial(fd, mode):
            obj = object.__new__(PartialWrite)
            obj.file = real_fdopen(fd, mode)
            return obj
        with io.SourceEdit(source, original) as guard:
            guard.replace(edited)
            try:
                with patch.object(io.os, 'fdopen', side_effect=partial):
                    guard.replace(b'next source that must not partially publish')
            except OSError as error:
                require(error.errno == errno.ENOSPC, 'wrong write failure')
            else:
                raise RuntimeError('partial write accepted')
            require(source.read_bytes() == edited and guard.current == edited, 'partial source published')
        require(source.read_bytes() == original, 'partial-write restore failed')
        passed.append('partial source write preserves previous source and restores original')

        receipt = directory / 'receipt.json'
        io.write_json(receipt, {'status': 'previous'})
        try:
            with patch.object(io.os, 'fdopen', side_effect=partial):
                io.write_json(receipt, {'status': 'new'})
        except OSError:
            pass
        require(json.loads(receipt.read_text()) == {'status': 'previous'}, 'partial receipt published')
        passed.append('partial receipt write preserves previous complete receipt')

        for fail_status in ['running', 'finished']:
            children = []
            marker = directory / ('child-' + fail_status)
            command = [sys.executable, '-c',
                'import pathlib,sys; sys.stdout.write("x"*2097152); sys.stderr.write("y"*2097152); '
                'pathlib.Path(sys.argv[1]).write_bytes(pathlib.Path(sys.argv[2]).read_bytes())', str(marker), str(source)]
            real_popen = subprocess.Popen
            real_write = io.write_json
            def start(*args, **kwargs):
                child = real_popen(*args, **kwargs)
                children.append(child)
                return child
            def write(path, record):
                if record['status'] == fail_status:
                    raise full()
                return real_write(path, record)
            try:
                with io.SourceEdit(source, original) as guard:
                    guard.replace(edited)
                    with patch.object(io.subprocess, 'Popen', side_effect=start), patch.object(io, 'write_json', side_effect=write):
                        io.capture(command, cwd=directory, env=os.environ.copy(), receipt_path=receipt, receipt={})
            except OSError as error:
                require(error.errno == errno.ENOSPC, 'wrong receipt failure')
            else:
                raise RuntimeError('receipt failure lost')
            require(len(children) == 1 and children[0].poll() == 0, 'child not drained and waited')
            require(marker.read_bytes() == edited and source.read_bytes() == original, 'source restored before child finished')
            passed.append(f'{fail_status} receipt ENOSPC waits/drains real child before restoration')

        guard = io.SourceEdit(source, original)
        try:
            with guard:
                guard.replace(edited)
                source.write_bytes(b'external change')
        except RuntimeError as error:
            require('outside benchmark' in str(error), 'unexpected external-change error')
        else:
            raise RuntimeError('external edit overwritten')
        require(source.read_bytes() == b'external change' and guard.backup.read_bytes() == original, 'external edit or backup lost')
        passed.append('external source change remains untouched; backup preserved')
        source.write_bytes(original)

        guard = io.SourceEdit(source, original)
        try:
            with guard:
                guard.replace(edited)
                guard.backup.write_bytes(b'changed backup')
        except RuntimeError as error:
            require('staged original' in str(error), 'unexpected backup-change error')
        else:
            raise RuntimeError('corrupt backup accepted')
        require(source.read_bytes() == edited, 'corrupt backup replaced source')
        passed.append('modified restoration backup rejected')

        try:
            with patch.object(io.shutil, 'disk_usage', return_value=type('Disk', (), {'free': 0})()):
                io.require_space(directory, 8)
        except RuntimeError:
            passed.append('low free-space preflight rejected')
        else:
            raise RuntimeError('low disk accepted')

    with tempfile.TemporaryDirectory(prefix='io-fault-', dir=ROOT / '.work/experiments') as folder:
        work = Path(folder)
        marker = work / 'child-completed'
        plan = work / 'plan.json'
        supervisor.write(plan, dict(owner=str(ROOT), supervisor_sha256=supervisor.sha(Path(supervisor.__file__)),
            command=[sys.executable, '-c', 'import pathlib,sys; pathlib.Path(sys.argv[1]).write_text("finished")', str(marker)]))
        real_write = supervisor.write
        def write(path, record):
            if record.get('status') == 'running':
                raise full()
            return real_write(path, record)
        try:
            with patch.object(supervisor, 'write', side_effect=write):
                supervisor.supervise(plan)
        except OSError as error:
            require(error.errno == errno.ENOSPC, 'wrong supervisor failure')
        else:
            raise RuntimeError('supervisor publication failure lost')
        require(marker.read_text() == 'finished', 'supervisor returned before child completion')
        passed.append('supervisor receipt ENOSPC waits for actual child')

    out = ROOT / 'results' / args.run_id
    out.mkdir(exist_ok=False)
    inputs = [Path(__file__), Path(io.__file__), Path(supervisor.__file__), ROOT / 'scripts/bench_e2e_workflow.py', ROOT / 'scripts/bench_workflow_corpus.py']
    summary = dict(status='passed', checks=passed, real_child_processes=3, process_signals_sent=False,
                   inputs={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(dict(status='passed', checks=len(passed), real_child_processes=3)))


if __name__ == '__main__':
    main()
