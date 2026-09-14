import copy
import hashlib
import unittest
from native_observation import validate,logical_counts,exact_logical_counts

def fixture():
    code=bytes(8)
    common=dict(pid=42,arena_base=4096,code_bytes=8,demand_regions=True,profiled=True,persistent_registers=True,resumable_calls=True)
    ranges=[dict(offset=0,end=4,function=0,name='f',kind='scalar_leaf',pc=None,pc_end=None),
            dict(offset=4,end=8,function=0,name='f',kind='resumable_region',pc=0,pc_end=1)]
    def f(offset,end,span):return dict(function=0,name='f',offset=offset,end=end,assertion_base=0,assertion_count=0,spans=[span])
    functions=[f(0,4,dict(offset=0,end=4,region_pc=0,pc=None,kind='scalar_leaf')),
               f(4,8,dict(offset=4,end=8,region_pc=0,pc=0,kind='operation'))]
    functions[1]['region_pc']=0
    operations=dict(common,schema_version=3,complete=True,reconstructed_bytes_match=True,
        code_sha256=hashlib.sha256(code).hexdigest(),functions=functions,spans=2)
    regions=dict(common,schema_version=2,architecture='aarch64',byte_order='little',native_call_stubs=False,ranges=ranges)
    profile=dict(functions=[dict(name='f',frame_size=16,registers=8,operations=['Imm','Return'],interpreted=[1,0],
        jit_blocks=[3,0],jit_block_ends=[1,0],jit_tree_blocks=[0,0],jit_tree_block_ends=[0,0],jit_scalar_hits=[2,2])])
    return operations,regions,code,profile,42

class Observations(unittest.TestCase):
    def test_interleaved_fragments_whole_fallback_and_scalar_ownership(self):
        operations, regions, _, profile, pid = fixture()
        other = copy.deepcopy(profile['functions'][0]); other['name'] = 'g'
        other['jit_block_ends'] = [2, 0]; profile['functions'].append(other)
        profile['functions'][0]['jit_block_ends'][1] = 2
        regions['ranges'].extend([
            dict(offset=8,end=16,function=1,name='g',kind='resumable_region',pc=0,pc_end=2),
            dict(offset=16,end=20,function=0,name='f',kind='resumable_return',pc=1,pc_end=2)])
        operations['functions'].extend([
            dict(offset=8,end=16,function=1,name='g',assertion_base=0,assertion_count=0,spans=[
                dict(offset=8,end=12,region_pc=0,pc=0,kind='operation'),
                dict(offset=12,end=16,region_pc=0,pc=1,kind='operation')]),
            dict(offset=16,end=20,function=0,name='f',region_pc=1,assertion_base=0,assertion_count=0,
                spans=[dict(offset=16,end=20,region_pc=1,pc=1,kind='transition')])])
        code=bytes(20); operations.update(code_bytes=20,code_sha256=hashlib.sha256(code).hexdigest(),spans=5)
        regions['code_bytes']=20
        args=(operations,regions,code,profile,pid)
        result=validate(*args)
        self.assertEqual(result['mapped_pcs'],4)
        for mutation in [lambda a:a[0].update(demand_regions=False),
                         lambda a:a[1].update(demand_regions=False),
                         lambda a:a[0]['functions'][1].pop('region_pc'),
                         lambda a:a[0]['functions'][3].update(region_pc=0),
                         lambda a:a[0]['functions'][3].update(region_pc=True),
                         lambda a:a[0]['functions'][3]['spans'][0].update(region_pc=0),
                         lambda a:a[0]['functions'][2].update(region_pc=1),
                         lambda a:a[0]['functions'][0].update(region_pc=0)]:
            changed=copy.deepcopy(args);mutation(changed)
            with self.assertRaises((AssertionError,KeyError)):validate(*changed)

    def test_independent_scalar_and_ordinary_bodies_share_original_function_identity(self):
        args=fixture();index=validate(*args)
        self.assertEqual(index['static_words'],{'scalar_leaf':1,'operation:Imm':1})
        self.assertEqual(index['mapped_pcs'],1)
        self.assertEqual(logical_counts(args[3]),([[6,2]],dict(native=7,interpreted=1,scalar=4,total=8)))
        previous=copy.deepcopy(args[3]);f=previous['functions'][0]
        f.pop('jit_scalar_hits');f['interpreted']=[3,2]
        self.assertEqual(exact_logical_counts(args[3],previous)['total'],8)
    def test_scalar_extent_identity_and_pc_claim_corruption_are_rejected(self):
        for mutation in [lambda a:a[0].update(schema_version=1),lambda a:a[1]['ranges'][0].update(pc=0),
                         lambda a:a[0]['functions'][0]['spans'][0].update(pc=0),
                         lambda a:a[0]['functions'][0].update(assertion_count=1),
                         lambda a:a[1]['ranges'][0].update(end=8),
                         lambda a:a[0]['functions'][1]['spans'][0].update(kind='scalar_leaf'),
                         lambda a:a[0]['functions'][0].update(name='other'),
                         lambda a:a[0].update(code_sha256='0'*64)]:
            args=fixture();mutation(args)
            with self.assertRaises((AssertionError,KeyError)):validate(*args)
    def test_negative_overflow_and_mismatched_logical_counts_are_rejected(self):
        for value in [[-1,0],[True,0],[2**64,0],[0],[]]:
            profile=fixture()[3];profile['functions'][0]['jit_scalar_hits']=value
            with self.assertRaises(AssertionError):logical_counts(profile)
        a=fixture()[3];b=copy.deepcopy(a);b['functions'][0]['jit_scalar_hits'][0]+=1
        with self.assertRaises(AssertionError):exact_logical_counts(a,b)
        b=copy.deepcopy(a);b['functions'][0]['jit_scalar_hits'][0]=2**64-1
        with self.assertRaises(AssertionError):logical_counts(b)
        b=copy.deepcopy(a);b['functions'][0]['jit_block_ends'][0]=0
        with self.assertRaises(AssertionError):logical_counts(b)

if __name__=='__main__':unittest.main()
