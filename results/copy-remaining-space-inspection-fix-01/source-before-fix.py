#!/usr/bin/env python3
"""Read only the four remaining cases' completed historical cache metadata."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from reclaim_workflow_objects import sha
from verify_repeated_workflow import require, verify
from workflow_io import write_json
from workflow_space import required_bytes


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        recovery_path = 'results/resumable-bulk-heldout-recovery-01/summary.json'
        require(sha(ROOT / recovery_path) == 'b7a4c639c0b6c9600d368e0072e41301257c46fb0d2b72f708e5a3a2d24ed245',
                'completed historical recovery evidence changed')
        recovery = json.loads((ROOT / recovery_path).read_text())
        rows, bound = [], {recovery_path: sha(ROOT / recovery_path)}
        for label in ['forward-anchored-tls', 'pgrust-sha1-inline8', 'pgrust', 'rg-aot']:
            row = next(row for row in recovery['workflows'] if row['workflow'] == label)
            path = ROOT / row['report']
            require(sha(path) == row['report_sha256'], 'historical workflow changed')
            report = json.loads(path.read_text())
            checked = verify(report)
            require(checked['commands'] == 63 and checked['check_commands'] == 21 and
                    checked['exact_artifact_hashes_verified'] == 42, 'incomplete historical workflow')
            raw = ROOT / report['raw']
            records = json.loads((raw / 'records.json').read_text())
            targets = {'native': raw / 'native', 'check': raw / 'check'}
            for mode in ['baseline', 'candidate']:
                artifacts = [Path(record['calls'][0]['launch']['artifact_path'])
                             for record in records if record['mode'] == mode]
                roots = {next(p for p in artifact.parents if p.name == 'target') for artifact in artifacts}
                require(len(roots) == 1, 'historical custom cache changes within the workflow')
                target = roots.pop()
                require(target.is_relative_to(ROOT / '.work/interpreter-workspaces'), 'unexpected custom cache')
                targets[mode] = target
            require(len(set(targets.values())) == 4, 'reference cache targets overlap')
            totals = {}
            for mode, target in targets.items():
                require(target.resolve() == target and target.is_dir(), 'noncanonical or absent reference cache')
                groups, names, objects = {}, [], 0
                for folder, dirs, files in os.walk(target, followlinks=False):
                    for name in dirs + files:
                        item = Path(folder) / name
                        info = item.lstat()
                        require(not stat.S_ISLNK(info.st_mode), 'reference metadata contains a symlink')
                        if stat.S_ISREG(info.st_mode):
                            groups[(info.st_dev, info.st_ino)] = info.st_size
                            names.append((str(item.relative_to(target)), info.st_size, info.st_mtime_ns))
                            objects += int(name.endswith('.o'))
                        else:
                            require(stat.S_ISDIR(info.st_mode), 'reference cache contains a special file')
                require(names and objects, 'reference was archived or object-reclaimed; inspect separately')
                totals[mode] = dict(unique_bytes=sum(groups.values()), files=len(names), objects=objects,
                    metadata_sha256=hashlib.sha256(json.dumps(sorted(names)).encode()).hexdigest())
            total = sum(value['unique_bytes'] for value in totals.values())
            require(total <= 4 * 1024**3 and totals['check']['unique_bytes'] <= 512 * 1024**2,
                    'remaining history exceeds the proposed conservative cache reserve')
            rows.append(dict(case=label, historical_caches=totals, historical_total_bytes=total))
            bound[row['report']] = row['report_sha256']
            for name in ['records.json', 'check-records.json', 'source-transitions.json']:
                bound[str((raw / name).relative_to(ROOT))] = sha(raw / name)
        # Deliberately use a larger common reserve than any observed case.
        estimate = required_bytes(cache_bytes=4 * 1024**3, growth_percent=20,
            command_floor_bytes=8 * 1024**3, archive_reserve_bytes=2 * 1024**3,
            evidence_reserve_bytes=256 * 1024**2)
        result = dict(status='completed read-only inventory', cases=rows, estimate=estimate,
            references=bound, source_sha256=sha(Path(__file__)), cache_files_modified=False,
            note='Only aggregate cache sizes and metadata digests are published, including for rg-aot. No private cache is archived. Before each future case, require this full reserve from fresh available-space data; do not lower it to fit.')
        out = ROOT / 'results/copy-remaining-space-inventory-01'
        out.mkdir(exist_ok=False)
        write_json(out / 'summary.json', result)
        (out / 'assessment.md').write_text(
            'Four completed histories and sixteen exact caches were inspected read-only. '
            'Each total is below the conservative 4 GiB cache budget, and each check cache '
            'is below 512 MiB. With 20% growth, an 8 GiB running floor, 2 GiB archive reserve '
            'and 256 MiB evidence, each next admission requires 15.05 GiB. '
            'Only aggregates are published; no cache was modified.\n')
        print(json.dumps(dict(cases=[dict(case=row['case'], bytes=row['historical_total_bytes']) for row in rows],
                              minimum_free_bytes=estimate['minimum_free_bytes'])))


if __name__ == '__main__':
    main()
