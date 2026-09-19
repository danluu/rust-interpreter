import copy,hashlib,struct,unittest
from compare import compare,immediate,BLR16

def fixture(base):
    words=[0xd65f03c0,*immediate(base),BLR16,0xd65f03c0]
    code=struct.pack('<'+'I'*len(words),*words);size=len(code)
    mapping=dict(pid=42,arena_base=base,code_bytes=size,code_sha256=hashlib.sha256(code).hexdigest(),functions=[
        dict(function=0,spans=[dict(kind='transition',pc=0,offset=4,end=size)])])
    regions=dict(pid=42,arena_base=base,code_bytes=size,ranges=[dict(kind='scalar_leaf',function=1,offset=0,end=4)])
    profile=dict(functions=[dict(operations=['Call { function: 1, args: [1], destination: 2 }'])])
    return code,mapping,regions,profile

def change_word(args,index,value):
    args=copy.deepcopy(args)
    words=list(struct.unpack('<'+'I'*(len(args[0])//4),args[0]));words[index]=value
    code=struct.pack('<'+'I'*len(words),*words);args[1]['code_sha256']=hashlib.sha256(code).hexdigest()
    return code,*args[1:]

class Relocations(unittest.TestCase):
    def setUp(self):self.a=fixture(0x105cdc000);self.b=fixture(0x105a78000)
    def test_exact_arena_relocation_retains_all_other_bytes(self):
        proof=compare(self.a,self.b);self.assertEqual(proof['relocations'],1)
        self.assertTrue(proof['exact_nonrelocation_bytes'] and proof['exact_scalar_targets'])
    def test_same_arena_remains_exact(self):self.assertEqual(compare(self.a,self.a)['relocations'],1)
    def test_ordinary_instruction_change_is_rejected(self):
        with self.assertRaisesRegex(AssertionError,'non-relocation'):compare(self.a,change_word(self.b,0,0xd503201f))
    def test_wrong_even_in_arena_target_is_rejected(self):
        with self.assertRaises(AssertionError):compare(self.a,change_word(self.b,1,immediate(self.b[2]['arena_base']+4)[0]))
    def test_wrong_register_or_branch_is_rejected(self):
        for i,value in [(2,immediate(self.b[2]['arena_base'])[1]|1),(4,0xd63f0220)]:
            with self.subTest(i=i),self.assertRaises(AssertionError):compare(self.a,change_word(copy.deepcopy(self.b),i,value))
    def test_noncanonical_immediate_and_unproven_address_are_rejected(self):
        with self.assertRaises(AssertionError):compare(self.a,change_word(self.b,2,immediate(self.b[2]['arena_base'])[2]))
        b=copy.deepcopy(self.b);b[1]['functions'][0]['spans'][0]['kind']='operation'
        with self.assertRaises(AssertionError):compare(self.a,b)
    def test_callee_or_entry_identity_cannot_be_substituted(self):
        for mutation in [lambda b:b[3]['functions'][0]['operations'].__setitem__(0,'Call { function: 2, args: [1], destination: 2 }'),
                         lambda b:b[2]['ranges'][0].update(offset=4,end=8)]:
            b=copy.deepcopy(self.b);mutation(b)
            with self.assertRaises(AssertionError):compare(self.a,b)
    def test_duplicate_or_out_of_bounds_entry_and_cross_span_immediate_are_rejected(self):
        for mutation in [lambda b:b[2]['ranges'].append(copy.deepcopy(b[2]['ranges'][0])),
                         lambda b:b[2]['ranges'][0].update(end=1000),
                         lambda b:b[1]['functions'][0]['spans'][0].update(offset=8)]:
            b=copy.deepcopy(self.b);mutation(b)
            with self.assertRaises(AssertionError):compare(self.a,b)
    def test_digest_and_map_mutations_are_rejected(self):
        for mutation in [lambda b:b[1].update(code_sha256='0'*64),lambda b:b[2].update(note='changed')]:
            b=copy.deepcopy(self.b);mutation(b)
            with self.assertRaises(AssertionError):compare(self.a,b)

if __name__=='__main__':unittest.main()
