import copy
import struct
import unittest
from mechanism import verify

def pair():
    def make(words,entry_end,kind='operation'):
        code=struct.pack('<'+'I'*len(words),*words)
        return dict(code_bytes=len(code),functions=[dict(function=0,name='fixture',assertion_base=0,assertion_count=0,
            spans=[dict(kind='entry',region_pc=0,pc=None,offset=0,end=entry_end),
                   dict(kind=kind,region_pc=0,pc=0,offset=entry_end,end=len(code))])]),code
    old=make([0xaa0703f3,0xaa0503e7,0xaa0603e8,0xd503201f,0xd503201f],12)
    new=make([0xaa0703f3,0xd280000e,0xf2e8000e,0xcb0e00a7,0x8b0e00c8,0xd503201f],20)
    return [*old,*new]

class MechanismTests(unittest.TestCase):
    def test_net_growth_reconciles_entry_cost_and_smaller_checked_parts(self):
        result=verify(*pair())
        self.assertEqual((result['entry_contexts'],result['added_entry_bytes'],result['removed_checked_bytes'],result['net_code_bytes']),(1,8,4,4))

    def test_wrong_context_register_or_bias_instruction_rejects(self):
        values=pair();words=list(struct.unpack('<6I',values[3]));words[3]^=1
        values[3]=struct.pack('<6I',*words)
        with self.assertRaises(AssertionError):verify(*values)

    def test_unaffected_part_size_change_is_rejected(self):
        values=pair()
        for index in [0,2]:values[index]['functions'][0]['spans'][1]['kind']='budget'
        with self.assertRaises(AssertionError):verify(*values)

    def test_shape_and_function_identity_are_bound(self):
        for field,value in [('function',1),('name','other'),('assertion_count',1)]:
            values=pair();values[2]['functions'][0][field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):verify(*values)
        values=pair();values[2]['functions'][0]['spans'][1]['pc']=1
        with self.assertRaises(AssertionError):verify(*values)

if __name__=='__main__':unittest.main()
