"""Finite closed evidence copy; held ROOT source and packet stay in place."""
import hashlib
import json
import os
from pathlib import Path
import stat
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
PLAN = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/runtime-exporter07-metadata-build02-publication-plan-01.json')
PLAN_SHA = 'c7f493172d5f7459e572d398b0708a61a70b417d78ff9b8f55d2d19ef76be52d'
OUT = ROOT/'results/runtime-exporter07-metadata-build02-01'


def identity(s):
    return [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]


def read(path):
    path = Path(path)
    before = identity(path.lstat())
    assert path.is_absolute() and path.resolve(strict=True) == path
    assert stat.S_ISREG(before[2]) and before[6] == 1 and 0 <= before[3] <= 8*2**20
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
        assert identity(os.fstat(stream.fileno())) == before
        data = stream.read(8*2**20+1)
        assert identity(os.fstat(stream.fileno())) == before
    assert identity(path.lstat()) == before and len(data) == before[3]
    return data, dict(size=len(data), sha256=hashlib.sha256(data).hexdigest(), identity=before)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    assert read(path)[0] == data


def membership(root):
    root = Path(root)
    assert root.resolve(strict=True) == root and root.is_dir()
    rows = []
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
            path = Path(parent)/name; mode = path.lstat().st_mode
            assert stat.S_ISDIR(mode) or stat.S_ISREG(mode)
            rows.append(dict(path=str(path.relative_to(root)), kind='directory' if stat.S_ISDIR(mode) else 'file'))
    return sorted(rows, key=lambda row: row['path'])


def main():
    started = time.time()
    data, plan_ref = read(PLAN)
    assert plan_ref['sha256'] == PLAN_SHA
    plan = json.loads(data)
    assert plan['output'] == str(OUT) and plan['status'] == 'finite-metadata-build02-capsule-plan'
    assert (plan['payload_files'], plan['payload_bytes'], plan['reference_files'], plan['reference_bytes']) == (152, 4295817, 33, 5761072)
    payloads = {}
    for name, expected in plan['files'].items():
        raw, row = read(name)
        assert row == {k: expected[k] for k in ('size', 'sha256', 'identity')}
        relative = Path(expected['destination'])
        assert not relative.is_absolute() and '..' not in relative.parts and relative.parts[0] == 'retained'
        assert relative not in payloads
        payloads[relative] = (name, raw, row)
    for name, expected in plan['references'].items():
        assert read(name)[1] == expected
    assert {root: membership(root) for root in plan['closed_trees']} == plan['closed_trees']
    assert not os.path.lexists(OUT)
    OUT.mkdir(mode=0o700)
    copies = []
    for relative, (name, raw, row) in payloads.items():
        write(OUT/relative, raw)
        target = read(OUT/relative)[1]
        assert target['identity'][1] != row['identity'][1] and read(name) == (raw, row)
        copies.append(dict(original=name, relative=str(relative), source=row, destination=target))
    write(OUT/'scope.json', data)
    own, own_ref = read(Path(__file__).resolve())
    write(OUT/'publisher.py', own)
    status = """# Exporter07 metadata02 and build02

Metadata02 passed all36 declared children and closed normally: parent97343, supervisor98056, controller98058. Build02 then passed its seven declared children and closed normally: parent53853, supervisor54567, controller54569. The ordinary Cargo command remained locked/offline/release/jobs2. Two fresh exporter/wrapper binaries were built for the exact D2/B3/runtime07 role composition; no compiler or VM was rebuilt.

Root and X independently read the closed raw/receipt/result chain. X checked409 named files, all238 immutable source hashes/identities, the43 exact child commands/environment/chronology,44 compiler rows in Cargo verbose output, both fresh binary hashes, generated role binding and complete Cargo JSON/raw associations. Recorded loader nodes match saved otool output; resolved-library bytes/hashes match the frozen packet. Each of the two compiler roles and the exporter produced705 dyld events,548 distinct images,391 final loaded and157 delayed images, with its selected driver active.

The ordinary bind_recorded_wrapper helper adds the wrapper SHA/role association to raw capabilities; the retained readbacks check this transformation. Short-lived commands can finish before the separate cwd observation succeeds. Missing cwd observations remain recorded; saved spawn arguments and PID/parent/normal wait receipts establish the declared command/cwd transport. Four real build-script identity probes remain source/Cargo/generated-output evidence, not four independently supervised receipts.

This capsule copies152 closed evidence/reader/root-review files and preserves exact six closed-tree memberships. The5.4MB packet plan, current source manifests and prior preparation capsule remain referenced in place. Two binary payloads, provider trees, the adopted VM and238 source-copy payloads are not copied. Failed preparation and metadata01 histories remain in preceding capsules. Frontend, publication, application and performance outcomes are outside this capture; no active frontend output was consumed.

The publisher performed only bounded file copies and EOF/SHA/current-identity readback. It ran no compiler, Cargo, target import, provider probe or Git operation. Historical source documents retain their original qualification status.
""".encode()
    write(OUT/'STATUS.md', status)
    for name, expected in plan['references'].items():
        assert read(name)[1] == expected
    for _, (name, raw, row) in payloads.items():
        assert read(name) == (raw, row)
    assert read(PLAN) == (data, plan_ref)
    assert {root: membership(root) for root in plan['closed_trees']} == plan['closed_trees']
    manifest = dict(status='published-closed-metadata-and-build-only', pid=os.getpid(), parent_pid=os.getppid(),
        started_at=started, finished_at=time.time(), scope=dict(path=str(PLAN), **plan_ref),
        publisher=dict(path=str(Path(__file__).resolve()), **own_ref), payload_files=152,
        payload_bytes=4295817, files=copies, in_place_references=plan['references'],
        metadata={name: read(OUT/name)[1] for name in ('scope.json', 'publisher.py', 'STATUS.md')},
        active_frontend_outputs_included=False, closed_trees=plan['closed_trees'], originals_unchanged=True, compiler_calls=0,
        provider_calls=0, binary_payload_copies=0, source238_payload_copies=0)
    write(OUT/'manifest.json', encoded(manifest))
    staged = sorted(set(plan['in_place_stage_paths']) | {str((OUT/name).relative_to(ROOT)) for name in
        [*(str(p) for p in payloads), 'scope.json', 'publisher.py', 'STATUS.md', 'manifest.json', 'stage-paths.json', 'readback.json']})
    write(OUT/'stage-paths.json', encoded(dict(status='exact-paths-not-staged', paths=staged)))
    print(json.dumps(dict(status=manifest['status'], manifest=read(OUT/'manifest.json')[1], stage_paths=len(staged)), sort_keys=True))


if __name__ == '__main__':
    main()
