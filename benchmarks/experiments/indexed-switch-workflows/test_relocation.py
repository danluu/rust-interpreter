import struct,unittest
from relocation import normalize

def code(low,high,tail=0xd503201f):
    # Independent concrete MOVZ x16 / MOVK x16,LSL16 / BLR x16 encoding.
    return struct.pack('<IIII',0xd2800010|(low<<5),0xf2a00010|(high<<5),0xd63f0200,tail)

class RelocationTests(unittest.TestCase):
    def test_exact_declared_call_address_is_the_only_permitted_difference(self):
        result=normalize(code(0x1234,0x5678),code(0x3456,0x6789),[(0,3,0x56781234,0x67893456)])
        self.assertEqual(result['scalar_address_relocations'],1);self.assertEqual(result['changed_words'],2)
    def test_wrong_or_absent_target_binding_fails(self):
        for calls in [[],[(0,3,0x56781234,0x67893457)],[(0,3,0x56781235,0x67893456)]]:
            with self.assertRaises(AssertionError):normalize(code(0x1234,0x5678),code(0x3456,0x6789),calls)
    def test_other_words_and_missing_call_instruction_are_not_masked(self):
        for b in [code(0x3456,0x6789,0xd65f03c0),code(0x3456,0x6789).replace(struct.pack('<I',0xd63f0200),struct.pack('<I',0xd63f0220))]:
            with self.assertRaises(AssertionError):normalize(code(0x1234,0x5678),b,[(0,3,0x56781234,0x67893456)])
    def test_ambiguous_or_overlapping_ownership_fails(self):
        a=code(0x1234,0x5678);b=code(0x3456,0x6789)
        with self.assertRaises(AssertionError):normalize(a+a,b+b,[(0,8,0x56781234,0x67893456)])
        with self.assertRaises(AssertionError):normalize(a,b,[(0,3,0x56781234,0x67893456)]*2)
if __name__=='__main__':unittest.main()
