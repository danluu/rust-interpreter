import unittest
from regions import groups
def span(start,end,region,kind='operation',function=0):
    return dict(offset=start,end=end,region_pc=region,kind=kind,function=function)
class Groups(unittest.TestCase):
    def test_distinct_function_and_region_entries_are_kept(self):
        source=[span(0,4,0,'scalar_leaf'),span(4,8,0,'entry',1),span(8,12,0,function=1),
                span(12,16,5,'entry',1),span(16,20,0,'entry',2)]
        result=groups(source)
        self.assertEqual([(r['key'],r['offset'],r['end']) for r in result],
            [((1,0),4,12),((1,5),12,16),((2,0),16,20)])
    def test_gaps_and_interleaved_regions_are_rejected(self):
        for source in [[span(0,4,0),span(8,12,0)],
                       [span(0,4,0),span(4,8,1),span(8,12,0)]]:
            with self.assertRaises(AssertionError):groups(source)
if __name__=='__main__':unittest.main()
