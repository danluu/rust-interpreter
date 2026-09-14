"""Conservative linear-span liveness using the qualified finite recognizer."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scalar-word-census'))
from words import decode
ALL=(1<<34)-1


def direct_target(word,pc):
    if word&0x7c000000==0x14000000:bits,raw=26,word&0x3ffffff
    elif word&0xff000010==0x54000000 or word&0x7e000000==0x34000000:bits,raw=19,(word>>5)&0x7ffff
    elif word&0x7e000000==0x36000000:bits,raw=14,(word>>5)&0x3fff
    else:return None
    return pc+raw-(1<<bits if raw&(1<<(bits-1)) else 0)


def analyze(words,entries=()):
    assert len(words)<=65536
    live=ALL;dead=[];known=unknown=0
    entries=set(entries)
    for pc in range(len(words)-1,-1,-1):
        word=words[pc]
        # Control flow is never analyzed using the scalar ABI or a guessed
        # fallthrough. Unknown words include other SIMD and memory encodings.
        if direct_target(word,pc) is not None or word&0xfe000000==0xd6000000:
            live=ALL;unknown+=1
        else:
            try:op=decode(word,0,2)
            except AssertionError:op=None
            if op is None or op.kind=='vector':live=ALL;unknown+=1
            else:
                known+=1
                if op.pure and op.writes and not op.writes&live:dead.append((pc,op.kind))
                else:live=op.reads|(live&~op.writes)
        if pc in entries:live=ALL
    return dict(dead=sorted(dead),recognized=known,barriers=unknown)
