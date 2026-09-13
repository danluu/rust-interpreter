#!/usr/bin/env python3
"""Attribute saved Nushell composition Cargo intervals without another build."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from cargo_timing_data import group_key, units_from_html
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write
from intervals import enclosing_scope

MODES = ['baseline', 'duplicate', 'candidate']
KEYS = dict(baseline='f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8',
    duplicate='f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8',
    candidate='f0af2e3e4c1093fd0e7bb5a5a53dd8e72b305d7e1536ea9c4b999ba2acaa965a')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'cargo-residual-nushell-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 8)
        summary_path = ROOT / 'results/memory-lookup-edit-nushell-01/summary.json'
        summary = json.loads(summary_path.read_text())
        assert summary['status'] == 'passed' and summary['commands'] == 132 and summary['case'] == 'nushell'
        assert not summary['private'] and summary['source_restored'] and summary['test_source_unchanged']
        assert summary['tool_keys'] == KEYS
        raw = ROOT / summary['raw']
        paths = [summary_path, Path(__file__), Path(__file__).with_name('PLAN.md'),
                 Path(__file__).with_name('intervals.py'), ROOT / 'scripts/cargo_timing_data.py',
                 ROOT / 'scripts/compare_saved_runtime.py', ROOT / 'scripts/workflow_io.py']
        for name, digest in summary['evidence'].items():
            path = raw / (name + '.json'); assert sha(path) == digest; paths.append(path)
        records_path = raw / 'records.json'
        assert records_path.stat().st_size <= 128 * 1024**2
        records = json.loads(records_path.read_text()); assert len(records) == 132
        selected = [r for r in records if r['mode'] in MODES and r['state'] > 0]
        assert len(selected) == 45
        for mode in MODES:
            assert {(r['cycle'], r['state']) for r in selected if r['mode'] == mode} == {
                (cycle, state) for cycle in range(3) for state in range(1, 6)}
        for row in selected:
            html = ROOT / row['cargo_timing']['path']
            assert sha(html) == row['cargo_timing']['sha256']; paths.append(html)
            assert row['launch']['tool_key'] == KEYS[row['mode']] and row['returncode'] == 0
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / args.run_id; work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, observations=45,
            guest_executions=0, compiler_executions=0, historical_tool_keys=KEYS))
        results = []
        for row in selected:
            units = units_from_html((ROOT / row['cargo_timing']['path']).read_bytes())
            scope = enclosing_scope(units, row['launch']['cargo_seconds'])
            groups = defaultdict(list)
            for unit in units: groups[group_key(unit)].append(unit)
            results.append(dict(mode=row['mode'], cycle=row['cycle'], state=row['state'],
                source_sha256=row['source_sha256'], scope=scope,
                unit_groups=[dict(name=key[0], version=key[1], mode_label=key[2],
                    target_label=key[3], features=list(key[4]), unit_ids=[u['i'] for u in values],
                    sum_reported_unit_durations=sum(u['duration'] for u in values))
                    for key, values in groups.items()]))
        write(work / 'observations.json', results)
        fields = ['cargo_seconds', 'reported_interval_union_seconds', 'reported_unit_span_seconds',
            'internal_reported_gap_seconds', 'combined_time_outside_reported_span_seconds',
            'time_without_reported_active_unit_seconds']
        medians = {mode: {key: statistics.median(r['scope'][key] for r in results if r['mode'] == mode)
                         for key in fields} for mode in MODES}
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        destination = ROOT / 'results' / args.run_id; destination.mkdir(exist_ok=False)
        write(destination / 'summary.json', dict(status='passed', observations=45,
            compiler_executions=0, guest_executions=0, performance_measurement=False,
            historical_tool_keys=KEYS, medians=medians,
            inconsistent_envelopes=[{k:r[k] for k in ['mode','cycle','state']}
                for r in results if not r['scope']['enclosing_duration_consistent']],
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            observations_sha256=sha(work / 'observations.json'),
            scope='Saved composition observations; all15 edited custom commands per mode. '
                'Native commands and original/wrong/restored controls remain in hashed source records. '
                'Uncovered time is unattributed. Stage medians are nonadditive; unit duration sums '
                'may overlap and are not CPU time or a critical path. No current-tool or latency-gain claim.'))
        print(json.dumps(medians), flush=True)


if __name__ == '__main__': main()
