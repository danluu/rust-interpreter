"""Bounded diagnostic byte identities within one ordinary native region.

This string reader estimates scope only. A production pass must consume typed
bytecode and the actual emitter's proven frame ranges, with native controls.
"""
import re

class Bytes:
    def __init__(self, capacity=4096):
        assert 256 <= capacity <= 65536
        self.capacity=capacity;self.values={};self.serial=0

    def clear(self):self.values.clear()

    def invalidate(self, offset, size):
        assert size>=0
        if size==0:return
        if offset is None:self.clear();return
        assert offset>=0
        self.values={p:v for p,v in self.values.items() if not offset<=p<offset+size}

    def copy(self, source, destination, size):
        assert source>=0 and destination>=0 and 1<=size<=128
        positions=set(range(source,source+size))|set(range(destination,destination+size))
        if len(self.values)+len(positions-self.values.keys())>self.capacity:self.clear()
        for position in sorted(positions):
            if position not in self.values:
                self.serial+=1;self.values[position]=self.serial
        before=[self.values[p] for p in range(source,source+size)]
        equal=before==[self.values[p] for p in range(destination,destination+size)]
        # Snapshot before writing: memmove, including partial overlap.
        for index,value in enumerate(before):self.values[destination+index]=value
        assert len(self.values)<=self.capacity
        return equal


class Region:
    def __init__(self, frame_size):
        assert 0<=frame_size<=2**32
        self.frame_size=frame_size;self.facts={};self.memory=Bytes();self.barriers=0

    def local(self, reg, size):
        fact=self.facts.get(reg)
        if fact is not None and fact[0]=='local' and 0<=fact[1]<=self.frame_size-size:
            return fact[1]
        return None

    def step(self, text):
        m=re.fullmatch(r'Imm \{ dst: ([0-9]+), value: ([0-9]+) \}',text)
        if m:
            value=int(m[2]);assert value<2**128
            self.facts[int(m[1])]=('imm',value);return None
        m=re.fullmatch(r'Local \{ dst: ([0-9]+), offset: ([0-9]+) \}',text)
        if m:
            self.facts[int(m[1])]=('local',int(m[2]));return None
        m=re.fullmatch(r'Copy \{ dst: ([0-9]+), src: ([0-9]+), size: ([0-9]+) \}',text)
        if m:
            size=int(m[3]);destination=self.local(int(m[1]),size);source=self.local(int(m[2]),size)
            if size==0:return None
            if source is not None and destination is not None and size<=128:
                if self.memory.copy(source,destination,size):
                    return dict(source=source,destination=destination,size=size,
                        reason='same_range' if source==destination else 'copied_byte_identities')
            else:self.memory.invalidate(destination,size)
            return None
        m=re.fullmatch(r'Store \{ address: ([0-9]+), src: ([0-9]+), size: ([0-9]+) \}',text)
        if m:
            size=int(m[3]);self.memory.invalidate(self.local(int(m[1]),size),size);return None
        m=re.fullmatch(r'Binary \{ dst: ([0-9]+), overflow: ([0-9]+), op: ([A-Za-z]+), a: ([0-9]+), b: ([0-9]+), bits: ([0-9]+), signed: (true|false) \}',text)
        if m:
            dst,overflow,op,a,b,bits,signed=int(m[1]),int(m[2]),m[3],int(m[4]),int(m[5]),int(m[6]),m[7]
            left,right=self.facts.get(a),self.facts.get(b)
            self.facts.pop(dst,None);self.facts.pop(overflow,None)
            if dst==overflow:return None
            # Only this exact integer address idiom is modeled. Everything else
            # loses the destination fact, retaining independent memory facts.
            if bits==64 and signed=='false' and op in ['Add','Sub'] and left and right and right[0]=='imm' and right[1]<2**64:
                value=left[1]+right[1] if op=='Add' else left[1]-right[1]
                if left[0]=='local' and 0<=value<=self.frame_size:
                    self.facts[dst]=('local',value)
                elif left[0]=='imm' and left[1]<2**64:
                    self.facts[dst]=('imm',value%(2**64))
            return None
        variant=text.split(' ',1)[0]
        if variant in ['Load','Unary','Cast','Select','CompareBytes']:
            m=re.match(r'[A-Za-z]+ \{ dst: ([0-9]+),',text)
            if m:self.facts.pop(int(m[1]),None);return None
        if variant in ['Jump','Switch','Assert','Return','Trap']:return None
        # Unmodeled writes/calls/effects must never inherit memory equality.
        self.memory.clear();self.facts.clear();self.barriers+=1
        return None
