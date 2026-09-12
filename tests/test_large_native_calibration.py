"""Native controls report small differences without inheriting optimizer gates."""
import importlib.util
from pathlib import Path
import unittest
import tempfile

path = Path(__file__).resolve().parents[1] / 'benchmarks/experiments/large-native-calibration/run.py'
spec = importlib.util.spec_from_file_location('large_native_calibration', path)
calibration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibration)


class LargeNativeCalibrationTests(unittest.TestCase):
    def test_tracked_links_bind_link_text_without_following_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'directory').mkdir()
            link = root/'link'
            link.symlink_to('directory')
            first = calibration.input_fingerprint(link)
            self.assertEqual(first['kind'], 'symlink')
            link.unlink()
            link.symlink_to('missing')
            second = calibration.input_fingerprint(link)
            self.assertNotEqual(first, second)
            link.unlink()
            link.write_text('missing')
            third = calibration.input_fingerprint(link)
            self.assertEqual(second['sha256'], third['sha256'])
            self.assertNotEqual(second, third)

    def rows(self, line_ratio=.99, duplicate_ratio=1):
        rows = []
        for cycle in range(3):
            for state in range(1, 6):
                for mode in calibration.MODES:
                    value = {'repository': 10, 'duplicate': 10*duplicate_ratio,
                             'line_tables': 10*line_ratio, 'check': 4}[mode]
                    rows.append(dict(cycle=cycle, state=state, mode=mode, source_sha256=str(state),
                                     seconds=value, cpu=dict(total_seconds=value)))
        return rows

    def test_native_control_has_no_minimum_optimizer_gate(self):
        for ratio in [.85, .99, 1.01]:
            result = calibration.assessment(self.rows(line_ratio=ratio))
            self.assertIsNone(result['optimization_gate'])
            self.assertTrue(result['noise_acceptable'])
            self.assertAlmostEqual(result['paired_wall_ratio'], ratio)
            self.assertEqual((result['edited_pairs'], result['aa_pairs']), (15, 15))

    def test_noise_partial_pairs_and_mixed_sources_remain_visible(self):
        self.assertFalse(calibration.assessment(self.rows(duplicate_ratio=1.08))['noise_acceptable'])
        rows = self.rows()
        for bad in [rows[:-1], rows + [rows[0]]]:
            with self.assertRaises(AssertionError): calibration.assessment(bad)
        rows[0]['source_sha256'] = 'other source'
        with self.assertRaises(AssertionError): calibration.assessment(rows)
