"""Preserve benchmark sources and wait for children when receipt writes fail."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def atomic_bytes(path, payload, *, mode=None, sync=False):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload)
            if sync:
                stream.flush()
                os.fsync(stream.fileno())
        if mode is not None:
            temporary.chmod(mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path, record):
    atomic_bytes(path, (json.dumps(record, indent=2) + '\n').encode())


def require_space(path, minimum_gib):
    free = shutil.disk_usage(path).free
    if free < minimum_gib * 1024**3:
        raise RuntimeError(f'insufficient free disk: {free} bytes; no child started or automatic cleanup attempted')


def capture(command, *, cwd, env, receipt_path, receipt):
    """Always drain/wait the child even if publishing its identity fails.

    A receipt failure still fails the benchmark. Waiting retains serialization
    and prevents source restoration while that child may still compile it.
    This does not guarantee recovery from process/host termination.
    """
    child = subprocess.Popen(command, cwd=cwd, env=env, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    active = dict(receipt, pid=child.pid, parent_pid=os.getpid(), command=command,
                  cwd=str(cwd), started_at=time.time(), status='running')
    try:
        write_json(receipt_path, active)
    finally:
        stdout, stderr = child.communicate()
    active.update(status='finished', returncode=child.returncode, finished_at=time.time())
    write_json(receipt_path, active)
    return child, stdout, stderr


class SourceEdit:
    """Stage original bytes before editing; restore by same-directory rename.

    Partial writes never replace the source. Restoration needs no new payload
    allocation, though filesystem metadata operations can still fail. Keep the
    original backup on an external edit or failed restore for manual recovery.
    """
    def __init__(self, path, original):
        self.path = Path(path)
        self.original = original
        self.current = original
        self.backup = None

    def matches(self, expected):
        return not self.path.is_symlink() and self.path.read_bytes() == expected

    def __enter__(self):
        if not self.matches(self.original):
            raise RuntimeError('source changed before staging restoration')
        self.mode = self.path.stat().st_mode & 0o777
        fd, name = tempfile.mkstemp(prefix='.rust-interp-original-', dir=self.path.parent)
        self.backup = Path(name)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(self.original)
                stream.flush()
                os.fsync(stream.fileno())
            self.backup.chmod(self.mode)
        except BaseException:
            self.backup.unlink(missing_ok=True)
            raise
        return self

    def replace(self, payload):
        if not self.matches(self.current):
            raise RuntimeError('source changed outside this benchmark')
        atomic_bytes(self.path, payload, mode=self.mode)
        self.current = payload

    def __exit__(self, kind, value, traceback):
        if not self.matches(self.current):
            raise RuntimeError(f'source changed outside benchmark; original preserved at {self.backup}')
        if self.backup.is_symlink() or self.backup.read_bytes() != self.original:
            raise RuntimeError('staged original source changed; refusing restoration')
        try:
            self.backup.replace(self.path)
        except OSError as error:
            raise RuntimeError(f'source restoration failed; original preserved at {self.backup}') from error
        if not self.matches(self.original):
            raise RuntimeError('restored source differs')
