import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('shift_profile', Path(__file__).with_name('profile.py'))
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.reference = dict(functions=[dict(name='guest', operations=['Imm', 'Shr'],
            interpreted=[1, 0], jit_blocks=[0, 3], jit_block_ends=[0, 3],
            jit_tree_blocks=[0, 2], jit_tree_block_ends=[0, 2])])

    def test_same_totals_cannot_hide_a_per_pc_or_native_interval_change(self):
        self.assertTrue(profile.exact_profile_counts(copy.deepcopy(self.reference), self.reference))
        for field in self.reference['functions'][0]:
            changed = copy.deepcopy(self.reference)
            value = changed['functions'][0][field]
            changed['functions'][0][field] = 'other' if isinstance(value, str) else list(reversed(value))
            with self.subTest(field=field), self.assertRaises(AssertionError):
                profile.exact_profile_counts(changed, self.reference)

    def test_missing_or_extra_function_is_rejected(self):
        for functions in [[], self.reference['functions'] * 2]:
            with self.assertRaises(AssertionError):
                profile.exact_profile_counts(dict(functions=functions), self.reference)


if __name__ == '__main__':
    unittest.main()
