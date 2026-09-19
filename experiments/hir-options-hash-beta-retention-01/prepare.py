"""Freeze completed source/control retention only; no archive or workload run."""
import ast
import json
from pathlib import Path
import sys

import retain as r


def main():
    assert Path.cwd() == r.OWNER and sys.dont_write_bytecode
    assert not any((r.HERE / name).exists() for name in ['inputs.json', 'launch.json'])
    assert not r.WORK.exists() and not r.RESULT.exists()
    original = r.read(r.CONTROL / 'inputs.json'); r.control.guard(original)
    files = dict(original['files']); routes = dict(original['routes'])
    excluded = {name: row for name, row in files.items() if not name.startswith('/Users/danluu/dev/')}
    assert len(excluded) == 3 and all(Path(name).name in ['python3.14', 'ps', 'lsof'] for name in excluded)
    archive_sources = set(files) - set(excluded)
    def add(path):
        path = Path(path); assert path.resolve(strict=True) == path and path.is_file()
        before = r.control.stamp(path); assert before[3] <= 96 * 2**20
        row = dict(sha256=r.owned.sha(path), stamp=before)
        assert before == r.control.stamp(path)
        assert str(path) not in files or files[str(path)] == row
        files[str(path)] = row; archive_sources.add(str(path))
        if path.suffix == '.py': ast.parse(path.read_text(), filename=str(path))
    membership = {}
    roots = [r.CONTROL.with_name('hir-options-hash-beta-composition-01'),
             r.CONTROL.with_name('hir-options-hash-beta-composition-02'), r.CONTROL, r.control.WORK,
             r.OWNER / '.work/experiments/hir-options-hash-beta-controls-supervisor-01',
             r.OWNER / '.work/beta-controls-launch-execution-01']
    for root in roots:
        members = []
        for path in sorted(root.rglob('*')):
            assert not path.is_symlink()
            if path.is_file(): add(path); members.append(str(path.relative_to(root)))
            else: assert path.is_dir()
        membership[str(root)] = sorted(members)
    root_audit = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/root-beta-composition-controls-actual-verification-01.json')
    own_audit = r.OWNER / '.work/beta-controls-independent-verification-01.json'
    for path in [*r.HERE.iterdir(), r.OWNER / '.work/launch_beta_controls_01.py',
                 r.OWNER / '.work/verify_beta_controls_01.py', own_audit, root_audit,
                 root_audit.with_name('root-beta-composition-controls-plan-verification-01.json')]:
        add(path)
    assert len(archive_sources) + 1 <= 128
    logical = sum(files[name]['stamp'][3] for name in archive_sources)
    assert logical <= 95 * 2**20
    python = str(Path(sys.executable).resolve(strict=True)); assert python == original['python']
    environment = dict(original['environment']); environment['TMPDIR'] = '/tmp'
    freeze = dict(status='prepared-unrun', files=files, routes=routes, python=python, environment=environment,
                  archive_sources=sorted(archive_sources), membership=membership, payload_exclusions=excluded,
                  controls_receipt_sha256=r.owned.sha(r.control.WORK / 'receipt.json'),
                  verifications={str(own_audit): 'receipt_sha256', str(root_audit): 'terminal_sha256'},
                  capacity=dict(entry_gib=9, stop_gib=9, floor_gib=8, reservation_bytes=r.CAP),
                  bounds=dict(logical_members=128, logical_bytes=96 * 2**20, gzip_expanded_bytes=112 * 2**20,
                              compressed_bytes=r.CAP, manifest_bytes=2**20),
                  canonical_lock=str(r.owned.CANONICAL_LOCK), wait_seconds=600, workload_children=0)
    r.owned.write(r.HERE / 'inputs.json', freeze)
    launch = dict(status='prepared-unrun-awaiting-review-and-compiler-priority', owner=str(r.OWNER), environment=environment,
                  command=[python, '-B', str(r.OWNER / 'scripts/supervise_experiment.py'), '--run-id',
                           'hir-options-hash-beta-retention-supervisor-01', '--', python, '-B', str(r.HERE / 'retain.py'),
                           '--inputs-sha256', r.owned.sha(r.HERE / 'inputs.json')],
                  inputs_sha256=r.owned.sha(r.HERE / 'inputs.json'), helper_sha256=r.owned.sha(r.HERE / 'retain.py'),
                  expected_workload_children=0, capacity=freeze['capacity'], bounds=freeze['bounds'])
    r.owned.write(r.HERE / 'launch.json', launch); r.guard(freeze)
    print(json.dumps(dict(status='prepared-unrun', launch_sha256=r.owned.sha(r.HERE / 'launch.json'),
                         inputs_sha256=launch['inputs_sha256'], files=len(files), archive_files=len(archive_sources) + 1,
                         logical_bytes_before_freeze=logical, excluded_payloads=len(excluded)), indent=2))


if __name__ == '__main__': main()
