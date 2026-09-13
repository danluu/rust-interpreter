import copy
import unittest
from pathlib import Path

from protocol import MODES, selected_states, schedule, measurement

ROOT = Path(__file__).resolve().parents[3]


def observations(cycles=1):
    states = [(c, s) for c in range(cycles) for s in [0, -1, 1, 2, 3, 4, 5]] + [(cycles, 0)]
    return [dict(cycle=c, state=s, mode=m, wall_seconds={'native': 0.8, 'custom-a': 1., 'custom-b': 1.01, 'custom-32': .97}[m],
                 cpu_seconds={'native': .8, 'custom-a': 1., 'custom-b': 1.01, 'custom-32': .99}[m])
            for c, s in states for m in MODES]


class Protocol(unittest.TestCase):
    def test_schedule_and_production_states(self):
        original = (ROOT / '.work/sources/pgrust/crates/backend/parser/gram_core/src/parse.rs').read_bytes()
        for cycles, count in [(1, 32), (3, 88)]:
            states = selected_states(original, cycles)
            planned = schedule(states)
            self.assertEqual(len(planned), count)
            self.assertEqual(len({(r['cycle'], r['state'], r['mode']) for r in planned}), count)
            self.assertEqual(states[-1]['source'], original)
            self.assertEqual(len({s['source'] for s in states if s['cycle'] == 0}), 7)
            self.assertEqual([r['mode'] for r in planned[:4]], MODES)
            edited = [r for r in planned if r['state'] > 0]
            for position in range(4):
                counts = [sum(r['mode'] == m for r in edited[position::4]) for m in MODES]
                self.assertLessEqual(max(counts) - min(counts), 1)
        with self.assertRaises(ValueError): selected_states(original, 2)

    def test_missing_duplicate_and_unknown_observations_rejected(self):
        good = observations()
        for rows in [good[:-1], good + [good[0]], good[:-1] + [good[0]],
                     good[:-1] + [dict(good[-1], mode='unexpected')]]:
            with self.assertRaises(ValueError): measurement(rows, 1)

    def test_controls_never_supply_timing_ratios(self):
        rows = observations()
        before = measurement(rows, 1)
        for r in rows:
            if r['state'] <= 0:
                r['wall_seconds'] = .00001 if r['mode'] == 'native' else 999
                r['cpu_seconds'] = 999 if r['mode'] == 'native' else .00001
        self.assertEqual(before, measurement(rows, 1))
        self.assertEqual(before['edited_pairs'], 5)
        self.assertTrue(before['gate']['passed'])

    def test_gain_inside_noise_rejected(self):
        rows = observations()
        for r in rows:
            if r['mode'] == 'custom-b' and r['state'] == 3: r['wall_seconds'] = 1.04
        result = measurement(rows, 1)
        self.assertLess(result['medians']['wall_seconds']['candidate_baseline'], 1)
        self.assertFalse(result['gate']['wall_passed'])

    def test_cpu_guard_rejects_wall_winner(self):
        rows = observations()
        for r in rows:
            if r['mode'] == 'custom-32': r['cpu_seconds'] = 1.04
        result = measurement(rows, 1)
        self.assertTrue(result['gate']['wall_passed'])
        self.assertFalse(result['gate']['passed'])

    def test_full_uses_per_edit_median_noise_and_paired_ratios(self):
        rows = observations(3)
        for r in rows:
            if r['mode'] == 'custom-b' and r['cycle'] == 0: r['wall_seconds'] = 2
            if r['state'] == 5:
                for metric in ['wall_seconds', 'cpu_seconds']: r[metric] *= 100
        result = measurement(rows, 3)
        self.assertEqual(result['edited_pairs'], 15)
        self.assertAlmostEqual(result['medians']['wall_seconds']['aa_max_absolute_per_edit_median'], .01)
        self.assertAlmostEqual(result['medians']['wall_seconds']['candidate_baseline'], .97)

    def test_invalid_measurements_rejected(self):
        for value in [0, -1, float('nan'), float('inf')]:
            rows = copy.deepcopy(observations())
            rows[0]['wall_seconds'] = value
            with self.assertRaises(ValueError): measurement(rows, 1)


if __name__ == '__main__': unittest.main()
