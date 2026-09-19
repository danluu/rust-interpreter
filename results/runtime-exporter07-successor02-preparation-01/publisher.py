"""Finite closed evidence copy; held ROOT source and packet stay in place."""
import hashlib
import json
import os
from pathlib import Path
import stat
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
PLAN = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/runtime-exporter07-successor02-publication-plan-01.json')
PLAN_SHA = '67e77e3cd234456a633ccc5d7cfb33a293dda3e04bbe30f58bd561aa79524335'
OUT = ROOT/'results/runtime-exporter07-successor02-preparation-01'


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


def main():
    started = time.time()
    data, plan_ref = read(PLAN)
    assert plan_ref['sha256'] == PLAN_SHA
    plan = json.loads(data)
    assert plan['output'] == str(OUT) and plan['status'] == 'finite-successor02-preparation-capsule-plan'
    assert (plan['payload_files'], plan['payload_bytes'], plan['reference_files'], plan['reference_bytes']) == (17, 263152, 70, 5957692)
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
    status = """# Exporter07 successor02 preparation

Preparation03 failed closed before compiler/provider probes because a normal main merge reapplied negative sparse-checkout patterns and removed required historical proof files. Its raw output and renamed failed preparation record remain retained. Root added five exact positive sparse rules and restored the original proof bytes. Preparation04 then passed closed0, parent50190/child50904, using the unchanged reviewed source02.

The closed preparation produced four packet files and the exact238 source copy (2,150,761 bytes). Root and X independently checked packet/closure; X checked every copied source SHA, size, seven-field identity and membership and reconstructed all36 metadata commands. Provider payloads were not rehashed for this capsule.

This capsule preserves preparation evidence only. Root separately launched metadata02; no metadata02 outputs were read or copied here. Build, frontend, tool publication, application and performance are not qualified by this preparation snapshot. The publication-controller sources and templates are retained source, with actual future proof pins unset.

Seventeen closed evidence/review/handoff files are copied. Current source02, histories and packet remain in place for staging, including the 5.4MB plan without a duplicate. Original frontend01 four sources, manifest, extraction diffs, template, handoff and review preserve the reviewed basis. The four current source manifests contain11/15/20/25 rows. The already retained parser24 result and preceding preparation capsule are references. External imported sources are exact current references; providers, binaries, materialized source238 and renamed failed source238 are not copied.

No Git operation, target import, compiler/Cargo/provider probe or workload execution was performed by this publisher. Historical documents keep their original status wording. The copied packet readback records one corrected local stdout-shape assertion, with no target rerun or evidence change.
""".encode()
    write(OUT/'STATUS.md', status)
    for name, expected in plan['references'].items():
        assert read(name)[1] == expected
    for _, (name, raw, row) in payloads.items():
        assert read(name) == (raw, row)
    assert read(PLAN) == (data, plan_ref)
    manifest = dict(status='published-closed-preparation-only', pid=os.getpid(), parent_pid=os.getppid(),
        started_at=started, finished_at=time.time(), scope=dict(path=str(PLAN), **plan_ref),
        publisher=dict(path=str(Path(__file__).resolve()), **own_ref), payload_files=17,
        payload_bytes=263152, files=copies, in_place_references=plan['references'],
        metadata={name: read(OUT/name)[1] for name in ('scope.json', 'publisher.py', 'STATUS.md')},
        active_metadata_outputs_included=False, originals_unchanged=True, compiler_calls=0,
        provider_calls=0, binary_payload_copies=0, source238_payload_copies=0)
    write(OUT/'manifest.json', encoded(manifest))
    staged = sorted(set(plan['in_place_stage_paths']) | {str((OUT/name).relative_to(ROOT)) for name in
        [*(str(p) for p in payloads), 'scope.json', 'publisher.py', 'STATUS.md', 'manifest.json', 'stage-paths.json', 'readback.json']})
    write(OUT/'stage-paths.json', encoded(dict(status='exact-paths-not-staged', paths=staged)))
    print(json.dumps(dict(status=manifest['status'], manifest=read(OUT/'manifest.json')[1], stage_paths=len(staged)), sort_keys=True))


if __name__ == '__main__':
    main()
