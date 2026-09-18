import unittest
from attribute import selection,payload_selection
class Attribution(unittest.TestCase):
    def rows(self):return [dict(function=0,region_pc=0,pc=None,kind='entry',offset=0,end=8),dict(function=0,region_pc=0,pc=1,kind='operation',offset=8,end=20),dict(function=0,region_pc=0,pc=2,kind='operation',offset=20,end=24)]
    def test_only_one_exact_operation_selects_a_read(self):
        rows=self.rows();hit={'operation':'Load'};hits={(0,1):hit}
        self.assertIs(selection(rows,[0,8,20],[8,12,16],hits),hit)
        self.assertIsNone(selection(rows,[0,8,20],[0,4],hits));self.assertIsNone(selection(rows,[0,8,20],[20],hits))
    def test_unknown_or_ambiguous_native_offsets_are_rejected(self):
        for offsets in [[],[-4],[9],[24],[8,20],[0,8]]:
            with self.assertRaises(AssertionError):selection(self.rows(),[0,8,20],offsets,{(0,1):{}})
    def test_payload_selection_excludes_destination_and_publication(self):
        rows=[dict(offset=0,end=4,part='guarded_address',access='source'),dict(offset=4,end=8,part='guarded_address',access='destination'),dict(offset=8,end=12,part='load_data',access='none'),dict(offset=12,end=16,part='register_publication',access='none')]
        for offset,expected in [(0,True),(4,False),(8,True),(12,False)]:self.assertEqual(payload_selection(rows,[0,4,8,12],[offset]),expected)
        with self.assertRaises(AssertionError):payload_selection(rows,[0,4,8,12],[0,4])
if __name__=='__main__':unittest.main()
