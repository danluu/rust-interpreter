import copy
import unittest
from coverage import analyze


class CoverageTests(unittest.TestCase):
    def inputs(self):
        rows=[dict(function=i,name='same',frame_size=8,registers=2,bytecode_operations=4,
            native_incoming_calls=100+i,call_samples=2,return_samples=1,
            whole_function_native_operations=800,whole_function_interpreted_operations=0) for i in range(2)]
        typed=dict(status='passed',guest_commands=0,runtime_changes=0,address_nonescape_proved=False,
            functions=[dict(r,arguments=[dict(offset=0,size=8)],result=dict(offset=0,size=0),
                plan=dict(eligible=True,decline=None,work=12,accesses=[dict(pc=2,reads=[dict(offset=0,size=8)],writes=[]),
                dict(pc=3,reads=[dict(offset=None,size=0)],writes=[])])) for r in rows])
        sums={k:sum(r[k] for r in rows) for k in ['native_incoming_calls','call_samples','return_samples',
            'whole_function_native_operations','whole_function_interpreted_operations']};sums['functions']=2
        prior=dict(case='fixture',selected=rows,groups=dict(bounded_confined_leaf=sums),generated_samples=10)
        return typed,prior

    def test_identity_partition_and_widths(self):
        typed,prior=self.inputs();result=analyze(typed,prior)
        self.assertEqual(result['groups']['resolved_accesses']['native_incoming_calls'],201)
        self.assertEqual([r['function'] for r in result['selected']],[0,1])
        self.assertEqual(result['selected'][0]['access_widths'],{'reads:8':1,'reads:0':1})
        typed['functions'][0]['plan'].update(eligible=False,decline=dict(reason='boundary_width'),accesses=[])
        result=analyze(typed,prior)
        self.assertEqual(result['groups']['boundary_width']['native_incoming_calls'],100)
        self.assertEqual(result['groups']['resolved_accesses']['native_incoming_calls'],101)

    def test_rejects_identity_extent_order_and_reconciliation_corruption(self):
        def duplicate(t,p):p['selected'][1]['function']=0
        def wrong_name(t,p):t['functions'][0]['name']='other'
        def overflow(t,p):t['functions'][0]['plan']['accesses'][0]['reads'][0]['size']=9
        def null_nonempty(t,p):t['functions'][0]['plan']['accesses'][0]['reads'][0]['offset']=None
        def fake_zero(t,p):t['functions'][0]['plan']['accesses'][1]['reads'][0]['offset']=0
        def repeated_pc(t,p):t['functions'][0]['plan']['accesses'][1]['pc']=2
        def partial(t,p):t['functions'][0]['plan'].update(eligible=False,decline=dict(reason='work_limit'))
        def counts(t,p):p['groups']['bounded_confined_leaf']['call_samples']=99
        for change in [duplicate,wrong_name,overflow,null_nonempty,fake_zero,repeated_pc,partial,counts]:
            t,p=self.inputs();change(t,p)
            with self.subTest(change=change.__name__),self.assertRaises(AssertionError):analyze(t,p)

if __name__=='__main__':unittest.main()
