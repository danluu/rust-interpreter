import unittest
from census import decode,scan


def old_words(value,reg=14):
    words=[0xd2800000|((value&0xffff)<<5)|reg]
    for shift in range(1,4):
        part=(value>>(16*shift))&0xffff
        if part:words.append(0xf2800000|(shift<<21)|(part<<5)|reg)
    return words


class CensusTests(unittest.TestCase):
    def test_exact_tag_prefix_is_the_removable_word(self):
        words=old_words(1<<62)
        self.assertEqual(words,[0xd280000e,0xf2e8000e])
        sequences,classes=scan(words,[dict(offset=0,end=8,kind='region')])
        self.assertEqual(sequences[0]['value'],1<<62)
        self.assertEqual(sequences[0]['shifted_zero_words'],1)
        self.assertEqual(classes,{0:(True,True,'region'),1:(False,True,'region')})

    def test_all_halfword_patterns_have_exact_values_and_minimum_move_counts(self):
        from itertools import product
        for parts in product([0,1,0x8000,0xffff],repeat=4):
            value=sum(p<<(16*i) for i,p in enumerate(parts));words=old_words(value)
            result=decode(words,0,len(words))
            self.assertEqual(result['value'],value)
            # Exhaust all seed positions and both constant fills independently.
            costs=[1+sum(parts[i]!=fill for i in range(4) if i!=seed)
                   for fill in [0,0xffff] for seed in range(4)]
            self.assertEqual(result['minimal_wide_words'],min(costs))
            self.assertEqual(result['removable_zero_seed'],value!=0 and parts[0]==0)

    def test_zero_and_all_ones_still_need_one_instruction(self):
        for value in [0,(1<<64)-1]:
            words=old_words(value);r=decode(words,0,len(words))
            self.assertEqual(r['minimal_wide_words'],1)
        self.assertEqual(decode(old_words(0),0,1)['old_words'],1)
        self.assertEqual(decode(old_words((1<<64)-1),0,4)['old_words'],4)

    def test_other_register_or_instruction_ends_a_sequence(self):
        words=old_words(1<<62)
        self.assertEqual(decode([words[0],words[1]^1],0,2)['end'],1)
        self.assertEqual(decode([words[0],0xd503201f,words[1]],0,3)['end'],1)
        for word in [0x5280000e,0xd2a0000e,0xf2e8000e,0x9280000e,0xd503201f]:
            self.assertIsNone(decode([word],0,1))

    def test_sequences_cannot_cross_published_ranges(self):
        words=old_words(1<<62)
        sequences,classes=scan(words,[dict(offset=0,end=4,kind='one'),dict(offset=4,end=8,kind='two')])
        self.assertEqual(len(sequences),1)
        self.assertFalse(sequences[0]['removable_zero_seed'])
        self.assertNotIn(1,classes)
        for ranges in [[],[dict(offset=4,end=8,kind='bad')],[dict(offset=0,end=12,kind='bad')]]:
            with self.assertRaises(AssertionError):scan(words,ranges)

    def test_sparse_and_dense_constants_report_distinct_opportunities(self):
        for value,old,shifted,minimal in [(0x1234000000000000,2,1,1),
            (0xffffffffffff1234,4,4,1),(0x123456789abcdef0,4,4,4),(0x1234000056780000,3,2,2)]:
            words=old_words(value,9);r=decode(words,0,len(words))
            self.assertEqual((r['old_words'],r['shifted_zero_words'],r['minimal_wide_words']),(old,shifted,minimal))

if __name__=='__main__':unittest.main()
