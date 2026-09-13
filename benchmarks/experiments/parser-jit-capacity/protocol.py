"""Frozen capacity experiment schedule and conservative same-session screen."""
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'pgrust-parser-edits'))
sys.path.insert(0, str(HERE.parents[2] / 'scripts'))
from states import source_states

MODES = ['native', 'custom-a', 'custom-b', 'custom-32']
LIMITS = {'custom-a': 16777216, 'custom-b': 16777216, 'custom-32': 33554432}


def selected_states(original, cycles):
    if type(cycles) is not int or cycles not in [1, 3]:
        raise ValueError('only the declared one- or three-cycle study is supported')
    rows = [r for r in source_states(original) if r['cycle'] < cycles]
    rows.append(dict(cycle=cycles, state=0, label='restored-original', source=original))
    return rows


def schedule(states):
    # Four treatments need a four-treatment order: the existing workflow helper
    # selects six three-mode permutations and would put native first every time.
    orders = [[0, 1, 3, 2], [1, 2, 0, 3], [2, 3, 1, 0], [3, 0, 2, 1]]
    rows = []
    for s in states:
        if s['state'] > 0:
            indices = orders[(s['cycle'] * 5 + s['state'] - 1) % 4]
        else:
            indices = list(range(4)) if s['state'] == 0 else list(reversed(range(4)))
            rotation = s['cycle'] % 4
            indices = indices[rotation:] + indices[:rotation]
        rows += [dict(cycle=s['cycle'], state=s['state'], label=s['label'], mode=MODES[i]) for i in indices]
    return rows


def measurement(records, cycles):
    expected = [(c, s) for c in range(cycles) for s in [0, -1, 1, 2, 3, 4, 5]] + [(cycles, 0)]
    if cycles not in [1, 3] or len(records) != len(expected) * 4:
        raise ValueError('missing or extra observations')
    groups = {}
    for row in records:
        key = row['cycle'], row['state']
        if key not in expected or row['mode'] not in MODES:
            raise ValueError('unexpected observation')
        group = groups.setdefault(key, {})
        if row['mode'] in group:
            raise ValueError('duplicate observation')
        group[row['mode']] = row
        for metric in ['wall_seconds', 'cpu_seconds']:
            if not math.isfinite(row[metric]) or row[metric] <= 0:
                raise ValueError('invalid timing observation')
    if set(groups) != set(expected) or any(set(g) != set(MODES) for g in groups.values()):
        raise ValueError('incomplete mode/state coverage')
    pairs = []
    for (cycle, state), group in groups.items():
        if state <= 0: continue
        pair = dict(cycle=cycle, state=state)
        for metric in ['wall_seconds', 'cpu_seconds']:
            values = {m: group[m][metric] for m in MODES}
            pair[metric] = dict(values, candidate_baseline=values['custom-32']/values['custom-a'],
                candidate_native=values['custom-32']/values['native'],
                baseline_native=values['custom-a']/values['native'],
                aa=values['custom-b']/values['custom-a'])
        pairs.append(pair)
    medians = {}
    for metric in ['wall_seconds', 'cpu_seconds']:
        medians[metric] = {name: statistics.median(p[metric][name] for p in pairs)
                          for name in [*MODES, 'candidate_baseline', 'candidate_native', 'baseline_native', 'aa']}
        medians[metric]['aa_max_absolute_per_edit_median'] = max(
            abs(statistics.median(p[metric]['aa'] for p in pairs if p['state'] == s)-1) for s in range(1, 6))
        medians[metric]['candidate_plus_noise'] = (medians[metric]['candidate_baseline'] +
                                                  medians[metric]['aa_max_absolute_per_edit_median'])
    wall = medians['wall_seconds']['candidate_plus_noise'] < 1
    cpu = medians['cpu_seconds']['candidate_plus_noise'] <= 1.03
    return dict(edited_pairs=len(pairs), pairs=pairs, medians=medians,
                gate=dict(wall_passed=wall, cpu_passed=cpu, passed=wall and cpu,
                          wall_threshold=1, cpu_threshold=1.03,
                          meaning='screen eligibility for a fresh full study' if cycles == 1 else 'parser-specific performance gate'))
