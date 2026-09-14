import copy
import unittest
from analyze import analyze


class JoinTests(unittest.TestCase):
    def inputs(self):
        typed=dict(status='passed',guest_commands=0,runtime_changes=0,functions=[
            dict(function=i,name='same name',frame_size=64,calls=[],confined=dict(eligible=True),
                 cfg_without_callee_effects=dict(eligible=True)) for i in range(2)])
        cost=dict(status='passed',guest_commands=0,case='fixture',generated_samples=10,callees=[
            dict(function=i,name='same name',frame_size=64,registers=4,bytecode_operations=8,
                 native_incoming_calls=100+i,native_outgoing_calls=0,whole_function_native_operations=800+i,
                 whole_function_interpreted_operations=0,call_samples=2,return_samples=1,
                 call_parts={'argument_source':2},return_parts={'return_dispatch':1}) for i in range(2)])
        return typed,cost

    def test_same_display_names_keep_distinct_typed_ids(self):
        result=analyze(*self.inputs())
        self.assertEqual(result['incoming_calls'],201)
        self.assertEqual(result['protocol_samples'],6)
        self.assertEqual([r['function'] for r in result['selected']],[1,0])
        for mutation in ['duplicate','negative','name','frame']:
            typed,cost=self.inputs()
            if mutation=='duplicate':cost['callees'][1]['function']=0
            elif mutation=='negative':cost['callees'][1]['function']=-1
            elif mutation=='name':cost['callees'][1]['name']='other'
            else:cost['callees'][1]['frame_size']=65
            with self.assertRaises(AssertionError):analyze(typed,cost)

    def test_confinement_initialization_calls_and_shape_are_separate(self):
        for category in ['unconfined','has_direct_callee','needs_initial_zeroes','outside_small_shape']:
            typed,cost=self.inputs();f=typed['functions'][0]
            if category=='unconfined':f['confined']['eligible']=False
            elif category=='has_direct_callee':f['calls']=[dict(pc=1,callee=1)]
            elif category=='needs_initial_zeroes':f['cfg_without_callee_effects']['eligible']=False
            else:cost['callees'][0]['registers']=513
            result=analyze(typed,cost)
            self.assertEqual(result['groups'][category]['native_incoming_calls'],100)
            self.assertEqual(result['groups']['bounded_confined_leaf']['native_incoming_calls'],101)
            self.assertEqual(result['protocol_samples'],6)

    def test_missing_partition_or_conflicting_leaf_effects_reject(self):
        for field,value in [('call_samples',3),('return_samples',2),('native_outgoing_calls',1)]:
            typed,cost=self.inputs();cost['callees'][0][field]=value
            with self.assertRaises(AssertionError):analyze(typed,cost)
        typed,cost=self.inputs();typed['functions'].reverse()
        with self.assertRaises(AssertionError):analyze(typed,cost)

if __name__=='__main__':unittest.main()
