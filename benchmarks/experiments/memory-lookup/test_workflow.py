"""Apply the documented held-out margin without an extra CPU ceiling."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
import test_guarded_indirect_workflow as base


class MemoryLookupWorkflowTests(base.GuardedIndirectWorkflowTests):
    workflow = base.base.load_workflow('memory-lookup', 'memory_lookup_workflow')

    def cpu_rows(self, candidate, duplicate):
        rows = self.rows()
        for row in rows:
            row['cpu']['total_seconds'] = {
                'baseline': 2, 'anchor': 2.2, 'candidate': candidate,
                'duplicate': duplicate, 'native': 1, 'native_lines': .9, 'check': .3,
            }[row['mode']]
        return rows

    def test_heldout_accepts_small_cpu_increase_within_documented_margin(self):
        rows = self.cpu_rows(candidate=2.02, duplicate=2.04)
        for case in ['folded', 'pgrust']:
            result = self.workflow.assessment(rows, case)
            self.assertAlmostEqual(result['cpu_with_noise_margin'], 1.03)
            self.assertTrue(result['gate_passed'])
        self.assertFalse(self.workflow.assessment(rows, 'token')['gate_passed'])

    def test_heldout_rejects_margin_between_105_and_1055(self):
        for duplicate, passed in [(2.098, True), (2.102, False), (2.108, False)]:
            rows = self.cpu_rows(candidate=2, duplicate=duplicate)
            for case in ['folded', 'pgrust']:
                self.assertEqual(self.workflow.assessment(rows, case)['gate_passed'], passed)
