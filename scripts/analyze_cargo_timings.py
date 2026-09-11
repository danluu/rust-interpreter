#!/usr/bin/env python3
"""Attribute preserved Cargo timing snapshots from a verified edit workflow."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
from statistics import median

from cargo_timing_data import group_key, timeline, units_from_html
from verify_repeated_workflow import verify, require

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['.', '..'], 'invalid run ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    path = args.report.resolve(strict=True)
    require(path.is_relative_to(ROOT / 'results'), 'report is outside results')
    report = json.loads(path.read_text())
    require(report['project'] in ['pgrust', 'nushell', 'ruff', 'fre'], 'unit reporting is public-project only')
    require(report['cargo_timings'] is True, 'workflow did not capture timing snapshots')
    verified = verify(report)
    require(verified == json.loads(path.with_name('verification.json').read_text()), 'verification differs')
    raw = ROOT / report['raw']
    records = json.loads((raw / 'records.json').read_text())
    parsed = []
    seen = set()
    for row in records:
        timing = row.get('cargo_timings', [])
        require(len(timing) == 1 and len(row['calls']) == 1, 'expected one complete batched timing per command')
        proof = timing[0]
        snapshot = (ROOT / proof['path']).resolve(strict=True)
        require(snapshot.is_relative_to((raw / 'cargo-timings').resolve()) and snapshot not in seen,
                'unexpected or reused timing snapshot')
        seen.add(snapshot)
        payload = snapshot.read_bytes()
        require(len(payload) == proof['bytes'] and hashlib.sha256(payload).hexdigest() == proof['sha256'], 'timing snapshot changed')
        units = units_from_html(payload)
        parsed.append(dict(mode=row['mode'], cycle=row['cycle'], state=row['state'], phase=row['phase'],
            label=row['label'], source_sha256=row['source_sha256'], seconds=row['seconds'], cpu_seconds=row['cpu_seconds'],
            artifact=proof, units=units, timeline=timeline(units)))
    grouped = []
    for mode in ['native', 'baseline', 'candidate']:
        edited = [r for r in parsed if r['mode'] == mode and r['state'] > 0]
        require(bool(edited), 'missing edited commands')
        keys = sorted({group_key(u) for r in edited for u in r['units']})
        for key in keys:
            observations = []
            for row in edited:
                matching = [u for u in row['units'] if group_key(u) == key]
                observations.append(dict(cycle=row['cycle'], state=row['state'],
                    unit_ids=[u['i'] for u in matching], durations=[u['duration'] for u in matching],
                    summed_elapsed_seconds=sum(u['duration'] for u in matching)))
            grouped.append(dict(engine_mode=mode, package=key[0], version=key[1], reported_mode=key[2],
                target_description=key[3], features=list(key[4]), observations=observations,
                median_unit_count=median(len(o['unit_ids']) for o in observations),
                median_summed_elapsed_seconds=median(o['summed_elapsed_seconds'] for o in observations)))
    out = ROOT / 'results' / args.run_id
    out.mkdir(exist_ok=False)
    summary = dict(status='verified timing snapshots parsed', input_report=str(path.relative_to(ROOT)),
        input_sha256=sha(path), input_verification_sha256=sha(path.with_name('verification.json')),
        verification=verified, project=report['project'], workflow=report['workflow'],
        tool_builds=report['tool_builds'], native_control=report['native_control'],
        snapshot_count=len(parsed), rows=parsed, edited_unit_groups=grouped,
        tools={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), ROOT / 'scripts/cargo_timing_data.py', ROOT / 'scripts/verify_repeated_workflow.py']},
        note='Diagnostic instrumentation stays inside the timed commands. Group sums retain every duplicate unit and overlap; missing groups contribute zero. They are not CPU times, total command time or a causal critical path. Cold and wrong-edit captures are preserved separately from edited groups.')
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    lines = ['# Cargo units after real source edits', '',
        f"Parsed {len(parsed)} verified snapshots from `{report['project']}` / `{report['workflow']}`.",
        'Reported durations can overlap. The table preserves all matching units per command;',
        'a row is not a serial contribution or an isolated speedup opportunity.',
        'Cold and wrong-edit captures, features, duplicates and unblocking IDs are in [summary.json](summary.json).', '']
    def escape(text):
        return text.replace('|', '\\|').replace('\n', ' ')
    for mode in ['native', 'baseline', 'candidate']:
        lines += [f'## {mode}', '', '| Package / target | Features | Median units | Median summed elapsed |',
                  '| --- | --- | ---: | ---: |']
        rows = sorted((g for g in grouped if g['engine_mode'] == mode), key=lambda g: -g['median_summed_elapsed_seconds'])
        for group in rows[:25]:
            lines.append(f"| {escape(group['package'] + group['target_description'])} | {escape(', '.join(group['features']))} | {group['median_unit_count']:g} | {group['median_summed_elapsed_seconds']:.3f} s |")
        lines.append('')
    (out / 'assessment.md').write_text('\n'.join(lines))
    print(json.dumps(dict(snapshots=len(parsed), edited_unit_groups=len(grouped))))


if __name__ == '__main__':
    main()
