#!/usr/bin/env python3
"""Reclaim only .o files from a completed public workflow's native Cargo target.

Prepare an inventory first; apply its exact identity separately. Executables,
libraries, metadata, incremental query caches, sidecars and reports are retained.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

from verify_repeated_workflow import verify, require
from workflow_io import write_json

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def identifier(value):
    require(isinstance(value, str) and Path(value).name == value and value not in ['', '.', '..'], 'invalid ID')
    return value


def identity(path):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode), 'non-regular file: ' + str(path))
    return dict(device=info.st_dev, inode=info.st_ino, bytes=info.st_size,
                mode=info.st_mode, mtime_ns=info.st_mtime_ns)


def files(target):
    require(target.is_dir() and target.resolve(strict=True) == target, 'noncanonical target')
    found = []
    for parent, directories, names in os.walk(target, followlinks=False):
        for name in directories:
            require(not (Path(parent) / name).is_symlink(), 'symlink directory in native target')
        for name in names:
            path = Path(parent) / name
            identity(path)  # Reject symlinks and special files without following them.
            found.append(path)
    return sorted(found)


def inventory(target):
    result = []
    for path in files(target):
        before = identity(path)
        digest = sha(path)
        require(identity(path) == before, 'file changed during inventory')
        result.append(dict(path=str(path.relative_to(target)), **before, sha256=digest,
            remove=path.suffix == '.o' and not before['mode'] & 0o111))
    return result


def validate_inventory(target, entries, *, removed=False):
    expected = [item for item in entries if not (removed and item['remove'])]
    require([str(p.relative_to(target)) for p in files(target)] == [item['path'] for item in expected],
            'native target file set changed')
    for item in expected:
        path = target / item['path']
        require(identity(path) == {k: item[k] for k in ['device', 'inode', 'bytes', 'mode', 'mtime_ns']} and
                sha(path) == item['sha256'], 'native target content or identity changed: ' + str(path))


def no_open_files(target):
    check = subprocess.run(['lsof', '-nP', '+D', str(target)], text=True, capture_output=True)
    require(check.returncode == 1 and not check.stdout.strip() and not check.stderr.strip(),
            'native target has open files or lsof could not establish that it is unused: ' + check.stdout + check.stderr)
    return dict(command=check.args, returncode=check.returncode, stdout=check.stdout,
                stderr=check.stderr, checked_at=time.time())


def workflow(run_id):
    """Derive a single target from completed commands, never from an arbitrary path."""
    run_id = identifier(run_id)
    report_path = ROOT / 'results' / run_id / 'summary.json'
    report = json.loads(report_path.read_text())
    require(report['project'] in ['pgrust', 'nushell', 'ruff', 'fre'], 'public workflow required')
    raw = ROOT / '.work/runs' / run_id
    require(report['raw'] == str(raw.relative_to(ROOT)) and raw.resolve(strict=True) == raw, 'unexpected workflow root')
    status_path = ROOT / '.work/experiments' / run_id / 'status.json'
    status = json.loads(status_path.read_text())
    require(status['owner'] == str(ROOT) and status['cwd'] == str(ROOT) and
            status['status'] == 'finished' and status['returncode'] == 0, 'workflow is not completed under this owner')
    command = status['command']
    require(Path(command[1]).name == 'bench_e2e_workflow.py' and
            command[command.index('--run-id') + 1] == run_id, 'not a standalone completed workflow')
    # PID reuse is harmless; a still-live command for this same run is not.
    check = subprocess.run(['ps', '-p', str(status['supervisor_pid']) + ',' + str(status['child_pid']),
                            '-o', 'pid,ppid,lstart,command'], capture_output=True, text=True)
    require(check.returncode in [0, 1] and not check.stderr and
            not any(run_id in line for line in check.stdout.splitlines()[1:]), 'original workflow process is still live or ps failed')
    verified = verify(report)
    stored = json.loads(report_path.with_name('verification.json').read_text())
    # The separate reference-history comparison is not rerun here. The complete
    # command/source/paired-artifact checks must still exactly reproduce.
    require(all(verified[k] == stored[k] for k in verified if k != 'reference_bytecode'), 'workflow verification differs')
    rows = json.loads((raw / 'records.json').read_text())
    target = raw / 'native'
    require(target.resolve(strict=True) == target and target.is_dir(), 'native target is not canonical')
    for row in rows:
        if row['mode'] == 'native':
            for call in row['calls']:
                command = call['command']
                require(command[command.index('--target-dir') + 1] == str(target), 'native commands name another target')
    proof_paths = [report_path, report_path.with_name('verification.json'), status_path,
        raw / 'records.json', raw / 'source-transitions.json', raw / 'active-command.json']
    proof_paths += [p for p in [raw / 'check-records.json', raw / 'case.json'] if p.exists()]
    return target, {str(p.relative_to(ROOT)): sha(p) for p in proof_paths}, verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', metavar='CLEANUP_ID')
    action.add_argument('--apply', metavar='CLEANUP_ID')
    parser.add_argument('--workflow', help='completed public workflow; required for --prepare')
    args = parser.parse_args()
    require(bool(args.workflow) == bool(args.prepare), 'supply --workflow only when preparing')
    cleanup_id = identifier(args.prepare or args.apply)
    work = ROOT / '.work/reclaims' / cleanup_id
    require(not (ROOT / 'results' / cleanup_id).exists(), 'cleanup result already exists')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if args.prepare:
        require(not work.exists(), 'cleanup identity already exists')
        target, proofs, verified = workflow(args.workflow)
        work.mkdir(parents=True)
        opened = no_open_files(target)
        entries = inventory(target)
        require(any(item['remove'] for item in entries), 'no removable objects')
        plan = dict(schema_version=1, owner=str(ROOT), workflow=args.workflow, target=str(target),
            prepared_at=time.time(), driver_sha256=sha(Path(__file__)), proofs=proofs,
            verification=verified, process_and_open_file_check=opened, entries=entries)
        write_json(work / 'plan.json', plan)
        write_json(work / 'status.json', dict(status='prepared', plan_sha256=sha(work / 'plan.json')))
        print(json.dumps(dict(status='prepared', cleanup_id=cleanup_id,
            files=len(entries), removable_objects=sum(e['remove'] for e in entries),
            removable_logical_bytes=sum(e['bytes'] for e in entries if e['remove']),
            retained_files=sum(not e['remove'] for e in entries))), flush=True)
        return
    status = json.loads((work / 'status.json').read_text())
    require(status['status'] == 'prepared' and sha(work / 'plan.json') == status['plan_sha256'],
            'cleanup is not an untouched prepared inventory; inspect partial work separately')
    plan = json.loads((work / 'plan.json').read_text())
    require(plan['owner'] == str(ROOT) and plan['schema_version'] == 1 and
            plan['driver_sha256'] == sha(Path(__file__)), 'cleanup owner/schema/driver differs')
    target, proofs, verified = workflow(plan['workflow'])
    require(str(target) == plan['target'] and proofs == plan['proofs'] and verified == plan['verification'],
            'workflow changed after preparation')
    entries = plan['entries']
    validate_inventory(target, entries)
    opened = no_open_files(target)
    status.update(status='applying', pid=os.getpid(), parent_pid=os.getppid(), cwd=str(ROOT),
                  started_at=time.time(), open_file_check=opened, deleted_objects=0,
                  free_bytes_before=os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize)
    write_json(work / 'status.json', status)
    try:
        for item in entries:
            if not item['remove']:
                continue
            path = target / item['path']
            require(path.suffix == '.o' and not item['mode'] & 0o111 and
                    identity(path) == {k: item[k] for k in ['device', 'inode', 'bytes', 'mode', 'mtime_ns']},
                    'object identity changed before unlink')
            path.unlink()
            status['deleted_objects'] += 1
            if status['deleted_objects'] % 10000 == 0:
                write_json(work / 'status.json', status)
                print('removed objects', status['deleted_objects'], flush=True)
        validate_inventory(target, entries, removed=True)
        require(all(sha(ROOT / p) == digest for p, digest in proofs.items()), 'preserved workflow evidence changed')
        require(verify(json.loads((ROOT / 'results' / plan['workflow'] / 'summary.json').read_text())) == verified,
                'post-cleanup workflow verification differs')
        status.update(status='completed', finished_at=time.time(),
            free_bytes_after=os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize,
            retained_files_verified=sum(not item['remove'] for item in entries),
            removed_logical_bytes=sum(item['bytes'] for item in entries if item['remove']))
        write_json(work / 'status.json', status)
        output = ROOT / 'results' / cleanup_id
        output.mkdir(exist_ok=False)
        write_json(output / 'summary.json', dict(**status, workflow=plan['workflow'], target=str(target),
            inventory=str((work / 'plan.json').relative_to(ROOT)), proofs=proofs, verification=verified,
            note='Only non-executable .o files in this completed native target were unlinked. Every other native-target file and all workflow snapshots/reports were verified unchanged. Logical byte sums do not measure physical space freed on a shared/APFS host. No processes were signaled.'))
    except BaseException as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write_json(work / 'status.json', status)
        raise
    print(json.dumps(dict(status='completed', objects=status['deleted_objects'],
                         retained_files=status['retained_files_verified'])))


if __name__ == '__main__':
    main()
