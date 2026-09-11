#!/usr/bin/env python3
"""Check six-history lower bounds without producing any benchmark samples."""
import argparse
import fcntl
from fractions import Fraction as F
from itertools import product
import json
from pathlib import Path
from statistics import median
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_repeated_workflow import require
from workflow_io import write_json
from assess_worker_cold import median_lower_bound
from assess_worker_warm import sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['.', '..'], 'invalid run ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        cases = [
            ([F(13, 10)] * 3, F(13, 20)),
            ([F(13, 10)] * 4, F(13, 10)),
            ([F(1), F(6, 5), F(13, 10), F(7, 5)], F(11, 10)),
            ([F(3, 5)] * 4, F(3, 5)),
            ([F(1), F(2), F(3), F(4), F(5), F(6)], F(7, 2)),
            ([F(100)], F(0)),
        ]
        checks = 0
        grid = [F(1, 100), F(1, 2), F(9, 10), F(1), F(11, 10), F(2), F(1000)]
        for known, expected in cases:
            bound = median_lower_bound(known)
            require(bound == expected, 'lower-bound example differs')
            for unknown in product(grid, repeat=6 - len(known)):
                require(median([*known, *unknown]) >= bound, 'a completion violated the lower bound')
                checks += 1
        require(median_lower_bound(cases[2][0]) == F(11, 10), 'CPU threshold boundary changed')
        require(not median_lower_bound(cases[2][0]) > F(11, 10), 'equality incorrectly rejects the CPU guard')
        rejected = 0
        for known in [[], [F(1)] * 7, [F(0)], [F(-1)], [1.0], [True]]:
            try:
                median_lower_bound(known)
            except RuntimeError:
                rejected += 1
            else:
                raise RuntimeError('invalid ratio collection accepted')
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write_json(out / 'summary.json', dict(status='passed', exact_examples=len(cases),
            enumerated_completions=checks, invalid_collections_rejected=rejected,
            source_sha256={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__),
                Path(__file__).with_name('assess_worker_cold.py')]},
            note='Synthetic arithmetic checks only. No missing timings are filled in and no project benchmark ran. Complete cold receipts must still qualify the assessor on actual histories.'))
        print(json.dumps(dict(status='passed', exact_examples=len(cases), enumerated_completions=checks,
                              invalid_collections_rejected=rejected)))


if __name__ == '__main__':
    main()
