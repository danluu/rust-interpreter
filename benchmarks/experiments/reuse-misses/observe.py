"""Validate the draft reuse observation against rows and existing cache counters."""
import json
import math
import re

LOOKUPS = ['green_present', 'green_absent', 'red_present', 'red_absent']
PHASES = ['prepare_seconds', 'lower_seconds', 'template_encode_seconds',
          'template_decode_seconds', 'binding_seconds']
COUNTS = ['functions', 'operations', 'reused', 'staged', 'declined',
          'replay_body_required_functions', 'replay_body_free_functions']
NESTED = ['replay_current_context_seconds', 'replay_body_free_context_seconds']


def require(ok, message):
    if not ok:
        raise ValueError('invalid reuse-miss observation: ' + message)


def messages(stderr, prefix):
    values = []
    for line in stderr.splitlines():
        if line.startswith(prefix + ': '):
            require(len(line.encode()) <= 16 * 1024**2 + len(prefix) + 2, 'report byte bound')
            values.append(json.loads(line[len(prefix) + 2:]))
    return values


def count(value):
    return type(value) is int and value >= 0


def seconds(value):
    return type(value) in [int, float] and math.isfinite(value) and value >= 0


def same_time(a, b):
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def observation(stderr, enabled):
    reports = messages(stderr, 'rust-interp-reuse-misses')
    if not enabled:
        require(not reports, 'disabled observer emitted a report')
        return None
    caches = messages(stderr, 'rust-interp-function-cache')
    require(len(reports) == len(caches) == 1, 'missing or repeated reports')
    report, cache = reports[0], caches[0]
    require(count(report['schema_version']) and count(cache['schema_version'])
            and report['schema_version'] == cache['schema_version'] == 1, 'schema')
    require(report['complete'] is True and report['performance_measurement'] is False, 'scope')
    require(cache['mode'] == 'reuse', 'actual reuse required')
    rows = report['functions']
    require(isinstance(rows, list) and len(rows) <= 10_000, 'function bound')
    require(set(report['by_lookup']) == set(LOOKUPS), 'lookup groups')
    indices, declines = set(), {}
    expected = {key: {field: 0 for field in [*COUNTS, *PHASES, *NESTED]} for key in LOOKUPS}
    for row in rows:
        require(count(row['index']) and row['index'] < 10_000 and row['index'] not in indices, 'index')
        indices.add(row['index'])
        require(isinstance(row['name'], str) and len(row['name'].encode()) <= 4096, 'name')
        require(count(row['operations']) and row['lookup'] in LOOKUPS, 'operations or lookup')
        require(all(seconds(row[key]) for key in PHASES), 'phase duration')
        group = expected[row['lookup']]
        group['functions'] += 1; group['operations'] += row['operations']
        for key in PHASES: group[key] += row[key]
        action = row['action']; kind = action['kind']
        require(kind in ['reused', 'staged', 'declined'], 'action')
        require((kind == 'reused') == (row['lookup'] == 'green_present'), 'lookup/action mismatch')
        group[kind] += 1
        if kind == 'declined':
            reason = action['first_reason']
            require(isinstance(reason, str) and 0 < len(reason.encode()) <= 4096, 'first decline')
            require(row['template_encode_seconds'] == 0, 'declined template encoded')
            declines[reason] = declines.get(reason, 0) + 1
        if kind == 'reused':
            require(all(row[k] == 0 for k in PHASES[:3]), 'lowering phases on a hit')
            replay = row['replay']
            require(isinstance(replay, dict) and count(replay['events']), 'missing recipe')
            needed = replay['recipe_requires_current_mir']; context = replay['current_context_seconds']
            require(type(needed) is bool and (replay['events'] > 0 or not needed), 'recipe body requirement')
            require(seconds(context) and context <= row['binding_seconds'], 'nested context')
            group['replay_current_context_seconds'] += context
            group['replay_body_required_functions' if needed else 'replay_body_free_functions'] += 1
            if not needed: group['replay_body_free_context_seconds'] += context
        else:
            require(row['replay'] is None and all(row[k] == 0 for k in PHASES[3:]), 'replay phases on a miss')
    for key, group in expected.items():
        actual = report['by_lookup'][key]
        require(set(actual) == set(group), 'group fields')
        for field in COUNTS: require(count(actual[field]) and actual[field] == group[field], 'group count')
        for field in [*PHASES, *NESTED]:
            require(seconds(actual[field]) and same_time(actual[field], group[field]), 'group duration')
    total = lambda key: sum(group[key] for group in expected.values())
    reused, staged, declined = (total(key) for key in ['reused', 'staged', 'declined'])
    for key, value in dict(observed_functions=len(rows), reused=reused, lowered=staged+declined,
                           staged_new=staged, declined=declined).items():
        require(count(report[key]) and report[key] == value, 'report count')
    require(all(count(n) and n > 0 for n in report['first_decline_reasons'].values())
            and report['first_decline_reasons'] == declines, 'decline aggregation')
    for key, value in dict(previous_payload_uses=reused, skipped_functions=reused,
        lowered_functions=staged+declined, declined_functions=declined, staged_entries=reused+staged,
        green_missing=expected['green_absent']['functions'],
        red_functions=expected['red_present']['functions']+expected['red_absent']['functions']).items():
        require(count(cache[key]) and cache[key] == value, 'original cache count')
    require(report['cache_load_note'] == cache['load_note'] and isinstance(cache['load_note'], str), 'load note')
    require(count(report['loaded_entries']) and count(cache['loaded_entries'])
            and report['loaded_entries'] == cache['loaded_entries'], 'loaded entries')
    for phase, field in [('binding_seconds', 'previous_binding_seconds'),
        ('template_decode_seconds', 'previous_template_decoding_seconds'),
        ('template_encode_seconds', 'current_template_encoding_seconds')]:
        require(seconds(cache[field]) and same_time(total(phase), cache[field]), 'original cache duration')
    return report


def require_cargo_export(stderr, package):
    require(re.search(r'^\s*(Checking|Compiling)\s+' + re.escape(package) + r'\s', stderr, re.M),
            'Cargo did not rebuild the requested package')
