import copy
import unittest
from intervals import enclosing_scope


def unit(i, start, duration):
    return dict(i=i, name='crate', version='1', mode='todo', target='', features=[],
        start=start, duration=duration, unblocked_units=[], unblocked_rmeta_units=[])


class EnclosingScopeTests(unittest.TestCase):
    def test_overlap_and_gaps_partition_elapsed_without_summing_unit_durations(self):
        units = [unit(0, 1, 3), unit(1, 2, 2), unit(2, 5, 1)]
        scope = enclosing_scope(units, 7)
        self.assertEqual(scope['reported_interval_union_seconds'], 4)
        self.assertEqual(scope['reported_unit_span_seconds'], 5)
        self.assertEqual(scope['internal_reported_gap_seconds'], 1)
        self.assertEqual(scope['combined_time_outside_reported_span_seconds'], 2)
        self.assertEqual(scope['time_without_reported_active_unit_seconds'], 3)
        self.assertTrue(scope['enclosing_duration_consistent'])
        self.assertEqual(scope['maximum_reported_overlap'], 2)

    def test_clock_origin_cannot_change_durations_or_split_boundary_time(self):
        units = [unit(0, .1, .2), unit(1, .3, .1)]
        original = enclosing_scope(units, .5)
        shifted = copy.deepcopy(units)
        for u in shifted: u['start'] += 10
        later = enclosing_scope(shifted, .5)
        for key in ['reported_interval_union_seconds', 'reported_unit_span_seconds',
                    'internal_reported_gap_seconds', 'combined_time_outside_reported_span_seconds',
                    'time_without_reported_active_unit_seconds', 'enclosing_duration_consistent']:
            self.assertEqual(original[key], later[key])
        self.assertEqual(original['internal_reported_gap_seconds'], 0)
        self.assertNotEqual(original['first_reported_start'], later['first_reported_start'])

    def test_inconsistent_envelope_is_preserved_and_invalid_parent_durations_reject(self):
        scope = enclosing_scope([unit(0, 1, 2)], 1.9)
        self.assertFalse(scope['enclosing_duration_consistent'])
        self.assertEqual(scope['combined_time_outside_reported_span_seconds'], -.1)
        self.assertEqual(scope['time_without_reported_active_unit_seconds'], -.1)
        for duration in [0, -1, float('nan'), float('inf'), True, '3']:
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                enclosing_scope([unit(0, 1, 2)], duration)


if __name__ == '__main__': unittest.main()
