"""Bounded zero-child retention of B308 actual assembly, compressed proofs and honest preparation/audit history."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
A = HERE.parents[1]
WORK = A/'.work/beta-composition08-retention-01'
OUT = A/'results/hir-options-hash-beta-composition-08'
OWNED = A/'experiments/stable-cgu/owned_stage.py'
MIB = 2**20
BOUNDS = dict(members=2048, file_bytes=64*MIB, logical_bytes=512*MIB,
              physical_bytes=384*MIB, compressed_bytes=192*MIB, expanded_bytes=416*MIB)


def require(value, message):
    if not value:
        raise RuntimeError(message)


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stamp(path):
    s = Path(path).lstat()
    return [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]


def check(path, row, disk=lambda: None):
    path = Path(path)
    before = stamp(path)
    require(path.resolve(strict=True) == path and stat.S_ISREG(before[2]) and before == row['stamp'], 'input identity: '+str(path))
    require(before[3] == row['bytes'] <= BOUNDS['file_bytes'], 'input size')
    h, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        while block := stream.read(MIB):
            disk(); h.update(block); size += len(block)
    require(stamp(path) == before and size == row['bytes'] and h.hexdigest() == row['sha256'], 'input bytes: '+str(path))


def members(root, excluded=()):
    root = Path(root)
    require(root.resolve(strict=True) == root and root.is_dir(), 'ordinary evidence root')
    found = []
    def error(value):
        raise value
    for parent, dirs, files in os.walk(root, followlinks=False, onerror=error):
        for name in dirs+files:
            p = Path(parent)/name
            require(not p.is_symlink(), 'evidence link')
            require(p.is_dir() or p.is_file(), 'evidence special file')
        for name in files:
            p = Path(parent)/name
            if str(p) not in excluded:
                found.append(str(p))
                require(len(found) <= BOUNDS['members'], 'membership bound')
    return sorted(found)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m)
    return m


def guard(freeze, history, disk=lambda: None):
    require(freeze['bounds'] == BOUNDS and freeze['owner'] == str(A), 'freeze scope')
    for name, row in freeze['directories'].items():
        require(members(name, row['excluded_future_outputs']) == row['members'], 'membership: '+name)
    for name, row in freeze['files'].items():
        check(name, row, disk)
    for route, resolved in freeze['routes'].items():
        require(str(Path(route).resolve(strict=True)) == resolved, 'executor route')
    for path in freeze['absent_paths']:
        require(not Path(path).exists() and not Path(path).is_symlink(), 'closed failed discovery gained output')
    require(history.validate_all(disk) == freeze['history'], 'actual assembly/preparation/audit history')
    for prior in freeze['prior_archives']:
        require(sha(prior['path']) == prior['sha256'], 'prior retained archive reference')



class Capped:
    def __init__(self, raw, disk):
        self.raw, self.disk = raw, disk
    def write(self, value):
        self.disk()
        require(self.raw.tell()+len(value) <= BOUNDS['compressed_bytes'], 'compressed cap')
        return self.raw.write(value)
    def tell(self):
        return self.raw.tell()
    def flush(self):
        return self.raw.flush()


def archive(files, disk):
    manifest, first = {}, {}
    path = OUT/'evidence.tar.gz'
    with path.open('xb') as raw:
        with gzip.GzipFile(fileobj=Capped(raw, disk), mode='wb', filename='', mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as tar:
                for name, row in sorted(files.items()):
                    disk(); p = Path(name)
                    require(stamp(p) == row['stamp'], 'prearchive identity')
                    member = tarfile.TarInfo(name.lstrip('/')); member.mode = 0o644
                    key = (row['sha256'], row['bytes'])
                    saved = dict(source=name, sha256=key[0], bytes=key[1])
                    if key in first:
                        member.type = tarfile.LNKTYPE; member.linkname = first[key]
                        saved['linkname'] = member.linkname; tar.addfile(member)
                    else:
                        member.size = row['bytes']
                        with p.open('rb') as stream:
                            tar.addfile(member, stream)
                        first[key] = member.name
                    require(stamp(p) == row['stamp'], 'duringarchive identity')
                    manifest[member.name] = saved
        raw.flush(); os.fsync(raw.fileno())
    seen = set()
    with tarfile.open(path, 'r:gz') as tar:
        for member in tar:
            require(member.name in manifest and member.name not in seen, 'archive membership')
            row = manifest[member.name]
            if 'linkname' in row:
                require(member.islnk() and member.linkname == row['linkname'] and member.linkname in seen and member.size == 0, 'archive dedup route')
            else:
                require(member.isfile() and member.size == row['bytes'], 'archive ordinary member')
            h, size = hashlib.sha256(), 0
            with tar.extractfile(member) as stream:
                while block := stream.read(MIB):
                    disk(); h.update(block); size += len(block)
                    require(size <= BOUNDS['file_bytes'], 'member readback bound')
            require(size == row['bytes'] and h.hexdigest() == row['sha256'], 'full member readback')
            seen.add(member.name)
    require(seen == set(manifest), 'complete member set')
    expanded = 0
    with gzip.open(path, 'rb') as stream:
        while block := stream.read(MIB):
            disk(); expanded += len(block)
            require(expanded <= BOUNDS['expanded_bytes'], 'gzip EOF bound')
    return manifest, dict(sha256=sha(path), bytes=path.stat().st_size, logical_members=len(manifest),
        physical_members=len(first), expanded_bytes=expanded, full_member_hashes_verified=True, full_gzip_eof_crc_verified=True)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--inputs-sha256', required=True); args = parser.parse_args()
    require(Path.cwd() == A and sys.dont_write_bytecode and not sys.flags.optimize, 'owner/Python flags')
    inputs = HERE/'inputs.json'
    require(sha(inputs) == args.inputs_sha256, 'freeze hash')
    freeze = read(inputs)
    require(str(Path(sys.executable).resolve(strict=True)) == freeze['python'], 'Python route')
    environment = dict(os.environ); context = environment.pop('__CF_USER_TEXT_ENCODING', None)
    if context is not None:
        parts = context.split(':')
        require(len(parts) == 3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})', p) for p in parts), 'CF context grammar')
        require(int(parts[0], 16 if parts[0].lower().startswith('0x') else 10) == os.getuid() == 501, 'CF user')
    require(environment == freeze['environment'], 'exact environment')
    for p in [Path(__file__).resolve(), HERE/'history.py', OWNED, Path(freeze['python'])]:
        check(p, freeze['files'][str(p)])
    owned = module('beta_retention_owned', OWNED)
    history = module('beta_retention_history', HERE/'history.py')
    require(not WORK.exists() and not WORK.is_symlink() and not OUT.exists() and not OUT.is_symlink(), 'fresh owned output')
    WORK.mkdir(); receipt = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
        inputs_sha256=args.inputs_sha256, workload_children=0, compiler_calls=0, B3_compositions=0)
    def save():
        owned.write(WORK/'receipt.json', receipt)
    save()
    try:
        with owned.workload_lock(owned.CANONICAL_LOCK, 600):
            disk = lambda: owned.disk(A, 9)
            free = disk(); require(free >= 9*2**30+BOUNDS['expanded_bytes'], 'archive reservation')
            receipt.update(status='running', admitted_at=time.time(), free_bytes_before=free); save()
            guard(freeze, history, disk)
            files = {name: freeze['files'][name] for name in freeze['archive_sources']}
            files[str(inputs)] = dict(stamp=stamp(inputs), bytes=inputs.stat().st_size, sha256=args.inputs_sha256)
            require(len(files) <= BOUNDS['members'] and sum(r['bytes'] for r in files.values()) <= BOUNDS['logical_bytes'], 'logical cap')
            require(sum(n for _, n in {(r['sha256'], r['bytes']) for r in files.values()}) <= BOUNDS['physical_bytes'], 'physical cap')
            OUT.mkdir(exist_ok=False)
            manifest, result = archive(files, disk)
            guard(freeze, history, disk); check(inputs, files[str(inputs)], disk)
            owned.write(OUT/'manifest.json', manifest)
            summary = dict(status='passed', history=freeze['history'], archive=result, manifest_sha256=sha(OUT/'manifest.json'),
                inputs_sha256=args.inputs_sha256, prior_archives=freeze['prior_archives'], payload_exclusions=freeze['payload_exclusions'],
                scope='Actual B308 assembly and auxiliary strip qualification. Nineteen original children; no repeated workload in retention. No native-stock/hash-driver/application or performance qualification.',
                source07_scope='Original prepared-unrun proposal and prelaunch capacity rejection retained unchanged.')
            owned.write(OUT/'summary.json', summary)
            receipt.update(status='passed', finished_at=time.time(), free_bytes_after=disk(), archive=result, summary_sha256=sha(OUT/'summary.json'))
            save()
    except BaseException as error:
        receipt.update(status='failed', finished_at=time.time(), error=repr(error)); save(); raise


if __name__ == '__main__':
    main()
