"""Bounded machine-CFG liveness; diagnostic only."""
from collections import deque
from linear import ALL,direct_target
from words import decode,reg,FLAGS,VECTOR,Word
C_RETURN=reg(0)|sum(1<<r for r in range(18,32))|(1<<VECTOR)

def analyze_cfg(words,abi=False,work_limit=None):
    n=len(words);assert 0<n<=65536
    nodes=[];known=barriers=0
    for pc,w in enumerate(words):
        fall=(pc+1,) if pc+1<n else ()
        outside=not fall
        target=direct_target(w,pc)
        if w==0xd65f03c0:
            node=Word(C_RETURN if abi else ALL,0,False,(),'return');outside=False
        elif w&0xfc000000==0x14000000:
            successors=(target,) if 0<=target<n else ()
            node=Word(0 if successors else ALL,0,False,successors,'branch');outside=False
        elif w&0xff000010==0x54000000 or w&0x7e000000 in (0x34000000,0x36000000):
            reads=(1<<FLAGS) if w&0xff000010==0x54000000 else reg(w&31)
            if w&0xff000010==0x54000000 and w&15>=14:reads=ALL
            successors=tuple(dict.fromkeys([*fall,*([target] if 0<=target<n else [])]))
            if not 0<=target<n:reads=ALL
            node=Word(reads,0,False,successors,'conditional')
        elif w&0xfc000000==0x94000000 or w&0xfffffc1f==0xd63f0000:
            node=Word(ALL,0,False,fall,'opaque_call')
        elif w&0xfe000000==0xd6000000:
            node=Word(ALL,0,False,(),'opaque_transfer');outside=False
        else:
            try:decoded=decode(w,0,2)
            except AssertionError:decoded=None
            if decoded is None or decoded.kind=='vector':node=Word(ALL,0,False,fall,'opaque')
            else:node=Word(decoded.reads,decoded.writes,decoded.pure,fall,decoded.kind)
        if outside:node=Word(node.reads|ALL,node.writes,False,node.successors,node.kind)
        nodes.append(node)
        if node.kind.startswith('opaque'):barriers+=1
        else:known+=1
    predecessors=[[] for _ in nodes]
    for pc,node in enumerate(nodes):
        for successor in node.successors:predecessors[successor].append(pc)
    live=[0]*n;queue=deque(reversed(range(n)));queued=[True]*n
    limit=n*80 if work_limit is None else work_limit
    steps=0
    while queue:
        steps+=1
        if steps>limit:return None
        pc=queue.popleft();queued[pc]=False;node=nodes[pc]
        out=0
        for successor in node.successors:out|=live[successor]
        value=out if node.pure and node.writes and not node.writes&out else node.reads|(out&~node.writes)
        assert live[pc]&value==live[pc],'nonmonotone liveness'
        if value!=live[pc]:
            live[pc]=value
            for predecessor in predecessors[pc]:
                if not queued[predecessor]:queued[predecessor]=True;queue.append(predecessor)
    dead=[]
    for pc,node in enumerate(nodes):
        out=0
        for successor in node.successors:out|=live[successor]
        if node.pure and node.writes and not node.writes&out:dead.append((pc,node.kind))
    return dict(dead=dead,recognized=known,barriers=barriers,work_steps=steps)
