import unittest

from timing import choose


def rows(line, none):
    return [dict(preset=p, state=s, seconds=t) for s in [1, 2, 3]
            for p, t in [('repository', 1), ('line-tables-only', line), ('none', none)]]


class CalibrationTests(unittest.TestCase):
    def test_small_effect_declines(self):
        self.assertIsNone(choose(rows(.93, .94))['selected'])

    def test_line_preference_is_bounded(self):
        self.assertEqual(choose(rows(.81, .80))['selected'], 'line-tables-only')
        self.assertEqual(choose(rows(.85, .80))['selected'], 'none')

    def test_confirmation_cannot_choose_preset(self):
        samples = rows(.85, .80)
        samples += [dict(preset='line-tables-only', state=4, seconds=.001)]
        self.assertEqual(choose(samples)['selected'], 'none')

    def test_incomplete_calibration_fails(self):
        with self.assertRaises(RuntimeError):
            choose(rows(.8, .7)[:-1])


if __name__ == '__main__':
    unittest.main()
