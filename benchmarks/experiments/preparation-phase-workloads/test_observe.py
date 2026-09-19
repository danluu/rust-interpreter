import copy,unittest
from observe import validate_observations

def report():
    rows=[[None,p,dict(calls=1,nanos=10 if p=='constructor' else 2)] for p in ['constructor','validation','jit_metadata','execution_metadata']]
    rows += [[0,p,dict(calls=1,nanos=n)] for p,n in [('compile_function',30),('scalar_callees',10),('ordinary_emission',10),('ordinary_publication',2)]]
    rows += [[1,p,dict(calls=1,nanos=n)] for p,n in [('scalar_function',8),('scalar_proof',2),('scalar_lowering',1),('scalar_emission',1),('scalar_publication',1)]]
    obs=dict(trace=dict(schema_version=1,complete=True,overflowed=False,dropped_intervals=0,bucket_limit=65536,rows=rows),
        functions=[dict(function=i,name=str(i),bytecode_operations=8,ordinary_prepared=i==0,ordinary_native_entries=int(i==0),scalar_native_bytes=4*int(i==1)) for i in [0,1]],
        compiled_functions=1,declined_functions=0,code_bytes=16)
    return dict(workers=1,preparation_observations=dict(schema_version=1,workers=[dict(worker=0,status='observed',observation=obs)]))

class Controls(unittest.TestCase):
    def reject(self,mutate):
        value=report();mutate(value,value['preparation_observations']['workers'][0]['observation'])
        with self.assertRaises((ValueError,KeyError,TypeError)):validate_observations(value)
    def test_nested_phases_stay_separate_and_workers_overlap(self):
        value=report();second=copy.deepcopy(value['preparation_observations']['workers'][0]);second['worker']=1
        value['workers']=2;value['preparation_observations']['workers'].append(second)
        result=validate_observations(value);self.assertEqual(len(result),2)
        self.assertEqual(result[0]['phase_ns']['compile_function'],30)
        self.assertEqual(result[0]['top_scalar'][0]['scalar_function_ns'],8)
    def test_incomplete_overflow_and_drop_rejected(self):
        for k,v in [('complete',False),('overflowed',True),('dropped_intervals',1),('bucket_limit',65537)]:
            self.reject(lambda r,o:o['trace'].__setitem__(k,v))
    def test_worker_identity_and_failure_rejected(self):
        self.reject(lambda r,o:r.__setitem__('workers',2))
        self.reject(lambda r,o:r['preparation_observations']['workers'][0].__setitem__('worker',1))
        self.reject(lambda r,o:r['preparation_observations']['workers'][0].__setitem__('status','diagnostic_failed'))
    def test_phase_identity_duplicates_and_counts_rejected(self):
        self.reject(lambda r,o:o['trace']['rows'].append(o['trace']['rows'][0]))
        self.reject(lambda r,o:o['trace']['rows'][0].__setitem__(1,'unknown'))
        self.reject(lambda r,o:o['trace']['rows'][0][2].__setitem__('calls',True))
        self.reject(lambda r,o:o['trace']['rows'][0][2].__setitem__('nanos',-1))
    def test_function_alias_and_scope_rejected(self):
        self.reject(lambda r,o:o['functions'].append(o['functions'][0]))
        self.reject(lambda r,o:o['trace']['rows'][0].__setitem__(0,0))
        self.reject(lambda r,o:o['trace']['rows'][4].__setitem__(0,7))
    def test_parent_intervals_must_cover_children(self):
        for index in [0,4,8]:self.reject(lambda r,o:o['trace']['rows'][index][2].__setitem__('nanos',0))
        self.reject(lambda r,o:o['trace']['rows'].pop(5))
    def test_empty_native_entries_are_not_reported_as_exact_declines(self):
        value=report();obs=value['preparation_observations']['workers'][0]['observation']
        obs['functions'][0]['ordinary_native_entries']=0
        result=validate_observations(value)[0]
        self.assertEqual(len(result['prepared_without_entries']),1)
        self.assertEqual(result['declined_functions'],0)

if __name__=='__main__':unittest.main()
