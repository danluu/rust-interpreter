"""Exact partial retirement of nine closed task-owned caches; keep every directory.

The unlink implementation is the unchanged, actually qualified six-control
fd_remove.remove_files. This controller binds its finite saved inventories and
retains normal probe closure and a durable per-root unlink ledger.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
OWNER = HERE.parents[1]
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
WORK = X/'.work/runtime-exporter07-closed-cache-retirement-01'
PLAN = HERE/'plan.json'
FIELDS = ('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
DEADLINE = None


def require(ok, message):
    if not ok: raise RuntimeError(message)


def identity(path):
    s = path if isinstance(path, os.stat_result) else Path(path).lstat()
    return {key:getattr(s, 'st_'+key) for key in FIELDS}


def capacity():
    if DEADLINE is not None:
        require(time.monotonic() < DEADLINE, 'retirement observation deadline')
    s = os.statvfs(OWNER); free = s.f_bavail*s.f_frsize
    require(free >= 9*2**30, 'nine GiB stop floor')
    return free


def file(path, check_capacity=True):
    path = Path(path); before = identity(path)
    require(path.resolve(strict=True) == path and stat.S_ISREG(before['mode'])
        and before['size'] <= 256*2**20, 'ordinary bounded file required')
    h = hashlib.sha256(); size = 0
    with os.fdopen(os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK), 'rb') as stream:
        require(identity(os.fstat(stream.fileno())) == before, 'opened file differs')
        while block := stream.read(2**20):
            if check_capacity: capacity()
            h.update(block); size += len(block)
            require(size <= 256*2**20, 'file grew beyond bound')
        require(identity(os.fstat(stream.fileno())) == before, 'opened file changed')
    require(identity(path) == before and size == before['size'], 'file changed')
    return dict(identity=before, sha256=h.hexdigest())


def read(path): return json.loads(Path(path).read_bytes())


def write(path, value):
    data = (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
    require(len(data) <= 16*2**20, 'evidence file bound')
    temporary = path.with_name(path.name+'.staged')
    with temporary.open('xb') as out:
        out.write(data); out.flush(); os.fsync(out.fileno())
    temporary.replace(path)


def no_signals(event, args):
    if event in ('os.kill', 'os.killpg'):
        raise RuntimeError('no explicit signals authorized')


def load_module(name, ref):
    require(file(ref['path']) == ref['file'], 'imported source differs')
    spec = importlib.util.spec_from_file_location(name, ref['path'])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def inventory(root, expected):
    """Same ordinary-file row schema; bounded to the exact admitted membership."""
    require(root.resolve(strict=True) == root and root.is_dir() and not root.is_symlink(), 'ordinary root required')
    rows = {'.':dict(kind='directory', identity=identity(root))}; allocated = 0; seen = set()
    for parent, dirs, files in os.walk(root, followlinks=False):
        capacity()
        for name in sorted(dirs+files):
            path = Path(parent)/name; key = str(path.relative_to(root)); s = path.lstat()
            require(key in expected, 'unadmitted tree member: '+str(path))
            before = identity(s); require(before['dev'] == rows['.']['identity']['dev'], 'cross-filesystem entry')
            inode = (before['dev'], before['ino'])
            if inode not in seen: allocated += s.st_blocks*512; seen.add(inode)
            if stat.S_ISREG(before['mode']):
                require(before['nlink'] == 1, 'hardlinked cache file')
                rows[key] = dict(kind='file', **file(path))
            else:
                require(stat.S_ISDIR(before['mode']) and before['mode'] & 0o200, 'unexpected link/type/readonly directory')
                rows[key] = dict(kind='directory', identity=before)
            require(identity(path) == before, 'entry changed while reading')
    require(set(rows) == set(expected) and identity(root) == rows['.']['identity'], 'tree membership changed')
    return rows, allocated


class Retirement:
    def __init__(self, digest):
        require(Path.cwd() == OWNER and sys.dont_write_bytecode and not sys.flags.optimize, 'fixed owner/Python required')
        require(file(PLAN)['sha256'] == digest, 'plan differs')
        self.plan = read(PLAN); self.digest = digest
        require(self.plan['selected_files'] == 1456 and self.plan['retained_files'] == 9952
            and len(self.plan['scopes']) == 9 and self.plan['remove_directories'] is False, 'scope differs')
        require(dict(os.environ) == self.plan['environment'], 'exact environment differs')
        require(str(Path(sys.executable).resolve(strict=True)) == self.plan['python'], 'Python route differs')
        self.guard()
        self.remover = load_module('qualified_partial_file_remover', self.plan['remover'])
        self.owned = load_module('qualified_owned_lock', self.plan['owned_stage'])
        require(not os.path.lexists(WORK), 'fresh work namespace required')
        WORK.mkdir(mode=0o700); (WORK/'commands').mkdir(); (WORK/'ledgers').mkdir()
        self.record = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
            plan_sha256=digest, children=[], roots=[], compiler_calls=0, signals=0, removed_directories=0,
            benchmark=False, canonical_parent_lock_closed_at=None, live_probe_possible=False)
        self.save()

    def save(self): write(WORK/'receipt.json', self.record)

    def guard(self):
        require(list(os.uname()) == self.plan['platform'] and file(PLAN)['sha256'] == self.digest, 'platform/plan changed')
        for path, row in self.plan['frozen_files'].items(): require(file(path) == row, 'frozen source/evidence differs: '+path)
        for path, row in self.plan['routes'].items():
            require(identity(path) == row['identity'] and str(Path(path).resolve(strict=True)) == row['resolved'], 'executor route differs')
        controls = self.plan['controls']; audit = read(controls['audit']); receipt = read(controls['receipt']); freeze = read(controls['freeze'])
        require(audit['status'] == 'verified' and audit['controls'] == receipt['controls_passed'] == 6
            and receipt['status'] == 'passed' and receipt['inputs_sha256'] == audit['inputs_sha256'] == file(controls['freeze'])['sha256']
            and audit['receipt_sha256'] == file(controls['receipt'])['sha256'], 'actual six-control qualification differs')
        require(freeze['files'][controls['qualified_remover_path']]['sha256'] == self.plan['remover']['file']['sha256'], 'qualified remover association differs')
        for row in self.plan['published_copies']:
            require(file(row['destination']) == row['file'], 'retained installed copy differs')

    def probe(self, spec, fd):
        """Exact ps/lsof only; bounded wait, inherited owning FD, no signals/retry."""
        out = WORK/'commands'/spec['label']; out.mkdir()
        record = dict(status='starting', argv=spec['argv'], cwd=str(OWNER), environment=self.plan['environment'],
            parent_pid=os.getpid(), started_at=time.time(), child_may_be_live=False)
        write(out/'receipt.json', record); child = None
        try:
            with (out/'stdout').open('xb') as stdout, (out/'stderr').open('xb') as stderr:
                child = subprocess.Popen(spec['argv'], cwd=OWNER, env=self.plan['environment'], stdout=stdout,
                    stderr=stderr, pass_fds=(fd,), start_new_session=True)
                deadline = time.monotonic()+30
                record.update(status='running', pid=child.pid, child_may_be_live=True)
                write(out/'receipt.json', record)
                while child.poll() is None:
                    require(time.monotonic() < deadline, 'exact read-only probe deadline; no signal or retry')
                    capacity()
                    require(stdout.tell()+stderr.tell() <= 2**20, 'probe raw output bound')
                    try: child.wait(timeout=min(.25, max(.001, deadline-time.monotonic())))
                    except subprocess.TimeoutExpired: pass
                record.update(status='finished', returncode=child.returncode, child_may_be_live=False, wait_returned_at=time.time())
        except BaseException as error:
            record.update(status='failed', error=repr(error))
            if child is not None:
                if child.poll() is None:
                    record['child_may_be_live'] = True
                else:
                    record.update(returncode=child.returncode, child_may_be_live=False, wait_returned_at=time.time())
            raise
        finally:
            record['observation_finished_at'] = time.time()
            self.record['live_probe_possible'] |= record['child_may_be_live']
            write(out/'receipt.json', record)
            if not record['child_may_be_live']:
                record['raw_bytes'] = sum((out/label).stat().st_size for label in ['stdout','stderr'] if (out/label).exists())
                record['raw_bound_exceeded'] = record['raw_bytes'] > 2**20
                if not record['raw_bound_exceeded']:
                    for label in ['stdout','stderr']:
                        if (out/label).exists(): record[label] = file(out/label, False)
                write(out/'receipt.json', record)
            self.record['children'].append(dict(label=spec['label'], path=str(out/'receipt.json'), **file(out/'receipt.json', False))); self.save()
        require(not record['raw_bound_exceeded'] and record['returncode'] == 1 and (out/'stdout').read_bytes() == (out/'stderr').read_bytes() == b'',
            'handles or historical PID present; no inference from PID reuse')

    def ledger(self, index):
        path = WORK/'ledgers'/f'{index:02d}.jsonl'; events = []; error = None
        try:
            if path.exists():
                for line in path.read_bytes().splitlines(keepends=True):
                    require(line.endswith(b'\n'), 'partial final ledger line'); events.append(json.loads(line))
        except BaseException as failure: error = repr(failure)
        result = {kind:[row['path'] for row in events if row['event'] == kind] for kind in ['intent','unlinked','validated']}
        result.update(path=str(path), readback_error=error, uncertain=sorted(set(result['intent'])-set(result['unlinked'])))
        return result

    def run(self):
        global DEADLINE
        try:
            with self.owned.workload_lock(self.owned.CANONICAL_LOCK, 600) as fd:
                require(capacity() >= 9*2**30+32*2**20, 'retirement evidence reserve unavailable')
                DEADLINE = time.monotonic()+600
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=capacity()); self.save()
                self.guard(); admitted = []
                for scope in self.plan['scopes']:
                    packed = Path(scope['inventory']['path']).read_bytes(); payload = gzip.decompress(packed)
                    require(len(payload) == scope['inventory']['expanded_bytes'] and hashlib.sha256(payload).hexdigest() == scope['inventory']['expanded_sha256'], 'saved complete gzip inventory differs')
                    saved = json.loads(payload); root = Path(scope['root'])
                    require(saved['root'] == str(root) and saved['outer_parent'] == scope['outer_parent'], 'inventory route differs')
                    current, allocated = inventory(root, saved['rows'])
                    require(current == saved['rows'] and identity(root.parent) == scope['outer_parent'], 'full current inventory differs')
                    selected = scope['selected_files']; retained = scope['retained_files']
                    require(len(selected) == scope['selected_count'] and len(retained) == scope['retained_count']
                        and set(selected).isdisjoint(retained) and set(selected)|set(retained) == {n for n,r in current.items() if r['kind']=='file'}, 'selection partition differs')
                    admitted.append(current)
                write(WORK/'transition.json', self.plan['transition'])
                for spec in self.plan['commands']: self.probe(spec, fd)
                self.guard()
                # Revalidate every root after all point-in-time probes, before the first unlink.
                for scope, rows in zip(self.plan['scopes'], admitted, strict=True):
                    require(inventory(Path(scope['root']), rows)[0] == rows and identity(Path(scope['root']).parent) == scope['outer_parent'], 'target changed after probes')
                remaining_all = []
                for index, (scope, rows) in enumerate(zip(self.plan['scopes'], admitted, strict=True)):
                    root = Path(scope['root']); ledger = WORK/'ledgers'/f'{index:02d}.jsonl'
                    with ledger.open('xb'): pass
                    try:
                        remaining = self.remover.remove_files(root, rows, scope['selected_files'], scope['outer_parent'], ledger, capacity)
                    finally:
                        self.record['roots'].append(dict(root=str(root), ledger=self.ledger(index))); self.save()
                    current, allocated = inventory(root, remaining)
                    require(current == remaining and identity(root.parent) == scope['outer_parent'], 'remaining complete tree differs')
                    for name in scope['retained_files']: require(current[name] == rows[name], 'retained file changed')
                    require({n for n,r in current.items() if r['kind']=='directory'} == {n for n,r in rows.items() if r['kind']=='directory'}, 'directory removed')
                    encoded = (json.dumps(dict(root=str(root), rows=current), sort_keys=True)+'\n').encode()
                    output = WORK/f'remaining-{index:02d}.json.gz'
                    with output.open('xb') as stream: stream.write(gzip.compress(encoded, mtime=0)); stream.flush(); os.fsync(stream.fileno())
                    require(gzip.decompress(output.read_bytes()) == encoded, 'remaining inventory roundtrip differs')
                    summary = self.record['roots'][-1]; expected = {str(root/name) for name in scope['selected_files']}
                    require(all(len(summary['ledger'][k]) == len(expected) and set(summary['ledger'][k]) == expected for k in ['intent','unlinked','validated'])
                        and not summary['ledger']['uncertain'] and summary['ledger']['readback_error'] is None, 'incomplete deletion ledger')
                    summary.update(retained_files=len(scope['retained_files']), allocated_bytes_after=allocated, remaining_inventory=dict(path=str(output), **file(output)))
                    remaining_all.append(remaining)
                for scope, remaining in zip(self.plan['scopes'], remaining_all, strict=True):
                    require(inventory(Path(scope['root']), remaining)[0] == remaining
                        and identity(Path(scope['root']).parent) == scope['outer_parent'], 'final full retained tree differs')
                self.guard()
                self.record.update(status='passed', removed_files=1456, retained_files=9952, all_directories_retained=True,
                    free_bytes_after=capacity(), finished_at=time.time(), capacity_reservation_claim=False)
            self.record['canonical_parent_lock_closed_at'] = time.time()
        except BaseException as error:
            self.record.update(status='failed', error=repr(error), observation_finished_at=time.time())
            self.record['canonical_parent_lock_closed_at'] = time.time()
            raise
        finally: self.save()


if __name__ == '__main__':
    sys.addaudithook(no_signals)
    parser = argparse.ArgumentParser(); parser.add_argument('--plan-sha256', required=True)
    Retirement(parser.parse_args().plan_sha256).run()
