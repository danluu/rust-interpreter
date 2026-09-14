import unittest
from scalar_coverage import analyze

class ScalarJoinTests(unittest.TestCase):
    def inputs(self):
        row=dict(function=0,name='fixture',frame_size=8,registers=2,bytecode_operations=4,native_incoming_calls=4,
            call_samples=2,return_samples=1,whole_function_native_operations=18,whole_function_interpreted_operations=1)
        scalar=dict(eligible=True,decline=None,nodes=5,live_nodes=4,live_phis=1,maximum_steps=4,
            reachable_operations=4,live_computations_per_pc=[0,1,0,2])
        typed=dict(status='passed',guest_commands=0,runtime_changes=0,functions=[dict(row,scalar=scalar)])
        group={k:row[k] for k in ['native_incoming_calls','call_samples','return_samples','whole_function_native_operations','whole_function_interpreted_operations']};group['functions']=1
        prior=dict(case='fixture',selected=[row],groups=dict(resolved_accesses=group))
        profile=dict(functions=[dict(name='fixture',frame_size=8,registers=2,operations=['a','b','c','d'],
            jit_blocks=[4,2,0,0],jit_block_ends=[4,2,0,0],interpreted=[1,0,0,0],jit_tree_blocks=[0]*4)])
        return typed,prior,profile

    def test_overlapping_original_native_ranges_and_declines_reconcile(self):
        t,p,f=self.inputs();r=analyze(t,p,f)
        self.assertEqual(r['groups']['scalar_ir']['weighted_native_scalar_computation_nodes'],14)
        t['functions'][0]['scalar'].update(eligible=False,decline='scalar_cycle',live_computations_per_pc=[])
        r=analyze(t,p,f);self.assertEqual(r['groups']['scalar_cycle']['native_incoming_calls'],4)
        self.assertEqual(r['selected'],[])

    def test_identity_counts_extents_and_scalar_shape_corruption_reject(self):
        for change in ['name','end','counts','nodes','maximum','tree']:
            t,p,f=self.inputs()
            if change=='name':f['functions'][0]['name']='other'
            elif change=='end':f['functions'][0]['jit_block_ends'][0]=5
            elif change=='counts':f['functions'][0]['jit_blocks'][0]=3
            elif change=='nodes':t['functions'][0]['scalar']['live_computations_per_pc']=[1]
            elif change=='maximum':t['functions'][0]['scalar']['maximum_steps']=5
            else:f['functions'][0]['jit_tree_blocks'][0]=1
            with self.subTest(change=change),self.assertRaises(AssertionError):analyze(t,p,f)

if __name__=='__main__':unittest.main()
