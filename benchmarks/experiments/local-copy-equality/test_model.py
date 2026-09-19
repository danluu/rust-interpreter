import random
import unittest
from model import Bytes,Region

def local(r,o):return f'Local {{ dst: {r}, offset: {o} }}'
def copy(d,s,n):return f'Copy {{ dst: {d}, src: {s}, size: {n} }}'
def store(a,n):return f'Store {{ address: {a}, src: 9, size: {n} }}'

class Tests(unittest.TestCase):
    def test_round_trip(self):
        b=Bytes();self.assertFalse(b.copy(0,16,8));self.assertTrue(b.copy(16,0,8))

    def test_unknown_bytes_not_equal(self):
        b=Bytes();self.assertFalse(b.copy(0,16,8));self.assertFalse(b.copy(32,16,8))

    def test_overlap_snapshot(self):
        b=Bytes();self.assertFalse(b.copy(0,1,8));self.assertFalse(b.copy(1,0,8))
        self.assertTrue(b.copy(7,8,1))

    def test_partial_overwrite_kills(self):
        b=Bytes();b.copy(0,16,8);b.invalidate(19,1)
        self.assertFalse(b.copy(0,16,8))

    def test_disjoint_and_zero_writes_preserve(self):
        b=Bytes();b.copy(0,16,8);b.invalidate(40,8);b.invalidate(None,0)
        self.assertTrue(b.copy(0,16,8))

    def test_unknown_write_clears(self):
        b=Bytes();b.copy(0,16,8);b.invalidate(None,1)
        self.assertFalse(b.copy(0,16,8))

    def test_bounded_eviction(self):
        b=Bytes(256);b.copy(0,16,8)
        for i in range(20):b.copy(1000+256*i,1128+256*i,128)
        self.assertLessEqual(len(b.values),256);self.assertFalse(b.copy(0,16,8))

    def test_same_range(self):
        self.assertTrue(Bytes().copy(8,8,128))

    def test_region_scope(self):
        r=Region(64);r.step(local(0,0));r.step(local(1,16))
        self.assertIsNone(r.step(copy(1,0,8)))
        self.assertIsNotNone(r.step(copy(0,1,8)))
        fresh=Region(64);fresh.step(local(0,0));fresh.step(local(1,16))
        self.assertIsNone(fresh.step(copy(0,1,8)))

    def test_invalid_range_and_redefinition(self):
        r=Region(24);r.step(local(0,0));r.step(local(1,16))
        self.assertIsNone(r.step(copy(1,0,16)))
        r.step(copy(1,0,8));r.step('Load { dst: 0, address: 1, size: 8 }')
        self.assertIsNone(r.step(copy(1,0,8)))

    def test_unknown_alias(self):
        r=Region(64);r.step(local(0,0));r.step(local(1,16));r.step(copy(1,0,8))
        r.step(store(10,1));self.assertIsNone(r.step(copy(1,0,8)))

    def test_effect_barrier(self):
        for effect in ['Call { function: 1, args: [], destination: 0 }','ResetThreadLocals',
            'CopyDynamic { dst: 0, src: 1, size: 2 }','NewUnreviewedOpcode']:
            r=Region(64);r.step(local(0,0));r.step(local(1,16));r.step(copy(1,0,8))
            r.step(effect);r.step(local(0,0));r.step(local(1,16))
            self.assertIsNone(r.step(copy(1,0,8)))

    def test_address_arithmetic(self):
        r=Region(64);r.step(local(0,0));r.step('Imm { dst: 1, value: 16 }')
        r.step('Binary { dst: 2, overflow: 3, op: Add, a: 0, b: 1, bits: 64, signed: false }')
        self.assertEqual(r.local(2,8),16)
        r.step('Binary { dst: 2, overflow: 3, op: Sub, a: 0, b: 1, bits: 64, signed: false }')
        self.assertIsNone(r.local(2,8))
        r.step('Binary { dst: 0, overflow: 0, op: Add, a: 0, b: 1, bits: 64, signed: false }')
        self.assertIsNone(r.local(0,8))

    def test_concrete_memory_oracle(self):
        rng=random.Random(2409)
        for _ in range(50):
            memory=bytearray(rng.randrange(256) for _ in range(512));b=Bytes(256)
            for _ in range(300):
                size=rng.randrange(1,129);src=rng.randrange(513-size);dst=rng.randrange(513-size)
                if rng.randrange(4)==0:
                    memory[dst:dst+size]=bytes(rng.randrange(256) for _ in range(size))
                    b.invalidate(None if rng.randrange(2) else dst,size)
                else:
                    original=bytes(memory[src:src+size]);same=original==memory[dst:dst+size]
                    if b.copy(src,dst,size):self.assertTrue(same)
                    memory[dst:dst+size]=original

if __name__=='__main__':unittest.main()
