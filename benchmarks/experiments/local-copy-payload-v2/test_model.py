import random,unittest
from model import Cache,decode,ADD_FRAME,LOAD,STORE

class Tests(unittest.TestCase):
    def test_three_word_decode(self):
        self.assertEqual(decode([0x8b01004b,0xf9401169,0xf9001969],64),(32,48))
        self.assertEqual(decode([ADD_FRAME,LOAD,STORE],8),(0,0))
    def test_decline_other_encodings(self):
        for words in [[ADD_FRAME,STORE],[ADD_FRAME,LOAD,STORE,0xd503201f],
            [ADD_FRAME^1,LOAD,STORE],[ADD_FRAME,LOAD^1,STORE],
            [ADD_FRAME,LOAD,STORE^(1<<5)],[ADD_FRAME,LOAD^(1<<30),STORE]]:
            self.assertIsNone(decode(words,64))
        self.assertIsNone(decode([ADD_FRAME,LOAD,STORE],7))
    def test_hit_after_scratch_independent_work(self):
        c=Cache();_,hit=c.copy(0,16);self.assertFalse(hit)
        _,hit=c.copy(16,32);self.assertTrue(hit)
    def test_alias_source_and_destination(self):
        c=Cache();slot,_=c.copy(0,16)
        self.assertEqual(c.copy(0,32),(slot,True));self.assertEqual(c.copy(16,48),(slot,True))
    def test_partial_write_and_disjoint(self):
        c=Cache();c.copy(0,16);c.invalidate(19,1)
        self.assertFalse(c.copy(16,32)[1]);self.assertTrue(c.copy(0,48)[1])
    def test_overlap_snapshot(self):
        c=Cache();c.copy(0,1)
        self.assertTrue(c.copy(1,16)[1]);self.assertFalse(c.copy(0,32)[1])
    def test_eviction_and_alias_bound(self):
        c=Cache()
        for i in range(20):c.copy(1000+32*i,1016+32*i)
        self.assertFalse(c.copy(1000,0)[1])
        for i in range(30):c.copy(0,100+i*8)
        self.assertLessEqual(sum(map(len,c.offsets)),32)
    def test_clear_and_self_copy(self):
        c=Cache();c.copy(0,0);self.assertTrue(c.copy(0,0)[1])
        c.clear();self.assertFalse(c.copy(0,0)[1])
    def test_empty_invalidation(self):
        c=Cache();c.copy(0,16);c.invalidate(0,0)
        self.assertTrue(c.copy(0,32)[1])
    def test_concrete_payload_oracle(self):
        rng=random.Random(6521)
        for _ in range(40):
            memory=bytearray(rng.randrange(256) for _ in range(512));registers=[None]*8;c=Cache()
            for _ in range(500):
                src=rng.randrange(505);dst=rng.randrange(505)
                if rng.randrange(4)==0:
                    memory[dst:dst+8]=bytes(rng.randrange(256) for _ in range(8))
                    if rng.randrange(2):c.clear()
                    else:c.invalidate(dst,8)
                else:
                    value=bytes(memory[src:src+8]);slot,hit=c.copy(src,dst)
                    if hit:self.assertEqual(registers[slot],value)
                    else:registers[slot]=value
                    memory[dst:dst+8]=value
if __name__=='__main__':unittest.main()
