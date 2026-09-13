"""Independent small-profile controls for changed native partitions."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('bridge_profile',Path(__file__).with_name('profile.py'))
profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)

def row(ops,interpreted,ordinary=None,ends=None,tree=None,tree_ends=None):
    size=len(ops)
    return dict(name='same name',frame_size=16,registers=2,operations=ops,interpreted=interpreted,
        jit_blocks=ordinary or [0]*size,jit_block_ends=ends or [0]*size,
        jit_tree_blocks=tree or [0]*size,jit_tree_block_ends=tree_ends or [0]*size)

def fixture():
    baseline=dict(functions=[row(['Call { function: 1 }','Return'],[1,1]),row(['Return'],[1])])
    current=dict(functions=[row(['Call { function: 1 }','Return'],[0,1],[1,0],[1,0]),
        row(['Return'],[0],tree=[1],tree_ends=[1])])
    stats=dict(instructions=3,jit_instructions=2,jit_tree_instructions=1,jit_tree_calls=0,
        jit_tree_entries=1,jit_resumable_calls=1,jit_resumable_returns=1)
    return baseline,current,stats

class ProfileContracts(unittest.TestCase):
    def test_backend_changes_preserve_logical_identity(self):
        old,new,stats=fixture();result=profile.reconcile(new,old,stats)
        self.assertTrue(result['exact_logical_per_pc_counts']);self.assertEqual(len(result['changed_backend_functions']),2)
        self.assertEqual(result['totals']['tree_function_entries'],1)

    def test_counter_fields_all_reconcile(self):
        old,new,stats=fixture()
        for field in stats:
            bad=dict(stats);bad[field]+=1
            with self.subTest(field=field),self.assertRaises(AssertionError):profile.reconcile(new,old,bad)

    def test_changed_logical_count_fails_even_when_totals_are_adjusted(self):
        old,new,stats=fixture();new['functions'][1]['jit_tree_blocks'][0]=2
        for field in ['instructions','jit_instructions','jit_tree_instructions','jit_tree_entries','jit_resumable_returns']:stats[field]+=1
        with self.assertRaises(AssertionError):profile.reconcile(new,old,stats)

    def test_function_shape_and_order_are_bound(self):
        old,new,stats=fixture()
        for field,value in [('name','other'),('registers',3),('frame_size',32),('operations',['Return','Return'])]:
            bad=copy.deepcopy(new);bad['functions'][0][field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):profile.reconcile(bad,old,stats)
        with self.assertRaises(AssertionError):profile.reconcile(dict(functions=new['functions'][:1]),old,stats)

    def test_invalid_intervals_and_values_fail(self):
        old,new,stats=fixture()
        for field,value in [('jit_tree_block_ends',[0]),('jit_tree_block_ends',[2]),('jit_tree_blocks',[-1]),('interpreted',[True])]:
            bad=copy.deepcopy(new);bad['functions'][1][field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):profile.reconcile(bad,old,stats)

    def test_region_expansion_matches_explicit_operation_counts(self):
        f=row(['Imm','Load','Store','Return'],[0]*4,[2,0,3,0],[2,0,4,0])
        self.assertEqual(profile.expanded(f,'jit_blocks'),[2,2,3,3])
        self.assertEqual(profile.expanded(f,'jit_tree_blocks'),[0,0,0,0])

if __name__=='__main__':unittest.main()
