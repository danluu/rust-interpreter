#!/usr/bin/env python3
"""Bounded source/provider acquisition only; no compiler or Cargo invocation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import time

HERE = Path(__file__).resolve().parent
OWNER = HERE.parents[2]
sys.path.insert(0, str(OWNER / 'experiments/stable-cgu'))
import owned_stage as owned

WORK = OWNER / '.work/hir-options-hash-acquisition-01'
NAMESPACE = OWNER / '.work/hir-options-hash-compiler-01'
SOURCE = NAMESPACE / 'source'
CARGO = NAMESPACE / 'cargo-home'
GIB = 2 ** 30


def read(path):
    return json.loads(Path(path).read_bytes())


def stamp(path):
    s = path.lstat()
    return [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]


def guard_inputs(frozen):
    for name, record in frozen['files'].items():
        path = Path(name)
        assert path.resolve(strict=True) == path and stat.S_ISREG(path.lstat().st_mode)
        assert stamp(path) == record['stamp'] and owned.sha(path) == record['sha256'], name
    for name, record in frozen['symlinks'].items():
        path = Path(name)
        assert path.is_symlink() and os.readlink(path) == record['target'] and stamp(path) == record['stamp'], name
    for name, expected in frozen['configurations'].items():
        path = Path(name)
        assert not path.is_symlink()
        assert (owned.sha(path) if path.is_file() else None) == expected, name


def allocation(root):
    total = 0
    seen = set()
    for parent, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [n for n in dirs if not (Path(parent) / n).is_symlink()]
        for name in files:
            path = Path(parent) / name
            s = path.lstat()
            if stat.S_ISLNK(s.st_mode):
                continue
            assert stat.S_ISREG(s.st_mode), path
            key = (s.st_dev, s.st_ino)
            if key not in seen:
                total += s.st_blocks * 512
                seen.add(key)
    assert total <= 2 * GIB, 'acquisition allocation exceeded its 2 GiB share of the 14 GiB aggregate cap'
    return total


def copy_new(source, destination, expected):
    source, destination = Path(source), Path(destination)
    assert destination.is_absolute() and destination.is_relative_to(NAMESPACE)
    assert not any(p in ['.', '..'] for p in destination.parts)
    for parent in [destination.parent, *destination.parents]:
        assert not parent.is_symlink()
        if parent.exists():
            assert parent.is_dir() and parent.resolve(strict=True) == parent
    assert source.resolve(strict=True) == source and stat.S_ISREG(source.lstat().st_mode)
    assert owned.sha(source) == expected
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert destination.parent.resolve(strict=True) == destination.parent
    with source.open('rb') as src, destination.open('xb') as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)
    assert destination.stat().st_nlink == 1
    assert (source.stat().st_dev, source.stat().st_ino) != (destination.stat().st_dev, destination.stat().st_ino)
    assert owned.sha(destination) == expected


def source_guard(root, entries, replacements=None):
    replacements = replacements or {}
    actual = {}
    for name, record in entries.items():
        path = root / name
        if record['mode'] == '160000':
            continue
        if record['mode'] == '120000':
            assert path.is_symlink() and os.readlink(path) == record['target'], name
            actual[name] = dict(mode='120000', target=record['target'])
        else:
            assert path.resolve(strict=True) == path and stat.S_ISREG(path.lstat().st_mode), name
            expected = replacements.get(name, record['sha256'])
            assert owned.sha(path) == expected, name
            actual[name] = dict(mode=record['mode'], bytes=path.stat().st_size, sha256=expected)
    return actual


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--inputs-sha256', required=True)
    args = p.parse_args()
    assert sys.dont_write_bytecode and not sys.flags.optimize
    assert owned.sha(HERE / 'acquisition-inputs.json') == args.inputs_sha256
    frozen = read(HERE / 'acquisition-inputs.json')
    assert owned.sha(HERE / 'acquisition-plan.json') == frozen['plan_sha256']
    plan = read(HERE / 'acquisition-plan.json')
    assert plan['namespace'] == str(NAMESPACE) and plan['owner'] == str(OWNER)
    assert plan['canonical_lock'] == str(owned.CANONICAL_LOCK) and plan['wait_seconds'] == 600
    assert plan['compiler_builds'] == plan['cargo_commands'] == 0
    assert plan['capacity'] == dict(initial_free_gib=24, capacity_stop_gib=9, running_floor_gib=8,
        aggregate_allocated_gib=14, acquisition_allocated_gib=2)
    WORK.mkdir(exist_ok=False)
    receipt = dict(status='waiting', owner=str(OWNER), namespace=str(NAMESPACE), pid=os.getpid(),
        parent_pid=os.getppid(), started_at=time.time(), commands=[], compiler_builds=0, cargo_commands=0)
    owned.write(WORK / 'receipt.json', receipt)
    try:
        guard_inputs(frozen)
        with owned.workload_lock(owned.CANONICAL_LOCK, 600):
            receipt.update(status='running', admitted_at=time.time(), free_bytes_before=owned.disk(OWNER, 24))
            owned.write(WORK / 'receipt.json', receipt)
            guard_inputs(frozen)
            assert not NAMESPACE.exists() and not NAMESPACE.is_symlink()
            assert NAMESPACE.parent.resolve(strict=True) == NAMESPACE.parent
            NAMESPACE.mkdir()
            (NAMESPACE / 'tmp').mkdir()
            inherited = read(HERE / 'source-01/manifest.json')
            def command(row):
                owned.disk(OWNER, 9)
                allocation(NAMESPACE)
                output = WORK / 'commands' / f"{len(receipt['commands']):03}"
                try:
                    result = owned.run(row['argv'], cwd=Path(row['cwd']), env=row['environment'],
                        out=output, capacity_root=OWNER)
                finally:
                    child = output / 'receipt.json'
                    if child.is_file():
                        saved = read(child)
                        receipt['commands'].append(dict(path=str(child), sha256=owned.sha(child),
                            pid=saved.get('pid'), command=row['argv']))
                        owned.write(WORK / 'receipt.json', receipt)
                if row['expected_stdout'] is not None:
                    assert (output/'stdout').read_text() == row['expected_stdout'], row['argv']
                allocation(NAMESPACE)
                return result
            for row in plan['children_before_copy']:
                command(row)
            assert not (SOURCE / '.git/objects/info/alternates').exists()
            assert not (SOURCE / 'library/backtrace/.git/objects/info/alternates').exists()
            source_guard(SOURCE, plan['source_tree'], inherited['complete_closure_files'])
            source_guard(SOURCE / 'library/backtrace', plan['backtrace_tree'])
            copied = []
            for row in plan['copies']:
                owned.disk(OWNER, 9)
                copy_new(row['source'], row['destination'], row['sha256'])
                copied.append(row)
                allocation(NAMESPACE)
            for row in plan['children_after_copy']:
                command(row)
            candidate_revision = (WORK / 'commands' / f"{plan['candidate_revision_child']:03}" / 'stdout').read_text().strip()
            assert len(candidate_revision) == 40 and all(c in '0123456789abcdef' for c in candidate_revision)
            assert candidate_revision != plan['base_commit']
            final = source_guard(SOURCE, plan['source_tree'], inherited['complete_closure_files'])
            backtrace = source_guard(SOURCE / 'library/backtrace', plan['backtrace_tree'])
            for row in copied:
                assert owned.sha(row['destination']) == row['sha256'] and Path(row['destination']).stat().st_nlink == 1
            guard_inputs(frozen)
            owned.write(WORK / 'acquired.json', dict(status='acquired-not-build-qualified',
                candidate_revision=candidate_revision, source=str(SOURCE), source_files=final,
                backtrace_files=backtrace, copies=copied, source_identity=inherited['source_identity'],
                allocated_bytes=allocation(NAMESPACE), builds=0))
            receipt.update(status='passed', candidate_revision=candidate_revision,
                acquired_sha256=owned.sha(WORK / 'acquired.json'), free_bytes_after=owned.disk(OWNER, 8))
    except BaseException as error:
        receipt.update(status='failed', error=repr(error))
        raise
    finally:
        receipt['finished_at'] = time.time()
        owned.write(WORK / 'receipt.json', receipt)


if __name__ == '__main__':
    main()
