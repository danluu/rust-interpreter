#!/usr/bin/env python3
"""Share identical completed public artifact data while retaining independent files."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import time

from artifact_clones import inspect, replace_duplicate
from reclaim_workflow_objects import ROOT, files, identifier, no_open_files, sha, workflow
from verify_repeated_workflow import require
from workflow_io import write_json


def source_hashes():
    names = ['clone_workflow_artifacts.py', 'artifact_clones.py', 'reclaim_workflow_objects.py',
             'verify_repeated_workflow.py', 'workflow_io.py']
    return {str((Path('scripts') / name)): sha(ROOT / 'scripts' / name) for name in names}


def snapshots(run_id, corpus):
    target, proofs, verified = workflow(run_id, corpus)
    artifact_root = target.parent / 'artifacts'
    rows = json.loads((target.parent / 'records.json').read_text())
    entries = [a for row in rows for a in row['artifacts']]
    require(0 < len(entries) <= 128 and len({a['path'] for a in entries}) == len(entries),
            'artifact inventory is empty, duplicated or too large')
    require(sorted(str(p.relative_to(ROOT)) for p in files(artifact_root)) == sorted(a['path'] for a in entries),
            'recorded artifacts do not match the closed snapshot directory')
    opened = no_open_files(artifact_root)
    result = []
    anchors = {}
    for entry in sorted(entries, key=lambda a: a['path']):
        path = ROOT / entry['path']
        require(path.suffix == '.rbc' and path.is_relative_to(artifact_root), 'unexpected snapshot path')
        info = inspect(path, entry['sha256'])
        require(info['bytes'] == entry['bytes'], 'snapshot size differs from executed artifact')
        key = (info['sha256'], info['bytes'])
        anchor = anchors.setdefault(key, entry['path'])
        result.append(dict(path=entry['path'], anchor=anchor, **info))
    return dict(workflow=run_id, corpus=corpus, root=str(artifact_root.relative_to(ROOT)), proofs=proofs,
                verification=verified, entries=result, open_file_check=opened)


def stable(record):
    return {k: v for k, v in record.items() if k not in ['atime_ns', 'open_file_check']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare')
    action.add_argument('--apply')
    parser.add_argument('--corpus', action='append', default=[])
    parser.add_argument('--workflow', action='append', default=[])
    parser.add_argument('--plan-sha256')
    args = parser.parse_args()
    require((bool(args.prepare) and 0 < len(args.workflow) == len(args.corpus) <= 8 and not args.plan_sha256) or
            (bool(args.apply) and not args.workflow and not args.corpus and args.plan_sha256), 'invalid preparation/application arguments')
    run = identifier(args.prepare or args.apply)
    raw, out = [ROOT / parent / run for parent in ['.work/clones', 'results']]
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.prepare:
            require(not raw.exists() and not out.exists(), 'clone inventory already exists')
            qualification = ROOT / 'results/artifact-clones-qualification-01/summary.json'
            qualified = json.loads(qualification.read_text())
            require(qualified['status'] == 'passed' and qualified['independent_writes_both_directions'] and
                    qualified['sources_sha256']['scripts/artifact_clones.py'] == sha(ROOT / 'scripts/artifact_clones.py'),
                    'current clone helper has not passed qualification')
            pairs = list(zip(args.workflow, args.corpus))
            require(len(set(args.workflow)) == len(pairs), 'duplicate workflow')
            histories = [snapshots(identifier(w), identifier(c)) for w, c in pairs]
            plan = dict(schema_version=1, owner=str(ROOT), prepared_at=time.time(), histories=histories,
                sources_sha256=source_hashes(), qualification_sha256=sha(qualification),
                semantics='Preserve exact paths/bytes/ownership/mode/mtime and independent writes. Inode/ctime/birthtime change; access times may change during verification. Plain files only; no hardlink or ordinary-copy fallback.')
            raw.mkdir(parents=True)
            out.mkdir()
            write_json(raw / 'plan.json', plan)
            digest = sha(raw / 'plan.json')
            write_json(raw / 'status.json', dict(status='prepared', plan_sha256=digest))
            entries = [e for h in histories for e in h['entries']]
            write_json(out / 'review.json', dict(plan_sha256=digest, raw=str(raw.relative_to(ROOT)),
                workflows=args.workflow, files=len(entries), replacements=sum(e['path'] != e['anchor'] for e in entries),
                duplicate_logical_bytes=sum(e['bytes'] for e in entries if e['path'] != e['anchor']),
                sources_sha256=plan['sources_sha256'], qualification_sha256=plan['qualification_sha256'],
                semantics=plan['semantics']))
            print((out / 'review.json').read_text(), flush=True)
            return
        status = json.loads((raw / 'status.json').read_text())
        review = json.loads((out / 'review.json').read_text())
        require(status['status'] == 'prepared' and status['plan_sha256'] == args.plan_sha256 ==
                sha(raw / 'plan.json') == review['plan_sha256'] and not (out / 'summary.json').exists(),
                'inventory is not an untouched reviewed preparation; inspect partial work separately')
        plan = json.loads((raw / 'plan.json').read_text())
        require(plan['schema_version'] == 1 and plan['owner'] == str(ROOT) and
                plan['sources_sha256'] == source_hashes(), 'owner/schema/source differs')
        for history in plan['histories']:
            current = snapshots(history['workflow'], history['corpus'])
            require(current['proofs'] == history['proofs'] and current['verification'] == history['verification'] and
                    [stable(e) for e in current['entries']] == [stable(e) for e in history['entries']],
                    'completed workflow changed since review')
        status.update(status='applying', started_at=time.time(), pid=os.getpid(), parent_pid=os.getppid(),
            cwd=str(ROOT), completed=0, free_bytes_before=os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize)
        write_json(raw / 'status.json', status)
        try:
            with (raw / 'replacements.jsonl').open('x') as journal:
                for history in plan['histories']:
                    by_path = {e['path']: e for e in history['entries']}
                    for entry in history['entries']:
                        if entry['path'] == entry['anchor']:
                            continue
                        anchor = by_path[entry['anchor']]
                        info = lambda e: {k: v for k, v in e.items() if k not in ['path', 'anchor']}
                        result = replace_duplicate(ROOT / anchor['path'], ROOT / entry['path'], info(anchor), info(entry))
                        journal.write(json.dumps(dict(path=entry['path'], anchor=anchor['path'], result=result)) + '\n')
                        journal.flush()
                        os.fsync(journal.fileno())
                        status['completed'] += 1
                    write_json(raw / 'status.json', status)
                    print(json.dumps(dict(workflow=history['workflow'], completed=status['completed'])), flush=True)
            for history in plan['histories']:
                current = snapshots(history['workflow'], history['corpus'])
                require(current['proofs'] == history['proofs'] and current['verification'] == history['verification'],
                        'preserved workflow verification changed')
                for before, after in zip(history['entries'], current['entries']):
                    require(all(before[k] == after[k] for k in ['path', 'anchor', 'sha256', 'bytes', 'uid', 'gid', 'mode', 'mtime_ns']),
                            'preserved snapshot data or metadata changed')
            status.update(status='completed and verified', finished_at=time.time(),
                free_bytes_after=os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize)
            write_json(raw / 'status.json', status)
            write_json(out / 'summary.json', dict(**review, completion=status,
                plan_sha256_verified=sha(raw / 'plan.json'), journal_sha256=sha(raw / 'replacements.jsonl'),
                all_original_workflow_verifications_reproduced=True,
                note='Duplicate logical bytes are not a measured physical-space saving; shared-volume free space can change due to other work. No benchmark timers include this maintenance.'))
            print(json.dumps(status), flush=True)
        except BaseException as error:
            status.update(status='failed; inspect partial work', error=repr(error), finished_at=time.time())
            write_json(raw / 'status.json', status)
            raise


if __name__ == '__main__':
    main()
