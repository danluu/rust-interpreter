import os,struct,unittest
from pathlib import Path
from memory import decode_memory
from words import reg
from cfg_memory import analyze_cfg
from test_linear import mov
WORDS=[0x39000569,0x39400569,0x7900058a,0x7940058a,
       0xb9000569,0xb9400569,0xf9000569,0xf9400569,
       0xa9012969,0xa9412969,0xa9bf2be9,0xa9c12be9,0xa8812be9,0xa8c12be9]

def text_words(path):
    data=path.read_bytes();assert len(data)<512*1024
    assert struct.unpack_from('<I',data)[0]==0xfeedfacf
    count=struct.unpack_from('<I',data,16)[0];offset=32;sections=[]
    for _ in range(count):
        command,size=struct.unpack_from('<II',data,offset);assert size>=8 and offset+size<=len(data)
        if command==0x19:
            nsects=struct.unpack_from('<I',data,offset+64)[0]
            assert 72+nsects*80==size
            for i in range(nsects):
                section=offset+72+i*80
                if data[section:section+16].rstrip(b'\0')==b'__text':
                    length=struct.unpack_from('<Q',data,section+40)[0]
                    start=struct.unpack_from('<I',data,section+48)[0]
                    assert start+length<=len(data) and length%4==0
                    sections.append(list(struct.unpack_from('<'+'I'*(length//4),data,start)))
        offset+=size
    assert len(sections)==1
    return sections[0]

class Memory(unittest.TestCase):
    def test_independent_host_assembler_encodings(self):
        self.assertEqual(text_words(Path(os.environ['ORDINARY_MEMORY_OBJECT'])),WORDS)
    def test_payloads_bases_pair_destinations_and_writeback(self):
        for i,w in enumerate(WORDS):
            op=decode_memory(w);self.assertIsNotNone(op);self.assertFalse(op.pure)
            load=i%2==1
            if i<8:
                base,dest=(12,10) if i in [2,3] else (11,9)
                self.assertEqual(op.reads,reg(base)|(0 if load else reg(dest)))
                self.assertEqual(op.writes,reg(dest) if load else 0)
            else:
                base=11 if i<10 else 31;wb=i>=10
                self.assertEqual(op.reads,reg(base,True)|(0 if load else reg(9)|reg(10)))
                self.assertEqual(op.writes,(reg(9)|reg(10) if load else 0)|(reg(base,True) if wb else 0))
    def test_unreviewed_or_unpredictable_memory_stays_opaque(self):
        for w in [0x39800569,0x3d800569,0xf8400569,0xa9402529,0xa8c12d69,0xffffffff]:
            self.assertIsNone(decode_memory(w),hex(w))
    def test_stack_restore_does_not_observe_scratch_but_store_does(self):
        words=[mov(9,1),0xa8c17bf3,0xd65f03c0]
        self.assertEqual(analyze_cfg(words,True)['dead'],[(0,'movz')])
        self.assertEqual(analyze_cfg(words,False)['dead'],[])
        self.assertEqual(analyze_cfg([mov(9,1),0xa9012be9,0xd65f03c0],True)['dead'],[])
if __name__=='__main__':unittest.main()
