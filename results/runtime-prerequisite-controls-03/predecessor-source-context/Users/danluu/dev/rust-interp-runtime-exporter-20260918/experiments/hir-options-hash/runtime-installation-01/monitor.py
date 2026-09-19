"""Explicit shared candidate-stage budget monitor; source-only/unqualified.

The hash driver uses its separate finite deadline runner. This monitor never
changes a foreign process and never treats a failed identity probe as authority.
"""
import errno
import os
from pathlib import Path
import resource
import signal
import shutil
import stat
import subprocess
import sys
import time

OWNER = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
CONTROLLER_OWNER = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
ALLOWED_CWDS = frozenset()  # Exact reviewed runtime stage paths; configured before admission.
sys.path.insert(0, str(OWNER/'experiments/stable-cgu'))
import owned_stage as owned

NAMESPACE = OWNER/'.work/hir-options-hash-compiler-01'
EVIDENCE_OWNERS = (OWNER, CONTROLLER_OWNER,
    Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918'),
    Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913'))
EVIDENCE_PREFIXES = ('hir-options-hash-compiler-build-',
    'hir-options-hash-beta-composition-', 'hir-options-hash-native-controls-',
    'hir-options-hash-run-make-', 'hir-options-hash-driver-')
GIB = 2**30


def allocated(root, allowed_roots):
    """Best-effort current allocation, recording ordinary traversal races."""
    assert root in allowed_roots
    assert root.resolve(strict=True) == root and root.is_dir()
    seen = set()
    total = 0
    raced_entries = 0
    entries = 0
    def account(s):
        nonlocal total, entries
        assert stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode) or stat.S_ISLNK(s.st_mode)
        entries += 1
        key = (s.st_dev, s.st_ino)
        if key not in seen:
            total += s.st_blocks*512
            seen.add(key)
    def walk_present(fd):
        nonlocal raced_entries
        # Operate relative to the open directory, with O_NOFOLLOW on each
        # child. A concurrent rename cannot redirect traversal through a link.
        with os.scandir(fd) as listing:
            for entry in listing:
                try:
                    s = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    raced_entries += 1
                    continue
                account(s)
                if not stat.S_ISDIR(s.st_mode):
                    continue
                try:
                    child = os.open(entry.name, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW, dir_fd=fd)
                except OSError as error:
                    if error.errno in [errno.ENOENT, errno.ENOTDIR, errno.ELOOP]:
                        raced_entries += 1
                        continue
                    raise
                try:
                    account(os.fstat(child))
                    walk(child)
                finally:
                    os.close(child)
    def walk(fd):
        nonlocal raced_entries
        try:
            walk_present(fd)
        except FileNotFoundError:
            raced_entries += 1
    fd = os.open(root, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        account(os.fstat(fd))
        walk(fd)
    finally:
        os.close(fd)
    return dict(bytes=total, raced_entries=raced_entries, entries_visited=entries,
        limitation='Non-atomic current allocation sample; vanished or replaced entries are counted as races. New files and concurrent size changes can appear between samples. Free-space monitoring remains separate.')


def evidence_contract(evidence_root, evidence_roots):
    """All extant relevant roots must occur in the explicit frozen array.

    Only immediate names under the four admitted owners are discovered; this
    performs no scan of unrelated target/cache contents. Future roots may be
    declared absent, but symlinks and newly appearing undeclared roots reject.
    The caller binds historical receipts and absence records before admission.
    """
    assert type(evidence_root) is Path or isinstance(evidence_root, Path)
    assert evidence_roots and len(evidence_roots) == len(set(evidence_roots))
    assert evidence_root in evidence_roots
    def accepted(path):
        return (isinstance(path, Path) and path.parent in {o/'.work' for o in EVIDENCE_OWNERS}
                and path.name.startswith(EVIDENCE_PREFIXES) and '..' not in path.parts)
    assert all(accepted(path) for path in evidence_roots), 'unapproved evidence root'
    found = set()
    for owner in EVIDENCE_OWNERS:
        parent = owner/'.work'
        assert parent.resolve(strict=True) == parent and parent.is_dir()
        for path in parent.iterdir():
            if path.name.startswith(EVIDENCE_PREFIXES) and (path.is_dir() or path.is_symlink()):
                assert not path.is_symlink(), 'evidence-root symlink'
                found.add(path)
    assert found <= set(evidence_roots), 'unbudgeted existing candidate stage evidence'
    for path in evidence_roots:
        assert not path.is_symlink()
        if path.exists():
            assert path.resolve(strict=True) == path and path.is_dir()
    return tuple(evidence_roots)


def sample(*, evidence_root, evidence_roots):
    before = shutil.disk_usage(OWNER).free
    errors = []
    try:
        declared = evidence_contract(evidence_root, evidence_roots)
    except (OSError, AssertionError) as error:
        declared = ()
        errors.append(dict(root=str(evidence_root), error=repr(error)))
    roots = (NAMESPACE, *declared)
    def inspect(root):
        try:
            return allocated(root, roots)
        except (OSError, AssertionError) as error:
            errors.append(dict(root=str(root), error=repr(error)))
            return dict(bytes=0, raced_entries=0, entries_visited=0, unavailable=True)
    namespace = inspect(NAMESPACE)
    stages = {}
    for path in declared:
        stages[str(path)] = inspect(path) if path.exists() else dict(bytes=0, absent=True)
    after = shutil.disk_usage(OWNER).free
    return dict(time=time.time(), free_bytes=min(before, after), free_bytes_before=before,
        free_bytes_after=after, namespace_allocated_bytes=namespace['bytes'],
        evidence_allocated_bytes=sum(row['bytes'] for row in stages.values()),
        evidence_root=str(evidence_root), evidence_roots=list(map(str, evidence_roots)),
        stage_evidence_allocation_samples=stages, namespace_allocation_sample=namespace,
        allocation_errors=errors)


def rejection(row):
    if row['free_bytes'] < 9*GIB:
        return 'free space below 9 GiB stop threshold'
    if row.get('allocation_errors'):
        return 'owned allocation inventory unavailable; preserve free-space monitoring and stop owned command'
    if row['namespace_allocated_bytes'] > 14*GIB:
        return 'owned compiler/provider/B3 namespace exceeded 14 GiB allocation'
    if row['evidence_allocated_bytes'] > 256*2**20:
        return 'owned build evidence exceeded 256 MiB allocation'
    return None


def stop_owned(child, original, output, reason):
    """The existing owned-stage proof, with the actual triggering budget reason."""
    if child.poll() is not None:
        return
    def complete(identity):
        return (identity.get('ps_returncode') == 0 and identity.get('cwd_returncode') == 0
                and isinstance(identity.get('ps'), str) and bool(identity['ps'].strip())
                and isinstance(identity.get('cwd'), str) and bool(identity['cwd'].strip()))
    current = owned.identity(child.pid)
    assert complete(original) and complete(current), 'unavailable root identity probe; refusing signal'
    assert current == original and os.getpgid(child.pid) == child.pid
    table = subprocess.check_output(['ps','-axo','pid=,ppid=,pgid='],text=True)
    members = {}
    for line in table.splitlines():
        pid,parent,group=map(int,line.split())
        if group==child.pid:
            members[pid]=dict(parent=parent,identity=owned.identity(pid))
    assert child.pid in members
    assert all(pid==child.pid or row['parent'] in members for pid,row in members.items())
    assert all(complete(row['identity']) for row in members.values()), 'unavailable group identity probe; refusing signal'
    assert members[child.pid]['identity'] == current
    owned.write(output,dict(reason=reason,signal='SIGINT',child=child.pid,group=members,time=time.time()))
    os.killpg(child.pid,signal.SIGINT)



def drain_failed_child(child, record, output, *, evidence_root, evidence_roots, stop_requested=False):
    """Retain the original error while monitoring this already-owned child."""
    while child.poll() is None:
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                observation = sample(evidence_root=evidence_root, evidence_roots=evidence_roots)
                record['samples'].append(observation)
                reason = rejection(observation)
                if reason is not None and not stop_requested:
                    # No general exception creates signal authority. The same
                    # capacity condition and original identity are required.
                    original = record.get('identity')
                    if original is None:
                        raise RuntimeError('missing original child identity; refusing capacity signal')
                    stop_owned(child, original, output/'owned-stop.json', reason)
                    stop_requested = True
            except BaseException as error:
                record.setdefault('drain_errors', []).append(dict(time=time.time(), error=repr(error)))
            try:
                owned.write(output/'receipt.json', record)
            except BaseException as error:
                # A broken receipt write was a possible cause of the original
                # failure. Keep the error in memory and keep checking capacity.
                record.setdefault('drain_errors', []).append(dict(time=time.time(), error=repr(error)))


def run(command, *, cwd, environment, output, canonical_fd, evidence_root, evidence_roots, expected=(0,)):
    """Caller supplies a frozen allowlist row and holds the canonical lock."""
    assert output.is_relative_to(evidence_root) and output.parent.resolve(strict=True) == output.parent
    assert cwd in ALLOWED_CWDS and cwd.resolve(strict=True) == cwd
    assert not any(p in ['.', '..'] for p in output.parts)
    with owned.workload_lock(owned.CANONICAL_LOCK,600,inherited_fd=canonical_fd):
        pass  # The caller keeps its owning context and open description alive.
    output.mkdir(exist_ok=False)
    initial = sample(evidence_root=evidence_root, evidence_roots=evidence_roots)
    assert rejection(initial) is None, rejection(initial)
    record = dict(schema_version=1, status='starting', command=list(command), cwd=str(cwd),
        environment=environment, expected=list(expected), supervisor_pid=os.getpid(),
        parent_pid=os.getppid(), started_at=time.time(), samples=[initial])
    owned.write(output/'receipt.json',record)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    with (output/'stdout').open('xb') as stdout, (output/'stderr').open('xb') as stderr:
        child = subprocess.Popen(command, cwd=cwd, env=environment, stdout=stdout, stderr=stderr,
            start_new_session=True, pass_fds=(canonical_fd,))
        stop_requested = False
        try:
            record.update(status='running', pid=child.pid, identity=owned.identity(child.pid))
            owned.write(output/'receipt.json',record)
            while child.poll() is None:
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    observation = sample(evidence_root=evidence_root, evidence_roots=evidence_roots)
                    record['samples'].append(observation)
                    owned.write(output/'receipt.json',record)
                    reason = rejection(observation)
                    if reason is not None:
                        # Only this fresh child/session and revalidated descendants
                        # may be stopped. Never derive a target from a process name.
                        owned.write(output/'budget-reason.json',dict(reason=reason, observation=observation,
                            child_pid=child.pid, process_group=child.pid))
                        stop_owned(child,record['identity'],output/'owned-stop.json',reason)
                        stop_requested = True
                        raise RuntimeError(reason)
                    if len(record['samples']) % 6 == 0:
                        print('candidate B3 child',child.pid,'active',observation,flush=True)
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            record.update(status='finished',returncode=child.returncode,
                child_cpu=dict(user_seconds=after.ru_utime-before.ru_utime,
                    system_seconds=after.ru_stime-before.ru_stime))
            record['samples'].append(sample(evidence_root=evidence_root, evidence_roots=evidence_roots))
            assert rejection(record['samples'][-1]) is None, rejection(record['samples'][-1])
            assert child.returncode in expected, 'unexpected compiler-stage return code'
        except BaseException as error:
            record.update(status='failed',error=repr(error))
            # Receipt/validation errors must neither abandon a live child nor
            # turn off the active resource guard while waiting for its result.
            drain_failed_child(child, record, output, evidence_root=evidence_root, evidence_roots=evidence_roots, stop_requested=stop_requested)
            record['returncode']=child.returncode
            raise
        finally:
            record['finished_at']=time.time()
            stdout.flush();stderr.flush()
            record['stdout_sha256']=owned.sha(output/'stdout')
            record['stderr_sha256']=owned.sha(output/'stderr')
            owned.write(output/'receipt.json',record)
    return record
