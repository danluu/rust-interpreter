#!/usr/bin/env python3
"""Preserve exactly catalogued, completed published host-build Cargo targets.

This is separate from the frozen public workflow/unpublished-debug selectors.
Shared archive format, hashing, restoration and checked retirement stay unchanged.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = ROOT / '.work/published-build-cache-archives'
sys.path.insert(0, str(ROOT / 'scripts'))
import cache_archive as archive
from archive_workflow_cache import retire, sync_directory
from reclaim_workflow_objects import sha, no_open_files, identifier
from verify_repeated_workflow import require
from workflow_io import write_json


def read(path): return json.loads(path.read_text())


def metadata(run, report, execution, catalog):
    require(run in catalog, 'uncatalogued build')
    item = catalog[run]
    target = ROOT / '.work/diagnostic-builds' / run
    source = ROOT / '.work' / run / 'tool-source'
    supervisor, controller = execution['supervisor'], execution['controller']
    require(report['status'] == 'passed' and not report['production_change'] and
            not report['performance_measurement'], 'not a completed isolated build')
    require(report['source'] == str(source.relative_to(ROOT)) and
            report['provenance'] == f'.work/{run}/provenance.json', 'source identity differs')
    require(supervisor['owner'] == supervisor['cwd'] == str(ROOT) and
            supervisor['command'] == item['controller_command'], 'owner/command differs')
    require(supervisor['status'] == controller['status'] == 'finished' and
            supervisor['returncode'] == controller['returncode'] == 0 and
            supervisor['child_pid'] == controller['pid'] and
            supervisor['supervisor_pid'] == controller['parent_pid'] and
            supervisor['finished_at'] >= controller['finished_at'], 'unfinished or unrelated process receipt')
    require(report['tests']['debug'] == report['tests']['release'] and
            report['tests']['debug']['passed'] == item['tests'] and
            report['tests']['debug']['ignored'] == 1, 'qualification differs')
    require(len(report['commands']) == 3 and
            [c['label'] for c in report['commands'][:2]] == ['debug', 'release'], 'command coverage differs')
    for c in report['commands']:
        command = c['command']
        require(c['returncode'] == 0 and command[:2] == ['cargo', '+nightly-2026-09-08'] and
                command.count('--target-dir') == command.count('--manifest-path') == 1 and
                command[command.index('--target-dir') + 1] == str(target) and
                command[command.index('--manifest-path') + 1] == str(source / 'Cargo.toml'),
                'completed command does not own the exact target')
    return target, source


def evidence(run):
    catalog = read(HERE / 'catalog.json')
    require(run in catalog, 'uncatalogued build')
    proofs = {}
    def bind(path, expected=None):
        require(path.resolve(strict=True) == path and path.is_file(), 'noncanonical evidence')
        digest = sha(path)
        require(expected is None or digest == expected, 'evidence hash differs: ' + str(path))
        proofs[str(path.relative_to(ROOT))] = digest
        return read(path) if path.suffix == '.json' else None
    item = catalog[run]
    report = bind(ROOT / 'results' / run / 'summary.json', item['summary_sha256'])
    execution = bind(ROOT / 'results' / run / 'execution.json', item['execution_sha256'])
    target, source = metadata(run, report, execution, catalog)
    require(target.resolve(strict=True) == target and source.resolve(strict=True) == source,
            'noncanonical owned source/target')
    for path, digest in execution['evidence'].items(): bind(ROOT / path, digest)
    provenance = bind(ROOT / report['provenance'], report['provenance_sha256'])
    require(provenance['source'] == report['source'] and provenance['tool_key'] == report['tool_key'],
            'published source differs')
    for path, digest in provenance['copied_inputs'].items(): bind(source / path, digest)
    tools = ROOT / '.work/interpreter-tools' / report['tool_key']
    require(bind(tools / 'ready.json') == report['binaries'], 'published binaries differ')
    source_receipt = bind(tools / 'source.json')
    require(source_receipt['files'] == provenance['copied_inputs'] and
            source_receipt['provenance_sha256'] == report['provenance_sha256'], 'published source receipt differs')
    bind(tools / 'capabilities.json')
    for name, digest in report['binaries'].items(): bind(tools / name, digest)
    for c in report['commands']: bind(ROOT / '.work' / run / (c['label'] + '.log'), c['log_sha256'])
    require(all(target not in (ROOT / p).parents for p in proofs), 'proof inside retired target')
    pids = [execution['supervisor']['supervisor_pid'], execution['controller']['pid'],
            *[c['pid'] for c in report['commands']]]
    observed = subprocess.run(['ps', '-p', ','.join(map(str, pids)), '-o', 'pid,ppid,lstart,tty,command'],
                              text=True, capture_output=True)
    require(observed.returncode in [0, 1] and not observed.stderr and
            all(run not in line and str(target) not in line for line in observed.stdout.splitlines()[1:]),
            'owned build process still live or process inspection failed')
    return target, proofs


def sources():
    paths = [Path(__file__), HERE / 'catalog.json']
    # Imported archive helpers are retained by exact source identity too.
    paths += [ROOT / 'scripts' / name for name in ['cache_archive.py', 'archive_workflow_cache.py',
        'reclaim_workflow_objects.py', 'verify_repeated_workflow.py', 'workflow_io.py']]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def prepare(run, name):
    target, proofs = evidence(run)
    require(str(target) not in read(ROOT / '.work/workflow-cache-archives/targets.json'),
            'target reserved by existing archive system')
    work = BASE / name
    require(not work.exists(), 'archive identity exists')
    for previous in BASE.iterdir():
        if (previous / 'plan.json').exists():
            require(read(previous / 'plan.json')['target'] != str(target), 'target already reserved')
    opened = no_open_files(target)
    manifest = archive.snapshot(target)
    require(bool(manifest['groups']), 'empty cache')
    plan = dict(format=1, owner=str(ROOT), run=run, target=str(target), sources=sources(),
                proofs=proofs, manifest=manifest, open_files=opened, prepared_at=time.time())
    work.mkdir(mode=0o700)
    write_json(work / 'plan.json', plan)
    write_json(work / 'status.json', dict(status='prepared', plan_sha256=sha(work / 'plan.json')))
    report = ROOT / 'results' / name
    report.mkdir(exist_ok=False)
    write_json(report / 'plan.json', plan)
    print(json.dumps(dict(status='prepared', name=name, files=sum(len(g['paths']) for g in manifest['groups']),
                          bytes=sum(g['bytes'] for g in manifest['groups']), proofs=len(proofs))), flush=True)


def load(name):
    work = BASE / name
    require(work.resolve(strict=True) == work, 'noncanonical archive root')
    plan, status = read(work / 'plan.json'), read(work / 'status.json')
    require(plan['owner'] == str(ROOT) and plan['format'] == 1 and plan['sources'] == sources() and
            sha(work / 'plan.json') == status['plan_sha256'] == sha(ROOT / 'results' / name / 'plan.json'),
            'archive plan/source identity differs')
    target, proofs = evidence(plan['run'])
    require(str(target) == plan['target'] and proofs == plan['proofs'], 'source or installed evidence changed')
    archive.validate(plan['manifest'])
    return work, plan, status, target


def apply(name):
    work, plan, status, target = load(name)
    require(status['status'] == 'prepared', 'not an untouched preparation')
    committed = subprocess.run(['git', 'show', f'HEAD:results/{name}/plan.json'], cwd=ROOT, capture_output=True)
    require(committed.returncode == 0 and committed.stdout == (work / 'plan.json').read_bytes(),
            'exact inventory must be reviewed and committed before retirement')
    manifest = plan['manifest']
    archive.unchanged(target, manifest)
    no_open_files(target)
    unique = sum(g['bytes'] for g in manifest['groups'])
    required = (unique * 103 + 99) // 100 + 2 * len(archive.encoded(manifest)) + len(manifest['groups']) * 1024 + 1024**3
    free = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    require(free >= required, 'insufficient archive reserve')
    partial, complete = work / 'cache.partial.zip', work / 'cache.zip'
    require(not partial.exists() and not complete.exists(), 'archive output exists')
    status.update(status='writing', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
                  free_bytes_before=free, required_bytes=required, retired_files=0)
    write_json(work / 'status.json', status)
    try:
        archive.write_archive(target, manifest, partial)
        archive.verify_archive(partial, manifest)
        archive.unchanged(target, manifest)
        load(name)
        no_open_files(target)
        partial.rename(complete)
        sync_directory(work)
        status.update(status='verified; retiring originals', archive_sha256=sha(complete), archive_bytes=complete.stat().st_size)
        write_json(work / 'status.json', status)
        def progress(count):
            status['retired_files'] = count
            write_json(work / 'status.json', status)
        retire(target, manifest, progress)
        load(name)
        require(sha(complete) == status['archive_sha256'], 'archive changed during retirement')
        status.update(status='completed', finished_at=time.time(), unique_original_bytes=unique,
                      free_bytes_after=os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize)
        write_json(work / 'status.json', status)
        write_json(ROOT / 'results' / name / 'summary.json', dict(**status, target=str(target),
            archive=str(complete.relative_to(ROOT)), proofs=plan['proofs'], sources=plan['sources'],
            note='All payloads decoded and hashed before retirement; source, installed tools and receipts remain. No processes signaled.'))
    except BaseException as error:
        status.update(status='failed; audit required', error=repr(error), failed_at=time.time())
        write_json(work / 'status.json', status)
        raise
    print(json.dumps(dict(status='completed', name=name, original_bytes=unique, archive_bytes=status['archive_bytes'])), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'apply', 'verify'])
    parser.add_argument('--name', required=True)
    parser.add_argument('--build')
    args = parser.parse_args()
    name = identifier(args.name)
    require((args.action == 'prepare') == bool(args.build), 'build required only during preparation')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        BASE.mkdir(mode=0o700, exist_ok=True)
        require(BASE.resolve(strict=True) == BASE, 'noncanonical archive base')
        if args.action == 'prepare': prepare(args.build, name)
        elif args.action == 'apply': apply(name)
        else:
            work, plan, status, target = load(name)
            require(status['status'] == 'completed' and not list(target.iterdir()), 'retirement incomplete')
            require(sha(work / 'cache.zip') == status['archive_sha256'], 'archive hash differs')
            archive.verify_archive(work / 'cache.zip', plan['manifest'])
            print(json.dumps(dict(status='verified', name=name, proofs=len(plan['proofs']))))


if __name__ == '__main__': main()
