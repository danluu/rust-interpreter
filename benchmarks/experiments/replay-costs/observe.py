"""Check observer coverage and non-overlapping timing accounting."""
import json
import math
import re


def require_cargo_export(stderr, package):
    assert re.search(r'^\s*(Checking|Compiling) ' + re.escape(package) + r' v', stderr, re.M), 'no current Cargo unit activity'


def messages(stderr, prefix):
    return [json.loads(line.split(': ', 1)[1]) for line in stderr.splitlines()
            if line.startswith(prefix + ': ')]


def observation(stderr, enabled):
    rows = messages(stderr, 'rust-interp-replay-costs')
    if not enabled:
        assert not rows, 'disabled observer emitted costs'
        return None
    row, = rows
    cache, = messages(stderr, 'rust-interp-function-cache')
    assert row['schema_version'] in [1, 2] and row['performance_measurement'] is False
    totals = row['totals']
    assert cache['mode'] == 'reuse' and totals['functions'] == cache['skipped_functions']
    for field in ['functions', 'instructions', 'immediate_sites', 'events', 'call_sites']:
        assert type(totals[field]) is int and totals[field] >= 0
    phases = [totals[p + '_seconds'] for p in ['setup', 'events', 'patch']]
    assert all(math.isfinite(x) and x >= 0 for x in phases)
    assert math.isfinite(row['binding_seconds']) and row['binding_seconds'] >= 0
    assert row['binding_seconds'] == cache['previous_binding_seconds']
    assert abs(sum(phases) - row['phase_seconds']) < 1e-9
    assert abs(row['binding_seconds'] - sum(phases) - row['unassigned_seconds']) < 1e-9
    assert row['unassigned_seconds'] >= -1e-9
    if row['schema_version'] == 2:
        nested = [totals[p + '_seconds'] for p in ['current_context', 'immediate_index']]
        assert all(math.isfinite(x) and x >= 0 for x in nested)
        assert abs(sum(nested) - totals['setup_seconds']) < 1e-9
    if totals['functions'] == 0:
        assert not any(totals.values()) and row['binding_seconds'] == 0
    return row
