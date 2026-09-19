"""Bounded lossless retention of the exact closed failed-driver proposal.

One archive-processing child, no provider commands and no source mutations.
The wrapper supplies the held canonical lock. No execution is authorized by
this source file's existence.
"""
import argparse
from contextlib import contextmanager
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import resource
import shutil
import stat
import sys
import tarfile
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
HERE = ROOT/'experiments/hash-driver-failure-evidence-01'
WORK = ROOT/'.work/hash-driver-failure-evidence-01'
RESULT = ROOT/'results/hir-options-hash-driver-failure-01'
PROPOSAL = O/'.work/hash-driver-failure-retention-proposal-01.json'
PROPOSAL_SHA = '8a3b56f5dd8d52e12e14389bba3771fea32c3d06cf3b2b4b5348330aeebafe13'
PYTHON = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
LIMITS = dict(maximum_selected_files=256, maximum_file_bytes=64*2**20,
              maximum_logical_bytes=128*2**20, maximum_compressed_bytes=32*2**20,
              maximum_manifest_bytes=2*2**20, maximum_expanded_archive_bytes=132*2**20)
RESERVATION = 64*2**20
ENVIRONMENT = dict(HOME='/Users/danluu', USER='danluu', LOGNAME='danluu', LANG='C', LC_ALL='C',
                   TZ='UTC', PATH='/usr/bin:/bin:/usr/sbin:/sbin', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
START = time.monotonic()
READ_BYTES = 0


def require(value, message):
    if not value:
        raise RuntimeError(message)


def identity(path):
    s = Path(path).lstat()
    return {k: getattr(s, 'st_'+k) for k in FIELDS}


def held_identity(stream):
    s = os.fstat(stream.fileno())
    return {k: getattr(s, 'st_'+k) for k in FIELDS}


def guard():
    require(time.monotonic()-START <= 600, 'finite 600s archive wall bound')
    require(shutil.disk_usage(ROOT).free >= 9*2**30, 'live 9GiB archive floor')


def count_read(size):
    global READ_BYTES
    guard()
    READ_BYTES += size
    require(READ_BYTES <= 1024*2**20, 'finite total source and archive read bound')


@contextmanager
def ordinary(path, expected=None):
    path = Path(path)
    require(path.resolve(strict=True) == path, 'ordinary absolute input route')
    before = identity(path)
    require(stat.S_ISREG(before['mode']) and before['size'] <= LIMITS['maximum_file_bytes'], 'bounded ordinary input')
    if expected is not None:
        require(before == expected, 'original input identity changed: '+str(path))
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        require(held_identity(stream) == before, 'opened input identity changed')
        yield stream
        require(held_identity(stream) == before, 'held input identity changed')
    require(path.resolve(strict=True) == path and identity(path) == before, 'input route or identity changed')


def read_bytes(path, expected=None):
    with ordinary(path, expected) as stream:
        data = stream.read(LIMITS['maximum_file_bytes']+1)
        count_read(len(data))
        require(len(data) <= LIMITS['maximum_file_bytes'], 'input grew beyond bound')
        return data


def sha(path, expected=None):
    digest = hashlib.sha256()
    with ordinary(path, expected) as stream:
        while block := stream.read(2**20):
            count_read(len(block))
            digest.update(block)
    return digest.hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def write(path, data, replace=False):
    require(len(data) <= LIMITS['maximum_manifest_bytes'], 'finite generated document')
    target = path.with_name(path.name+'.staged') if replace else path
    with target.open('xb') as stream:
        require(stream.write(data) == len(data), 'short document write')
        stream.flush()
        os.fsync(stream.fileno())
    if replace:
        target.replace(path)
    sync_directory(path.parent)


def sync_directory(path):
    require(path.resolve(strict=True) == path and path.is_dir(), 'ordinary output directory')
    before = path.stat()
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        held = os.fstat(fd)
        require((held.st_dev, held.st_ino) == (before.st_dev, before.st_ino), 'output directory changed')
        os.fsync(fd)
        after = path.stat()
        require((held.st_dev, held.st_ino) == (after.st_dev, after.st_ino), 'output directory replaced')
    finally:
        os.close(fd)


def members_under(root):
    root = Path(root)
    require(root.resolve(strict=True) == root and root.is_dir(), 'ordinary closed evidence directory')
    found = []
    entries = 0
    for parent, dirs, files in os.walk(root, followlinks=False, onerror=lambda e: (_ for _ in ()).throw(e)):
        guard()
        for name in dirs+files:
            entries += 1
            require(entries <= 1024, 'finite closed evidence membership')
            path = Path(parent)/name
            s = path.lstat()
            require(stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode), 'closed evidence special entry')
            if stat.S_ISREG(s.st_mode):
                found.append(str(path.relative_to(root)))
    return sorted(found)


def checked_json(row):
    data = read_bytes(row['path'], row['identity'])
    require(len(data) == row['size'] and hashlib.sha256(data).hexdigest() == row['sha256'], 'selected JSON differs')
    return json.loads(data)


def source_guards(proposal, rows):
    for row in rows.values():
        guard()
        require(sha(row['path'], row['identity']) == row['sha256'], 'selected source bytes changed')
    for root, expected in proposal['complete_scoped_directories'].items():
        require(members_under(root) == expected, 'closed source directory membership changed')


def validate_history(proposal, rows):
    failed = ROOT/'.work/hir-options-hash-driver-01'
    audit = checked_json(rows[str(ROOT/'.work/hir-options-hash-driver-failure-verification-01.json')])
    terminal = checked_json(rows[str(failed/'receipt.json')])
    compiled = checked_json(rows[str(failed/'compile/receipt.json')])
    require(audit['status'] == 'verified-retained-failure' and terminal['status'] == 'failed'
            and audit['receipt_sha256'] == rows[str(failed/'receipt.json')]['sha256'] == proposal['history']['receipt_sha256']
            and rows[str(ROOT/'.work/hir-options-hash-driver-failure-verification-01.json')]['sha256'] == proposal['history']['failure_audit_sha256']
            and audit['compile_receipt_sha256'] == rows[str(failed/'compile/receipt.json')]['sha256']
            and compiled['returncode'] == 1 and audit['actual_compiler_children'] == 1
            and audit['actual_driver_processes'] == audit['qualified_hash_driver_processes'] == 0
            and audit['hash_driver_qualified'] is False, 'exact audited failed compiler history')
    require(compiled['stderr_sha256'] == proposal['history']['exact_diagnostic_sha256'] == rows[str(failed/'compile/stderr')]['sha256'], 'exact failed diagnostic')
    require(audit['closure']['actual_outer_closed'] is True and audit['closure']['actual_wrapper_closed'] is True,
            'closed original compiler owner')
    for name in ['result.json', 'serial', 'parallel', 'linker-command.json', 'driver-loader-closure.json']:
        path = failed/name
        require(not path.exists() and not path.is_symlink(), 'original failed output unexpectedly present')
    # Historical prepared absences are intentionally not rerun: successor roots may now exist.
    return audit


def validate_references(proposal, rows):
    manifests = {}
    for key, ref in proposal['prior_archives'].items():
        manifest = checked_json(rows[ref['manifest']['path']])
        summary = checked_json(rows[ref['summary']['path']])
        audit = checked_json(rows[ref['independent_audit']['path']])
        require(summary['status'] == 'passed' and audit['status'] == 'verified'
                and summary['archive']['sha256'] == audit['archive_sha256'] == ref['sha256']
                and summary['archive']['bytes'] == ref['size']
                and summary['manifest_sha256'] == audit['manifest_sha256'] == ref['manifest']['sha256']
                and audit['summary_sha256'] == ref['summary']['sha256']
                and audit['full_gzip_eof_crc'] is audit['full_member_readback'] is True,
                'published archive manifest/summary/actual audit association')
        manifests[key] = manifest

    def association(ref, path, digest, size):
        require(ref['logical_member'] == str(path).lstrip('/') and ref['sha256'] == digest and ref['size'] == size,
                'published member source association')
        members = manifests[ref['archive']]
        name = ref['logical_member']
        chain = []
        while True:
            require(name in members and name not in chain and len(chain) < 256, 'bounded acyclic published alias')
            chain.append(name)
            row = members[name]
            require(row['sha256'] == digest and row['bytes'] == size, 'published alias bytes differ')
            if 'linkname' not in row:
                break
            name = row['linkname']
        require(chain == ref['alias_chain'] and name == ref['physical_member'], 'exact published physical member')

    manifest = checked_json(rows[str(ROOT/'.work/hir-options-hash-driver-01/source-snapshots.json')])
    snapshots = proposal['snapshots']
    require(len(manifest['files']) == snapshots['logical_files'] == 103 and len(manifest['blobs']) == snapshots['unique_payloads'] == 99,
            'complete original logical snapshot set')
    stored = {k: v for k, v in manifest['storage'].items() if v['kind'] == 'stored'}
    reused = {k: v for k, v in manifest['storage'].items() if v['kind'] == 'reused'}
    require(len(stored) == snapshots['new_stored_blobs'] == 65 and len(reused) == snapshots['reused_blobs'] == 34
            and len(stored)+len(reused) == 99, 'complete physical snapshot classification')
    for key, storage in stored.items():
        blob = manifest['blobs'][key]
        row = rows[storage['path']]
        require(row['sha256'] == blob['sha256'] and row['size'] == blob['compressed_bytes'], 'all new gzip bytes selected')
    require(sum(manifest['blobs'][k]['compressed_bytes'] for k in stored) == snapshots['new_stored_bytes'] == 9460166,
            'complete new gzip byte count')
    refs = snapshots['reused_archive_associations']
    require(len(refs) == 34 and len({r['source']['blob']['logical_sha256'] for r in refs}) == 34, 'all unique reused associations')
    for ref in refs:
        source = ref['source']; key = source['blob']['logical_sha256']
        require(key in reused and source == manifest['reuse'][key] and source['path'] == reused[key]['path'], 'exact old snapshot reference')
        association(ref['archived'], source['path'], source['blob']['sha256'], source['blob']['compressed_bytes'])
    base = snapshots['compact_base_archive_association']
    compact = checked_json(rows[str(ROOT/'experiments/hir-options-hash-driver-stage-02/inputs.json')])
    require(compact['file_table_base'] == base['reference'], 'original compact base reference retained')
    base_row = compact['files'][base['reference']['path']]
    association(base['archived'], base['reference']['path'], base['reference']['sha256'], base_row['size'])
    return dict(reused_blobs=34, new_blobs=65, referenced_native_base=True,
                prior_archive_payloads_read=False, prior_archive_payloads_included=False,
                meaning='Exact manifest and independently audited published archive associations; fetch the referenced Git blobs to recover excluded bytes.')


class SourceReader:
    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()
        self.size = 0

    def read(self, size):
        block = self.stream.read(size)
        count_read(len(block))
        self.size += len(block)
        self.digest.update(block)
        return block


class CappedOutput:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        guard()
        require(self.stream.tell()+len(data) <= LIMITS['maximum_compressed_bytes'], 'compressed archive cap before write')
        result = self.stream.write(data)
        require(result == len(data), 'short archive write')
        return result

    def flush(self):
        return self.stream.flush()

    def tell(self):
        return self.stream.tell()


def archive_readback(path, selected):
    class ExpandedReader:
        def __init__(self, stream):
            self.stream = stream
            self.total = 0

        def read(self, size):
            require(0 <= size <= 2**20, 'bounded gzip read request')
            block = self.stream.read(size)
            count_read(len(block))
            self.total += len(block)
            require(self.total <= LIMITS['maximum_expanded_archive_bytes'], 'expanded archive cap')
            return block

    seen = []
    with ordinary(path) as source, gzip.GzipFile(fileobj=source, mode='rb') as gz:
        expanded = ExpandedReader(gz)
        with tarfile.open(fileobj=expanded, mode='r|', format=tarfile.GNU_FORMAT) as archive:
            for entry in archive:
                require(len(seen) < len(selected) and entry.name == selected[len(seen)]['member'], 'exact ordered archive members')
                row = selected[len(seen)]
                require(entry.isfile() and entry.size == row['size'] and entry.mode == 0o644
                        and entry.mtime == entry.uid == entry.gid == 0 and not entry.uname and not entry.gname
                        and not entry.linkname, 'exact ordinary deterministic member')
                stream = archive.extractfile(entry)
                digest = hashlib.sha256(); size = 0
                while block := stream.read(2**20):
                    guard(); size += len(block); digest.update(block)
                require(size == row['size'] and digest.hexdigest() == row['sha256'], 'complete archive member readback')
                seen.append(entry.name)
            while block := archive.fileobj.read(2**20):
                require(not any(block), 'nonzero bytes after tar end marker')
        require(gz.read(1) == b'', 'full gzip EOF and trailer')
    require(len(seen) == len(selected) == 168, 'complete selected archive readback')
    return dict(members=len(seen), expanded_bytes=expanded.total, full_member_readback=True, full_gzip_eof_crc=True)


def main(fd):
    require(Path.cwd() == ROOT and Path(__file__).resolve() == HERE/'archive.py'
            and Path(sys.executable).resolve() == PYTHON and sys.dont_write_bytecode and not sys.flags.optimize,
            'fixed owner, source and Python route')
    require(dict(os.environ) == ENVIRONMENT, 'exact archive environment')
    resource.setrlimit(resource.RLIMIT_CPU, (300, 300))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32*2**20, 32*2**20))
    opened = os.fstat(fd); current = LOCK.stat()
    require((opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino) and LOCK.resolve(strict=True) == LOCK,
            'exact inherited canonical descriptor')
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with LOCK.open('r+') as competing:
        try:
            fcntl.flock(competing, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
        else:
            raise RuntimeError('inherited canonical lock not held')
    require(shutil.disk_usage(ROOT).free >= 9*2**30+RESERVATION, 'entry 9GiB plus64MiB reservation before output')
    data = read_bytes(PROPOSAL)
    require(hashlib.sha256(data).hexdigest() == PROPOSAL_SHA, 'exact reviewed proposal')
    proposal = json.loads(data)
    require(proposal['archive_source'] == str(HERE) and proposal['work'] == str(WORK) and proposal['destination'] == str(RESULT)
            and proposal['limits'] == LIMITS and proposal['file_count'] == 168 and proposal['logical_bytes'] == 40467639,
            'exact bounded retention scope')
    selected = proposal['files']
    require(len(selected) == 168 <= LIMITS['maximum_selected_files']
            and sum(r['size'] for r in selected) == 40467639 <= LIMITS['maximum_logical_bytes'], 'complete finite selection')
    rows = {r['path']: r for r in selected}
    require(len(rows) == len({r['member'] for r in selected}) == 168 and list(rows) == sorted(rows), 'unique ordered selection')
    for row in selected:
        name = PurePosixPath(row['member'])
        require(not name.is_absolute() and '..' not in name.parts and str(name) == row['path'].lstrip('/')
                and type(row['size']) is int and 0 <= row['size'] <= LIMITS['maximum_file_bytes']
                and row['identity']['size'] == row['size'], 'safe finite archive member')
    source_guards(proposal, rows)
    validate_history(proposal, rows)
    refs = validate_references(proposal, rows)
    require(all(not p.exists() and not p.is_symlink() for p in [WORK, RESULT]), 'fresh archive output namespaces')
    WORK.mkdir(mode=0o700); sync_directory(WORK.parent)
    receipt = dict(status='running', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
                   proposal_sha256=PROPOSAL_SHA, engine_sha256=sha(Path(__file__)), workload_children=0,
                   children=[], original_status='failed', actual_compiler_children=1, actual_driver_processes=0,
                   application_qualified=False, hash_driver_qualified=False, performance_measurement=False)
    write(WORK/'receipt.json', encoded(receipt))
    try:
        RESULT.mkdir(mode=0o700); sync_directory(RESULT.parent)
        write(RESULT/'proposal.json', data)
        manifest = dict(policy='closed-failed-driver-evidence-v1', proposal_sha256=PROPOSAL_SHA,
                        members=selected, original_history=proposal['history'], prior_archives=proposal['prior_archives'],
                        snapshots=proposal['snapshots'], prior_packet_audits=proposal['prior_packet_audits'], exclusions=proposal['exclusions'])
        write(RESULT/'manifest.json', encoded(manifest))
        archive_path = RESULT/'evidence.tar.gz'
        with archive_path.open('xb') as output:
            with gzip.GzipFile(filename='', fileobj=CappedOutput(output), mode='wb', mtime=0, compresslevel=9) as gz:
                with tarfile.open(fileobj=gz, mode='w', format=tarfile.GNU_FORMAT) as archive:
                    for row in selected:
                        entry = tarfile.TarInfo(row['member']); entry.mode = 0o644; entry.mtime = 0; entry.size = row['size']
                        with ordinary(row['path'], row['identity']) as stream:
                            reader = SourceReader(stream); archive.addfile(entry, reader)
                            require(reader.size == row['size'] and reader.digest.hexdigest() == row['sha256'], 'complete archived source bytes')
            output.flush(); os.fsync(output.fileno())
        sync_directory(RESULT)
        proof = archive_readback(archive_path, selected)
        source_guards(proposal, rows)
        validate_history(proposal, rows)
        require(sha(PROPOSAL) == PROPOSAL_SHA, 'proposal unchanged after archive')
        summary = dict(status='passed', meaning='Lossless retention passed; original compiler owner remains failed.',
                       original_status='failed', workload_children=0, actual_compiler_children=1, actual_driver_processes=0,
                       hash_driver_qualified=False, application_qualified=False, performance_measurement=False,
                       proposal_sha256=PROPOSAL_SHA, manifest_sha256=sha(RESULT/'manifest.json'),
                       archive=dict(sha256=sha(archive_path), bytes=archive_path.stat().st_size,
                                    logical_bytes=40467639, **proof), external_references=refs,
                       source_bytes_and_identities_unchanged=True, limits=LIMITS)
        write(RESULT/'summary.json', encoded(summary))
        sync_directory(RESULT); sync_directory(RESULT.parent)
        receipt.update(status='passed', archive_sha256=summary['archive']['sha256'],
                       manifest_sha256=summary['manifest_sha256'], summary_sha256=sha(RESULT/'summary.json'),
                       member_count=168, logical_bytes=40467639, full_member_readback=True, full_gzip_eof_crc=True,
                       free_bytes_after=shutil.disk_usage(ROOT).free, read_bytes=READ_BYTES)
        guard()
    except BaseException as error:
        receipt.update(status='failed', error=repr(error), partial_outputs_retained=True)
        raise
    finally:
        receipt['finished_at'] = time.time()
        write(WORK/'receipt.json', encoded(receipt), replace=True)
    print(json.dumps(dict(status='passed', receipt=str(WORK/'receipt.json'), receipt_sha256=sha(WORK/'receipt.json'),
                          archive_sha256=receipt['archive_sha256'], workload_children=0)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--canonical-fd', required=True, type=int)
    main(parser.parse_args().canonical_fd)
