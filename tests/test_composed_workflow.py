"""Prevent invalid native outcomes or noisy/partial pairs from passing a gate."""
import copy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'benchmarks/experiments/composed-development/workflows.py'
spec = importlib.util.spec_from_file_location('composed_workflow', path)
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


class ComposedWorkflowTests(unittest.TestCase):
    def test_native_parallel_order_is_allowed_but_exact_names_and_failures_are_required(self):
        output = ('running 2 tests\ntest suite::b ... ok\ntest suite::a ... ok\n'
                  'test result: ok. 2 passed; 0 failed; 0 ignored; 4 filtered out; finished in 0.12s\n')
        names = ['suite::a', 'suite::b']
        self.assertEqual(workflow.native_outcomes(output, names, True),
                         [('suite::a', 'passed'), ('suite::b', 'passed')])
        failed = output.replace('suite::a ... ok', 'suite::a ... FAILED').replace(
            'ok. 2 passed; 0 failed', 'FAILED. 1 passed; 1 failed')
        self.assertEqual(workflow.native_outcomes(failed, names, False),
                         [('suite::a', 'failed'), ('suite::b', 'passed')])
        for bad, success in [(output, False), (failed, True),
                (output.replace('suite::b', 'suite::a'), True),
                (output.replace('suite::b', 'unselected'), True),
                (output.replace('2 passed', '3 passed'), True),
                (output.replace('suite::b ... ok', 'suite::b ... ignored'), True),
                ('error: could not compile crate; 2 passed is only diagnostic text', False)]:
            with self.subTest(output=bad, success=success), self.assertRaises(AssertionError):
                workflow.native_outcomes(bad, names, success)

    def rows(self):
        result = []
        for cycle in range(3):
            for state in range(1, 6):
                for mode in workflow.MODES:
                    wall, cpu = {'baseline': (2, 4), 'duplicate': (2, 4), 'candidate': (1.8, 3.8),
                                 'native': (1, 2), 'native_lines': (.9, 1.8), 'check': (.3, .4)}[mode]
                    result.append(dict(cycle=cycle, state=state, mode=mode, seconds=wall,
                                       cpu=dict(total_seconds=cpu), source_sha256=str(state)))
        return result

    def test_noise_cpu_and_missing_pairs_cannot_be_hidden_by_a_wall_win(self):
        rows = self.rows()
        result = workflow.assessment(rows, 'token')
        self.assertTrue(result['gate_passed'])
        self.assertEqual((result['edited_pairs'], result['aa_pairs']), (15, 15))
        self.assertAlmostEqual(result['paired_native_wall_ratio'], 1.8)
        noisy = copy.deepcopy(rows)
        for row in noisy:
            if row['mode'] == 'duplicate' and row['state'] == 1: row['seconds'] = 2.12
        result = workflow.assessment(noisy, 'token')
        self.assertFalse(result['noise_acceptable'])
        self.assertFalse(result['gate_passed'])
        cpu = copy.deepcopy(rows)
        for row in cpu:
            if row['mode'] == 'candidate': row['cpu']['total_seconds'] = 4.2
        self.assertFalse(workflow.assessment(cpu, 'token')['gate_passed'])
        for bad in [rows[:-1], rows + [rows[0]]]:
            with self.assertRaises(AssertionError): workflow.assessment(bad, 'token')
        different_source = copy.deepcopy(rows)
        different_source[0]['source_sha256'] = 'wrong source'
        with self.assertRaises(AssertionError): workflow.assessment(different_source, 'token')

    def test_heldout_guard_covers_wall_and_cpu(self):
        for field in ['wall', 'cpu']:
            rows = self.rows()
            for row in rows:
                if row['mode'] == 'candidate':
                    if field == 'wall': row['seconds'] = 2.12
                    else: row['cpu']['total_seconds'] = 4.24
            self.assertFalse(workflow.assessment(rows, 'folded')['gate_passed'])
            self.assertFalse(workflow.assessment(rows, 'pgrust')['gate_passed'])


if __name__ == '__main__':
    unittest.main()
