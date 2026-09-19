"""Finite closed evidence copy; held ROOT source and packet stay in place."""
import hashlib
import json
import os
from pathlib import Path
import stat
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
PLAN = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/runtime-exporter07-frontend-publication02-publication-plan-01.json')
PLAN_SHA = 'fd80ed9eba576d76e6e797e37b5de8ab24deb1247c05bebf3be7fddfd8db89d3'
OUT = ROOT/'results/runtime-exporter07-frontend-publication02-01'


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
    assert plan['output'] == str(OUT) and plan['status'] == 'finite-frontend-publication02-capsule-plan'
    assert (plan['payload_files'], plan['payload_bytes'], plan['reference_files'], plan['reference_bytes']) == (196, 1907941, 38, 6011922)
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
    status = b'# Exporter07 frontend02 and publication02\n\nFrontend02 passed its complete34-child schedule: ten SDK checks, six fresh loader inspections and18 frontend controls with nine diagnostic pairs. Parent46235 reaped supervisor47672 after controller47675 returned0. The controls preserve explicit/default runtime selection, wrapper wrong-role refusal, ordinary metadata compilation, test discovery, type/borrow failures, restored source and build-sysroot rejection. Seventeen stderr streams retain a lossless compiler/telemetry split; the wrong-role refusal is an intentional plain error. The immutable source and mutable fixture were restored and independently checked.\n\nPublication02 then passed three actual commands: published exporter capabilities with complete dyld event records, published wrapper roles, and the ordinary installed-tools/runtime association reader. Parent13206 reaped supervisor14420 after controller14462 returned0. Tool key89cb2751d9e6cfd4a9572dd8ab5405fae7480350bc9198bc5f1bc79fc35bceac names the reconstructed runtime07 composition. Three distinct binary copies are0555; compiler/capabilities/ready metadata are0444. The exporter and wrapper are the new build02 binaries; the VM remains the explicitly adopted historical qualified binary. No VM rebuild or guest execution is claimed.\n\nX independently checked the saved schedules, source manifests, raw outputs, normal closures, exact composition digest, capabilities transformation and six installed files. The installed binaries were read through EOF and compared with frozen source digests; the adopted VM source itself was checked by its recorded seven-field identity without another provider payload read. Publication readback attempt01 stopped before creating a report because its new reader incorrectly expected two absent outer-record keys. The corrected attempt02 reads those source associations from the actual manifests and controller argv. Both reader sources and the failure note are retained; no workload was retried.\n\nThis finite capsule copies196 closed evidence, installed metadata, review and reader files, and records six exact closed-tree memberships. The5.4MB packet, current source closures, launcher source/diff and earlier preparation/metadata/build capsules remain references. Binary payloads, provider trees and238 immutable source-copy payloads are not copied. Historical handoffs preserve their original unbound status.\n\nFrontend and ordinary tool publication passed. Ruff application qualification, the full behavioral protocol and performance measurement remain outside this capsule. No active outputs were read. No compiler, Cargo, target import, provider probe, Git action or retirement was performed by this publisher.\n'
    write(OUT/'STATUS.md', status)
    for name, expected in plan['references'].items():
        assert read(name)[1] == expected
    for _, (name, raw, row) in payloads.items():
        assert read(name) == (raw, row)
    assert read(PLAN) == (data, plan_ref)
    assert {root: membership(root) for root in plan['closed_trees']} == plan['closed_trees']
    manifest = dict(status='published-closed-frontend-and-tool-publication', pid=os.getpid(), parent_pid=os.getppid(),
        started_at=started, finished_at=time.time(), scope=dict(path=str(PLAN), **plan_ref),
        publisher=dict(path=str(Path(__file__).resolve()), **own_ref), payload_files=196,
        payload_bytes=1907941, files=copies, in_place_references=plan['references'],
        metadata={name: read(OUT/name)[1] for name in ('scope.json', 'publisher.py', 'STATUS.md')},
        active_outputs_included=False, application_qualified=False, performance_qualified=False, closed_trees=plan['closed_trees'], originals_unchanged=True, compiler_calls=0,
        provider_calls=0, binary_payload_copies=0, source238_payload_copies=0)
    write(OUT/'manifest.json', encoded(manifest))
    staged = sorted(set(plan['in_place_stage_paths']) | {str((OUT/name).relative_to(ROOT)) for name in
        [*(str(p) for p in payloads), 'scope.json', 'publisher.py', 'STATUS.md', 'manifest.json', 'stage-paths.json', 'readback.json']})
    write(OUT/'stage-paths.json', encoded(dict(status='exact-paths-not-staged', paths=staged)))
    print(json.dumps(dict(status=manifest['status'], manifest=read(OUT/'manifest.json')[1], stage_paths=len(staged)), sort_keys=True))


if __name__ == '__main__':
    main()
