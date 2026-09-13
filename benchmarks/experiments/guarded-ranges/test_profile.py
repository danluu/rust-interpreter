import copy
import hashlib
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

    def range_fixture(self):
        words=[0x540000e3,0x540000c8,0x540000a0,0x9e670170,
               0xd503201f,0x9e66020b,0xd503201f,0xd65f03c0]
        spans=[dict(offset=0,end=16,region_pc=0,pc=None,kind='range_guard'),
               dict(offset=16,end=20,region_pc=0,pc=None,kind='budget'),
               dict(offset=20,end=24,region_pc=0,pc=0,kind='operation'),
               dict(offset=24,end=28,region_pc=0,pc=None,kind='region_exit'),
               dict(offset=28,end=32,region_pc=0,pc=None,kind='budget_fallback')]
        return dict(code_bytes=32,functions=[dict(spans=spans)]),struct.pack('<8I',*words)

    def test_guard_branches_target_only_preflight_or_unchanged_entry_fallback(self):
        mapping,code=self.range_fixture()
        self.assertEqual(profile.verify_range_checks(mapping,code)['cached_base_reloads'],1)
        # Both a guest-fault/exit target and an out-of-function target reject.
        for target in [24,36]:
            words=list(struct.unpack('<8I',code));words[0]=0x54000003|((target//4)<<5)
            with self.assertRaises(AssertionError):profile.verify_range_checks(mapping,struct.pack('<8I',*words))

    def test_cache_save_register_and_reload_scope_are_verified(self):
        mapping,code=self.range_fixture()
        for change in range(5):
            m=copy.deepcopy(mapping);words=list(struct.unpack('<8I',code));rows=m['functions'][0]['spans']
            if change==0:words[3]^=1
            elif change==1:rows[2]['region_pc']=1
            elif change==2:rows[2]['pc']=None
            elif change==3:words[5]=0x9e660205
            else:rows[1]['offset']=12
            with self.subTest(change=change),self.assertRaises(AssertionError):
                profile.verify_range_checks(m,struct.pack('<8I',*words))

    def test_missing_guard_or_cache_reload_cannot_claim_the_mechanism(self):
        mapping,code=self.range_fixture()
        words=list(struct.unpack('<8I',code));words[5]=0xd503201f
        with self.assertRaises(AssertionError):profile.verify_range_checks(mapping,struct.pack('<8I',*words))
        mapping['functions'][0]['spans'][0]['kind']='entry'
        with self.assertRaises(AssertionError):profile.verify_range_checks(mapping,code)

    def test_inactive_control_requires_both_guard_and_cache_counts_to_be_zero(self):
        mapping,code=self.range_fixture()
        mapping['functions'][0]['spans'][0]['kind']='entry'
        with self.assertRaises(AssertionError):profile.verify_range_checks(mapping,code,require_active=False)
        words=list(struct.unpack('<8I',code));words[5]=0xd503201f
        got=profile.verify_range_checks(mapping,struct.pack('<8I',*words),require_active=False)
        self.assertEqual((got['guards'],got['cached_base_reloads']),(0,0))

    def test_only_the_inactive_folded_control_can_reuse_identical_adopted_code(self):
        mapping,code=self.range_fixture();mapping['functions'][0]['spans'][0]['kind']='entry'
        words=list(struct.unpack('<8I',code));words[5]=0xd503201f;code=struct.pack('<8I',*words)
        adopted=dict(comparisons=[dict(index=2,code_sha256=hashlib.sha256(code).hexdigest())])
        self.assertTrue(profile.verify_profile_mechanism(mapping,code,2,adopted)[1])
        for index in [0,1]:
            with self.assertRaises(AssertionError):profile.verify_profile_mechanism(mapping,code,index,adopted)
        words[4]^=1
        with self.assertRaises(AssertionError):profile.verify_profile_mechanism(mapping,struct.pack('<8I',*words),2,adopted)


if __name__ == '__main__':unittest.main()
