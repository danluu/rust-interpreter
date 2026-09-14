"""Compare complete captures, permitting only bound scalar-Call arena addresses."""
import re,struct
from native_observation import validate

def immediate(value):
    assert type(value) is int and 0<=value<2**64
    words=[0xd2800010|((value&0xffff)<<5)]
    words += [0xf2800010|(shift<<21)|(((value>>(16*shift))&0xffff)<<5)
              for shift in range(1,4) if (value>>(16*shift))&0xffff]
    return words+[0xd63f0200] # exact imm x16; blr x16 sequence

def normalize(old,new,calls):
    assert len(old)==len(new) and len(old)%4==0
    a=list(struct.unpack('<'+'I'*(len(old)//4),old));b=list(struct.unpack('<'+'I'*(len(new)//4),new))
    changed=sum(x!=y for x,y in zip(a,b));count=0;covered=set()
    for lo,hi,old_target,new_target in calls:
        assert 0<=lo<hi<=len(a)
        x,y=immediate(old_target),immediate(new_target);assert len(x)==len(y)
        old_sites=[i for i in range(lo,hi-len(x)+1) if a[i:i+len(x)]==x]
        new_sites=[i for i in range(lo,hi-len(y)+1) if b[i:i+len(y)]==y]
        assert old_sites==new_sites and len(old_sites)<=1,'unbound scalar Call relocation'
        if old_sites:
            i=old_sites[0];positions=set(range(i,i+len(x)))
            assert not covered&positions,'overlapping relocation ownership'
            covered|=positions;b[i:i+len(x)]=x;count+=1
    assert a==b,'native code differs outside bound scalar addresses'
    return dict(scalar_address_relocations=count,changed_words=changed,exact_after_bound_relocation=True)

def compare(old_code,old_map,old_operations,old_profile,new_code,new_map,new_operations,new_profile):
    a=validate(old_operations,old_map,old_code,old_profile,old_map['pid'])
    b=validate(new_operations,new_map,new_code,new_profile,new_map['pid'])
    assert a['rows']==b['rows'] and old_map['ranges']==new_map['ranges']
    scalar={r['function']:r['offset'] for r in old_map['ranges'] if r['kind']=='scalar_leaf'}
    calls=[]
    for row in a['rows']:
        if row['kind']!='transition' or row['pc'] is None:continue
        op=old_profile['functions'][row['function']]['operations'][row['pc']]
        match=re.match(r'^Call \{ function: (\d+), ',op)
        if match and int(match[1]) in scalar:
            offset=scalar[int(match[1])]
            calls.append((row['offset']//4,row['end']//4,old_map['arena_base']+offset,new_map['arena_base']+offset))
    return normalize(old_code,new_code,calls)
