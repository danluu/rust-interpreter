"""Copy finite closed exporter preparation proof; root source/packet stay in place."""
import hashlib
import json
import os
from pathlib import Path
import resource
import stat
import time

O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
PLAN = O/'.work/runtime-exporter07-preparation-publication-plan-01.json'
PLAN_SHA = '8d984a11dce4dcb73f3a94513c999717e32c49ce35e6d6d08895d3f201a35162'
OUT = ROOT/'results/runtime-exporter07-preparation-01'
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')


def stamp(info):
    return {key: getattr(info, 'st_'+key) for key in FIELDS}


def read(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve(strict=True) == path
    before = stamp(path.lstat())
    assert stat.S_ISREG(before['mode']) and before['nlink'] == 1
    assert 0 <= before['size'] <= 8*2**20
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
        assert stamp(os.fstat(stream.fileno())) == before
        data = stream.read(8*2**20+1)
        assert stamp(os.fstat(stream.fileno())) == before
    assert stamp(path.lstat()) == before and len(data) == before['size']
    return data, dict(identity=before, size=len(data), sha256=hashlib.sha256(data).hexdigest())


def tree(root):
    root = Path(root)
    assert root.resolve(strict=True) == root and stat.S_ISDIR(root.lstat().st_mode)
    rows = {'.': stamp(root.lstat())}
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs+files:
            path = Path(parent)/name
            identity = stamp(path.lstat())
            assert stat.S_ISDIR(identity['mode']) or stat.S_ISREG(identity['mode'])
            rows[str(path.relative_to(root))] = identity
    return rows


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    assert read(path)[0] == data


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8*2**20, 8*2**20))
    started = time.time()
    plan_bytes, plan_row = read(PLAN)
    assert plan_row['sha256'] == PLAN_SHA
    plan = json.loads(plan_bytes)
    assert plan['status'] == 'finite-exporter07-preparation-publication-plan'
    assert plan['output'] == str(OUT) and plan['file_count'] == 26 and plan['payload_bytes'] == 1008830
    assert plan['reference_count'] == 32 and plan['reference_bytes'] == 5889992
    before = {root: tree(root) for root in plan['source_trees']}
    for root, entries in plan['source_trees'].items():
        actual = [dict(path=name, kind='directory' if stat.S_ISDIR(row['mode']) else 'file')
                  for name, row in sorted(before[root].items()) if name != '.']
        assert actual == entries
    for name, expected in plan['references'].items():
        assert read(name)[1] == expected
    payloads = {}; destinations = set()
    for name, expected in plan['files'].items():
        data, row = read(name)
        assert row == {key: expected[key] for key in ('size', 'sha256', 'identity')}
        relative = Path(expected['destination'])
        assert not relative.is_absolute() and '..' not in relative.parts and relative.parts[0] == 'retained'
        assert str(relative) not in destinations
        destinations.add(str(relative)); payloads[name] = (data, row, relative)
    assert len(payloads) == 26 and sum(v[1]['size'] for v in payloads.values()) == 1008830
    assert not os.path.lexists(OUT)
    OUT.mkdir(mode=0o700); copied = []
    for name, (data, row, relative) in payloads.items():
        write(OUT/relative, data)
        assert read(name) == (data, row)
        destination = read(OUT/relative)[1]
        assert destination['identity']['ino'] != row['identity']['ino']
        copied.append(dict(original=name, relative=str(relative), source=row, destination=destination))
    write(OUT/'scope.json', plan_bytes)
    own_bytes, own_row = read(Path(__file__).resolve()); write(OUT/'publisher.py', own_bytes)
    status = """# Exporter07 preparation snapshot

Preparation attempt 01 closed with exit 1 because an exact saved VM proof was absent from the sparse working tree. Its raw output and renamed failed preparation record are preserved. Root restored the five exact saved metadata files from pinned Git bytes. No preparation source or validation was changed. Attempt 02 then passed and closed with exit 0 (parent 87433, child 88145).

Root and the independent reader checked the four actual packet files and closure. The independent reader also hashed all 238 ordinary materialized source files (2,150,761 bytes), checked all seven identity fields and exact membership, verified all ten current metadata sources, and reconstructed the complete 36-command metadata schedule. Provider payload verification performed by preparation is not repeated by publication.

This is the preparation capture: metadata has been invoked by root and its result is pending at capture; build, frontend, tool publication and performance qualification are also pending. Active metadata outputs are excluded. Historical source handoffs retain their original unrun wording and unset future pins.

The capsule copies 26 finite evidence/history/review files. Exact ROOT source and packet references, including the 5.4 MB plan, remain in place for Git staging instead of being duplicated. Six imported external source files and the ordinary supervisor have exact HEAD-blob or already-published source associations. Provider/binary trees, the 238 copied sources and the renamed failed source tree are not copied here; their frozen references and census remain retained. No target, compiler or provider command ran during publication.

The launch review records one failure-bookkeeping improvement for a later launcher successor: persist the observed supervisor OS wait before attempting to read its terminal file. The currently active launcher source is preserved unchanged.
""".encode()
    write(OUT/'STATUS.md', status)
    assert {root: tree(root) for root in before} == before
    for name, (data, row, _) in payloads.items(): assert read(name) == (data, row)
    for name, expected in plan['references'].items(): assert read(name)[1] == expected
    assert read(PLAN) == (plan_bytes, plan_row)
    manifest = dict(status='published-exporter07-preparation-snapshot', pid=os.getpid(), parent_pid=os.getppid(),
        started_at=started, finished_at=time.time(), scope=dict(path=str(PLAN), **plan_row),
        publisher=dict(path=str(Path(__file__).resolve()), **own_row), payload_files=len(copied),
        payload_bytes=sum(v['source']['size'] for v in copied), files=copied, source_trees=before,
        root_references=plan['references'], external_source_resolution=plan['external_source_resolution'],
        capture_status=plan['capture_status'], originals_unchanged=True,
        metadata_files={name: read(OUT/name)[1] for name in ('scope.json','publisher.py','STATUS.md')},
        compiler_calls=0, provider_calls=0, binary_payload_copies=0, source238_payload_copies=0,
        independent_readback='pending-separate-readback')
    write(OUT/'manifest.json', encoded(manifest))
    expected_files = destinations | {'scope.json','publisher.py','STATUS.md','manifest.json'}
    expected_dirs = {'.'} | {str(p) for name in expected_files for p in Path(name).parents}
    actual = tree(OUT)
    assert {name for name,v in actual.items() if stat.S_ISREG(v['mode'])} == expected_files
    assert {name for name,v in actual.items() if stat.S_ISDIR(v['mode'])} == expected_dirs
    assert sum(v['size'] for v in actual.values() if stat.S_ISREG(v['mode'])) <= 2*2**20
    print(json.dumps(dict(status=manifest['status'],pid=os.getpid(),manifest=read(OUT/'manifest.json')[1],
                         files=len(expected_files),payload_files=26,payload_bytes=1008830),sort_keys=True))


if __name__ == '__main__': main()
