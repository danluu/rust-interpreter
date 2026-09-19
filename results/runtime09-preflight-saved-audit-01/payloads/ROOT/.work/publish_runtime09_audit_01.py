"""Retain this closed audit's source, raw evidence and actual outcome."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
OUT = ROOT/'results/runtime09-preflight-saved-audit-01'
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')


def stamp(path):
    return {key: getattr(path.lstat(), 'st_'+key) for key in FIELDS}


def read(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve(strict=True) == path
    before = stamp(path)
    assert stat.S_ISREG(before['mode']) and before['size'] <= 8*2**20
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        assert {k:getattr(os.fstat(stream.fileno()), 'st_'+k) for k in FIELDS} == before
        data = stream.read(8*2**20+1)
        assert {k:getattr(os.fstat(stream.fileno()), 'st_'+k) for k in FIELDS} == before
    assert stamp(path) == before and len(data) == before['size']
    return data, dict(identity=before, size=len(data), sha256=hashlib.sha256(data).hexdigest())


def tree(root):
    rows = {'.': stamp(root)}
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs+files:
            path = Path(parent)/name
            assert not path.is_symlink()
            rows[str(path.relative_to(root))] = stamp(path)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execution-sha256', required=True)
    args = parser.parse_args()
    execution_root = ROOT/'.work/runtime09-saved-audit-preflight-execution-01'
    raw, row = read(execution_root/'record.json')
    assert row['sha256'] == args.execution_sha256
    execution = json.loads(raw)
    assert execution['status'] == 'finished' and type(execution['returncode']) is int
    assert execution['may_be_live'] is False and execution['observation_errors'] == []
    roots = [ROOT/'experiments/hir-options-hash-runtime-audit-09',
        ROOT/'results/runtime09-completed-directory-regressions-01',
        ROOT/'.work/runtime09-saved-audit-preflight-manifest-01',
        ROOT/'.work/runtime09-saved-audit-preflight-manifest-preparation-execution-01', execution_root]
    trees = {str(root): tree(root) for root in roots}
    paths = {root/name for root in roots for name, identity in trees[str(root)].items()
             if stat.S_ISREG(identity['mode'])}
    paths.update([Path(__file__), ROOT/'.work/runtime09-saved-audit-source-inventory-01.json',
        O/'.work/runtime09-completed-directory-integration-source-handoff-01.json',
        O/'.work/runtime09-manifest-preparation-independent-readback-01.json',
        O/'.work/run_runtime09_completed_directory_regressions_01.py',
        O/'.work/runtime09-completed-directory-regressions-independent-readback-01.json',
        X/'.work/runtime09-completed-directory-independent-source-review-01.json'])
    report = Path(execution['report'])
    if execution['returncode'] == 0:
        data, report_row = read(report)
        assert report_row['sha256'] == execution['result_sha256']
        result = json.loads(data)
        assert result['status'] == 'verified' and result['phase'] == 'preflight'
        assert result['pid'] == execution['pid'] and result['parent_pid'] == execution['parent_pid']
        assert execution['finished_at'] <= execution['canonical_released_at']
        paths.add(report)
    else:
        assert not os.path.lexists(report)
    saved = {str(path): read(path) for path in sorted(paths)}
    assert len(saved) <= 80 and sum(row['size'] for _, row in saved.values()) <= 16*2**20
    assert not os.path.lexists(OUT)
    OUT.mkdir()
    copies = []
    for name, (data, row) in saved.items():
        path = Path(name)
        label, base = next((label, base) for label, base in [('ROOT',ROOT),('O',O),('X',X),('R',R)] if path.is_relative_to(base))
        relative = Path('payloads')/label/path.relative_to(base)
        dest = OUT/relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        assert read(dest)[0] == data and read(path) == (data, row)
        copies.append(dict(path=name, relative=str(relative), **row))
    assert {str(root): tree(root) for root in roots} == trees
    manifest = dict(status='retained-closed-audit', returncode=execution['returncode'],
        execution_sha256=args.execution_sha256, report_sha256=execution.get('result_sha256'),
        originals_unchanged=True, source_trees=trees, files=copies, pid=os.getpid(), time=time.time(),
        benchmark=False, compiler_calls=0, provider_calls=0,
        scope='Saved preflight evidence validation only; no installation or performance qualification.')
    data = (json.dumps(manifest, sort_keys=True, indent=2)+'\n').encode()
    with (OUT/'manifest.json').open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    assert read(OUT/'manifest.json')[0] == data
    print(json.dumps(dict(files=len(copies), bytes=sum(row['size'] for _,row in saved.values()),
        manifest_sha256=hashlib.sha256(data).hexdigest(), returncode=execution['returncode'])))


if __name__ == '__main__':
    main()
