import unittest
from linear import analyze,direct_target

def mov(reg,value):return 0xd2800000|(value<<5)|reg
def dead(words,entries=()):return [pc for pc,_ in analyze(words,entries)['dead']]

class Linear(unittest.TestCase):
    def test_overwrite_and_live_final_state(self):
        self.assertEqual(dead([mov(9,1),mov(9,2)]),[0])
        self.assertEqual(dead([mov(9,1),0xf2800029,mov(10,2)]),[])
    def test_unknown_vector_and_control_barriers(self):
        for barrier in [0xffffffff,0x9e670120,0x14000001,0x94000001,0x54000020,0xd63f0200,0xd65f03c0]:
            self.assertEqual(dead([mov(9,1),barrier,mov(9,2)]),[])
    def test_external_entry_and_branch_signs(self):
        self.assertEqual(dead([mov(9,1),mov(10,0),mov(9,2)],entries=[1]),[])
        for word in [0x17ffffff,0x97ffffff,0x54ffffe0,0x34ffffe0,0x36ffffe0]:
            self.assertEqual(direct_target(word,5),4)
    def test_memory_side_effects_and_address_uses(self):
        self.assertEqual(dead([mov(9,1),0xf9000009,mov(9,2)]),[])
        self.assertEqual(dead([mov(9,1),0xf940012a,mov(9,2)]),[])
        self.assertEqual(dead([0xf9400009,mov(9,2)]),[])
        self.assertEqual(dead([mov(9,1),0xf9400009]),[0])
    def test_flags_and_pure_chain(self):
        # Both flags and destination are observable at a barrier/end.
        self.assertEqual(dead([0xab0a0129,mov(9,2)]),[])
        # A later flag-setting instruction kills flags, but its input stays live.
        self.assertEqual(dead([0xab0a0129,0xeb0c017f,mov(9,2)]),[0])
        self.assertEqual(dead([mov(9,1),0x8b090129,mov(9,2)]),[0,1])

if __name__=='__main__':unittest.main()
