#!/usr/bin/env python3
"""Check current headroom against the corrected, bound Nushell estimate."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from reclaim_workflow_objects import identifier, sha
from verify_repeated_workflow import require
from workflow_io import write_json
from workflow_space import required_bytes, admit

PLAN = 'benchmarks/experiments/resumable-native-calls/COPY-HELDOUTS.json'
PLAN_SHA = 'b12c33cc81f00558aebb03e104a9cb901fdb272417bf70b0124f2c13ec4a2e11'
REFERENCE = 'results/resumable-copy-heldout-01-case-01-preflight/summary.json'
REFERENCE_SHA = 'acbfdd5dd8e7367e451bc5e6232f60f53f8006c246682c84e4e33df979e6dff2'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    identifier(args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        out = ROOT / 'results' / args.run_id
        require(not out.exists(), 'space receipt already exists')
        require(sha(ROOT / PLAN) == PLAN_SHA and sha(ROOT / REFERENCE) == REFERENCE_SHA,
                'historical plan or reference estimate changed')
        plan = json.loads((ROOT / PLAN).read_text())
        reference = json.loads((ROOT / REFERENCE).read_text())
        require(plan['owner'] == str(ROOT) and plan['options']['minimum_free_gib'] == 8 and
                reference['owner'] == str(ROOT) and reference['plan_sha256'] == PLAN_SHA,
                'expected owned plan and unchanged 8 GiB floor')
        bound = {PLAN: PLAN_SHA, REFERENCE: REFERENCE_SHA, **reference['references'],
                 **plan['frozen'], **plan['evaluation_sources'], **plan['prerequisites']}
        require(all(sha(ROOT / path) == digest for path, digest in bound.items()),
                'bound reference or measured input changed')
        cache_bytes = reference['historical_unique_native_before_object_reclaim_bytes'] + sum(
            reference['historical_other_cache_bytes'].values())
        require(cache_bytes == reference['historical_total_bytes'], 'historical cache arithmetic differs')
        estimate = required_bytes(cache_bytes=cache_bytes,
            growth_percent=reference['cache_growth_allowance_percent'], command_floor_bytes=8 * 1024**3,
            archive_reserve_bytes=reference['first_check_archive_reserve_bytes'],
            evidence_reserve_bytes=reference['metadata_and_evidence_allowance_bytes'])
        fs = os.statvfs(ROOT)
        free = fs.f_bavail * fs.f_frsize
        passed = admit(free, estimate)
        result = dict(owner=str(ROOT), checked_at=time.time(), run_id=args.run_id,
            status='space admission passed' if passed else 'space admission rejected; no benchmark started',
            case='nushell-type-relations', estimate=estimate, observed_free_bytes=free,
            additional_bytes_required=max(0, estimate['minimum_free_bytes'] - free), passed=passed,
            benchmark_started=False, compiler_caches_modified=False, references=bound,
            sources={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in [Path(__file__), ROOT / 'scripts/workflow_space.py']},
            note='Admission is an estimate, not protection against unrelated shared-volume writes. A retry amendment and unchanged correctness/performance gates are still required.')
        out.mkdir()
        write_json(out / 'summary.json', result)
        (out / 'assessment.md').write_text(
            f"Nushell retry space admission: **{'pass' if passed else 'rejected'}**. "
            f"{free / 1024**3:.2f} GiB is available; the bound estimate requires "
            f"{estimate['minimum_free_bytes'] / 1024**3:.2f} GiB. "
            'No benchmark or cache cleanup was started by this check.\n')
        print(json.dumps({key: result[key] for key in
                         ['status', 'observed_free_bytes', 'additional_bytes_required', 'passed']}))
        return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
