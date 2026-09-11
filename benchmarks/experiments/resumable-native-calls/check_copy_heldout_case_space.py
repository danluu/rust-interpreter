#!/usr/bin/env python3
"""Qualify the public-case admission inputs without starting a benchmark."""
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import preflight_copy_heldout_case as subject

ROOT = subject.ROOT


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        checked, bound, rejected = {}, {}, 0
        for label in ['ruff', 'nushell']:
            reports, hashes = subject.references(label)
            bound.update(hashes)
            needed = subject.estimate(reports)
            boundary = needed['minimum_free_bytes']
            subject.require(not subject.admit(boundary - 1, needed) and
                            subject.admit(boundary, needed), 'admission boundary differs')
            # A free-space value which pays for all other terms still fails if
            # it omits the running floor that caused the original interruption.
            subject.require(not subject.admit(boundary - 8 * 1024**3, needed),
                            'the original missing-floor failure is accepted')
            if label == 'ruff':
                subject.require(boundary == 17351777078, 'Ruff historical estimate differs')
            checked[label] = needed
            changes = [('status', 'prepared'), ('unique_original_bytes', 0),
                ('unique_original_bytes', -1), ('unique_original_bytes', True),
                ('unique_original_bytes', 1.5), ('preflight_required_bytes', 1),
                ('preflight_required_bytes', True), ('verification.commands', 62),
                ('verification.check_commands', 20), ('verification.edited_pairs', 14),
                ('verification.explicit_controls_verified', False)]
            invalid = []
            for field, value in changes:
                altered = deepcopy(reports)
                target = altered['native']
                parts = field.split('.')
                for part in parts[:-1]:
                    target = target[part]
                target[parts[-1]] = value
                invalid.append(altered)
            altered = deepcopy(reports)
            del altered['candidate']
            invalid.append(altered)
            for altered in invalid:
                try:
                    subject.estimate(altered)
                except (ValueError, RuntimeError):
                    rejected += 1
                else:
                    raise RuntimeError('incomplete or invalid cache reference accepted')
        try:
            subject.references('rg-aot')
        except (ValueError, RuntimeError):
            rejected += 1
        else:
            raise RuntimeError('unbound private cache accepted as a public reference')
        sources = [Path(__file__), Path(subject.__file__), ROOT / 'scripts/workflow_space.py']
        result = dict(status='passed', estimates=checked, invalid_references_rejected=rejected,
            exact_boundaries_checked=True, missing_running_floor_rejected=True,
            benchmark_started=False, cache_files_modified=False, references=bound,
            sources={str(path.relative_to(ROOT)): subject.sha(path) for path in sources})
        out = ROOT / 'results/copy-heldout-case-space-01'
        out.mkdir(exist_ok=False)
        subject.write_json(out / 'summary.json', result)
        (out / 'assessment.md').write_text(
            f'The Ruff and Nushell admission estimates verify eight bound full-cache inventories, '
            f'reject {rejected} invalid references, and preserve the exact admission boundary and '
            '8 GiB running reserve. No benchmark or cache modification was performed.\n')
        print(json.dumps(dict(status=result['status'], rejected=rejected, estimates=checked)))


if __name__ == '__main__':
    main()
