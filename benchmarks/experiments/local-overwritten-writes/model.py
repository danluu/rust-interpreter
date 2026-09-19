"""Conservative scope model, not a typed emitter optimization."""
import re

class Writes:
    def __init__(self,capacity=128):
        assert 1<=capacity<=128
        self.capacity=capacity;self.pending={};self.dead=[]
    def barrier(self):self.pending.clear()
    def read(self,offset,size):
        assert size>=0
        if not size:return
        if offset is None:self.barrier();return
        assert offset>=0
        end=offset+size
        self.pending={pc:row for pc,row in self.pending.items() if not any(offset<=b<end for b in row['remaining'])}
    def write(self,pc,offset,size,kind):
        assert size>=0
        if not size:return
        if offset is None or size>128:self.barrier();return
        assert offset>=0 and pc not in self.pending
        extent=set(range(offset,offset+size));completed=[]
        for prior,row in self.pending.items():
            row['remaining'].difference_update(extent)
            if not row['remaining']:
                self.dead.append({k:v for k,v in row.items() if k!='remaining'}|dict(overwritten_by=pc))
                completed.append(prior)
        for prior in completed:del self.pending[prior]
        if len(self.pending)==self.capacity:
            # Lost opportunities only; never evict a write by calling it dead.
            self.pending.clear()
        self.pending[pc]=dict(pc=pc,offset=offset,size=size,kind=kind,remaining=extent)
    def copy(self,pc,destination,source,size):
        if size==0:return
        if destination is None or source is None or size>128:
            self.barrier();return
        # All source bytes are observed before any destination overwrite.
        self.read(source,size);self.write(pc,destination,size,'Copy')

class Region:
    def __init__(self,frame_size):
        assert 0<=frame_size<=2**32
        self.frame_size=frame_size;self.facts={};self.writes=Writes();self.barriers=0
    def local(self,reg,size):
        fact=self.facts.get(reg)
        if fact and fact[0]=='local' and 0<=fact[1]<=self.frame_size-size:return fact[1]
        return None
    def barrier(self):self.writes.barrier();self.barriers+=1
    def step(self,pc,text):
        m=re.fullmatch(r'Imm \{ dst: ([0-9]+), value: ([0-9]+) \}',text)
        if m:
            value=int(m[2]);assert value<2**128;self.facts[int(m[1])]=('imm',value);return
        m=re.fullmatch(r'Local \{ dst: ([0-9]+), offset: ([0-9]+) \}',text)
        if m:self.facts[int(m[1])]=('local',int(m[2]));return
        m=re.fullmatch(r'Load \{ dst: ([0-9]+), address: ([0-9]+), size: ([0-9]+) \}',text)
        if m:
            size=int(m[3]);offset=self.local(int(m[2]),size)
            if offset is None or size>16:self.barrier()
            else:self.writes.read(offset,size)
            self.facts.pop(int(m[1]),None);return
        m=re.fullmatch(r'Store \{ address: ([0-9]+), src: ([0-9]+), size: ([0-9]+) \}',text)
        if m:
            size=int(m[3]);offset=self.local(int(m[1]),size)
            if offset is None or size>16:self.barrier()
            else:self.writes.write(pc,offset,size,'Store')
            return
        m=re.fullmatch(r'Copy \{ dst: ([0-9]+), src: ([0-9]+), size: ([0-9]+) \}',text)
        if m:
            size=int(m[3]);dst=self.local(int(m[1]),size);src=self.local(int(m[2]),size)
            if dst is None or src is None or size>128:self.barrier()
            else:self.writes.copy(pc,dst,src,size)
            return
        m=re.fullmatch(r'Binary \{ dst: ([0-9]+), overflow: ([0-9]+), op: ([A-Za-z]+), a: ([0-9]+), b: ([0-9]+), bits: ([0-9]+), signed: (true|false) \}',text)
        if m:
            dst,overflow,op,a,b,bits,signed=int(m[1]),int(m[2]),m[3],int(m[4]),int(m[5]),int(m[6]),m[7]
            left,right=self.facts.get(a),self.facts.get(b)
            self.facts.pop(dst,None);self.facts.pop(overflow,None)
            if op not in ['Add','Sub','Mul','And','Or','Xor','Shl','Shr','Eq','Ne','Lt','Le','Gt','Ge','Cmp','RotateLeft','RotateRight'] or bits not in [8,16,32,64]:
                self.barrier();return
            if dst!=overflow and bits==64 and signed=='false' and op in ['Add','Sub'] and left and right and right[0]=='imm' and right[1]<2**64:
                value=left[1]+right[1] if op=='Add' else left[1]-right[1]
                if left[0]=='local' and 0<=value<=self.frame_size:self.facts[dst]=('local',value)
                elif left[0]=='imm' and left[1]<2**64:self.facts[dst]=('imm',value%(2**64))
            return
        # Deliberately narrow: even unmodeled pure operations end the proof.
        # Assertions, division, all calls and external reads/writes can observe
        # intermediate memory or fail, so no pending write survives them.
        self.barrier();self.facts.clear()
