#!/usr/bin/env python3
"""Check Cargo timing interpretation against preserved captures and bad input."""
import argparse
from copy import deepcopy
import fcntl
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from cargo_timing_data import group_key, timeline, units_from_html


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def payload(units):
    return ('<script>const UNIT_DATA = ' + json.dumps(units) + '; unrelatedJavascript();</script>').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['.', '..'], 'invalid run ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    legacy = ROOT / 'results/cargo-profile-nushell-float-ranges-01/summary.json'
    report = json.loads(legacy.read_text())
    records = json.loads((ROOT / report['raw'] / 'records.json').read_text())
    captures = []
    for row in records:
        path = ROOT / row['timing_report']
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == row['timing_sha256'], 'preserved timing changed')
        parsed = units_from_html(raw)
        require(parsed == row['units'], 'new parser changed preserved Cargo units')
        captures.append(dict(path=row['timing_report'], sha256=row['timing_sha256'],
                             state=row['state'], units=len(parsed), timeline=timeline(parsed)))

    unit = dict(i=1, name='example', version='0.1.0', mode='todo', target=' (check)',
                features=['feature-b', 'feature-a'], start=1.0, duration=3.0,
                unblocked_units=[], unblocked_rmeta_units=[], sections=None)
    # Two duplicate group keys overlap; a different feature set starts at their
    # endpoint. A zero-duration event must not inflate reported concurrency.
    second = dict(unit, i=2, start=2.0, duration=2.0, features=['feature-a', 'feature-b'])
    third = dict(unit, i=3, start=4.0, duration=2.0, features=['other'], unblocked_units=[999])
    fourth = dict(unit, i=4, start=4.0, duration=0.0, target=' build-script')
    units = units_from_html(payload([unit, second, third, fourth]))
    scope = timeline(units)
    require(scope['reported_interval_union_seconds'] == 5.0 and scope['maximum_reported_overlap'] == 2,
            'overlap/endpoint/zero-length accounting differs')
    require(scope['duplicate_group_keys'] == 1 and scope['unblocking_ids_without_observed_intervals'] == [999],
            'duplicate groups or unobserved edges lost')
    require(len(units) == 4 and group_key(units[0]) == group_key(units[1]) and
            group_key(units[0]) != group_key(units[2]), 'grouping loses feature distinctions')
    separated = [dict(unit, start=0.0, duration=1.0), dict(unit, i=2, start=3.0, duration=1.0)]
    gap = timeline(units_from_html(payload(separated)))
    require(gap['reported_interval_union_seconds'] == 2.0 and gap['last_reported_end'] == 4.0 and
            gap['maximum_reported_overlap'] == 1, 'gap counted as active compilation')
    decimal_adjacent = timeline(units_from_html(payload([
        dict(unit, start=.1, duration=.2), dict(unit, i=2, start=.3, duration=.1)])))
    require(decimal_adjacent['maximum_reported_overlap'] == 1 and
            decimal_adjacent['reported_interval_union_seconds'] == .3,
            'binary arithmetic invented overlap between adjacent decimal intervals')

    malformed = [
        ('duplicate ID', lambda x: x.append(deepcopy(x[0]))),
        ('boolean ID', lambda x: x[0].update(i=True)),
        ('negative start', lambda x: x[0].update(start=-1)),
        ('nonfinite duration', lambda x: x[0].update(duration=float('nan'))),
        ('infinite end', lambda x: x[0].update(start=1e308, duration=1e308)),
        ('oversized integer time', lambda x: x[0].update(start=10**1000)),
        ('boolean duration', lambda x: x[0].update(duration=False)),
        ('missing required field', lambda x: x[0].pop('target')),
        ('duplicate feature', lambda x: x[0].update(features=['a', 'a'])),
        ('invalid feature', lambda x: x[0].update(features=[3])),
        ('empty mode', lambda x: x[0].update(mode='')),
        ('boolean edge', lambda x: x[0].update(unblocked_units=[True])),
        ('duplicate edge', lambda x: x[0].update(unblocked_units=[2, 2])),
        ('reversed section', lambda x: x[0].update(sections=[['frontend', dict(start=2, end=1)]])),
        ('incomplete section', lambda x: x[0].update(sections=[['frontend', dict(start=0)]])),
    ]
    rejected = []
    for label, mutate in malformed:
        bad = [deepcopy(unit)]
        mutate(bad)
        try:
            units_from_html(payload(bad))
        except ValueError as error:
            rejected.append(dict(case=label, error=str(error)))
        else:
            raise RuntimeError('malformed Cargo timing accepted: ' + label)
    for label, bad in [('empty units', payload([])), ('missing marker', b'{}'),
                       ('repeated marker', payload([unit]) * 2), ('not an array', payload(unit))]:
        try:
            units_from_html(bad)
        except ValueError as error:
            rejected.append(dict(case=label, error=str(error)))
        else:
            raise RuntimeError('malformed timing document accepted: ' + label)
    out = ROOT / 'results' / args.run_id
    out.mkdir(exist_ok=False)
    paths = [Path(__file__), ROOT / 'scripts/cargo_timing_data.py', ROOT / 'scripts/analyze_cargo_timings.py']
    summary = dict(status='passed', preserved_captures=captures, synthetic_timeline=scope,
        gap_timeline=gap, decimal_adjacent_timeline=decimal_adjacent,
        rejected=rejected, compiler_or_project_execution=False,
        source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(dict(preserved_captures=len(captures), malformed_inputs_rejected=len(rejected))))


if __name__ == '__main__':
    main()
