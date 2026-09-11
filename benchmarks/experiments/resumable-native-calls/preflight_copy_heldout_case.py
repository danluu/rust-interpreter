#!/usr/bin/env python3
"""Admit the two remaining large public cases using completed cache inventories."""
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

PLAN = 'benchmarks/experiments/resumable-native-calls/COPY-HELDOUTS.json'
PLAN_SHA = 'b12c33cc81f00558aebb03e104a9cb901fdb272417bf70b0124f2c13ec4a2e11'
REFERENCES = {
    'ruff': [
        '85c6e6ce74183bb56f3466c4f2c17d00d8642e2eec31d26f2310e917430bbd3a',
        'de9f55f5f467136ee17fb1a615a1c270269f471aaf607d0b3c6c375949f31faf',
        'd46ab3f1a3b2a74e8ab4cedda611f6689f99e11b136ceb1095cb40ad42647af5',
        '0348bdf1c9d342b6affa1b571afdc3654627a8bf3654bca264784d1b3036fcaf'],
    'nushell': [
        '004272445c8abcdd0164ff2f7154fa23d0ca0341ad4752deead723c7a0dcc8fe',
        '40a08aea847aa66f35077d51570140e70fd1c8550cebc64e37404fdf2bda9284',
        '8699f77df2e3a09c435fb376e5b30fece630c89cff340a213daa6d60f2385cd7',
        '996c7abfc006a91e1f6831c9ed6cf420743dee5e98f6a80308aefaa6ed034844'],
}


def estimate(reports):
    require(set(reports) == {'check', 'baseline', 'candidate', 'native'},
            'four completed cache inventories required')
    for report in reports.values():
        require(report['status'] == 'completed' and
                type(report['unique_original_bytes']) is int and report['unique_original_bytes'] > 0 and
                type(report['preflight_required_bytes']) is int and
                report['preflight_required_bytes'] > report['unique_original_bytes'] and
                report['verification']['commands'] == 63 and
                report['verification']['check_commands'] == 21 and
                report['verification']['edited_pairs'] == 15 and
                report['verification']['explicit_controls_verified'] is True,
                'reference is not a complete controlled cache history')
    return required_bytes(cache_bytes=sum(r['unique_original_bytes'] for r in reports.values()),
        growth_percent=20, command_floor_bytes=8 * 1024**3,
        archive_reserve_bytes=reports['check']['preflight_required_bytes'],
        evidence_reserve_bytes=256 * 1024**2)


def references(label):
    require(label in REFERENCES, 'case lacks bound full-cache reference inventories')
    reports, bound = {}, {}
    for mode, digest in zip(['check', 'baseline', 'candidate', 'native'], REFERENCES[label]):
        path = f'results/resumable-bulk-heldout-01-{label}-{mode}-archive-01/summary.json'
        require(sha(ROOT / path) == digest, 'reference archive receipt changed')
        report = json.loads((ROOT / path).read_text())
        plan_path = ROOT / report['plan']
        require(sha(plan_path) == report['plan_sha256'], 'reference inventory changed')
        inventory = json.loads(plan_path.read_text())
        require(inventory['owner'] == str(ROOT) and
                inventory['workflow'] == f'resumable-bulk-heldout-01-{label}' and
                inventory['mode'] == mode and report['workflow'] == inventory['workflow'],
                'reference case or mode differs')
        groups = inventory['manifest']['groups']
        require(sum(group['bytes'] for group in groups) == report['unique_original_bytes'],
                'reference inventory byte count differs')
        # These selected histories were archived with their objects intact.
        # Do not substitute the earlier object-reclaimed native controls.
        require(any(name.endswith('.o') for group in groups for name in group['paths']),
                'reference inventory has no retained object files')
        reports[mode] = report
        bound[path], bound[report['plan']] = digest, report['plan_sha256']
    return reports, bound


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=REFERENCES, required=True)
    args = parser.parse_args()
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(sha(ROOT / PLAN) == PLAN_SHA, 'original plan changed')
        plan = json.loads((ROOT / PLAN).read_text())
        case = next(case for case in plan['cases'] if case['label'] == args.case)
        out = ROOT / 'results' / (case['run_id'] + '-preflight')
        require(not out.exists(), 'admission receipt already exists')
        require(not (ROOT / '.work/corpus-runs' / case['run_id']).exists() and
                not (ROOT / '.work/experiments' / case['run_id']).exists(), 'history already started')
        reports, bound = references(args.case)
        bound.update({PLAN: PLAN_SHA, **plan['frozen'], **plan['evaluation_sources'], **plan['prerequisites']})
        require(all(sha(ROOT / path) == digest for path, digest in bound.items()), 'bound input changed')
        needed = estimate(reports)
        fs = os.statvfs(ROOT)
        free = fs.f_bavail * fs.f_frsize
        passed = admit(free, needed)
        result = dict(owner=str(ROOT), checked_at=time.time(), case=args.case, run_id=case['run_id'],
            status='space admission passed' if passed else 'space admission rejected; no benchmark started',
            passed=passed, observed_free_bytes=free, estimate=needed,
            historical_cache_bytes={mode: report['unique_original_bytes'] for mode, report in reports.items()},
            cache_growth_allowance_percent=20, benchmark_started=False, compiler_caches_modified=False,
            references=bound, sources={str(path.relative_to(ROOT)): sha(path)
                for path in [Path(__file__), ROOT / 'scripts/workflow_space.py']},
            note='Includes full historical caches, 20% growth, the 8 GiB running floor, first check-cache archive reserve and 256 MiB evidence. Shared-volume writes can still consume headroom.')
        out.mkdir()
        write_json(out / 'summary.json', result)
        (out / 'assessment.md').write_text(
            f"{args.case} admission **{'passes' if passed else 'is rejected'}**: "
            f"{free / 1024**3:.2f} GiB available, {needed['minimum_free_bytes'] / 1024**3:.2f} GiB required. "
            'No benchmark or cache operation is started by this check.\n')
        print(json.dumps({key: result[key] for key in ['case', 'passed', 'observed_free_bytes', 'estimate']}))
        return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
