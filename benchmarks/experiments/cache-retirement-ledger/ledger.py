#!/usr/bin/env python3
"""Reconcile explicit completed cleanup receipts; never inspect or delete caches."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_path(value, prefix):
    if not isinstance(value, str):
        raise ValueError('noncanonical receipt path')
    path = Path(value)
    if (path.is_absolute()
            or '..' in path.parts or str(path) != value
            or path.parts[:len(prefix)] != prefix):
        raise ValueError('noncanonical receipt path')
    return path


def nonnegative(value):
    if type(value) is not int or value < 0:
        raise ValueError('invalid cleanup count')
    return value


def reconcile(root, summaries):
    """An historical inventory, not evidence that any remaining file is removable."""
    root = root.resolve(strict=True)
    seen = set()
    receipts, cache_roots = [], {}
    for supplied in summaries:
        summary_path = root / relative_path(supplied, ('results',))
        if summary_path in seen:
            raise ValueError('duplicate cleanup receipt')
        seen.add(summary_path)
        result = json.loads(summary_path.read_text())
        if result['status'] != 'passed' or result['all_protected_hashes_unchanged'] is not True:
            raise ValueError('cleanup did not complete with preserved evidence')
        raw = root / relative_path(result['raw'], ('.work',))
        plan_path = raw / 'plan.json'
        if sha(plan_path) != result['plan_sha256']:
            raise ValueError('cleanup plan hash mismatch')
        plan = json.loads(plan_path.read_text())
        if plan['owner'] != str(root):
            raise ValueError('cleanup owner mismatch')
        files, size = nonnegative(result['files_removed']), nonnegative(result['logical_bytes_removed'])
        plan_files, plan_size, local = 0, 0, set()
        for row in plan['roots']:
            path = str(relative_path(row['path'], ('.work',)))
            if path in local:
                raise ValueError('duplicate root in cleanup plan')
            local.add(path)
            count, logical = nonnegative(row['files']), nonnegative(row['logical_bytes'])
            # Removing empty files is valid; bytes without files are not.
            if count == 0 and logical != 0:
                raise ValueError('bytes claimed without removed files')
            plan_files += count
            plan_size += logical
            item = cache_roots.setdefault(path, dict(path=path, removal_receipts=[], empty_rechecks=[]))
            item['removal_receipts' if count else 'empty_rechecks'].append(supplied)
        if (plan_files != files or plan_size != size
                or nonnegative(plan['files']) != files or nonnegative(plan['logical_bytes']) != size):
            raise ValueError('cleanup totals do not reconcile')
        receipts.append(dict(summary=supplied, summary_sha256=sha(summary_path),
            plan_sha256=result['plan_sha256'], files_removed=files, logical_bytes_removed=size))
    roots = sorted(cache_roots.values(), key=lambda row: row['path'])
    return dict(schema='completed-cache-retirement-ledger-v1', receipts=receipts, roots=roots,
        unique_roots=len(roots), roots_with_recorded_removals=sum(bool(r['removal_receipts']) for r in roots),
        empty_rechecks=sum(len(r['empty_rechecks']) for r in roots), cache_files_inspected=0,
        files_deleted=0, guest_commands=0,
        scope='Explicit successful historical cleanup receipts only. Logical byte counts are not physical reclamation. '
              'A listed root has prior cleanup evidence; an absent root is unknown, never automatically eligible. '
              'Current processes, source ownership, cache contents and deletion eligibility are not evaluated.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary', nargs='+', help='explicit repository-relative summary.json paths')
    args = parser.parse_args()
    print(json.dumps(reconcile(ROOT, args.summary), indent=2))


if __name__ == '__main__':
    main()
