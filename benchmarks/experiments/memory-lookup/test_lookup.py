import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('memory_lookup_routing', Path(__file__).with_name('workflows.py'))
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


class LookupRoutingTests(unittest.TestCase):
    def test_only_candidate_requests_cached_identity(self):
        for mode in ['baseline', 'duplicate', 'anchor']:
            self.assertEqual(workflow.lookup_args(mode), ['--toolchain-lookup', 'fresh'])
        self.assertEqual(workflow.lookup_args('candidate'), ['--toolchain-lookup', 'cached'])
        with self.assertRaises(AssertionError):
            workflow.lookup_args('native')

    def test_measured_candidate_requires_a_hit_and_controls_require_fresh(self):
        trace = lambda mode, outcome: {'toolchain_lookup': dict(mode=mode, outcome=outcome)}
        self.assertTrue(workflow.validate_lookup(trace('cached', 'miss'), 'candidate', 0, 0))
        self.assertTrue(workflow.validate_lookup(trace('cached', 'hit'), 'candidate', 2, 5))
        for cycle, state in [(0, -1), (0, 1), (1, 0), (2, 5), (3, 0)]:
            with self.assertRaises(AssertionError):
                workflow.validate_lookup(trace('cached', 'miss'), 'candidate', cycle, state)
        for mode in ['baseline', 'duplicate', 'anchor']:
            self.assertTrue(workflow.validate_lookup(trace('fresh', 'fresh'), mode, 0, 0))
            with self.assertRaises(AssertionError):
                workflow.validate_lookup(trace('cached', 'hit'), mode, 0, 0)
        with self.assertRaises(AssertionError):
            workflow.validate_lookup(trace('fresh', 'fresh'), 'candidate', 0, 0)
