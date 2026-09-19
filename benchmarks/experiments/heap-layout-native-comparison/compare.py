"""Exact native equality after proving each mapped scalar-call relocation."""
import hashlib,re,struct

MOVZ16=0xd2800010
MOVK16=0xf2800010
BLR16=0xd63f0200
IMMEDIATE=0xffff<<5

def immediate(value):
    assert type(value) is int and 0<=value<2**64
    return [MOVZ16|((value&0xffff)<<5)]+[
        MOVK16|(shift<<21)|(((value>>(shift*16))&0xffff)<<5)
        for shift in range(1,4) if (value>>(shift*16))&0xffff]

def canonical(code,mapping,regions,profile):
    assert len(code)%4==0 and len(code)==mapping['code_bytes']==regions['code_bytes']
    assert mapping['code_sha256']==hashlib.sha256(code).hexdigest()
    base=regions['arena_base'];assert type(base) is int and base>0 and base%4==0 and base+len(code)<2**64
    assert mapping['arena_base']==base
    entries={}
    for row in regions['ranges']:
        if row['kind']=='scalar_leaf':
            assert row['function'] not in entries
            assert 0<=row['offset']<row['end']<=len(code) and row['offset']%4==row['end']%4==0
            entries[row['function']]=row['offset']
    words=list(struct.unpack('<'+'I'*(len(code)//4),code));normalized=list(words);relocations=[]
    for function in mapping['functions']:
        for span in function['spans']:
            if span['kind']!='transition':continue
            assert span['pc'] is not None
            operation=profile['functions'][function['function']]['operations'][span['pc']]
            call=re.fullmatch(r'Call \{ function: (\d+), args: \[[^\]]*\], destination: \d+ \}',operation)
            if call is None:continue
            callee=int(call[1]);start=span['offset']//4;end=span['end']//4
            assert 0<=start<end<=len(words) and span['offset']%4==span['end']%4==0
            branches=[i for i in range(start,end) if words[i]==BLR16]
            if not branches:continue
            assert len(branches)==1 and callee in entries
            branch=branches[0];first=branch-1
            # Only the exact emitter's ascending MOVZ/MOVK x16 sequence is eligible.
            while first>=start and words[first]&~(IMMEDIATE|(3<<21))==MOVK16:first-=1
            assert first>=start and words[first]&~IMMEDIATE==MOVZ16
            target=base+entries[callee]
            assert words[first:branch]==immediate(target),'wrong target, register, order or noncanonical immediate'
            for i in range(first,branch):
                assert normalized[i]==words[i],'overlapping relocation'
                normalized[i]&=~IMMEDIATE
            relocations.append(dict(function=function['function'],pc=span['pc'],callee=callee,entry_offset=entries[callee],
                                    start=first*4,end=branch*4,branch=branch*4))
    return struct.pack('<'+'I'*len(normalized),*normalized),relocations

def compare(old,new):
    # validate() from the qualified native observer must check each actual dump
    # before this additional equality proof is used for guest admission.
    a,ar=canonical(*old);b,br=canonical(*new)
    assert ar==br,'relocation identities changed'
    assert a==b,'non-relocation native bytes changed'
    for index,ignored in [(1,{'pid','arena_base','code_sha256'}),(2,{'pid','arena_base'})]:
        assert {k:v for k,v in old[index].items() if k not in ignored}=={k:v for k,v in new[index].items() if k not in ignored},'semantic map changed'
    return dict(relocations=len(ar),canonical_code_sha256=hashlib.sha256(a).hexdigest(),code_bytes=len(a),
                exact_nonrelocation_bytes=True,exact_scalar_targets=True,exact_semantic_maps=True)
