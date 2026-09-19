#!/usr/bin/env python3
"""Read-only inventory of three exact completed Ruff diagnostic target roots."""
import hashlib
import json
import os
from pathlib import Path
import stat
import time

OWNER = Path(__file__).resolve().parents[2]
A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
RUN = R/'.work/runs/runtime-ruff-hir-diagnostic-01'
KEY = '7610e295912b132303c95db6a587f9288c03a7f84b691de8ea60093e2829622a'
ROOTS = {
    'native': RUN/'native',
    'baseline': R/'.work/interpreter-workspaces'/KEY/'235fb35a40657ef8b469e58c/target',
    'candidate': R/'.work/interpreter-workspaces'/KEY/'781315b047a9041f4868ee88/target',
}
FIELDS = ['dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns']
ASSESSMENT = OWNER/'.work/ruff-diagnostic-target-cleanup-assessment-01.json'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def identity(path):
    value = path.lstat()
    return {name: getattr(value, 'st_'+name) for name in FIELDS}


def snapshot(root):
    assert root.resolve(strict=True) == root and root.is_dir()
    rows = {'.': identity(root)}
    seen = {(rows['.']['dev'], rows['.']['ino'])}
    allocated = root.lstat().st_blocks*512
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted([*dirs, *files]):
            path = Path(directory)/name
            value = path.lstat()
            assert path.resolve(strict=True) == path and (
                stat.S_ISDIR(value.st_mode) or stat.S_ISREG(value.st_mode)), path
            rows[str(path.relative_to(root))] = identity(path)
            key = value.st_dev, value.st_ino
            if key not in seen:
                allocated += value.st_blocks*512
                seen.add(key)
    return rows, allocated


def main():
    assert Path.cwd() == OWNER and not ASSESSMENT.exists()
    records = json.loads((RUN/'records.json').read_bytes())
    terminal_path = A/'.work/ruff-hir-diagnostic-supervision-01/receipt.json'
    terminal = json.loads(terminal_path.read_bytes())
    assert terminal['status'] == 'passed' and len(records) == 24
    roots = {}
    for mode, root in ROOTS.items():
        selected = [row for row in records if row['mode'] == mode]
        assert len(selected) == 8 and selected[-1]['state'] == -2
        for row in selected:
            assert len(row['calls']) == 1
            call = row['calls'][0]
            if mode == 'native':
                argv = call['command']
                assert argv.count('--target-dir') == 1 and argv[argv.index('--target-dir')+1] == str(root)
            else:
                assert call['launch']['workspace_path'] == str(root.parent)
                assert Path(call['launch']['artifact_path']).is_relative_to(root)
        entries, allocated = snapshot(root)
        assert all(max(row['mtime_ns'], row['ctime_ns'])/1e9 <= terminal['finished_at']
                   for row in entries.values()), ('post-completion cache mutation', mode)
        groups = {}
        for name, row in entries.items():
            if stat.S_ISREG(row['mode']):
                groups.setdefault((row['dev'], row['ino']), []).append(name)
        outside = [names for names in groups.values() if entries[names[0]]['nlink'] != len(names)]
        assert not outside, ('outside target hardlinks', mode, outside[:3])
        roots[mode] = dict(root=str(root), entries=entries, allocated_bytes=allocated,
                           outside_hardlink_candidates=outside, entries_with_root=len(entries))
    result = dict(schema_version=1, owner=str(OWNER), runtime_owner=str(R), prepared_at=time.time(),
                  completed_at=terminal['finished_at'], roots=roots, source_only=True,
                  allocation_blocks_are_observation=True,
                  proofs={str(p):digest(p) for p in [RUN/'records.json', terminal_path]},
                  scope='Only the three exact completed diagnostic target roots. Source, tools, workspace identity and historical evidence remain outside them.')
    with ASSESSMENT.open('x') as output:
        json.dump(result, output, indent=2, sort_keys=True)
        output.write('\n')
    print(json.dumps(dict(assessment=str(ASSESSMENT), sha256=digest(ASSESSMENT),
                         roots={mode:{k:v for k,v in row.items() if k != 'entries'} for mode,row in roots.items()},
                         allocated_bytes=sum(row['allocated_bytes'] for row in roots.values())), indent=2))


if __name__ == '__main__':
    main()
