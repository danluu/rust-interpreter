import unittest
from native_coverage import analyze

class NativeJoinTests(unittest.TestCase):
    def inputs(self):
        row=dict(function=0,name='same',frame_size=8,registers=2,bytecode_operations=4,scalar=dict(eligible=True),
            native_incoming_calls=100,call_samples=2,return_samples=1,whole_function_native_operations=400,
            whole_function_interpreted_operations=0,weighted_native_scalar_computation_nodes=100)
        t=dict(status='passed',guest_commands=0,runtime_changes=0,functions=[dict(row,native=[
            dict(profiled=p,eligible=True,code_bytes=100,stack_bytes=16) for p in [False,True]])])
        totals={k:row[k] for k in ['native_incoming_calls','call_samples','return_samples','whole_function_native_operations',
            'whole_function_interpreted_operations','weighted_native_scalar_computation_nodes']};totals['functions']=1
        return t,dict(case='fixture',selected=[row],groups=dict(scalar_ir=totals))
    def test_native_and_explicit_width_declines_reconcile(self):
        t,p=self.inputs();r=analyze(t,p);self.assertEqual(r['groups']['native_scalar']['native_incoming_calls'],100)
        t['functions'][0]['native']=[dict(profiled=x,eligible=False,decline='native_integer_128') for x in [False,True]]
        r=analyze(t,p);self.assertEqual(r['groups']['native_integer_128']['call_samples'],2);self.assertEqual(r['selected'],[])
    def test_mixed_modes_identity_caps_and_reconciliation_reject(self):
        for change in ['name','scalar','mode','admission','stack','code','counts']:
            t,p=self.inputs();f=t['functions'][0]
            if change=='name':f['name']='other'
            elif change=='scalar':f['scalar']={}
            elif change=='mode':f['native'][0]['profiled']=True
            elif change=='admission':f['native'][0]['eligible']=False
            elif change=='stack':f['native'][0]['stack_bytes']=32768
            elif change=='code':f['native'][0]['code_bytes']=65536*4+4
            else:p['groups']['scalar_ir']['call_samples']=3
            with self.subTest(change=change),self.assertRaises(AssertionError):analyze(t,p)
if __name__=='__main__':unittest.main()
