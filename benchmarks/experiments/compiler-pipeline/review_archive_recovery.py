#!/usr/bin/env python3
"""Review only a verified, untouched suffix of a failed archive batch."""
import argparse
import fcntl
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from assess_archive_batch import assess, read, sha
from reclaim_workflow_objects import identifier
from verify_repeated_workflow import require
from workflow_io import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', required=True)
    parser.add_argument('--from-batch', required=True)
    parser.add_argument('--completed-prefix', type=int, required=True)
    args = parser.parse_args()
    name, original = identifier(args.batch), identifier(args.from_batch)
    require(name != original, 'recovery needs a new batch identity')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        out = ROOT / 'results' / name
        batch_path = ROOT / '.work/cache-batches' / (name + '.json')
        require(not out.exists() and not batch_path.exists(), 'recovery review already exists')
        checked = assess(original, args.completed_prefix)
        partial_path = ROOT / 'results' / original / 'partial-summary.json'
        require(checked == read(partial_path), 'stored failed-prefix assessment differs')
        prior = read(ROOT / 'results' / original / 'inventory-review.json')
        entries = checked['unapplied_entries']
        reviewed = prior['entries'][args.completed_prefix:]
        require(checked['status'] == 'incomplete; completed prefix verified' and entries and
                checked['remaining_original_inventories_verified'] == len(entries) == len(reviewed) and
                all(all(item[key] == value for key, value in entry.items())
                    for entry, item in zip(entries, reviewed)), 'recovery is not the unchanged reviewed suffix')
        batch = dict(owner=str(ROOT), schema_version=1, entries=entries)
        write_json(batch_path, batch)
        out.mkdir()
        result = dict(status='reviewed untouched remainder; unapplied', reviewed_at=time.time(),
            batch_plan=str(batch_path.relative_to(ROOT)), batch_sha256=sha(batch_path),
            controller_sha256=prior['controller_sha256'], reviewer_sha256=sha(Path(__file__)),
            entries=reviewed, files=sum(e['files'] for e in reviewed),
            unique_bytes=sum(e['unique_bytes'] for e in reviewed),
            original_batch=original, original_batch_sha256=prior['batch_sha256'],
            verified_prefix_sha256=sha(partial_path),
            verified_prefix_assessor_sha256=checked['assessor_sha256'],
            failed_supervisor_status_sha256=checked['supervisor_status_sha256'],
            preapplication_rejection=checked['preapplication_rejection'],
            note='The qualified prefix assessor rechecked every remaining original inventory, external evidence and closed-file state. Only the untouched suffix is scheduled; the original failed batch remains incomplete. No archive application here.')
        write_json(out / 'inventory-review.json', result)
        print(json.dumps(dict(batch=name, entries=len(entries), files=result['files'],
                              unique_bytes=result['unique_bytes'], batch_sha256=result['batch_sha256'])))


if __name__ == '__main__':
    main()
