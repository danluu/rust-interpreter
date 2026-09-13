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

    def guard_fixture(self, cost=3):
        spans = [dict(offset=0,end=8,region_pc=0,pc=None,kind='budget')]
        spans += [dict(offset=8,end=8,region_pc=0,pc=i,kind='operation') for i in range(cost)]
        spans += [dict(offset=8,end=12,region_pc=0,pc=None,kind='budget_fallback')]
        mapping = dict(resumable_calls=True,code_bytes=12,functions=[dict(function=0,spans=spans)])
        data = struct.pack('<III', 0xf10002d6 | (cost << 10), 0x54000023, 0x910002d6 | (cost << 10))
        counts = dict(functions=[dict(jit_block_ends=[cost],jit_tree_block_ends=[0])])
        return mapping,data,counts

    def test_actual_guard_bytes_and_branch_target_at_region_cost_boundaries(self):
        for cost in [1,3,1024]:
            mapping,data,counts=self.guard_fixture(cost)
            self.assertEqual(profile.verify_budget_guards(mapping,data,counts)['guards'],1)

    def test_wrong_debit_condition_target_restore_or_profile_interval_rejected(self):
        mapping,data,counts=self.guard_fixture()
        for position,bit in [(0,10),(1,0),(1,5),(2,10),(2,0)]:
            words=list(struct.unpack('<III',data));words[position] ^= 1 << bit
            with self.subTest(position=position,bit=bit),self.assertRaises(AssertionError):
                profile.verify_budget_guards(mapping,struct.pack('<III',*words),counts)
        counts['functions'][0]['jit_block_ends'][0]=4
        with self.assertRaises(AssertionError):profile.verify_budget_guards(mapping,data,counts)

    def test_missing_or_ambiguous_restoration_tail_rejected(self):
        for duplicate in [False,True]:
            mapping,data,counts=self.guard_fixture()
            spans=mapping['functions'][0]['spans']
            if duplicate:spans.append(copy.deepcopy(spans[-1]))
            else:spans.pop()
            with self.assertRaises(ValueError):profile.verify_budget_guards(mapping,data,counts)


if __name__ == '__main__':
    unittest.main()
