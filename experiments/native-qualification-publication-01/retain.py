"""Bounded zero-child standalone native evidence publication; original native terminals remain failed."""
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
WORK = A/'.work/native-qualification-publication-01'
OUT = A/'results/hir-options-hash-native-reconciliation-01'
SOURCE_BUNDLE = A/'experiments/native-qualification-source-01'
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
        path=Path(prior['path']);before=stamp(path)
        require(path.resolve(strict=True)==path and stat.S_ISREG(before[2]) and before==prior['stamp']
            and before[3]<=192*MIB and sha(path)==prior['sha256'] and stamp(path)==before, 'prior retained archive reference')



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



def publish_sources(freeze,disk):
    rows=freeze['source_copies']
    require(len(rows)==58 and sum(row['size'] for row in rows.values())==512816,
            'exact bounded source-copy bundle required')
    require(not SOURCE_BUNDLE.exists() and not SOURCE_BUNDLE.is_symlink(), 'fresh source-copy namespace required')
    SOURCE_BUNDLE.mkdir();copied={}
    for destination,row in sorted(rows.items()):
        disk();path=Path(destination);source=Path(row['source'])
        require(path.is_relative_to(SOURCE_BUNDLE) and '..' not in path.parts
            and row['sha256']==freeze['files'][str(source)]['sha256']
            and row['size']==freeze['files'][str(source)]['bytes'], 'source-copy membership differs')
        check(source,freeze['files'][str(source)],disk)
        data=source.read_bytes();require(len(data)==row['size'] and hashlib.sha256(data).hexdigest()==row['sha256'],
            'source-copy current bytes differ')
        path.parent.mkdir(parents=True,exist_ok=True)
        require(path.parent.resolve(strict=True)==path.parent,'source-copy parent is indirect')
        with path.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        require(sha(path)==row['sha256'] and path.stat().st_size==row['size'] and path.stat().st_nlink==1,
                'source-copy full readback differs')
        copied[destination]=row
    require(set(members(SOURCE_BUNDLE))==set(rows),'source-copy exact membership differs')
    data=(json.dumps(dict(status='exact-source-copies',files=copied,
        interpretation='Immutable provenance copies; original A source/receipts remain authoritative. No compiler or generator run.'),
        sort_keys=True,indent=2)+'\n').encode()
    require(len(data)<=128*1024,'source-copy provenance bound')
    path=SOURCE_BUNDLE/'source-map.json'
    with path.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    require(path.read_bytes()==data,'source-map readback differs')
    return dict(directory=str(SOURCE_BUNDLE),files=copied,source_map_sha256=sha(path),bytes=512816)


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
    require(all(not p.exists() and not p.is_symlink() for p in [WORK,OUT,SOURCE_BUNDLE]), 'fresh owned output')
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
            source_copies = publish_sources(freeze,disk)
            guard(freeze, history, disk); check(inputs, files[str(inputs)], disk)
            owned.write(OUT/'manifest.json', manifest)
            summary = dict(status='passed', history=freeze['history'], archive=result, manifest_sha256=sha(OUT/'manifest.json'),
                inputs_sha256=args.inputs_sha256, prior_archives=freeze['prior_archives'], payload_exclusions=freeze['payload_exclusions'],
                source_copies=source_copies,
                scope='Standalone native evidence: original failed5+6+20 and separate zero-command reconciliation of saved20. All376original gzip files and125logical delta proofs retained. No workload rerun or performance qualification.',
                original_failures_preserved=True)
            owned.write(OUT/'summary.json', summary)
            receipt.update(status='passed', finished_at=time.time(), free_bytes_after=disk(), archive=result, summary_sha256=sha(OUT/'summary.json'))
            save()
    except BaseException as error:
        receipt.update(status='failed', finished_at=time.time(), error=repr(error)); save(); raise


if __name__ == '__main__':
    main()
