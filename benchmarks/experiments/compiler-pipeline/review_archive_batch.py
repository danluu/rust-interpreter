#!/usr/bin/env python3
"""Record exact prepared inventories for review, without applying any archive."""
import argparse
import fcntl
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import archive_workflow_cache as coordinator
from reclaim_workflow_objects import identifier, no_open_files, sha
from verify_repeated_workflow import require
from workflow_io import write_json


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', required=True)
    args = parser.parse_args()
    name = identifier(args.batch)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = ROOT / '.work/cache-batches' / (name + '.json')
        batch, digest = read(path), sha(path)
        require(batch['owner'] == str(ROOT) and batch['schema_version'] == 1 and
                1 <= len(batch['entries']) <= 32, 'batch identity or size differs')
        experiment = ROOT / '.work/experiments' / (name + '-prepare')
        status, launch = read(experiment / 'status.json'), read(experiment / 'plan.json')
        expected = ['benchmarks/experiments/compiler-pipeline/archive_batch.py', '--plan', str(path),
                    '--plan-sha256', digest, '--action', 'prepare']
        require(status['status'] == 'finished' and status['returncode'] == 0 and
                status['owner'] == status['cwd'] == launch['owner'] == str(ROOT) and
                status['command'] == launch['command'] and status['command'][1:] == expected and
                status['plan_sha256'] == sha(experiment / 'plan.json') and
                status['log_sha256'] == sha(experiment / 'command.log'), 'preparation did not finish with this exact plan')
        objects = [json.loads(line) for line in (experiment / 'command.log').read_text().splitlines()
                   if line.startswith('{')]
        require(objects[-1] == dict(status='completed', action='prepare', targets=len(batch['entries']),
                                    plan_sha256=digest), 'preparation completion ledger differs')
        entries, evidence = [], {}
        for entry in batch['entries']:
            archive = identifier(entry['archive'])
            work, prepared, state = coordinator.load(archive)
            require(state['status'] == 'prepared' and prepared['workflow'] == entry['workflow'] and
                    prepared.get('mode', 'native') == entry['mode'] and
                    prepared.get('proof_kind', 'workflow') == entry.get('proof_kind', 'workflow') and
                    prepared['corpus'] == entry.get('corpus') and
                    prepared['sources'] == coordinator.sources(), 'prepared selection or source changed')
            target = coordinator.check_evidence(prepared)
            manifest = prepared['manifest']
            coordinator.archive.unchanged(target, manifest)
            no_open_files(target)
            for source, expected_hash in {**prepared['proofs'], **prepared['sources']}.items():
                require(source not in evidence or evidence[source] == expected_hash, 'conflicting evidence hash')
                evidence[source] = expected_hash
            entries.append(dict(entry, target=str(target), plan_sha256=sha(work / 'plan.json'), closed=True,
                files=sum(len(group['paths']) for group in manifest['groups']), payloads=len(manifest['groups']),
                unique_bytes=sum(group['bytes'] for group in manifest['groups']),
                directories=len(manifest['directories']), root_xattrs=manifest.get('root_xattrs', {}),
                directory_xattrs=manifest.get('directory_xattrs', {})))
        require(len({e['target'] for e in entries}) == len(entries) and
                all(sha(ROOT / source) == digest for source, digest in evidence.items()), 'duplicate target or changed evidence')
        out = ROOT / 'results' / name
        out.mkdir(exist_ok=True)
        target = out / 'inventory-review.json'
        require(not target.exists(), 'inventory review already exists')
        result = dict(status='reviewed; unapplied', reviewed_at=time.time(), batch_plan=str(path.relative_to(ROOT)),
            batch_sha256=digest, controller_sha256=sha(Path(__file__).with_name('archive_batch.py')),
            reviewer_sha256=sha(Path(__file__)), prepare_status_sha256=sha(experiment / 'status.json'),
            entries=entries, files=sum(e['files'] for e in entries),
            unique_bytes=sum(e['unique_bytes'] for e in entries), distinct_evidence_hashes=len(evidence),
            note='Prepared ownership, source evidence, inventories and closed-file checks only. No archive is applied by this reviewer.')
        write_json(target, result)
        print(json.dumps({key: result[key] for key in ['status', 'files', 'unique_bytes', 'distinct_evidence_hashes']}))


if __name__ == '__main__':
    main()
