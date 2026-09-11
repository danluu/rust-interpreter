#!/usr/bin/env python3
"""Verify terminal archive receipts against the separately reviewed inventories."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from reclaim_workflow_objects import identifier
from verify_repeated_workflow import require
from workflow_io import write_json


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def assess(name, completed_prefix=None):
    identifier(name)
    out = ROOT / 'results' / name
    review = read(out / 'inventory-review.json')
    batch_path = ROOT / '.work/cache-batches' / (name + '.json')
    batch = read(batch_path)
    require(batch['owner'] == str(ROOT) and batch['schema_version'] == 1 and
            review['batch_plan'] == str(batch_path.relative_to(ROOT)) and
            review['batch_sha256'] == sha(batch_path) and
            review['controller_sha256'] == sha(Path(__file__).with_name('archive_batch.py')),
            'review, owner or batch/controller hash differs')
    require(len(batch['entries']) == len(review['entries']), 'review entry count differs')
    experiment = ROOT / '.work/experiments' / (name + '-apply')
    status, plan = read(experiment / 'status.json'), read(experiment / 'plan.json')
    require(status['status'] == 'finished' and status['returncode'] == (1 if completed_prefix else 0) and
            status['owner'] == status['cwd'] == plan['owner'] == str(ROOT) and
            status['command'] == plan['command'] and
            status['plan_sha256'] == sha(experiment / 'plan.json') and
            status['log_sha256'] == sha(experiment / 'command.log'), 'batch supervisor receipt differs')
    command = status['command']
    require(command[1:] == ['benchmarks/experiments/compiler-pipeline/archive_batch.py',
            '--plan', str(batch_path), '--plan-sha256', review['batch_sha256'], '--action', 'apply'],
            'batch command differs')
    objects = [json.loads(line) for line in (experiment / 'command.log').read_text().splitlines()
               if line.startswith('{')]
    launches = [o for o in objects if o.get('action') == 'apply' and 'pid' in o]
    count = len(batch['entries'])
    if completed_prefix is None:
        require([o['archive'] for o in launches] == [e['archive'] for e in batch['entries']] and
                objects[-1] == dict(status='completed', action='apply', targets=count,
                                    plan_sha256=review['batch_sha256']), 'child launch/completion ledger differs')
    else:
        require(0 < completed_prefix < count and
                [o['archive'] for o in launches] == [e['archive'] for e in batch['entries'][:completed_prefix + 1]] and
                'BlockingIOError: [Errno 35]' in (experiment / 'command.log').read_text(),
                'not the reviewed pre-application lock failure')
        for entry, reviewed in zip(batch['entries'][completed_prefix:], review['entries'][completed_prefix:]):
            work = ROOT / '.work/workflow-cache-archives' / entry['archive']
            require(read(work / 'status.json')['status'] == 'prepared' and
                    sha(work / 'plan.json') == reviewed['plan_sha256'] and
                    {p.name for p in work.iterdir()} == {'plan.json', 'status.json'} and
                    not (ROOT / 'results' / entry['archive']).exists(), 'remaining target was started')
        count = completed_prefix
    reservations = read(ROOT / '.work/workflow-cache-archives/targets.json')
    entries, evidence = [], {}
    for entry, reviewed, launch in zip(batch['entries'][:count], review['entries'][:count], launches[:count]):
        archive = identifier(entry['archive'])
        work = ROOT / '.work/workflow-cache-archives' / archive
        prepared = read(work / 'plan.json')
        child = read(work / 'status.json')
        result = read(ROOT / 'results' / archive / 'summary.json')
        require(all(reviewed[k] == v for k, v in entry.items()) and reviewed['closed'] and
                prepared['owner'] == str(ROOT) and prepared['workflow'] == entry['workflow'] and
                prepared.get('mode', 'native') == entry['mode'] and
                prepared['corpus'] == entry.get('corpus') and
                prepared['target'] == reviewed['target'] == result['target'] and
                reservations[prepared['target']] == archive, 'reviewed cache ownership differs')
        require(child['status'] == 'completed' and child['pid'] == launch['pid'] and
                child['parent_pid'] == status['child_pid'] and
                child['plan_sha256'] == reviewed['plan_sha256'] == sha(work / 'plan.json') and
                all(result[k] == v for k, v in child.items()), 'terminal child receipt differs')
        manifest = prepared['manifest']
        require(result['files'] == child['retired_files'] == reviewed['files'] ==
                sum(len(g['paths']) for g in manifest['groups']) and
                result['unique_payloads'] == reviewed['payloads'] == len(manifest['groups']) and
                result['unique_original_bytes'] == reviewed['unique_bytes'] ==
                sum(g['bytes'] for g in manifest['groups']), 'inventory totals differ')
        require(result['archive'] == str((work / 'cache.zip').relative_to(ROOT)) and
                (work / 'cache.zip').stat().st_size == result['archive_bytes'] and
                not any(Path(prepared['target']).iterdir()), 'archive size or retired target differs')
        require(result['workflow'] == entry['workflow'] and
                all(result[k] == prepared[k] for k in ['verification', 'proofs', 'sources']),
                'verification or external evidence maps differ')
        for path, digest in {**prepared['proofs'], **prepared['sources']}.items():
            require(path not in evidence or evidence[path] == digest, 'conflicting evidence hash')
            evidence[path] = digest
        entries.append(dict(entry, **{k: result[k] for k in ['files', 'unique_original_bytes',
            'archive_bytes', 'archive_sha256', 'free_bytes_before', 'free_bytes_after']}))
    require(all(sha(ROOT / path) == digest for path, digest in evidence.items()), 'external evidence changed')
    return dict(status=('completed and verified' if completed_prefix is None else 'incomplete; completed prefix verified'),
        completed_entries=count, total_entries=len(batch['entries']),
        unapplied_entries=batch['entries'][count:], batch_sha256=review['batch_sha256'],
        controller_sha256=review['controller_sha256'], review_sha256=sha(out / 'inventory-review.json'),
        entries=entries, total_files=sum(e['files'] for e in entries),
        total_unique_original_bytes=sum(e['unique_original_bytes'] for e in entries),
        total_archive_bytes=sum(e['archive_bytes'] for e in entries),
        distinct_evidence_hashes_verified=len(evidence),
        supervisor_status_sha256=sha(experiment / 'status.json'),
        supervisor_log_sha256=status['log_sha256'], assessor_sha256=sha(Path(__file__)),
        note='Each child decoded and hashed every payload before retirement. This assessment checks terminal receipts, exact reviewed inventories, archive sizes and unchanged external evidence. It does not redundantly decode the archives. Free space is a shared-volume observation; no benchmark ran during archival.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', required=True)
    parser.add_argument('--completed-prefix', type=int,
                        help='audit a failed batch prefix only after a pre-application lock rejection')
    args = parser.parse_args()
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        result = assess(args.batch, args.completed_prefix)
        output = ROOT / 'results' / args.batch / ('partial-summary.json' if args.completed_prefix else 'summary.json')
        require(not output.exists(), 'assessment already exists')
        write_json(output, result)
        print(json.dumps({k: result[k] for k in ['status', 'total_files', 'total_unique_original_bytes',
                                                'total_archive_bytes', 'distinct_evidence_hashes_verified']}))


if __name__ == '__main__':
    main()
