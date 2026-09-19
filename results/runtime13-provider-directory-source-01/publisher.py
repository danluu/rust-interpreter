"""Copy the exact reviewed audit13 source-only publication scope once."""
import hashlib
import json
import os
from pathlib import Path
import resource
import stat
import time

O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
PLAN = O/'.work/runtime13-source-publication-plan-01.json'
PLAN_SHA = '9bbffc345142450713c2e757d65a359b37f41c9f1d534227db78de6f875a6cdb'
OUT = ROOT/'results/runtime13-provider-directory-source-01'
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')


def stamp(info):
    return {key: getattr(info, 'st_'+key) for key in FIELDS}


def read(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve(strict=True) == path
    before = stamp(path.lstat())
    assert stat.S_ISREG(before['mode']) and before['nlink'] == 1
    assert 0 <= before['size'] <= 4*2**20
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
        assert stamp(os.fstat(stream.fileno())) == before
        data = stream.read(4*2**20+1)
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
    resource.setrlimit(resource.RLIMIT_FSIZE, (4*2**20, 4*2**20))
    started = time.time()
    plan_bytes, plan_row = read(PLAN)
    assert plan_row['sha256'] == PLAN_SHA
    plan = json.loads(plan_bytes)
    assert plan['status'] == 'source-only-finite-publication-plan-unexecuted'
    assert plan['output'] == str(OUT) and plan['file_count'] == 69
    assert plan['payload_bytes'] == 1285419
    assert plan['actual_audit13_execution'] is plan['actual_audit13_report'] is None
    before = {root: tree(root) for root in plan['source_trees']}
    for root, entries in plan['source_trees'].items():
        actual = [dict(path=name, kind='directory' if stat.S_ISDIR(row['mode']) else 'file')
                  for name, row in sorted(before[root].items()) if name != '.']
        assert actual == entries, root
    payloads = {}
    destinations = set()
    for name, expected in plan['files'].items():
        data, row = read(name)
        assert row == {key: expected[key] for key in ('size', 'sha256', 'identity')}, name
        dest = Path(expected['destination'])
        assert not dest.is_absolute() and '..' not in dest.parts and dest.parts[0] == 'retained'
        assert str(dest) not in destinations
        destinations.add(str(dest))
        payloads[name] = (data, row, dest)
    assert len(payloads) == 69 and sum(row['size'] for _, row, _ in payloads.values()) == 1285419
    assert not os.path.lexists(OUT)
    OUT.mkdir(mode=0o700)
    copied = []
    for name, (data, row, relative) in payloads.items():
        write(OUT/relative, data)
        assert read(name) == (data, row)
        copied.append(dict(original=name, relative=str(relative), source=row, destination=read(OUT/relative)[1]))
    write(OUT/'scope.json', plan_bytes)
    own_bytes, own_row = read(Path(__file__).resolve())
    write(OUT/'publisher.py', own_bytes)
    status = "# Audit13 provider-directory source and nine-test snapshot\n\nAll nine new ordinary provider-directory regressions passed once. The 29 prior regression bodies are unchanged and were not rerun. This capsule retains the exact new sources and diffs, all seven direct-test outputs, their 32 nonbinary source versions, source inventory, reviews and diagnosis. The actual closed manifest preparation and independent readbacks are included: 326 files and 7,185,333 bytes authenticated.\n\nRuntime installation07 remains unchanged. Audit12's closed failure and the predecessor source bytes are referenced through their existing published capsules; no archive or provider tree is duplicated. Python is retained as an exact metadata reference only.\n\nActual full audit13: **PENDING in this snapshot**. Root owns the separately running invocation. This publication neither reads its active outputs nor binds a future report or execution result. No claim of full installation audit success, application, std or performance qualification is made here.\n".encode()
    write(OUT/'STATUS.md', status)
    assert {root: tree(root) for root in before} == before
    for name, (data, row, _) in payloads.items():
        assert read(name) == (data, row)
    assert read(PLAN) == (plan_bytes, plan_row)
    manifest = dict(status='published-source-snapshot-with-actual-ordinary9-pass',
                    pid=os.getpid(), parent_pid=os.getppid(), started_at=started, finished_at=time.time(),
                    scope=dict(path=str(PLAN), **plan_row), publisher=dict(path=str(Path(__file__).resolve()), **own_row),
                    payload_files=len(copied), payload_bytes=sum(item['source']['size'] for item in copied),
                    files=copied, source_trees=before, originals_unchanged=True,
                    metadata_files={name: read(OUT/name)[1] for name in ['scope.json', 'publisher.py', 'STATUS.md']},
                    actual_audit13_preparation=plan['manifest_preparation'], actual_audit13_report=None,
                    compiler_calls=0, provider_calls=0, binary_payload_copies=0,
                    independent_readback='pending-separate-readback')
    write(OUT/'manifest.json', encoded(manifest))
    expected_files = destinations | {'scope.json', 'publisher.py', 'STATUS.md', 'manifest.json'}
    expected_dirs = {'.'} | {str(parent) for name in expected_files for parent in Path(name).parents}
    actual = tree(OUT)
    assert {name for name, row in actual.items() if stat.S_ISREG(row['mode'])} == expected_files
    assert {name for name, row in actual.items() if stat.S_ISDIR(row['mode'])} == expected_dirs
    print(json.dumps(dict(status=manifest['status'], output=str(OUT), manifest=read(OUT/'manifest.json')[1],
                          payload_files=len(copied), payload_bytes=manifest['payload_bytes'], pid=os.getpid())))


if __name__ == '__main__':
    main()
