"""Model eight reserved payload registers; no production/native code emitted."""
ADD_FRAME=0x8b01004b  # add x11,x2,x1
LOAD=0xf9400169       # ldr x9,[x11,#imm12*8]
STORE=0xf9000169      # str x9,[x11,#imm12*8]
MASK=0xffc003ff

def decode(words,frame_size):
    """Recognize only the complete existing three-word local eight-byte copy."""
    if len(words)!=3 or words[0]!=ADD_FRAME or words[1]&MASK!=LOAD or words[2]&MASK!=STORE:return None
    source=((words[1]>>10)&4095)*8;destination=((words[2]>>10)&4095)*8
    if source+8>frame_size or destination+8>frame_size:return None
    return source,destination

class Cache:
    def __init__(self):
        self.offsets=[set() for _ in range(8)];self.age=[0]*8;self.clock=0
    def clear(self):
        for row in self.offsets:row.clear()
    def invalidate(self,start,size):
        assert size>=0 and start>=0
        if size:
            for i,row in enumerate(self.offsets):
                self.offsets[i]={o for o in row if o+8<=start or start+size<=o}
    def copy(self,source,destination):
        assert source>=0 and destination>=0
        matching=[i for i,row in enumerate(self.offsets) if source in row]
        hit=bool(matching)
        if hit:slot=matching[0]
        else:
            slot=next((i for i,row in enumerate(self.offsets) if not row),None)
            if slot is None:slot=min(range(8),key=lambda i:(self.age[i],i))
            self.offsets[slot]={source}
        self.invalidate(destination,8)
        self.offsets[slot].add(destination)
        # Bound alias tracking too. Dropping an alias can only lose a hit.
        while len(self.offsets[slot])>4:
            self.offsets[slot].remove(min(o for o in self.offsets[slot] if o!=destination))
        self.clock+=1;self.age[slot]=self.clock
        return slot,hit

PRESERVE={'Imm','Local','Load','Binary','Unary','Cast','Select','Jump','Switch','Assert','Return','Trap'}
