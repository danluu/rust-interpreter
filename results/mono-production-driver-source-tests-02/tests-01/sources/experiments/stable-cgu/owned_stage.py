"""Owned compiler-stage process supervision, including retained failure receipts."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time

CANONICAL_LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
GIB = 2 ** 30


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.staged')
    with temporary.open('x') as output:
        json.dump(value, output, sort_keys=True, indent=2)
        output.write('\n')
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)


@contextmanager
def workload_lock(path, wait_seconds, inherited_fd=None):
    """Nested package/control helpers inherit this exact open file description."""
    path = Path(path)
    require(path == CANONICAL_LOCK and path.resolve(strict=True) == path
            and path.is_file(), 'supply the existing canonical workload lock')
    require(0 < wait_seconds <= 1800, 'invalid bounded lock wait')
    if inherited_fd is not None:
        opened, actual = os.fstat(inherited_fd), path.stat()
        require((opened.st_dev, opened.st_ino) == (actual.st_dev, actual.st_ino),
                'inherited descriptor is not the canonical lock')
        try:
            fcntl.flock(inherited_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('inherited descriptor belongs to a different lock owner') from error
        # A different open description must remain excluded. Never unlock the
        # inherited descriptor; its outer supervisor owns the full stage.
        with path.open('r+') as competing:
            try:
                fcntl.flock(competing, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise RuntimeError('inherited canonical lock is not held')
        yield inherited_fd
        return
    with path.open('r+') as lock:
        deadline = time.monotonic() + wait_seconds
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('canonical workload admission timed out')
                time.sleep(min(.25, max(0, deadline - time.monotonic())))
        yield lock.fileno()


def disk(root, minimum_gib=8):
    free = shutil.disk_usage(root).free
    require(free >= minimum_gib * GIB, 'insufficient free space: ' + str(free))
    return free


def identity(pid):
    completed = subprocess.run(['ps', '-p', str(pid), '-o', 'pid=,ppid=,pgid=,lstart=,tty=,command='],
                               capture_output=True, text=True)
    cwd = subprocess.run(['lsof', '-a', '-p', str(pid), '-d', 'cwd', '-Fn'],
                         capture_output=True, text=True)
    return dict(ps=completed.stdout.strip(), ps_returncode=completed.returncode,
                cwd=cwd.stdout, cwd_returncode=cwd.returncode)


def stop_owned_group(child, original, output):
    """Capacity stop only: prove the exact created session and current descendants."""
    if child.poll() is not None:
        return
    current = identity(child.pid)
    require(original['ps'] and current == original and os.getpgid(child.pid) == child.pid,
            'cannot revalidate owned supervisor child; refusing to signal')
    table = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,pgid='], text=True)
    members = {}
    for line in table.splitlines():
        pid, parent, group = map(int, line.split())
        if group == child.pid:
            members[pid] = dict(parent=parent, identity=identity(pid))
    require(child.pid in members and all(pid == child.pid or item['parent'] in members
                                        for pid, item in members.items()),
            'owned process group contains an unproved process')
    require(all(item['identity']['ps'] for item in members.values()),
            'owned process disappeared during capacity revalidation')
    write(output, dict(reason='free space below 9 GiB; preserve 8 GiB running floor',
                       signal='SIGINT', child=child.pid, group=members, time=time.time()))
    # Membership derives only from this task's fresh session; no peer PID or
    # process-name matching participates in the signal decision.
    os.killpg(child.pid, signal.SIGINT)


def run(command, *, cwd, env, out, capacity_root, pass_fds=(), expected=(0,)):
    """Drain/wait even if publishing an initial receipt raises after Popen."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    command = list(map(str, command))
    record = dict(schema_version=1, supervisor_pid=os.getpid(), parent_pid=os.getppid(),
        command=command, cwd=str(cwd), started_at=time.time(), status='starting',
        environment=env, free_bytes_before=disk(capacity_root), disk_samples=[])
    write(out / 'receipt.json', record)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    with (out / 'stdout').open('wb') as stdout, (out / 'stderr').open('wb') as stderr:
        child = subprocess.Popen(command, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                                 start_new_session=True, pass_fds=pass_fds)
        try:
            record.update(pid=child.pid, status='running', identity=identity(child.pid))
            write(out / 'receipt.json', record)
            print('owned stage child', child.pid, command, flush=True)
            while child.poll() is None:
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    free = shutil.disk_usage(capacity_root).free
                    record['disk_samples'].append(dict(time=time.time(), free_bytes=free))
                    write(out / 'receipt.json', record)
                    if free < 9 * GIB:
                        stop_owned_group(child, record['identity'], out / 'capacity-stop.json')
                        child.wait()
                        raise RuntimeError('owned command stopped at capacity guard')
                    if len(record['disk_samples']) % 6 == 0:
                        print('owned child', child.pid, 'active; free GiB', round(free / GIB, 2), flush=True)
        finally:
            child.wait()
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            record.update(status='finished', returncode=child.returncode, finished_at=time.time(),
                free_bytes_after=shutil.disk_usage(capacity_root).free,
                stdout_sha256=sha(out / 'stdout'), stderr_sha256=sha(out / 'stderr'),
                child_cpu=dict(user_seconds=after.ru_utime - before.ru_utime,
                               system_seconds=after.ru_stime - before.ru_stime))
            write(out / 'receipt.json', record)
    require(child.returncode in expected, 'owned command failed: ' + str(command))
    return record


def inventory(root):
    """Hash regular files and materialized file links; reject live directory links."""
    root = Path(root)
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_dir():
            if path.is_symlink():
                # Bootstrap's one known live source link is omitted by composer.
                require(str(path.relative_to(root)) == 'lib/rustlib/rustc-src/rust',
                        'unexpected artifact directory link')
            continue
        require(path.is_file(), 'unsupported artifact entry: ' + str(path))
        result[str(path.relative_to(root))] = dict(size=path.stat().st_size, sha256=sha(path))
    return result
