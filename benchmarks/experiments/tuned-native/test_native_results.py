import unittest

from native_results import libtest_summary, residual_seconds


def summary(seconds='0.62', counts='3 passed; 0 failed', outcome='ok'):
    return (f'test result: {outcome}. {counts}; 0 ignored; 0 measured; '
            f'386 filtered out; finished in {seconds}s\n')


class LibtestTests(unittest.TestCase):
    def test_grouped_harness_is_distinguished(self):
        output = ('test result: ok. 14 passed; 0 failed; 0 ignored; '
                  '0 filtered out; across 1 groups, finished in 0.00s\n')
        result = libtest_summary(output, selected=14)
        self.assertEqual(result['harness'], 'grouped')
        self.assertIsNone(result['measured'])
        with self.assertRaises(ValueError):
            libtest_summary(output + summary())

    def test_rounding_and_residual(self):
        result = libtest_summary(summary(), selected=3)
        self.assertAlmostEqual(result['lower_seconds'], .615)
        self.assertAlmostEqual(residual_seconds(2, result)['lower'], 1.375)
        self.assertAlmostEqual(residual_seconds(2, result)['upper'], 1.385)

    def test_zero_is_an_interval(self):
        result = libtest_summary(summary('0.00'))
        self.assertEqual((result['lower_seconds'], result['upper_seconds']), (0, .005))

    def test_missing_or_multiple_suites_rejected(self):
        for output in ['', summary() * 2]:
            with self.assertRaises(ValueError):
                libtest_summary(output)

    def test_missing_tests_and_unexpected_failure_rejected(self):
        with self.assertRaises(ValueError):
            libtest_summary(summary(), selected=4)
        with self.assertRaises(ValueError):
            libtest_summary(summary(counts='2 passed; 1 failed', outcome='FAILED'))

    def test_negative_control_and_impossible_time(self):
        result = libtest_summary(summary(counts='2 passed; 1 failed', outcome='FAILED'), success=False)
        self.assertEqual(result['failed'], 1)
        with self.assertRaises(ValueError):
            libtest_summary(summary(), success=False)
        with self.assertRaises(ValueError):
            residual_seconds(.1, result)


if __name__ == '__main__':
    unittest.main()
