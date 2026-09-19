"""Unrun exact reviewed ordinary copier; no provider reads or target imports."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import stat
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
SCOPE = O/'.work/retained-proof-copy-publication-scope-01.json'
DEST = ROOT/'results/retained-proof-copy-retirement-01'
REPORT = O/'.work/retained-proof-copy-publication-verification-01.json'
TARGET = O/'.work/hir-options-hash-run-make-01/retained'
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
LIMITS = dict(maximum_files=256, maximum_file_bytes=4*2**20,
              maximum_source_bytes=12*2**20, maximum_output_bytes=16*2**20)
README = '''# Exact proof-copy recovery and retirement

The retained source packets, actual receipts/raw, two read-only observations,
63-event ledger and independent audit document removal of exactly 21 historical
proof copies while preserving the other 40 files and their directory. Recovery
was separately completed before removal. Audit01 failed on its directory link-count
assumption; its complete source, raw output and closed execution are retained.
The separately corrected audit02 verifies the same completed retirement and
writes canonical report01 with explicit attempt2/failed01 provenance. Its
actual execution remains in the distinct audit execution02 directory.
Original failures remain failures; no release timestamp is invented for audit01.

publication-scope.json retains the complete source-to-payload map and the exact
21 original/archive-member/gzip-witness associations. The existing run-make
archive and Reader03 publication blobs remain external recovery dependencies;
their full manifests and completed verification metadata are retained here.
No selected copy, provider binary or archive/blob payload was recopied.

This capsule records evidence retirement only. It does not establish runtime
admission, compiler free-space eligibility or performance qualification. The
recorded historical file identities do not represent current absent files.
All original sources/evidence and Git state were left unchanged.
'''


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def identity(path):
    value = Path(path).lstat()
    return {key: getattr(value, 'st_'+key) for key in FIELDS}


def main(expected):
    started = time.monotonic(); read_bytes = 0
    def guard():
        require(time.monotonic()-started <= 300, 'finite publication wall bound')
        require(shutil.disk_usage(ROOT).free >= 9*2**30, 'publication live floor')
    require(type(expected) is str and len(expected) == 64, 'reviewed scope SHA required')
    require(shutil.disk_usage(ROOT).free >= 16*2**30, 'fresh16 before publication')
    require(not os.path.lexists(DEST) and not os.path.lexists(REPORT), 'fresh exclusive publication required')
    resource.setrlimit(resource.RLIMIT_CPU, (300, 300)); resource.setrlimit(resource.RLIMIT_FSIZE, (4*2**20, 4*2**20))
    before = identity(SCOPE)
    require(SCOPE.resolve(strict=True) == SCOPE and stat.S_ISREG(before['mode']) and before['size'] <= 2*2**20,
            'bounded ordinary exact scope')
    scope_bytes = SCOPE.read_bytes()
    require(sha(scope_bytes) == expected and identity(SCOPE) == before, 'reviewed scope changed')
    scope = json.loads(scope_bytes)
    require(scope['status'] == 'proposed-unpublished' and scope['destination'] == str(DEST)
            and scope['limits'] == LIMITS and scope['file_count'] == len(scope['files']) <= 256
            and scope['source_bytes'] == sum(row['size'] for row in scope['files']) <= 12*2**20,
            'exact finite reviewed publication scope')
    require(scope['claims'] == dict(removed_files=21, preserved_files=40, durable_events=63,
            runtime_admission=False, performance_measurement=False, global_capacity_credit_bytes=0),
            'publication qualification claims differ')
    require(DEST.parent.resolve(strict=True) == DEST.parent and DEST.parent.is_dir(), 'ordinary result parent')
    files = scope['files']; names = set(); by_source = {}
    for row in files:
        require(set(row) == {'source', 'destination', 'size', 'sha256', 'identity', 'roles'}, 'exact source row')
        path = Path(row['source']); relative = Path(row['destination'])
        require(path.is_absolute() and not path.is_relative_to(TARGET)
                and any(path.is_relative_to(root) for root in [ROOT, O, A, X])
                and (path.suffix in ['.py', '.json', '.jsonl', '.md', '.diff', '.log']
                     or path.name in ['stdout', 'stderr']),
                'selected/provider/blob bytes cannot enter publication')
        require(not relative.is_absolute() and '..' not in relative.parts and str(relative) == row['destination']
                and relative.parts[0] == 'payloads' and row['destination'] not in names
                and row['source'] not in by_source, 'unique exact source/destination route')
        require(type(row['size']) is int and 0 <= row['size'] <= 4*2**20
                and set(row['identity']) == set(FIELDS) and row['identity']['size'] == row['size'],
                'bounded complete source identity')
        names.add(row['destination']); by_source[row['source']] = row
    require(str(Path(__file__).resolve()) in by_source, 'copier source must be retained in reviewed scope')
    def current(row):
        nonlocal read_bytes
        guard(); path = Path(row['source']); stamp = identity(path)
        require(path.resolve(strict=True) == path and stamp == row['identity'] and stat.S_ISREG(stamp['mode']),
                'ordinary unchanged source')
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
            require({key: getattr(os.fstat(stream.fileno()), 'st_'+key) for key in FIELDS} == stamp,
                    'source replaced before held read')
            raw = stream.read(4*2**20+1)
            require({key: getattr(os.fstat(stream.fileno()), 'st_'+key) for key in FIELDS} == stamp,
                    'held source changed')
        require(len(raw) == row['size'] and sha(raw) == row['sha256'] and identity(path) == stamp,
                'complete stable source bytes')
        read_bytes += len(raw); require(read_bytes <= 96*2**20, 'bounded cumulative source reads')
        return raw
    def trees():
        for name, wanted in scope['trees'].items():
            guard(); root = Path(name)
            require(root.resolve(strict=True) == root and root.is_dir() and not root.is_relative_to(TARGET),
                    'ordinary exact closed evidence root')
            found = {'.': dict(kind='directory', identity=identity(root))}; pending = [root]
            while pending:
                for path in sorted(pending.pop().iterdir()):
                    guard(); stamp = identity(path)
                    require(not path.is_symlink() and len(found) < 256, 'finite closed tree')
                    if stat.S_ISDIR(stamp['mode']):
                        found[str(path.relative_to(root))] = dict(kind='directory', identity=stamp); pending.append(path)
                    else:
                        require(stat.S_ISREG(stamp['mode']) and str(path) in by_source, 'complete closed source membership')
                        found[str(path.relative_to(root))] = dict(kind='file', identity=stamp)
            require(found == wanted, 'closed evidence tree changed')
    summary = dict(status='published-independently-verified-proof-copy-retirement', scope_sha256=expected,
                   actual=scope['actual'], packet_sha256=scope['packet_sha256'], claims=scope['claims'],
                   failed_independent_audit=scope['failed_independent_audit'],
                   source_file_count=len(files), source_bytes=scope['source_bytes'],
                   originals_preserved=True, external_recovery='See publication-scope.json external_recovery.',
                   git_mutations=False)
    manifest = dict(status='retained-exact-evidence-copies', scope_sha256=expected, source_files=files,
                    source_tree_membership=scope['trees'], originals_preserved=True,
                    generated_files=scope['generated_files'])
    generated = {'README.md': README.encode(), 'summary.json': encoded(summary),
                 'manifest.json': encoded(manifest), 'publication-scope.json': scope_bytes}
    require(set(generated) == set(scope['generated_files'])
            and all(len(raw) <= 4*2**20 for raw in generated.values())
            and scope['source_bytes']+sum(map(len, generated.values())) <= 15*2**20,
            'complete output must fit before creating destination')
    trees()
    for row in files: current(row)
    outputs = []; DEST.mkdir(mode=0o700)
    def write(relative, raw):
        guard(); path = DEST/relative; path.parent.mkdir(parents=True, exist_ok=True)
        require(path.parent.resolve(strict=True) == path.parent, 'ordinary publication parent')
        with path.open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        require(path.read_bytes() == raw, 'complete output readback')
        outputs.append(dict(path=str(path), relative=relative, size=len(raw), sha256=sha(raw)))
    for row in files:
        write(row['destination'], current(row)); current(row)
    for name, raw in generated.items(): write(name, raw)
    trees()
    for row in files: current(row)
    observed = set(); directories = {DEST}; pending = [DEST]
    while pending:
        for path in pending.pop().iterdir():
            guard(); require(not path.is_symlink(), 'indirect output member')
            if path.is_dir(): directories.add(path); pending.append(path)
            else: require(path.is_file(), 'nonordinary output'); observed.add(str(path))
            require(len(observed)+len(directories) <= 1024, 'finite output membership')
    require(observed == {row['path'] for row in outputs} and len(outputs) == len(files)+4, 'exact output file membership')
    for row in outputs:
        path = Path(row['path']); require(path.resolve(strict=True) == path and path.stat().st_size == row['size']
                                        and sha(path.read_bytes()) == row['sha256'], 'final full output bytes')
    for path in sorted(directories, key=lambda path: len(path.parts), reverse=True)+[DEST.parent]:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try: os.fsync(fd)
        finally: os.close(fd)
    require(identity(SCOPE) == before and sha(SCOPE.read_bytes()) == expected, 'scope changed during publication')
    report = dict(status='verified-published-copies', finished_at=time.time(), scope=dict(path=str(SCOPE), sha256=expected),
                  destination=str(DEST), files=outputs, file_count=len(outputs), total_bytes=sum(row['size'] for row in outputs),
                  source_file_count=len(files), source_bytes=scope['source_bytes'],
                  source_identities_and_bytes_unchanged=True, full_output_readback=True,
                  exact_closed_tree_membership=True, selected_copy_payload_reads=0, provider_or_blob_payload_reads=0,
                  runtime_admission=False, git_mutations=False)
    raw = encoded(report)
    require(len(raw) <= 2**20 and report['total_bytes']+len(raw) <= 16*2**20,
            'bounded publication plus report aggregate')
    with REPORT.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    require(REPORT.read_bytes() == raw, 'publication report full readback')
    print(json.dumps(dict(path=str(REPORT), sha256=sha(raw), files=len(outputs), bytes=report['total_bytes'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--scope-sha256', required=True)
    main(parser.parse_args().scope_sha256)
