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
PLAN = O/'.work/runtime13-actual-publication-plan-01.json'
PLAN_SHA = 'b92adcdf17423f63620234b84752b674b2505cbf9b34658e846c07112aaa480a'
OUT = ROOT/'results/runtime13-installation-saved-audit-01'
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
    assert plan['status'] == 'finite-closed-audit13-publication-plan-unexecuted'
    assert plan['output'] == str(OUT) and plan['file_count'] == 12
    assert plan['payload_bytes'] == 3303666
    assert plan['audit']['sha256']=='878a1f363e6ca5e3acdcb16645c79d8412a260e8721a9fe75eacd7823a481728'
    assert plan['execution']['sha256']=='1f4d4a70657aa071fb85540f97b8ecbfeed3dcde85e340360b5065e7a3ed7d43'
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
    assert len(payloads) == 12 and sum(row['size'] for _, row, _ in payloads.values()) == 3303666
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
    status = "# Audit13 installation07 saved audit — passed\n\nThe actual read-only audit13 completed with exit status 0. This capsule retains the canonical verification report, all eight execution files, and the independent root and O saved-evidence readbacks. The audit verified the unchanged runtime07 installation and 15 saved native children. Its report accounts for all 944 admitted provider directories, including the two empty directories absent from the earlier inferred scope.\n\nThe report records independent hashing of 3,708 installed ordinary files (636,631,680 bytes), complete provider and installed inventory checks, native loader selection, retained source diagnostics and unchanged inputs. This publication and its readbacks use saved evidence; they do not rerun the audit, compiler, installation or provider commands.\n\nApplication, exporter, std preparation and performance qualification remain false. The source/direct-nine/preparation snapshot and runtime07 plus failed-audit12 history are linked through exact prior capsule manifests. They are not recursively copied here. The earlier source snapshot's pending-audit wording remains historical.\n".encode()
    write(OUT/'STATUS.md', status)
    assert {root: tree(root) for root in before} == before
    for name, (data, row, _) in payloads.items():
        assert read(name) == (data, row)
    assert read(PLAN) == (plan_bytes, plan_row)
    manifest = dict(status='published-actual-audit13-success',
                    pid=os.getpid(), parent_pid=os.getppid(), started_at=started, finished_at=time.time(),
                    scope=dict(path=str(PLAN), **plan_row), publisher=dict(path=str(Path(__file__).resolve()), **own_row),
                    payload_files=len(copied), payload_bytes=sum(item['source']['size'] for item in copied),
                    files=copied, source_trees=before, originals_unchanged=True,
                    metadata_files={name: read(OUT/name)[1] for name in ['scope.json', 'publisher.py', 'STATUS.md']},
                    actual_audit13_report=plan['audit'], actual_audit13_execution=plan['execution'],
                    source_capsule=plan['source_capsule'], runtime07_capsule=plan['runtime07_and_failed12_capsule'],
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
