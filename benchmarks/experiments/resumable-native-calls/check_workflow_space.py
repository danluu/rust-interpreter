#!/usr/bin/env python3
"""Reproduce and reject the observed missing-floor admission error."""
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from workflow_space import required_bytes, admit
from verify_repeated_workflow import require
from workflow_io import write_json


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        old_path = ROOT / 'results/resumable-copy-heldout-01-case-01-preflight/summary.json'
        old = json.loads(old_path.read_text())
        args = dict(cache_bytes=old['historical_total_bytes'],
            growth_percent=old['cache_growth_allowance_percent'], command_floor_bytes=8 * 1024**3,
            archive_reserve_bytes=old['first_check_archive_reserve_bytes'],
            evidence_reserve_bytes=old['metadata_and_evidence_allowance_bytes'])
        corrected = required_bytes(**args)
        require(old['passed'] and old['observed_free_bytes'] >= old['minimum_free_bytes'],
                'original admission evidence differs')
        require(not admit(old['observed_free_bytes'], corrected),
                'historical unsafe admission was accepted')
        require(corrected['minimum_free_bytes'] == old['minimum_free_bytes'] + 8 * 1024**3,
                'running floor was not reserved in addition to existing reserves')
        boundary = corrected['minimum_free_bytes']
        require(not admit(boundary - 1, corrected) and admit(boundary, corrected),
                'incorrect admission boundary')
        rejected = 0
        for field in args:
            for value in [-1, True, 1.5, '1', None]:
                altered = copy.deepcopy(args)
                altered[field] = value
                try:
                    required_bytes(**altered)
                except ValueError:
                    rejected += 1
                else:
                    raise RuntimeError('invalid estimate was accepted')
        for field in ['cache_bytes', 'command_floor_bytes']:
            altered = dict(args, **{field: 0})
            try:
                required_bytes(**altered)
            except ValueError:
                rejected += 1
            else:
                raise RuntimeError('absent estimate or running floor was accepted')
        for value in [-1, True, 1.5, '1', None]:
            try:
                admit(value, corrected)
            except ValueError:
                rejected += 1
            else:
                raise RuntimeError('invalid available space was accepted')
        sources = [Path(__file__), ROOT / 'scripts/workflow_space.py', old_path]
        result = dict(status='passed', historical_admission_now_rejected=True,
            historical_free_bytes=old['observed_free_bytes'], corrected_estimate=corrected,
            exact_boundary_checked=True, invalid_values_rejected=rejected,
            sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
        out = ROOT / 'results/workflow-space-floor-01'
        out.mkdir(exist_ok=False)
        write_json(out / 'summary.json', result)
        (out / 'assessment.md').write_text(
            '# Fresh-history space estimate includes the running floor\n\n'
            'The original Nushell admission at 18.20 GiB is now rejected. Keeping its '
            'historical cache sizes, 20% growth allowance, archive reserve and evidence reserve '
            'requires 25.99 GiB after adding the missing 8 GiB running floor. '
            'The exact admission boundary and 32 invalid inputs pass their checks.\n\n'
            'This helper does not change benchmark controls or historical evidence. '
            'It is an estimate; unrelated shared-volume writes can still exhaust headroom.\n')
        print(json.dumps(result))


if __name__ == '__main__':
    main()
