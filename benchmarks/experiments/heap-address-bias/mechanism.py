"""Reconcile larger external entries and smaller checks in paired native maps."""
from collections import Counter
import struct

def verify(old_map,old_code,new_map,new_code):
    assert old_map['code_bytes']==len(old_code) and new_map['code_bytes']==len(new_code)
    assert len(old_map['functions'])==len(new_map['functions'])
    counts=Counter();changes=Counter();entries=0
    before=[0xaa0503e7,0xaa0603e8]
    after=[0xd280000e,0xf2e8000e,0xcb0e00a7,0x8b0e00c8]
    for old,new in zip(old_map['functions'],new_map['functions']):
        for field in ['function','name','assertion_base','assertion_count']:assert old[field]==new[field],field
        assert len(old['spans'])==len(new['spans'])
        for a,b in zip(old['spans'],new['spans']):
            assert {k:v for k,v in a.items() if k not in ['offset','end']}=={k:v for k,v in b.items() if k not in ['offset','end']}
            x=list(struct.unpack('<'+'I'*((a['end']-a['offset'])//4),old_code[a['offset']:a['end']]))
            y=list(struct.unpack('<'+'I'*((b['end']-b['offset'])//4),new_code[b['offset']:b['end']]))
            kind=a['kind'];delta=4*(len(y)-len(x));counts[kind]+=1;changes[kind]+=delta
            if kind=='entry':
                sites=[i for i in range(len(x)-1) if x[i:i+2]==before]
                assert len(sites)<=1
                if sites:
                    i,=sites;assert y==x[:i]+after+x[i+2:];entries+=1
                else:assert x==y
            elif kind in ['operation','transition','range_guard']:
                assert delta<=0,(kind,delta)
            else:assert delta==0,(kind,delta)
    assert entries and changes['entry']==8*entries
    removed=-sum(changes[k] for k in ['operation','transition','range_guard'])
    assert removed>0
    assert sum(changes.values())==len(new_code)-len(old_code)==8*entries-removed
    return dict(status='passed',entry_contexts=entries,added_entry_bytes=8*entries,
        removed_checked_bytes=removed,net_code_bytes=len(new_code)-len(old_code),
        span_counts=dict(counts),byte_changes=dict(changes),entry_replacement_words_verified=True,
        stable_span_shapes_and_unaffected_word_counts=True,
        limitation='Static code partition, not execution frequency or latency. Only entry instructions are compared word for word; branch relocation is not normalized.')
