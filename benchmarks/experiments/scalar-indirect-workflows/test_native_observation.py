import copy
import hashlib
import unittest
from native_observation import validate,logical_counts,exact_logical_counts

def fixture():
    code=bytes(8)
    common=dict(pid=42,arena_base=4096,code_bytes=8,profiled=True,persistent_registers=True,resumable_calls=True)
    ranges=[dict(offset=0,end=4,function=0,name='f',kind='scalar_leaf',pc=None,pc_end=None),
            dict(offset=4,end=8,function=0,name='f',kind='resumable_region',pc=0,pc_end=1)]
    def f(offset,end,span):return dict(function=0,name='f',offset=offset,end=end,assertion_base=0,assertion_count=0,spans=[span])
    functions=[f(0,4,dict(offset=0,end=4,region_pc=0,pc=None,kind='scalar_leaf')),
               f(4,8,dict(offset=4,end=8,region_pc=0,pc=0,kind='operation'))]
    operations=dict(common,schema_version=2,complete=True,reconstructed_bytes_match=True,
        code_sha256=hashlib.sha256(code).hexdigest(),functions=functions,spans=2)
    regions=dict(common,schema_version=1,architecture='aarch64',byte_order='little',native_call_stubs=False,ranges=ranges)
    profile=dict(functions=[dict(name='f',frame_size=16,registers=8,operations=['Imm','Return'],interpreted=[1,0],
        jit_blocks=[3,0],jit_block_ends=[1,0],jit_tree_blocks=[0,0],jit_tree_block_ends=[0,0],jit_scalar_hits=[2,2])])
    return operations,regions,code,profile,42

class Observations(unittest.TestCase):
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
    def indirect_fixture(self):
        args=fixture()
        args[0]['indirect_calls']=args[1]['indirect_calls']=True
        args[3]['functions'][0]['operations'][0]='CallIndirect function: 2'
        args[1]['ranges'][1]['kind']='resumable_indirect_call'
        args[0]['functions'][1]['spans'][0]['kind']='transition'
        return args
    def test_indirect_transition_and_scalar_body_share_complete_code_ownership(self):
        index=validate(*self.indirect_fixture())
        self.assertEqual(index['static_words'],{'scalar_leaf':1,'transition:CallIndirect':1})
        self.assertEqual(index['mapped_pcs'],1)
        args=fixture()
        args[0]['indirect_calls']=args[1]['indirect_calls']=False
        validate(*args)
    def test_indirect_option_and_region_claim_corruption_are_rejected(self):
        mutations=[lambda a:a[0].update(indirect_calls=False),
            lambda a:a[1].update(indirect_calls=False),
            lambda a:(a[0].update(indirect_calls=1),a[1].update(indirect_calls=1)),
            lambda a:(a[0].pop('indirect_calls'),a[1].pop('indirect_calls')),
            lambda a:a[1]['ranges'][1].update(kind='resumable_call'),
            lambda a:a[3]['functions'][0]['operations'].__setitem__(0,'Call'),
            lambda a:(a[0].update(resumable_calls=False),a[1].update(resumable_calls=False))]
        for mutate in mutations:
            args=self.indirect_fixture();mutate(args)
            with self.assertRaises(AssertionError):validate(*args)
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
