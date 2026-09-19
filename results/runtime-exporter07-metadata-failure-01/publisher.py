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
PLAN = O/'.work/runtime-exporter07-metadata-failure-publication-plan-01.json'
PLAN_SHA = '00a6857e079c8410b37cbbd6c444deef1ad30bda1da8aed10b266d2ca8c13f3f'
OUT = ROOT/'results/runtime-exporter07-metadata-failure-01'
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
    assert plan['status'] == 'finite-exporter07-metadata-failure-publication-plan'
    assert plan['output'] == str(OUT) and plan['file_count'] == 118 and plan['payload_bytes'] == 570278
    assert plan['reference_count'] == 3 and plan['reference_bytes'] == 115978
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
    assert len(payloads) == 118 and sum(v[1]['size'] for v in payloads.values()) == 570278
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
    status = """# Exporter07 metadata01 — closed failure

All 36 declared metadata children completed with exit 0. The metadata controller then rejected ordinary dyld loaded-to-delayed telemetry while parsing the saved role-version streams. The phase failed with exit 1; no successful planned metadata result was published. The directly waited supervisor exited 0 after recording its controller's exit 1, and the parent launcher reported the phase failure. These outcomes are retained separately.

Root and an independent reader checked every command, environment, cwd, PID/parent association, ordered closure and raw stdout/stderr SHA. Both role-version logs contain 548 UUID load lines and 157 loaded-to-delayed transitions with matching PIDs and prior unique basenames; the selected drivers remain active. This diagnosis does not turn the failed metadata attempt into qualification.

The capsule retains all 108 command receipt/raw files, phase receipt, outer three files, parent three files, root readback, independent reader source and report: 118 payloads. Exact source and packet associations are referenced through the preparation capsule rather than duplicated. No provider or binary payload, materialized238 source tree, or later parser/control attempt is copied. No compiler, provider probe or workload was rerun by this publication. Exporter/compiler builds, frontend/application qualification and performance claims remain absent.
""".encode()
    write(OUT/'STATUS.md', status)
    assert {root: tree(root) for root in before} == before
    for name, (data, row, _) in payloads.items(): assert read(name) == (data, row)
    for name, expected in plan['references'].items(): assert read(name)[1] == expected
    assert read(PLAN) == (plan_bytes, plan_row)
    manifest = dict(status='published-exporter07-closed-metadata-failure', pid=os.getpid(), parent_pid=os.getppid(),
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
                         files=len(expected_files),payload_files=118,payload_bytes=570278),sort_keys=True))


if __name__ == '__main__': main()
