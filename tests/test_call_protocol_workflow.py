"""Require balanced edited states and both runtime/anchor acceptance checks."""
from collections import Counter
import copy
import importlib.util
from pathlib import Path
import unittest

def load_workflow(directory, name):
    path = Path(__file__).resolve().parents[1] / 'benchmarks/experiments' / directory / 'workflows.py'
    spec = importlib.util.spec_from_file_location(name, path)
    workflow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(workflow)
    return workflow


class CallProtocolWorkflowTests(unittest.TestCase):
    workflow = load_workflow('resumable-call-protocol', 'call_protocol_workflow')
    def test_four_mode_schedule_preserves_edits_tests_and_balances_positions(self):
        source = ' '.join('value' + str(i) for i in range(6)) + '\n#[cfg(test)]\nmod tests { original_assertions }'
        case = dict(negative=('wrong', 'value0', 'wrong0'),
                    edits=[('edit'+str(i), 'value'+str(i), 'new'+str(i)) for i in range(1, 6)])
        states = list(self.workflow.protocol_states(source, case))
        self.assertEqual(len(states), 21)
        edits = [s for s in states if s['state'] > 0]
        self.assertEqual(len(edits), 15)
        for s in states:
            self.assertEqual(set(s['modes']), set(self.workflow.CUSTOM))
            self.assertTrue(s['source'].endswith(b'mod tests { original_assertions }'))
        for state in range(1, 6):
            self.assertEqual(len({s['source'] for s in edits if s['state'] == state}), 1)
        for mode in self.workflow.CUSTOM:
            counts = Counter(s['modes'].index(mode) for s in edits)
            self.assertEqual(sorted(counts.values()), [3, 4, 4, 4])
        adjacent = Counter(pair for s in edits[:4] for pair in zip(s['modes'], s['modes'][1:]))
        self.assertEqual(len(adjacent), 12)
        self.assertEqual(set(adjacent.values()), {1})

    def rows(self, baseline=2, anchor=2.2, candidate=1.8, duplicate=2):
        rows = []
        for cycle in range(3):
            for state in range(1, 6):
                for mode in self.workflow.MODES:
                    value = dict(baseline=baseline, anchor=anchor, candidate=candidate,
                                 duplicate=duplicate, native=1, native_lines=.9, check=.3)[mode]
                    rows.append(dict(cycle=cycle, state=state, mode=mode, source_sha256=str(state),
                                     seconds=value, cpu=dict(total_seconds=value)))
        return rows

    def test_primary_needs_mechanism_gain_total_gain_and_acceptable_noise(self):
        self.assertTrue(self.workflow.assessment(self.rows(), 'token')['gate_passed'])
        for rows in [self.rows(candidate=2), self.rows(anchor=1.9), self.rows(duplicate=2.12)]:
            self.assertFalse(self.workflow.assessment(rows, 'token')['gate_passed'])
        rows = self.rows()
        for row in rows:
            if row['mode'] == 'candidate': row['cpu']['total_seconds'] = 2.2
        self.assertFalse(self.workflow.assessment(rows, 'token')['gate_passed'])

    def test_guards_cover_both_controls_and_reject_partial_or_mixed_source_pairs(self):
        for control in ['baseline', 'anchor']:
            rows = self.rows(**{control: 1.6})
            for case in ['folded', 'pgrust']:
                self.assertFalse(self.workflow.assessment(rows, case)['gate_passed'])
        rows = self.rows()
        for bad in [rows[:-1], rows + [rows[0]]]:
            with self.assertRaises(AssertionError): self.workflow.assessment(bad, 'token')
        mixed = copy.deepcopy(rows)
        mixed[0]['source_sha256'] = 'different'
        with self.assertRaises(AssertionError): self.workflow.assessment(mixed, 'token')


class CapacityCreditWorkflowTests(CallProtocolWorkflowTests):
    workflow = load_workflow('call-capacity-credit', 'capacity_credit_workflow')
