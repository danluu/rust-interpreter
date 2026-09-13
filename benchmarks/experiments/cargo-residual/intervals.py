"""Relate Cargo's reported unit intervals to an enclosing custom Cargo stage."""
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from cargo_timing_data import number, timeline


def enclosing_scope(units, cargo_seconds):
    if not number(cargo_seconds) or cargo_seconds <= 0:
        raise ValueError('Cargo duration must be finite and positive')
    observed = timeline(units)
    first = min(Decimal(str(u['start'])) for u in units)
    last = max(Decimal(str(u['start'])) + Decimal(str(u['duration'])) for u in units)
    span = last - first
    covered = Decimal(str(observed['reported_interval_union_seconds']))
    elapsed = Decimal(str(cargo_seconds))
    # Different clock origins prevent separating startup from finalization.
    # Interval lengths and their union remain translation invariant.
    return dict(cargo_seconds=cargo_seconds, **observed,
        reported_unit_span_seconds=float(span),
        internal_reported_gap_seconds=float(span - covered),
        combined_time_outside_reported_span_seconds=float(elapsed - span),
        time_without_reported_active_unit_seconds=float(elapsed - covered),
        enclosing_duration_consistent=covered <= span <= elapsed,
        scope='Rounded elapsed unit intervals inside the separately measured custom Cargo stage; '
            'uncovered time is unattributed, not measured fingerprinting or startup. '
            'Negative differences are retained as inconsistent envelopes, not clamped. '
            'This calculation does not apply to a native command that includes test execution.')
