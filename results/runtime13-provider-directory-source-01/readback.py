"""Independent byte, identity and membership readback of the finite source capsule."""
import hashlib
import json
import os
from pathlib import Path
import resource
import stat
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
OUT = ROOT/'results/runtime13-provider-directory-source-01'
MANIFEST_SHA = '604eb4ca27b1ccda2dcc641d1f0d44b7db18d2c5839fe2a103a40c2f9ed65748'
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')


def info(path):
    value = Path(path).lstat()
    return {name: getattr(value, 'st_'+name) for name in FIELDS}


def inspect(path):
    path = Path(path)
    assert path.resolve(strict=True) == path
    before = info(path)
    assert stat.S_ISREG(before['mode']) and before['nlink'] == 1 and before['size'] <= 4*2**20
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        assert {name: getattr(os.fstat(fd), 'st_'+name) for name in FIELDS} == before
        pieces = []
        total = 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            total += len(chunk)
            assert total <= 4*2**20
            pieces.append(chunk)
        assert {name: getattr(os.fstat(fd), 'st_'+name) for name in FIELDS} == before
    finally:
        os.close(fd)
    raw = b''.join(pieces)
    assert info(path) == before and len(raw) == before['size']
    return raw, dict(identity=before, size=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def walk(root):
    root = Path(root)
    rows = {'.': info(root)}
    for path in sorted(root.rglob('*')):
        row = info(path)
        assert stat.S_ISDIR(row['mode']) or stat.S_ISREG(row['mode'])
        rows[str(path.relative_to(root))] = row
    return rows


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    assert inspect(path)[0] == raw


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4*2**20, 4*2**20))
    started = time.time()
    raw, manifest_row = inspect(OUT/'manifest.json')
    assert manifest_row['sha256'] == MANIFEST_SHA
    manifest = json.loads(raw)
    assert manifest['status'] == 'published-source-snapshot-with-actual-ordinary9-pass'
    assert manifest['actual_audit13_report'] is None and manifest['actual_audit13_preparation']['report']['sha256']=='e23f5df3dd4f962b96b127d2bc9293befd0732fd9d67aebbd4d6bc6a4d65a495'
    scope_raw, scope_row = inspect(OUT/'scope.json')
    assert scope_row == manifest['metadata_files']['scope.json']
    assert inspect(manifest['scope']['path'])[0] == scope_raw
    scope = json.loads(scope_raw)
    assert len(manifest['files']) == len(scope['files']) == 69
    expected_files = {'manifest.json', *manifest['metadata_files']}
    copied = {}
    total = 0
    for item in manifest['files']:
        path = item['original']
        declared = scope['files'][path]
        assert item['relative'] == declared['destination']
        assert item['source'] == {key: declared[key] for key in ('identity', 'size', 'sha256')}
        original, source_row = inspect(path)
        retained, retained_row = inspect(OUT/item['relative'])
        assert source_row == item['source'] and retained_row == item['destination']
        assert retained == original
        assert (source_row['identity']['dev'], source_row['identity']['ino']) != (
            retained_row['identity']['dev'], retained_row['identity']['ino'])
        total += len(retained)
        expected_files.add(item['relative'])
        copied[path] = retained_row['sha256']
    assert total == manifest['payload_bytes'] == scope['payload_bytes'] == 1285419
    for name, expected in manifest['metadata_files'].items():
        assert inspect(OUT/name)[1] == expected
    for source, observed in manifest['source_trees'].items():
        assert walk(source) == observed, source
    tree = walk(OUT)
    assert {name for name, row in tree.items() if stat.S_ISREG(row['mode'])} == expected_files
    assert {name for name, row in tree.items() if stat.S_ISDIR(row['mode'])} == (
        {'.'} | {str(parent) for name in expected_files for parent in Path(name).parents})
    tested = json.loads(inspect(ROOT/'results/runtime13-direct-regressions-01/sources-before.json')[0])
    ordinary = {name:row for name,row in tested.items() if name.startswith('/Users/danluu/dev/rust-interp')}
    assert len(ordinary)==32 and len(scope['metadata_only_binary_references'])==1
    for name, row in ordinary.items():assert copied[name]==row['sha256']
    own, own_row = inspect(Path(__file__).resolve())
    save(OUT/'readback.py', own)
    report = dict(status='verified-source-publication', pid=os.getpid(), parent_pid=os.getppid(),
                  started_at=started, finished_at=time.time(), manifest_sha256=MANIFEST_SHA,
                  payload_files=69, payload_bytes=total, exact_original_rows=True,
                  original_source_trees_unchanged=True, complete_destination_membership=True,
                  independent_copy_inodes=True, exact_tested_source_versions=32,
                  binary_payloads_read_or_copied=0, Python_reference_only=True,
                  actual_audit13_preparation=manifest['actual_audit13_preparation'], actual_audit13_report=None,
                  provider_calls=0, compiler_calls=0, target_imports=0,
                  reader=dict(path=str(Path(__file__).resolve()), **own_row))
    save(OUT/'readback.json', json_bytes(report))
    rows = {}
    for path in sorted(OUT.rglob('*')):
        if path.is_file():
            rows[str(path.relative_to(ROOT))] = inspect(path)[1]
    assert len(rows) == 75 and sum(row['size'] for row in rows.values()) <= 4*2**20
    assert inspect(OUT/'manifest.json')[1] == manifest_row
    staged = dict(status='complete-finite-publication-path-list', files=rows,
                  count=len(rows), bytes=sum(row['size'] for row in rows.values()),
                  manifest_sha256=MANIFEST_SHA, readback_sha256=inspect(OUT/'readback.json')[1]['sha256'],
                  git_invoked=False)
    stage_path = O/'.work/runtime13-source-publication-staged-paths-01.json'
    save(stage_path, json_bytes(staged))
    print(json.dumps(dict(status=report['status'], payload_files=69, payload_bytes=total,
                          total_files=len(rows), total_bytes=staged['bytes'],
                          manifest_sha256=MANIFEST_SHA, readback=inspect(OUT/'readback.json')[1],
                          staged_path=str(stage_path), staged_sha256=inspect(stage_path)[1]['sha256'],
                          pid=os.getpid())))


if __name__ == '__main__':
    main()
