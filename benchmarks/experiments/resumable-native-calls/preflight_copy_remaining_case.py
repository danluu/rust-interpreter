#!/usr/bin/env python3
"""Use the fixed conservative reserve for the four remaining small cases."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from reclaim_workflow_objects import sha
from verify_repeated_workflow import require
from workflow_io import write_json
from workflow_space import required_bytes, admit

INVENTORY = 'results/copy-remaining-space-inventory-01/summary.json'
INVENTORY_SHA = 'aa88efa388c3065a16b5db3e7b8e0553f3b4d7f315d60783955bdb0103070707'
PLAN = 'benchmarks/experiments/resumable-native-calls/COPY-HELDOUTS.json'
PLAN_SHA = 'b12c33cc81f00558aebb03e104a9cb901fdb272417bf70b0124f2c13ec4a2e11'
CASES = ['forward-anchored-tls', 'pgrust-sha1-inline8', 'pgrust', 'rg-aot']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=CASES, required=True)
    args = parser.parse_args()
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(sha(ROOT / INVENTORY) == INVENTORY_SHA and sha(ROOT / PLAN) == PLAN_SHA,
                'inventory or fixed benchmark plan changed')
        inventory = json.loads((ROOT / INVENTORY).read_text())
        plan = json.loads((ROOT / PLAN).read_text())
        require([case['case'] for case in inventory['cases']] == CASES and
                inventory['cache_files_modified'] is False and
                all(case['historical_total_bytes'] <= 4 * 1024**3 for case in inventory['cases']),
                'completed inventory scope differs')
        case = next(case for case in plan['cases'] if case['label'] == args.case)
        run = case['run_id']
        require(not (ROOT / '.work/experiments' / run).exists() and
                not (ROOT / '.work/corpus-runs' / run).exists(), 'history already started')
        out = ROOT / 'results' / (run + '-preflight')
        require(not out.exists(), 'admission receipt already exists')
        bound = {INVENTORY: INVENTORY_SHA, PLAN: PLAN_SHA, **inventory['references'],
                 **plan['frozen'], **plan['evaluation_sources'], **plan['prerequisites']}
        require(all(sha(ROOT / path) == digest for path, digest in bound.items()), 'bound evidence changed')
        estimate = required_bytes(cache_bytes=4 * 1024**3, growth_percent=20,
            command_floor_bytes=8 * 1024**3, archive_reserve_bytes=2 * 1024**3,
            evidence_reserve_bytes=256 * 1024**2)
        require(estimate == inventory['estimate'], 'fixed space reserve changed')
        fs = os.statvfs(ROOT)
        free = fs.f_bavail * fs.f_frsize
        passed = admit(free, estimate)
        result = dict(owner=str(ROOT), run_id=run, case=args.case, checked_at=time.time(),
            status='space admission passed' if passed else 'space admission rejected; no benchmark started',
            passed=passed, observed_free_bytes=free, estimate=estimate, references=bound,
            sources={str(path.relative_to(ROOT)): sha(path)
                for path in [Path(__file__), ROOT / 'scripts/workflow_space.py']},
            benchmark_started=False, cache_files_modified=False,
            note='The same 15.05 GiB reserve applies to each fresh remaining history. Private caches are not modified. Shared-volume writes remain outside this admission estimate.')
        out.mkdir()
        write_json(out / 'summary.json', result)
        (out / 'assessment.md').write_text(
            f"{args.case} admission **{'passes' if passed else 'is rejected'}**: "
            f"{free / 1024**3:.2f} GiB available against {estimate['minimum_free_bytes'] / 1024**3:.2f} GiB required. "
            'No benchmark or cache modification starts in this helper.\n')
        print(json.dumps({key: result[key] for key in ['case', 'passed', 'observed_free_bytes', 'estimate']}))
        return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
