import copy,hashlib,unittest
from native_observation import validate


def fixture(mode='fast',guarded=False):
    def budget(n):return [0xd280000a|(n<<5),0xeb0a02df,0x54000003,0xcb0a02d6]
    words=[0xd503201f,*budget(3),0x14000000,0,0]
    spans=[dict(offset=a,end=b,region_pc=pc,pc=op,kind=kind) for a,b,pc,op,kind in [
        (0,4,0,None,'entry'),(4,20,0,None,'budget'),(20,24,0,0,'operation'),(24,32,0,None,'budget_edge')]]
    if mode=='transition':
        words += [0xd503201f,0xeb1f02df,0x54000000]
        spans.append(dict(offset=32,end=44,region_pc=1,pc=1,kind='transition'));target=36;kind='resumable_return'
    else:
        words += [0xd503201f]
        spans.append(dict(offset=32,end=36,region_pc=1,pc=None,kind='entry'))
        if guarded:
            words.append(0xd503201f);spans.append(dict(offset=36,end=40,region_pc=1,pc=None,kind='range_guard'))
        start=len(words)*4;words+=budget(1)
        spans.append(dict(offset=start,end=start+16,region_pc=1,pc=None,kind='budget'))
        spans.append(dict(offset=start+16,end=start+20,region_pc=1,pc=1,kind='operation'))
        words.append(0xd503201f);target=start+16 if mode=='fast' else 36;kind='resumable_region'
    refund=1 if mode=='fast' else 2
    words[6]=0x910002d6|(refund<<10);words[7]=0x14000000|(((target-28)//4)&0x3ffffff)
    code=b''.join(w.to_bytes(4,'little') for w in words);end=len(code)
    common=dict(pid=42,arena_base=4096,code_bytes=end,profiled=True,persistent_registers=True,resumable_calls=True)
    ranges=[dict(offset=0,end=32,function=0,name='f',kind='resumable_region',pc=0,pc_end=1),
            dict(offset=32,end=end,function=0,name='f',kind=kind,pc=1,pc_end=2)]
    opmap=dict(common,schema_version=2,complete=True,reconstructed_bytes_match=True,code_sha256=hashlib.sha256(code).hexdigest(),
        functions=[dict(function=0,name='f',offset=0,end=end,assertion_base=0,assertion_count=0,spans=spans)],spans=len(spans))
    regions=dict(common,schema_version=1,architecture='aarch64',byte_order='little',native_call_stubs=False,ranges=ranges)
    profile=dict(functions=[dict(name='f',frame_size=32,registers=8,operations=['Jump','Return' if mode=='transition' else 'Imm'],
        interpreted=[0,0],jit_blocks=[1,1],jit_block_ends=[1,2],jit_tree_blocks=[0,0],jit_tree_block_ends=[0,0])])
    return [opmap,regions,code,profile,42]


def change_word(args,at,value):
    code=bytearray(args[2]);code[at:at+4]=value.to_bytes(4,'little');args[2]=bytes(code)
    args[0]['code_sha256']=hashlib.sha256(args[2]).hexdigest()


class BudgetEdges(unittest.TestCase):
    def test_fast_checked_and_transition_refunds_have_explicit_ownership(self):
        for mode in ['fast','checked','transition']:
            args=fixture(mode);edges=validate(*args)['budget_edges'];self.assertEqual(len(edges),1)
            self.assertEqual((edges[0]['source_pc'],edges[0]['target_pc'],edges[0]['mode']),(0,1,mode))
            self.assertEqual(edges[0]['refund'],1 if mode=='fast' else 2)
    def test_refund_cannot_write_flags_other_registers_or_zero(self):
        for value in [0xb10006d6,0x910006d5,0x910006b6,0x910002d6,0x914006d6]:
            args=fixture();change_word(args,24,value)
            with self.assertRaises(AssertionError):validate(*args)
    def test_edge_cannot_call_escape_code_or_enter_the_middle_of_a_guard(self):
        for value in [0x94000006,0x140000ff,0x14000003]:
            args=fixture();change_word(args,28,value)
            with self.assertRaises(AssertionError):validate(*args)
    def test_guard_encoding_and_credit_arithmetic_are_checked(self):
        for at,value in [(4,0xd280000a),(4,0xd280000a|(4097<<5)),(4,0xd280000a|(4<<5)),
                         (8,0xeb0a02bf),(16,0xcb0a02d5)]:
            args=fixture();change_word(args,at,value)
            with self.assertRaises(AssertionError):validate(*args)
    def test_guarded_destinations_require_checked_entry_and_full_refund(self):
        with self.assertRaises(AssertionError):validate(*fixture('fast',True))
        self.assertEqual(validate(*fixture('checked',True))['budget_edges'][0]['mode'],'checked')
    def test_transition_must_receive_full_suffix_before_its_budget_check(self):
        for at,value in [(24,0x910006d6),(36,0xeb1e02df),(40,0x54000001)]:
            args=fixture('transition');change_word(args,at,value)
            with self.assertRaises(AssertionError):validate(*args)

if __name__=='__main__':unittest.main()
