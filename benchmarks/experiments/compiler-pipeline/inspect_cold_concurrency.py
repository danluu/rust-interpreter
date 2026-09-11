#!/usr/bin/env python3
"""Read preserved compiler timelines; no builds, guest execution or cache writes."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from cargo_timing_data import timeline, units_from_html
from reclaim_workflow_objects import identifier
from verify_repeated_workflow import require


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def occupancy(units):
    events = defaultdict(int)
    summed = Decimal(0)
    for unit in units:
        start, duration = Decimal(str(unit['start'])), Decimal(str(unit['duration']))
        if duration:
            events[start] += 1
            events[start + duration] -= 1
            summed += duration
    require(bool(events), 'no positive-duration intervals')
    active, previous = 0, min(events)
    histogram = defaultdict(Decimal)
    for when, delta in sorted(events.items()):
        histogram[active] += when - previous
        active += delta
        require(active >= 0, 'negative interval overlap')
        previous = when
    require(active == 0 and sum(k * v for k, v in histogram.items()) == summed,
            'overlap accounting differs from reported durations')
    require(sum(histogram.values()) == max(events) - min(events), 'interval span differs')
    return {str(k): float(v) for k, v in sorted(histogram.items()) if v}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    out = ROOT / 'results' / identifier(args.run_id)
    require(not out.exists(), 'inspection already exists')
    path = ROOT / 'results/interface-nushell-unit-analysis-01/summary.json'
    analysis = json.loads(path.read_text())
    workflow = ROOT / analysis['input_report']
    require(sha(workflow) == analysis['input_sha256'] and
            sha(workflow.with_name('verification.json')) == analysis['input_verification_sha256'],
            'original workflow evidence changed')
    summary = json.loads(workflow.read_text())
    rows = []
    for row in analysis['rows']:
        artifact = row['artifact']
        snapshot = ROOT / artifact['path']
        payload = snapshot.read_bytes()
        require(len(payload) == artifact['bytes'] and sha(snapshot) == artifact['sha256'], 'timing snapshot changed')
        units = units_from_html(payload)
        require(units == row['units'] and timeline(units) == row['timeline'], 'preserved parse differs')
        histogram = occupancy(units)
        span = sum(histogram.values())
        rows.append(dict(mode=row['mode'], phase=row['phase'], artifact=artifact,
            wall_seconds=row['seconds'], child_cpu_seconds=row['cpu_seconds'],
            child_cpu_per_wall_second=row['cpu_seconds'] / row['seconds'],
            configured_jobs=summary['native_control']['jobs'] if row['mode'] == 'native' else summary['build_jobs'],
            unit_count=len(units), maximum_reported_overlap=row['timeline']['maximum_reported_overlap'],
            reported_span_seconds=span, seconds_by_reported_overlap=histogram,
            fraction_with_at_least_four_intervals=sum(v for k, v in histogram.items() if int(k) >= 4) / span,
            units_by_package=dict(sorted(Counter(u['name'] for u in units).items()))))
    require(len(rows) == 9, 'expected the original nine instrumented commands')
    out.mkdir()
    result = dict(status='verified historical inspection', source_report=str(path.relative_to(ROOT)),
        source_report_sha256=sha(path), input_workflow_sha256=sha(workflow),
        source_hashes={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), ROOT / 'scripts/cargo_timing_data.py']},
        tool_builds=analysis['tool_builds'], rows=rows, compiler_commands_started=0,
        note='Reported interval overlap is not CPU utilization, ready-queue length or a causal critical path. Cargo can report more overlapping units than configured jobs. Per-package counts do not identify interchangeable units. This is an older instrumented b2/78 history, not another wrapper performance sample.')
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps([{k: row[k] for k in ['mode', 'phase', 'unit_count', 'maximum_reported_overlap',
        'child_cpu_per_wall_second', 'fraction_with_at_least_four_intervals']} for row in rows]))


if __name__ == '__main__':
    main()
