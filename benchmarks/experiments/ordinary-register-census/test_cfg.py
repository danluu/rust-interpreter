import unittest
from cfg import analyze_cfg
from test_linear import mov
RET=0xd65f03c0
def dead(words,abi=False):return [pc for pc,_ in analyze_cfg(words,abi)['dead']]
class Cfg(unittest.TestCase):
    def test_both_sides_of_diamond_overwrite(self):
        self.assertEqual(dead([mov(9,1),0x54000060,mov(9,2),0x14000002,mov(9,3),RET]),[0])
        self.assertEqual(dead([mov(9,1),0x54000060,mov(9,2),0x14000001,RET]),[])
    def test_cycles_preserve_flag_dependencies_and_are_bounded(self):
        self.assertEqual(dead([mov(9,1),0x8b0a0129,0x54ffffe1,mov(9,0),RET]),[0,1])
        self.assertEqual(dead([mov(9,1),0xab0a0129,0x54ffffe1,mov(9,0),RET]),[])
        self.assertIsNone(analyze_cfg([mov(9,1),RET],work_limit=0))
    def test_external_and_unknown_transfers_observe_inputs(self):
        for word in [0x1400007f,0x54000fe0,0x34000fe9,0x36000fe9,0xd61f0200,0xd63f0200,0xffffffff]:
            self.assertEqual(dead([mov(9,1),word,mov(9,0),RET]),[])
    def test_c_return_contract_keeps_result_and_preserved_registers(self):
        self.assertEqual(dead([mov(9,1),RET]),[])
        self.assertEqual(dead([mov(9,1),RET],True),[0])
        for register in [0,18,19,29,30]:self.assertEqual(dead([mov(register,1),RET],True),[])
    def test_bit_test_and_memory_reads_retain_definitions(self):
        for branch in [0x34000049,0x36000049]:
            self.assertEqual(dead([mov(9,1),branch,mov(9,2),RET]),[])
        self.assertEqual(dead([mov(9,1),0xf9000009,mov(9,2),RET]),[])
if __name__=='__main__':unittest.main()
