#!/usr/bin/env python3
"""Check Cargo freshness after restoring a production edit, without a manual touch."""
import argparse
import fcntl
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/tuned-native'))
from timing import environment, invoke, require, sha
from workflow_io import SourceEdit, write_json as write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['before', 'after'], required=True)
    args = parser.parse_args()
    run = 'source-restore-' + args.phase + '-01'
    work = ROOT / '.work' / run
    work.mkdir(exist_ok=False)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        source = work / 'fixture'
        (source / 'src').mkdir(parents=True)
        (source / 'Cargo.toml').write_text('[package]\nname="restore-fixture"\nversion="0.0.0"\nedition="2024"\n[workspace]\n')
        (source / 'Cargo.lock').write_text('version=4\n[[package]]\nname="restore-fixture"\nversion="0.0.0"\n')
        path = source / 'src/lib.rs'
        original = b'fn answer() -> u8 { 1 }\n#[test]\nfn correct_answer() { assert_eq!(answer(), 1); }\n'
        path.write_bytes(original)
        command = ['cargo', '+nightly-2026-09-08', 'test', '--manifest-path', str(source / 'Cargo.toml'), '--lib',
                   '--locked', '--offline', '--jobs', '2', '--target-dir', str(work / 'target')]
        env = environment('repository')
        rows = []

        def run_test(label):
            row, stdout, stderr = invoke(work, label, command, source, env)
            row.update(source_sha256=sha(path), source_mtime_ns=path.stat().st_mtime_ns,
                       recompiled='Compiling restore-fixture' in stderr)
            rows.append(row)
            write(work / 'records.json', rows)
            return row

        with SourceEdit(path, original) as edit:
            backup_stamp = edit.backup.stat().st_mtime_ns
            require(run_test('original')['returncode'] == 0, 'original fixture failed')
            edit.replace(original.replace(b'{ 1 }', b'{ 2 }'))
            wrong = run_test('wrong')
            require(wrong['returncode'] == 101 and wrong['recompiled'], 'wrong edit was not compiled/rejected')
        require(path.read_bytes() == original, 'original bytes not restored')
        restored = run_test('restored')
        if args.phase == 'before':
            require(restored['returncode'] == 101 and not restored['recompiled'], 'stale-cache behavior was not reproduced')
        else:
            require(restored['returncode'] == 0 and restored['recompiled'], 'Cargo did not rebuild the restored original')
        out = ROOT / 'results' / run
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='reproduced' if args.phase == 'before' else 'passed',
            raw=str(work.relative_to(ROOT)), commands=3, original_bytes_restored=True,
            backup_mtime_ns=backup_stamp, restored_mtime_ns=restored['source_mtime_ns'],
            cargo_recompiled_restored_source=restored['recompiled'], restored_command_returncode=restored['returncode'],
            records_sha256=sha(work / 'records.json'), workflow_io_sha256=sha(ROOT / 'scripts/workflow_io.py'),
            note='Original passes, changed answer fails. After context exit, run the identical Cargo command on restored original bytes with no manual touch.'))
        print(args.phase, 'restored exit:', restored['returncode'], 'recompiled:', restored['recompiled'])


if __name__ == '__main__':
    main()
