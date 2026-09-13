"""Emitter changes must preserve each VM operation and native region."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('paired_profile', Path(__file__).with_name('profile.py'))
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


class PairedProfileTests(unittest.TestCase):
    def fixture(self):
        return {'functions': [dict(name='caller', operations=['Load', 'Mul128', 'Return'],
            interpreted=[0, 7, 0], jit_blocks=[7, 0, 7], jit_block_ends=[1, 0, 3],
            jit_tree_blocks=[0, 0, 0], jit_tree_block_ends=[0, 0, 0])]}

    def test_matching_counts_and_independent_copy(self):
        prior = self.fixture()
        self.assertTrue(profile.exact_profile_counts(copy.deepcopy(prior), prior))

    def test_same_total_different_pc_or_region_fails(self):
        prior = self.fixture()
        for key, replacement in [('interpreted', [1, 6, 0]),
                ('jit_blocks', [6, 0, 8]), ('jit_block_ends', [2, 0, 3]),
                ('jit_tree_blocks', [1, 0, 0]), ('jit_tree_block_ends', [1, 0, 0]),
                ('operations', ['Store', 'Mul128', 'Return']), ('name', 'different')]:
            current = copy.deepcopy(prior)
            current['functions'][0][key] = replacement
            with self.assertRaises(AssertionError):
                profile.exact_profile_counts(current, prior)
        with self.assertRaises(AssertionError):
            profile.exact_profile_counts({'functions': []}, prior)


if __name__ == '__main__':
    unittest.main()
