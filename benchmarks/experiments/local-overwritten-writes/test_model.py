import random,unittest
from model import Writes,Region

def local(r,o):return f'Local {{ dst: {r}, offset: {o} }}'
def store(r,n):return f'Store {{ address: {r}, src: 9, size: {n} }}'
def copy(d,s,n):return f'Copy {{ dst: {d}, src: {s}, size: {n} }}'
def dead(w):return {r['pc'] for r in w.dead}

class Tests(unittest.TestCase):
    def test_full_and_partial_overwrites(self):
        w=Writes();w.write(0,0,8,'Store');w.write(1,0,4,'Store');self.assertEqual(dead(w),set())
        w.write(2,4,4,'Store');self.assertEqual(dead(w),{0})
    def test_reads_before_overwrite_observe_old_bytes(self):
        for offset in range(8):
            w=Writes();w.write(0,0,8,'Store');w.read(offset,1);w.write(1,0,8,'Store');self.assertEqual(dead(w),set())
    def test_read_of_already_overwritten_bytes(self):
        w=Writes();w.write(0,0,8,'Store');w.write(1,0,4,'Store');w.read(0,4);w.write(2,4,4,'Store')
        self.assertEqual(dead(w),{0})
    def test_overlap_copy_reads_before_writes(self):
        for src,dst in [(0,0),(0,1),(1,0)]:
            w=Writes();w.write(0,0,8,'Store');w.copy(1,dst,src,8);w.write(2,0,16,'Store')
            self.assertNotIn(0,dead(w));self.assertIn(1,dead(w))
    def test_copy_source_preserves_prior_store(self):
        w=Writes();w.write(0,0,8,'Store');w.copy(1,16,0,8);w.write(2,0,24,'Store')
        self.assertEqual(dead(w),{1})
    def test_unknown_reads_writes_and_barriers(self):
        for effect in [lambda w:w.read(None,1),lambda w:w.write(1,None,1,'Store'),lambda w:w.barrier()]:
            w=Writes();w.write(0,0,8,'Store');effect(w);w.write(2,0,8,'Store');self.assertEqual(dead(w),set())
    def test_zero_lengths_and_capacity_loss_are_conservative(self):
        w=Writes(1);w.write(0,0,8,'Store');w.read(None,0);w.write(1,None,0,'Store');w.write(2,0,8,'Store')
        self.assertEqual(dead(w),{0})
        w=Writes(1);w.write(0,0,8,'Store');w.write(1,16,8,'Store');w.write(2,0,8,'Store');self.assertEqual(dead(w),set())
    def test_register_alias_and_exact_local_bounds(self):
        for offset in [0,8,9]:
            r=Region(16);r.step(0,local(0,offset));r.step(1,store(0,8));r.step(2,store(0,8))
            self.assertEqual(dead(r.writes),{1} if offset<=8 else set())
        r=Region(16);r.step(0,local(0,0));r.step(1,store(0,8));r.step(2,'Load { dst: 0, address: 0, size: 8 }');r.step(3,store(0,8))
        self.assertEqual(dead(r.writes),set())
    def test_faults_and_native_exits_end_pending_interval(self):
        for op in ['Assert { condition: 0, expected: true, message: "x" }','Jump { target: 0 }','Return',
                   'Binary { dst: 2, overflow: 3, op: Div, a: 0, b: 1, bits: 64, signed: false }',
                   'Call { function: 0, args: [], destination: 0 }','NewUnreviewedOpcode']:
            r=Region(16);r.step(0,local(0,0));r.step(1,store(0,8));r.step(2,op);r.step(3,local(0,0));r.step(4,store(0,8))
            self.assertEqual(dead(r.writes),set())
        for op in ['Load { dst: 2, address: 4, size: 0 }',store(4,0),copy(0,4,0)]:
            r=Region(16);r.step(0,local(0,0));r.step(1,store(0,8));r.step(2,op);r.step(3,store(0,8))
            self.assertEqual(dead(r.writes),set(),'zero-byte unknown address may still fault')
    def test_arithmetic_offset_and_output_alias_order(self):
        for overflow in [2,3]:
            r=Region(32);r.step(0,local(0,0));r.step(1,'Imm { dst: 1, value: 8 }')
            r.step(2,f'Binary {{ dst: 2, overflow: {overflow}, op: Add, a: 0, b: 1, bits: 64, signed: false }}')
            r.step(3,store(2,8));r.step(4,store(2,8));self.assertEqual(dead(r.writes),{3} if overflow==3 else set())
    def test_native_regions_start_without_pending_writes(self):
        a=Region(16);a.step(0,local(0,0));a.step(1,store(0,8));b=Region(16);b.step(2,local(0,0));b.step(3,store(0,8))
        self.assertEqual(dead(a.writes)|dead(b.writes),set())
    def test_concrete_memory_and_every_observation_oracle(self):
        rng=random.Random(190926)
        for _ in range(2000):
            initial=bytes(rng.randrange(256) for _ in range(32));events=[];w=Writes(rng.choice([1,2,8,128]))
            for pc in range(40):
                kind=rng.choice(['write','copy','read','barrier']);size=rng.randrange(0,9);dst=rng.randrange(33-size);src=rng.randrange(33-size)
                value=bytes(rng.randrange(256) for _ in range(size));events.append((kind,dst,src,size,value))
                if kind=='write':w.write(pc,dst,size,'Store')
                elif kind=='copy':w.copy(pc,dst,src,size)
                elif kind=='read':w.read(src,size)
                else:w.barrier()
            def execute(skipped):
                memory=bytearray(initial);observed=[]
                for pc,(kind,dst,src,size,value) in enumerate(events):
                    if kind=='read':observed.append(bytes(memory[src:src+size]))
                    elif kind=='barrier':observed.append(bytes(memory))
                    elif pc not in skipped:
                        if kind=='copy':memory[dst:dst+size]=bytes(memory[src:src+size])
                        else:memory[dst:dst+size]=value
                return observed,bytes(memory)
            self.assertEqual(execute(set()),execute(dead(w)))

if __name__=='__main__':unittest.main()
