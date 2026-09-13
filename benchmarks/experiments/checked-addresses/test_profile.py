import copy
import importlib.util
from pathlib import Path
import unittest
import struct

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

    def range_fixture(self,literal=True,count=8):
        code=struct.pack('<IIII',0xeb0b01ef,(0xfa4029e0 if literal else 0xfa4021e0)|(count<<16),0x54000023,0xd65f03c0)
        return dict(code_bytes=16,functions=[dict(offset=0,end=16)]),code

    def test_literal_boundaries_and_dynamic_or_materialized_counts(self):
        for literal,count in [(True,0),(True,31),(False,10),(False,13)]:
            mapping,code=self.range_fixture(literal,count)
            got=profile.verify_range_checks(mapping,code)
            self.assertEqual(got['immediate_comparisons']+got['register_comparisons'],1)

    def test_wrong_carry_source_condition_default_flags_and_branch_rejected(self):
        mapping,code=self.range_fixture()
        for position,bit in [(0,29),(0,0),(1,12),(1,1),(2,0),(2,6)]:
            words=list(struct.unpack('<IIII',code));words[position]^=1<<bit
            with self.subTest(position=position,bit=bit),self.assertRaises(AssertionError):
                profile.verify_range_checks(mapping,struct.pack('<IIII',*words))

    def test_empty_or_boundary_truncated_range_check_rejected(self):
        mapping,code=self.range_fixture()
        mapping['functions'][0]['end']=8
        with self.assertRaises(AssertionError):profile.verify_range_checks(mapping,code)
        with self.assertRaises(AssertionError):profile.verify_range_checks(dict(code_bytes=0,functions=[]),b'')


if __name__ == '__main__':
    unittest.main()
