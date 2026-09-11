"""Read Cargo's embedded timing data without evaluating its JavaScript."""
import json
import math
from decimal import Decimal


def require(ok, message):
    if not ok:
        raise ValueError('invalid Cargo timing data: ' + message)


def number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def units_from_html(payload):
    require(isinstance(payload, bytes) and len(payload) <= 64 * 1024 * 1024, 'HTML exceeds byte bound')
    text = payload.decode('utf-8')
    marker = 'const UNIT_DATA = '
    require(text.count(marker) == 1, 'missing or repeated unit-data assignment')
    units, _ = json.JSONDecoder().raw_decode(text.split(marker, 1)[1])
    require(isinstance(units, list) and 0 < len(units) <= 100000, 'unexpected unit count')
    seen = set()
    fields = {'i', 'name', 'version', 'mode', 'target', 'features', 'start', 'duration',
              'unblocked_units', 'unblocked_rmeta_units', 'sections'}
    for unit in units:
        require(isinstance(unit, dict) and fields <= unit.keys(), 'missing unit fields')
        ident = unit['i']
        require(type(ident) is int and 0 <= ident < 2**32 and ident not in seen, 'invalid or duplicate unit ID')
        seen.add(ident)
        for field in ['name', 'version', 'mode', 'target']:
            require(isinstance(unit[field], str) and len(unit[field]) <= 4096, 'invalid unit label')
        require(unit['name'] and unit['version'] and unit['mode'], 'empty package or mode')
        features = unit['features']
        require(isinstance(features, list) and len(features) <= 4096 and
                all(isinstance(f, str) and 0 < len(f) <= 4096 for f in features), 'invalid features')
        require(len(features) == len(set(features)), 'duplicate feature')
        require(number(unit['start']) and number(unit['duration']) and
                number(unit['start'] + unit['duration']), 'invalid unit time')
        for field in ['unblocked_units', 'unblocked_rmeta_units']:
            edges = unit[field]
            require(isinstance(edges, list) and len(edges) <= 100000 and
                    all(type(i) is int and 0 <= i < 2**32 for i in edges), 'invalid unblocking edge')
            require(len(edges) == len(set(edges)), 'duplicate unblocking edge')
        sections = unit['sections']
        require(sections is None or isinstance(sections, list), 'invalid sections')
        if sections is not None:
            require(len(sections) <= 4096, 'too many sections')
            for section in sections:
                require(isinstance(section, list) and len(section) == 2 and
                        isinstance(section[0], str) and isinstance(section[1], dict), 'invalid section')
                times = section[1]
                require({'start', 'end'} <= times.keys() and number(times['start']) and
                        number(times['end']) and times['start'] <= times['end'], 'invalid section interval')
    return units


def group_key(unit):
    # Timing IDs are local to an invocation. Keep features and target text;
    # Cargo's current mode value can be "todo", which is not a compile mode.
    return (unit['name'], unit['version'], unit['mode'], unit['target'], tuple(sorted(unit['features'])))


def timeline(units):
    """Describe reported intervals, not CPU consumption or a critical path."""
    require(bool(units), 'empty timeline')
    # Work in the reported decimal values so, for example, .1 + .2 does not
    # create an artificial overlap with a unit starting at .3.
    intervals = sorted((Decimal(str(u['start'])), Decimal(str(u['start'])) + Decimal(str(u['duration'])))
                       for u in units if u['duration'] > 0)
    covered = Decimal(0)
    if intervals:
        start, end = intervals[0]
        for left, right in intervals[1:]:
            if left > end:
                covered += end - start
                start, end = left, right
            else:
                end = max(end, right)
        covered += end - start
    events = [(left, 1) for left, right in intervals] + [(right, -1) for left, right in intervals]
    active = maximum = 0
    for _, delta in sorted(events):
        active += delta  # Ends precede starts at the same reported instant.
        maximum = max(maximum, active)
    counts = {}
    for unit in units:
        key = group_key(unit)
        counts[key] = counts.get(key, 0) + 1
    ids = {u['i'] for u in units}
    external_edges = sorted({i for u in units for field in ['unblocked_units', 'unblocked_rmeta_units']
                             for i in u[field] if i not in ids})
    return dict(unit_count=len(units), first_reported_start=min(u['start'] for u in units),
        last_reported_end=float(max(Decimal(str(u['start'])) + Decimal(str(u['duration'])) for u in units)),
        reported_interval_union_seconds=float(covered), maximum_reported_overlap=maximum,
        duplicate_group_keys=sum(n > 1 for n in counts.values()),
        unblocking_ids_without_observed_intervals=external_edges,
        interpretation='Rounded Cargo intervals can overlap; neither their sum nor these unblocking edges establishes CPU time or a complete critical path. Section names are Cargo labels, not proof of LLVM code generation.')
