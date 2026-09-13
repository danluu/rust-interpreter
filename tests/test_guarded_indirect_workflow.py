"""The prospective margin penalizes noisy near-regressions, not large gains."""
import test_call_protocol_workflow as base


class GuardedIndirectWorkflowTests(base.CallProtocolWorkflowTests):
    workflow = base.load_workflow('guarded-indirect', 'guarded_indirect_workflow')

    def test_primary_needs_mechanism_gain_total_gain_and_acceptable_noise(self):
        self.assertTrue(self.workflow.assessment(self.rows(), 'token')['gate_passed'])
        # A 10% gain can exceed a 6% A/A margin; no old independent ceiling.
        self.assertTrue(self.workflow.assessment(self.rows(duplicate=2.12), 'token')['gate_passed'])
        for rows in [self.rows(candidate=2), self.rows(anchor=1.9), self.rows(duplicate=2.22)]:
            self.assertFalse(self.workflow.assessment(rows, 'token')['gate_passed'])
        rows = self.rows()
        for row in rows:
            if row['mode'] == 'candidate': row['cpu']['total_seconds'] = 2.0001
        self.assertFalse(self.workflow.assessment(rows, 'token')['gate_passed'])

    def test_heldout_margin_and_primary_cpu_margin_are_real_guards(self):
        for case in ['folded', 'pgrust']:
            self.assertTrue(self.workflow.assessment(self.rows(candidate=1.8, duplicate=2.12), case)['gate_passed'])
            self.assertFalse(self.workflow.assessment(self.rows(candidate=2, duplicate=2.12), case)['gate_passed'])
            self.assertFalse(self.workflow.assessment(self.rows(anchor=1.9, candidate=2, duplicate=2.02), case)['gate_passed'])
        rows = self.rows()
        for row in rows:
            row['cpu']['total_seconds'] = 2.12 if row['mode'] == 'duplicate' else 2
        self.assertFalse(self.workflow.assessment(rows, 'token')['gate_passed'])
