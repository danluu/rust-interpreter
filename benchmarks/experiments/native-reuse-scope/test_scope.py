import copy,hashlib,unittest
from scope import compare,native_pool,anchored_pool

def fixture():
    rows=[]
    for i in range(3):rows.append(dict(function=i,name_sha256=hashlib.sha256(str(i).encode()).hexdigest(),
        body_sha256=str(i)*64,necessary_inputs_sha256=str(i+3)*64,operations=2,serialized_bytes=20,
        direct_callees=[1] if i==0 else []))
    return dict(artifact_sha256='a'*64,identities=dict(namespace_sha256='b'*64,uses_heap=False,functions=rows))

def mapping():
    return dict(schema_version=1,architecture='aarch64',byte_order='little',profiled=False,
        native_call_stubs=False,persistent_registers=True,resumable_calls=True,code_bytes=20,ranges=[
        dict(offset=0,end=12,function=0,name='0',kind='resumable_call',pc=0,pc_end=1),
        dict(offset=12,end=20,function=1,name='1',kind='scalar_leaf',pc=None,pc_end=None)])

class ScopeControls(unittest.TestCase):
    def test_initializer_namespace_change_is_separate_from_body_dependencies(self):
        old=fixture();new=copy.deepcopy(old);new['identities']['namespace_sha256']='c'*64
        r=compare(old,new);self.assertFalse(r['namespace_same']);self.assertEqual(r['same_body_callees_heap_count'],3)
    def test_changed_callee_excludes_unchanged_caller_and_both_native_extents(self):
        old=fixture();new=copy.deepcopy(old);new['identities']['functions'][1]['body_sha256']='c'*64
        r=compare(old,new);self.assertEqual(r['same_body'],2);self.assertEqual(r['same_body_and_direct_callees'],1)
        w,_=native_pool(mapping(),old);r=anchored_pool(old,new,w)
        self.assertEqual(r['original_bytes_with_same_body'],12);self.assertEqual(r['original_bytes_with_stable_scope'],0)
    def test_heap_mode_and_function_count_changes_fail_conservative_scope(self):
        for mutation in [lambda n:n['identities'].update(uses_heap=True),lambda n:n['identities']['functions'].pop()]:
            old=fixture();new=copy.deepcopy(old);mutation(new)
            self.assertEqual(compare(old,new)['same_body_callees_heap_count'],0)
    def test_shifted_identical_body_is_not_rebound_to_new_numeric_id(self):
        old=fixture();new=copy.deepcopy(old);a=new['identities']['functions'];a[1],a[2]=a[2],a[1]
        a[1]['function']=1;a[2]['function']=2
        self.assertEqual(compare(old,new)['same_body_and_direct_callees'],0)
    def test_native_map_requires_complete_partition_exact_names_and_supported_options(self):
        w,k=native_pool(mapping(),fixture());self.assertEqual(sum(w.values()),20);self.assertEqual(k['scalar_leaf'],8)
        for mutation in [lambda m:m['ranges'][1].update(offset=8),lambda m:m['ranges'][1].update(offset=16),
                         lambda m:m['ranges'][0].update(name='wrong'),lambda m:m.update(profiled=True),
                         lambda m:m['ranges'][0].update(pc_end=3),lambda m:m['ranges'][1].update(function=True)]:
            m=mapping();mutation(m)
            with self.assertRaises(AssertionError):native_pool(m,fixture())

if __name__=='__main__':unittest.main()
