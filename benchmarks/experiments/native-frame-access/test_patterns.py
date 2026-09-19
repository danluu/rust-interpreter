import unittest
from patterns import PATTERNS,recognize,classify


class Patterns(unittest.TestCase):
    def test_complete_exact_sequences_keep_both_memory_pcs(self):
        for name,(operation,words,memory) in PATTERNS.items():
            row,=recognize(words,operation,64)
            self.assertEqual(row['kind'],name)
            self.assertEqual(row['memory_offsets'],[64+4*i for i in memory])
            self.assertEqual(row['prospective_words_saved'],1)

    def test_every_single_bit_change_rejects_the_sequence(self):
        for operation,words,_ in PATTERNS.values():
            for index in range(len(words)):
                for bit in range(32):
                    changed=list(words);changed[index]^=1<<bit
                    self.assertEqual(recognize(changed,operation),[])

    def test_separate_spans_never_form_a_pair(self):
        for operation,words,_ in PATTERNS.values():
            for cut in range(1,len(words)):
                self.assertEqual(recognize(words[:cut],operation),[])
                self.assertEqual(recognize(words[cut:],operation,cut*4),[])

    def test_call_and_return_identity_cannot_be_interchanged(self):
        for operation,words,_ in PATTERNS.values():
            self.assertEqual(recognize(words,'Return' if operation=='Call' else 'Call'),[])
        with self.assertRaises(AssertionError):recognize([], 'Copy')

    def test_collapsed_sample_uncertainty_is_retained(self):
        sites={4:'a',8:'a',12:'b'}
        self.assertEqual(classify([4,8],sites),('certain','a'))
        self.assertEqual(classify([0,16],sites),('other',None))
        for offsets in [[0,4],[4,12]]:
            self.assertEqual(classify(offsets,sites),('ambiguous',None))

    def test_bounds_alignment_and_words_are_checked(self):
        for base in [-4,1,16*1024**2+4,True]:
            with self.assertRaises(AssertionError):recognize([], 'Call',base)
        for words in [[-1],[2**32],[True]]:
            with self.assertRaises(AssertionError):recognize(words,'Call')
        with self.assertRaises(AssertionError):recognize([0],'Call',16*1024**2)
        for offsets in [[],[True],[3],[-4]]:
            with self.assertRaises(AssertionError):classify(offsets,{})


if __name__=='__main__':unittest.main()
