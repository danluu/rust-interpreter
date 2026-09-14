"""Reviewed integer memory effects, with every memory operation retained."""
from linear import ALL
from words import Word,reg
def decode_memory(w):
    rd,rn,rt2=w&31,(w>>5)&31,(w>>10)&31
    tag=w&0x3fc00000
    if tag in (0x39000000,0x39400000):
        load=tag==0x39400000
        return Word(reg(rn,True)|(0 if load else reg(rd)),reg(rd) if load else 0,False,(),'integer_memory')
    tag=w&0xffc00000
    if tag not in (0xa9000000,0xa9400000,0xa9800000,0xa9c00000,0xa8800000,0xa8c00000):return None
    load=bool(w&(1<<22));writeback=((w>>23)&3)!=2
    if (load and rd==rt2) or (writeback and rn!=31 and rn in (rd,rt2)):return None
    reads=reg(rn,True)|(0 if load else reg(rd)|reg(rt2))
    writes=(reg(rd)|reg(rt2) if load else 0)|(reg(rn,True) if writeback else 0)
    return Word(reads,writes,False,(),'integer_pair')
