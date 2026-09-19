"""Retain completed 49 controls and source proposals, never compiler payloads."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
OWNER = HERE.parents[1]
CONTROL = HERE.with_name('hir-options-hash-beta-controls-01')
sys.path.insert(0, str(CONTROL))
import run as control
owned = control.owned
WORK = OWNER / '.work/hir-options-hash-beta-retention-01'
RESULT = OWNER / 'results/hir-options-hash-beta-composition-02'
CAP = 32 * 2**20


def read(path): return json.loads(Path(path).read_bytes())


def guard(freeze):
    control.guard(freeze)
    for name, members in freeze['membership'].items():
        root = Path(name); actual = []
        for path in root.rglob('*'):
            assert not path.is_symlink()
            if path.is_file(): actual.append(str(path.relative_to(root)))
            else: assert path.is_dir()
        assert sorted(actual) == members, name
    terminal = read(control.WORK / 'receipt.json')
    assert terminal['status'] == 'passed' and terminal['controls_passed'] == 49
    assert all(terminal[key] == 0 for key in ['compiler_calls', 'provider_probes', 'B3_compositions'])
    assert owned.sha(control.WORK / 'result.json') == terminal['result_sha256']
    assert owned.sha(control.WORK / 'receipt.json') == freeze['controls_receipt_sha256']
    for name, receipt_field in freeze['verifications'].items():
        report = read(name)
        assert report['status'] in ['verified', 'passed']
        assert report[receipt_field] == freeze['controls_receipt_sha256'] and report['controls'] == 49
    assert not list((control.WORK / 'tmp').iterdir())


class CappedOutput:
    def __init__(self, raw): self.raw = raw
    def write(self, value):
        owned.disk(OWNER, 9)
        assert self.raw.tell() + len(value) <= CAP, 'compressed evidence cap reached'
        return self.raw.write(value)
    def tell(self): return self.raw.tell()
    def flush(self): return self.raw.flush()


class Reader:
    def __init__(self, raw): self.raw = raw; self.size = 0; self.digest = hashlib.sha256()
    def read(self, size):
        owned.disk(OWNER, 9)
        value = self.raw.read(size); self.size += len(value); self.digest.update(value)
        return value


def verify(path, members):
    seen = set()
    with tarfile.open(path, 'r:gz') as archive:
        actual = archive.getmembers()
        assert len(actual) == len(members) <= 128 and {row.name for row in actual} == set(members)
        for row in actual:
            expected = members[row.name]
            if row.islnk():
                assert row.linkname == expected['linkname'] and row.linkname in seen and row.size == 0
            else:
                assert row.isfile() and row.size == expected['size'] and 'linkname' not in expected
            digest = hashlib.sha256(); size = 0
            with archive.extractfile(row) as stream:
                while chunk := stream.read(2**20):
                    owned.disk(OWNER, 9); size += len(chunk); digest.update(chunk)
            assert size == expected['size'] and digest.hexdigest() == expected['sha256']
            seen.add(row.name)
    expanded = 0
    with gzip.open(path, 'rb') as stream:
        while chunk := stream.read(2**20):
            owned.disk(OWNER, 9); expanded += len(chunk)
            assert expanded <= 112 * 2**20
    return expanded


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--inputs-sha256', required=True)
    args = parser.parse_args()
    assert Path.cwd() == OWNER and sys.dont_write_bytecode and not sys.flags.optimize
    assert owned.sha(HERE / 'inputs.json') == args.inputs_sha256
    frozen = read(HERE / 'inputs.json')
    assert str(Path(sys.executable).resolve(strict=True)) == frozen['python']
    assert {k: v for k, v in os.environ.items() if k != '__CF_USER_TEXT_ENCODING'} == frozen['environment']
    if '__CF_USER_TEXT_ENCODING' in os.environ:
        import re
        parts = os.environ['__CF_USER_TEXT_ENCODING'].split(':')
        assert len(parts) == 3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})', value) for value in parts)
        assert int(parts[0], 16 if parts[0].lower().startswith('0x') else 10) == os.getuid() == 501
    guard(frozen)
    assert not WORK.exists() and not WORK.is_symlink() and not RESULT.exists() and not RESULT.is_symlink()
    WORK.mkdir()
    receipt = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
                   inputs_sha256=args.inputs_sha256, workload_children=0, compiler_calls=0, benchmark=False)
    def save(): owned.write(WORK / 'receipt.json', receipt)
    save()
    try:
        with owned.workload_lock(owned.CANONICAL_LOCK, 600):
            free = owned.disk(OWNER, 9); assert free >= 9 * 2**30 + CAP
            receipt.update(status='running', admitted_at=time.time(), free_bytes_before=free); save()
            guard(frozen)
            assert not RESULT.exists() and not RESULT.is_symlink() and RESULT.parent.resolve(strict=True) == RESULT.parent
            RESULT.mkdir()
            paths = [*frozen['archive_sources'], str(HERE / 'inputs.json')]
            assert len(paths) == len(set(paths)) <= 128
            members, duplicates = {}, {}
            logical = 0
            with (RESULT / 'evidence.tar.gz').open('xb') as raw:
                capped = CappedOutput(raw)
                with gzip.GzipFile(filename='', fileobj=capped, mode='wb', mtime=0) as gz:
                    with tarfile.open(fileobj=gz, mode='w') as archive:
                        for index, name in enumerate(paths):
                            path = Path(name); before = control.stamp(path)
                            expected = args.inputs_sha256 if path == HERE / 'inputs.json' else frozen['files'][name]['sha256']
                            size = before[3]; logical += size
                            assert logical <= 96 * 2**20 and stat.S_ISREG(before[2]) and path.resolve(strict=True) == path
                            member = 'files/' + path.as_posix().removeprefix('/')
                            assert member not in members
                            row = dict(source=name, size=size, sha256=expected)
                            info = tarfile.TarInfo(member); info.mode = 0o644; info.mtime = 0
                            key = (expected, size)
                            if key in duplicates:
                                assert owned.sha(path) == expected
                                row['linkname'] = duplicates[key]; info.type = tarfile.LNKTYPE; info.linkname = duplicates[key]
                                archive.addfile(info)
                            else:
                                info.size = size
                                with path.open('rb') as stream:
                                    reader = Reader(stream); archive.addfile(info, reader)
                                    assert reader.size == size and reader.digest.hexdigest() == expected
                                duplicates[key] = member
                            assert control.stamp(path) == before
                            members[member] = row
                raw.flush(); os.fsync(raw.fileno())
            expanded = verify(RESULT / 'evidence.tar.gz', members)
            guard(frozen)
            manifest = dict(status='verified', members=members, logical_members=len(members), physical_members=len(duplicates),
                            logical_file_bytes=logical, gzip_expanded_bytes=expanded, gzip_full_eof_crc_verified=True,
                            archive_sha256=owned.sha(RESULT / 'evidence.tar.gz'), inputs_sha256=args.inputs_sha256,
                            payload_exclusions=frozen['payload_exclusions'], controls_passed=49,
                            actual_B3_compositions=0, actual_candidate_compiler_builds=0,
                            scope='Both source drafts retained; successor02 has 49 pure controls only. Actual compiler/B3 qualification remains pending.')
            owned.write(RESULT / 'manifest.json', manifest)
            assert (RESULT / 'manifest.json').stat().st_size < 2**20
            receipt.update(status='passed', archive_sha256=manifest['archive_sha256'], manifest_sha256=owned.sha(RESULT / 'manifest.json'),
                           logical_members=len(members), physical_members=len(duplicates), free_bytes_after=owned.disk(OWNER, 9))
    except BaseException as error:
        receipt.update(status='failed', error=repr(error)); raise
    finally:
        receipt['finished_at'] = time.time(); save()


if __name__ == '__main__': main()
