import copy
from pathlib import Path
import unittest

from benchmark import ratios
from states import native_outcomes, source_states, custom_export_ran, check_prefix_schedule

ROOT = Path(__file__).resolve().parents[3]


def transcript(rows):
    passed = sum(status == 'ok' for _, status in rows)
    failed = sum(status == 'FAILED' for _, status in rows)
    ignored = sum(status == 'ignored' for _, status in rows)
    status = 'FAILED' if failed else 'ok'
    return f'running {len(rows)} tests\n' + ''.join(f'test {name} ... {value}\n' for name, value in rows) + (
        f'test result: {status}. {passed} passed; {failed} failed; {ignored} ignored; 0 measured; 0 filtered out;\n')


class ProtocolTests(unittest.TestCase):
    def test_actual_production_history_has_distinct_edits_and_exact_restoration(self):
        original = (ROOT / '.work/sources/pgrust/crates/backend/parser/gram_core/src/parse.rs').read_bytes()
        rows = source_states(original)
        self.assertEqual(len(rows), 22)
        self.assertEqual(len({r['source'] for r in rows}), 7)
        for cycle in range(3):
            self.assertEqual([r['state'] for r in rows if r['cycle'] == cycle], [0, -1, 1, 2, 3, 4, 5])
        self.assertEqual(rows[-1]['source'], original)
        self.assertEqual(rows[-1]['label'], 'restored-original')

    def test_changed_layout_or_ambiguous_edit_is_rejected(self):
        original = (ROOT / '.work/sources/pgrust/crates/backend/parser/gram_core/src/parse.rs').read_bytes()
        for bad in [original + b'\n#[test]\nfn new_test() {}',
                    original.replace(b'have_lookahead: mode_token != 0,', b'have_lookahead: false,'),
                    original + b'\n// have_lookahead: mode_token != 0,']:
            with self.assertRaises(ValueError): source_states(bad)
        with self.assertRaises(ValueError): source_states(original, cycles=1)

    def test_native_order_is_normalized_and_wrong_outcomes_preserved(self):
        names = ['a', 'b']
        self.assertEqual(native_outcomes(transcript([('b', 'ok'), ('a', 'ok')]), names, True),
                         [('a', 'passed'), ('b', 'passed')])
        self.assertEqual(native_outcomes(transcript([('b', 'FAILED'), ('a', 'ok')]), names, False),
                         [('a', 'passed'), ('b', 'failed')])

    def test_missing_duplicate_extra_and_ignored_tests_rejected(self):
        for rows in [[('a', 'ok')], [('a', 'ok'), ('a', 'ok')],
                     [('a', 'ok'), ('b', 'ok'), ('c', 'ok')], [('a', 'ok'), ('b', 'ignored')]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                native_outcomes(transcript(rows), ['a', 'b'], True)

    def test_compile_errors_filtered_results_and_wrong_control_success_rejected(self):
        good = transcript([('a', 'ok'), ('b', 'ok')])
        for text in ['error: rustc failed', good.replace('0 filtered out', '1 filtered out'), good + good,
                     good.replace('2 passed', '1 passed')]:
            with self.assertRaises(ValueError): native_outcomes(text, ['a', 'b'], True)
        with self.assertRaises(ValueError): native_outcomes(good, ['a', 'b'], False)

    def test_statistic_uses_paired_ratios_and_excludes_control_states(self):
        rows = []
        for cycle in range(3):
            for state in range(1, 6):
                native = (1, 10, 100)[cycle]
                custom = (2, 10, 50)[cycle]
                for mode, value in [('native', native), ('custom-a', custom), ('custom-b', custom * 1.02)]:
                    rows.append(dict(cycle=cycle, state=state, mode=mode, wall_seconds=value, cpu_seconds=value * 2))
        result = ratios(rows + [dict(cycle=0, state=-1, mode='native', wall_seconds=1e9, cpu_seconds=1e9)])
        self.assertEqual(result['edited_pairs'], 15)
        for metric in result['medians'].values():
            self.assertEqual(metric['custom_native'], 1)
            self.assertAlmostEqual(metric['aa'], 1.02)
            self.assertAlmostEqual(metric['aa_max_absolute_per_edit_median'], .02)

    def test_missing_mode_cannot_become_an_incomplete_timing_pair(self):
        with self.assertRaises(AssertionError): ratios([])

    def test_custom_export_requires_target_progress_and_exact_export_completion(self):
        export = 'rust-interp-export: frontend_ms=1 lowering_ms=2 functions=3 ops=4 bytes=5\n'
        for label in ['Checking', 'Compiling']:
            self.assertTrue(custom_export_ran('   ' + label + ' gram_core v0.1.0 (/source)\n' + export))
        for text in [export, 'Compiling gram_core\n', '   Fresh gram_core v0.1.0\n' + export,
                     '   Checking other_crate v0.1.0\n' + export,
                     '   Compiling gram_core v0.1.0\n' + export * 2]:
            self.assertFalse(custom_export_ran(text))

    def test_continuation_cannot_change_profile_order_source_or_prior_outcomes(self):
        schedule = [dict(cycle=0, state=0, mode=mode, label='original', source_sha256='original')
                    for mode in ['native', 'custom-a', 'custom-b']] * 22
        rows = [dict(s, index=i, returncode=0) for i, s in enumerate(schedule[:2])]
        check_prefix_schedule(rows, schedule, 'repository')
        with self.assertRaises(ValueError): check_prefix_schedule(rows, schedule, 'incremental')
        for bad in [rows[::-1], rows[:1], rows + rows[:1],
                    [dict(rows[0], source_sha256='different'), rows[1]],
                    [rows[0], dict(rows[1], returncode=1)]]:
            with self.assertRaises(ValueError): check_prefix_schedule(bad, schedule, 'repository')


if __name__ == '__main__':
    unittest.main()
