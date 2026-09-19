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
OUT = ROOT/'results/runtime10-preflight-saved-audit-01'
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
    execution_root = ROOT/'.work/runtime10-saved-audit-preflight-execution-01'
    raw, row = read(execution_root/'record.json')
    assert row['sha256'] == args.execution_sha256
    execution = json.loads(raw)
    assert execution['status'] == 'finished' and type(execution['returncode']) is int
    assert execution['may_be_live'] is False and execution['observation_errors'] == []
    roots = [ROOT/'experiments/hir-options-hash-runtime-audit-10',
        ROOT/'results/runtime10-tail-regressions-01',
        ROOT/'.work/runtime10-saved-audit-preflight-manifest-01',
        ROOT/'.work/runtime10-saved-audit-preflight-manifest-preparation-execution-01', execution_root]
    trees = {str(root): tree(root) for root in roots}
    paths = {root/name for root in roots for name, identity in trees[str(root)].items()
             if stat.S_ISREG(identity['mode'])}
    paths.update([Path(__file__), ROOT/'.work/runtime10-saved-audit-source-inventory-01.json',
        ROOT/'.work/runtime10-manifest-root-readback-01.json',
        ROOT/'results/runtime09-preflight-saved-audit-01/manifest.json',
        ROOT/'results/runtime08-preflight-saved-audit-failure-01/manifest.json',
        O/'.work/runtime09-tail-diagnosis-and-runtime10-budget-01.json',
        O/'.work/runtime10-tail-integration-source-handoff-01.json',
        O/'.work/runtime10-complete-prospective-manifest-census-01.json',
        O/'.work/run_runtime10_tail_regressions_01.py',
        O/'.work/run_runtime10_tail_regressions_01.py.from09.diff',
        O/'.work/verify_runtime10_tail_regressions_01.py',
        O/'.work/runtime10-tail-regressions-independent-readback-01.json',
        O/'.work/runtime10-manifest-invocation-command-error-01.json',
        O/'.work/verify_runtime10_manifest_preparation_01.py',
        O/'.work/runtime10-manifest-preparation-independent-readback-01.json',
        O/'.work/verify_runtime10_saved_audit_closure_01.py',
        O/'.work/runtime10-saved-audit-closure-independent-readback-01.json'])
    assert execution['returncode'] == 0
    assert args.execution_sha256 == 'f487e32878cd83bef5aea571910573d7b9457c7710810254a7520a52ea92cdc5'
    assert read(ROOT/'.work/runtime10-manifest-root-readback-01.json')[1]['sha256'] == '3b46e58ca7b66a2eafe7664d2b9c9fd09c2b2df0f91fbdf0fd0e109ffd1705e7'
    assert read(O/'.work/runtime10-saved-audit-closure-independent-readback-01.json')[1]['sha256'] == '336d1cc675b7b4935058e2455162f3f8ea94aba289b7a23f97562975b7f6e48e'
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
    status_text = '''Audit10 passed and closed with return code0. Independent report/raw/source
readback also passed. Parent52034 and child52747 closed normally, and the
canonical lock was released at1789826309.664437.

The20 focused regressions and actual303-row manifest preparation passed before
this audit. Full saved preflight evidence was verified:113255 original files,
7447 frozen links,497 preparation source rows, six completed-evidence directories,
and the original two typed source probes. The report is3,051,905 bytes.

Archived README and handoff documents describe the earlier source-only review
state. They remain unchanged historical documents; this STATUS records the
later actual result. Failed audits06,08 and09 remain failures. The included
prior08/09 publication manifests and the exact failure references in the saved
report identify their retained history. No prior failure is relabeled success.
The command-only argparse error before preparation evidence was created is
retained separately; the corrected preparation then closed successfully.

Scope: saved preflight qualification only. No new compiler/provider invocation,
installation, application, exporter or performance qualification occurred. The
303-row source manifest preserves exact external prerequisite associations;
provider payloads and toolchain binaries are not duplicated into this capsule.
'''
    with (OUT/'STATUS.md').open('xb') as stream:
        stream.write(status_text.encode()); stream.flush(); os.fsync(stream.fileno())
    status_row = read(OUT/'STATUS.md')[1]
    manifest = dict(status='retained-closed-audit', returncode=execution['returncode'],
        generated_files=[dict(relative='STATUS.md', size=status_row['size'], sha256=status_row['sha256'])],
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
