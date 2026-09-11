#!/usr/bin/env python3
"""Archive one completed public Cargo target, then retire its verified paths."""
import argparse
from contextlib import nullcontext
import fcntl
import json
import os
from pathlib import Path
import sys
import time

import cache_archive as archive
from reclaim_workflow_objects import identifier, no_open_files, sha, workflow
from verify_repeated_workflow import require
from workflow_io import write_json
from workflow_cache_evidence import cache_guard, workflow_cache
from host_cache_evidence import debug_workspace_cache

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.work/workflow-cache-archives'
SOURCES = [Path(__file__).resolve(), ROOT / 'scripts/cache_archive.py',
    ROOT / 'scripts/reclaim_workflow_objects.py', ROOT / 'scripts/verify_repeated_workflow.py',
    ROOT / 'scripts/workflow_case_file.py', ROOT / 'scripts/workflow_measurements.py', ROOT / 'scripts/workflow_io.py',
    ROOT / 'scripts/workflow_cache_evidence.py', ROOT / 'scripts/workflow_jobs.py',
    ROOT / 'scripts/workspace_check_evidence.py', ROOT / 'scripts/host_cache_evidence.py',
    ROOT / 'scripts/recovered_corpus_cache_evidence.py']


def read(path):
    return json.loads(path.read_text())


def owned_root():
    marker = BASE / 'owner.json'
    if not BASE.exists():
        BASE.mkdir(mode=0o700)
        write_json(marker, dict(owner=str(ROOT), format=1))
        write_json(BASE / 'targets.json', {})
    require(BASE.resolve(strict=True) == BASE and read(marker) == dict(owner=str(ROOT), format=1),
            'archive root is not owned by this workspace')


def sources():
    return {str(p.relative_to(ROOT)): sha(p) for p in SOURCES}


def selected_cache(run_id, corpus, mode, kind='workflow'):
    require(kind in ['workflow', 'recovered-workflow', 'workspace-check'], 'unknown cache provenance kind')
    identifier(run_id)
    if kind == 'workspace-check':
        require(corpus is None and mode == 'host', 'host cache cannot have a corpus or guest mode')
        return debug_workspace_cache(ROOT, run_id, sha)
    require(mode in ['native', 'check', 'baseline', 'candidate'], 'unknown workflow cache mode')
    proof = workflow
    if kind == 'recovered-workflow':
        require(corpus is not None, 'recovered workflow requires a corpus')
        proof = lambda run, parent: workflow(run, parent, recovered=True)
    return workflow_cache(ROOT, run_id, corpus, mode, proof, sha)


def selection_guard(target, mode, kind):
    require(kind in ['workflow', 'recovered-workflow', 'workspace-check'], 'unknown cache provenance kind')
    if kind == 'workspace-check':
        require(mode == 'host', 'host cache mode differs')
        # check_workspace.py uses the same enclosing benchmark lock.
        return nullcontext()
    return cache_guard(target, mode)


def check_evidence(plan):
    target, proofs, verification = selected_cache(plan['workflow'], plan['corpus'],
        plan.get('mode', 'native'), plan.get('proof_kind', 'workflow'))
    require(str(target) == plan['target'] and proofs == plan['proofs'] and verification == plan['verification'],
            'completed workflow evidence changed')
    return target


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def prepare(name, run_id, corpus, mode='native', kind='workflow'):
    target, _, _ = selected_cache(run_id, corpus, mode, kind)
    with selection_guard(target, mode, kind):
        prepare_locked(name, run_id, corpus, mode, kind)


def prepare_locked(name, run_id, corpus, mode, kind='workflow'):
    work = BASE / name
    require(not work.exists(), 'archive identity already exists')
    target, proofs, verification = selected_cache(run_id, corpus, mode, kind)
    registry = read(BASE / 'targets.json')
    require(str(target) not in registry, 'this target already has an archive reservation; inspect it before any retry')
    opened = no_open_files(target)
    manifest = archive.snapshot(target)
    require(bool(manifest['groups']), 'target contains no files')
    plan = dict(format=1, owner=str(ROOT), workflow=run_id, corpus=corpus, mode=mode, target=str(target),
        prepared_at=time.time(), sources=sources(), proofs=proofs, verification=verification,
        open_file_check=opened, manifest=manifest)
    if kind != 'workflow':
        plan['proof_kind'] = kind
    work.mkdir(mode=0o700)
    write_json(work / 'plan.json', plan)
    write_json(work / 'status.json', dict(status='prepared', plan_sha256=sha(work / 'plan.json')))
    registry[str(target)] = name
    write_json(BASE / 'targets.json', registry)
    print(json.dumps(dict(status='prepared', archive=name, target=str(target),
        files=sum(len(g['paths']) for g in manifest['groups']), unique_payloads=len(manifest['groups']),
        unique_bytes=sum(g['bytes'] for g in manifest['groups']), directories=len(manifest['directories']))), flush=True)


def load(name):
    work = BASE / name
    require(work.resolve(strict=True) == work, 'noncanonical archive identity')
    plan, status = read(work / 'plan.json'), read(work / 'status.json')
    require(plan['format'] == 1 and plan['owner'] == str(ROOT) and
            sha(work / 'plan.json') == status['plan_sha256'] and
            read(BASE / 'targets.json').get(plan['target']) == name, 'archive ownership, reservation or plan changed')
    kind, mode = plan.get('proof_kind', 'workflow'), plan.get('mode', 'native')
    require(kind in ['workflow', 'recovered-workflow', 'workspace-check'] and
            ((kind == 'workspace-check' and mode == 'host' and plan['corpus'] is None) or
             (kind in ['workflow', 'recovered-workflow'] and mode in ['native', 'check', 'baseline', 'candidate'] and
              (kind != 'recovered-workflow' or plan['corpus'] is not None))),
            'archive provenance kind or mode differs')
    archive.validate(plan['manifest'])
    return work, plan, status


def retire(target, manifest, progress):
    # Directories stay until their known contents have been retired. rmdir
    # refuses unexpected additions; there is deliberately no recursive delete.
    count = 0
    for group in manifest['groups']:
        for name in group['paths']:
            path = target / name
            current = archive.information(path)
            require(all(current[k] == group[k] for k in ['device', 'inode', 'mode', 'mtime_ns', 'bytes']),
                    'cache file changed before retirement')
            path.unlink()
            count += 1
            if count % 1000 == 0:
                progress(count)
    for directory in sorted(manifest['directories'][1:],
                            key=lambda d: len(Path(d['path']).parts), reverse=True):
        path = target / directory['path']
        current = archive.information(path, True)
        require(all(current[k] == directory[k] for k in ['device', 'inode', 'mode']),
                'cache directory changed before retirement')
        path.rmdir()
    require(not list(target.iterdir()), 'unexpected files appeared in the retired target')
    progress(count)


def apply(name):
    _, plan, _ = load(name)
    with selection_guard(Path(plan['target']), plan.get('mode', 'native'), plan.get('proof_kind', 'workflow')):
        apply_locked(name)


def apply_locked(name):
    work, plan, status = load(name)
    require(status['status'] == 'prepared' and sources() == plan['sources'],
            'archive is not an untouched preparation using these exact sources')
    require(not (ROOT / 'results' / name).exists(), 'archive report already exists')
    target = check_evidence(plan)
    manifest = plan['manifest']
    archive.unchanged(target, manifest)
    opened = no_open_files(target)
    unique_bytes = sum(g['bytes'] for g in manifest['groups'])
    # Reserve for a pessimistic DEFLATE expansion plus headers and journals.
    # This is a preflight estimate, not protection against unrelated disk use.
    required = (unique_bytes * 103 + 99) // 100 + 2 * len(archive.encoded(manifest)) + len(manifest['groups']) * 1024 + 1024**3
    free = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    require(free >= required, 'insufficient space to finish a worst-case archive before retiring originals')
    partial, completed = work / 'cache.partial.zip', work / 'cache.zip'
    require(not partial.exists() and not completed.exists(), 'archive output already exists')
    status.update(status='writing archive', pid=os.getpid(), parent_pid=os.getppid(), cwd=str(ROOT),
        started_at=time.time(), free_bytes_before=free, preflight_required_bytes=required,
        open_file_check=opened, retired_files=0)
    write_json(work / 'status.json', status)
    try:
        archive.write_archive(target, manifest, partial)
        archive.verify_archive(partial, manifest)
        archive.unchanged(target, manifest)
        check_evidence(plan)
        opened = no_open_files(target)
        partial.rename(completed)
        sync_directory(work)
        status.update(status='verified archive; retiring originals', archive_sha256=sha(completed),
            archive_bytes=completed.stat().st_size, pre_retirement_open_file_check=opened)
        write_json(work / 'status.json', status)

        def progress(count):
            status['retired_files'] = count
            write_json(work / 'status.json', status)
            print('retired files', count, flush=True)

        retire(target, manifest, progress)
        check_evidence(plan)
        require(sha(completed) == status['archive_sha256'], 'verified archive changed during retirement')
        status.update(status='completed', finished_at=time.time(),
            free_bytes_after=os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize)
        write_json(work / 'status.json', status)
        output = ROOT / 'results' / name
        output.mkdir(exist_ok=False)
        write_json(output / 'summary.json', dict(**status, target=str(target), workflow=plan['workflow'],
            proof_kind=plan.get('proof_kind', 'workflow'),
            archive=str(completed.relative_to(ROOT)), plan=str((work / 'plan.json').relative_to(ROOT)),
            files=status['retired_files'], directories=len(manifest['directories']),
            unique_payloads=len(manifest['groups']), unique_original_bytes=unique_bytes,
            verification=plan['verification'], proofs=plan['proofs'], sources=plan['sources'],
            note='Every original file payload was decoded and hashed before retirement. Reports, source and executed bytecode snapshots remain in place. The empty Cargo target is retired; archived bytes can be inspected or restored to a new owned directory. Future cache behavior is not implied. No processes were signaled.'))
    except BaseException as error:
        status.update(status='failed; audit required before further retirement', error=repr(error), failed_at=time.time())
        write_json(work / 'status.json', status)
        raise
    print(json.dumps(dict(status='completed', archive=name, bytes=status['archive_bytes'], files=status['retired_files'])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare')
    action.add_argument('--apply')
    action.add_argument('--inspect', help='read one archived file without restoring the whole cache')
    action.add_argument('--restore', help='restore into this archive identity\'s new owned restore directory')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--workflow')
    source.add_argument('--workspace-check', help='completed unpublished debug workspace check; preparation only')
    parser.add_argument('--mode', choices=['native', 'check', 'baseline', 'candidate'],
                        help='completed cache mode; preparation only, defaults to native')
    parser.add_argument('--corpus')
    parser.add_argument('--recovered-corpus', action='store_true', help='use explicitly qualified recovery evidence for a complete public case in an interrupted corpus')
    parser.add_argument('--member')
    parser.add_argument('--maximum-bytes', type=int, default=1024 * 1024)
    parser.add_argument('--restore-id')
    args = parser.parse_args()
    require(bool(args.prepare) == bool(args.workflow or args.workspace_check),
            'supply exactly one completed source only when preparing')
    require(not args.mode or args.prepare, 'supply --mode only when preparing')
    require(not args.corpus or args.prepare, 'supply --corpus only when preparing')
    require(not args.recovered_corpus or (args.prepare and args.workflow and args.corpus),
            'recovered-corpus requires a workflow and corpus during preparation')
    require(not args.workspace_check or (args.mode is None and args.corpus is None),
            'host cache preparation cannot have --mode or --corpus')
    require(bool(args.inspect) == bool(args.member), 'supply --member only when inspecting')
    require(bool(args.restore) == bool(args.restore_id), 'supply --restore-id only when restoring')
    name = identifier(args.prepare or args.apply or args.inspect or args.restore)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owned_root()
        if args.prepare:
            if args.workspace_check:
                prepare(name, args.workspace_check, None, 'host', 'workspace-check')
            else:
                prepare(name, args.workflow, args.corpus, args.mode or 'native',
                        'recovered-workflow' if args.recovered_corpus else 'workflow')
        elif args.apply:
            apply(name)
        else:
            work, plan, status = load(name)
            completed = work / 'cache.zip'
            require(completed.is_file(), 'no published archive; original or partial state requires inspection')
            if 'archive_sha256' in status:
                require(sha(completed) == status['archive_sha256'], 'published archive identity changed')
            if args.inspect:
                sys.stdout.buffer.write(archive.read_file(completed, plan['manifest'], args.member, args.maximum_bytes))
            else:
                archive.verify_archive(completed, plan['manifest'])
                restores = work / 'restores'
                restores.mkdir(mode=0o700, exist_ok=True)
                require(restores.resolve(strict=True) == restores, 'noncanonical restore root')
                destination = restores / identifier(args.restore_id)
                require(not destination.exists(), 'restore identity already exists')
                destination.mkdir(mode=0o700)
                staging = destination / 'staging'
                archive.restore(completed, plan['manifest'], staging)
                staging.rename(destination / 'cache')
                write_json(destination / 'verification.json', dict(status='verified restoration',
                    archive_sha256=sha(completed), plan_sha256=sha(work / 'plan.json'),
                    restored_at=time.time(), cache=str((destination / 'cache').relative_to(ROOT)),
                    note='Bytes, permission bits, modification times and internal hardlinks verify. Filesystem identities and future Cargo cache behavior are not reproduced.'))
                print(str(destination / 'cache'))


if __name__ == '__main__':
    main()
