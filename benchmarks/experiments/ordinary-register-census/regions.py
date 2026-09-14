"""Consecutive native regions, preserving every external entry boundary."""
def groups(spans):
    result=[];seen=set()
    for span in spans:
        if span['kind']=='scalar_leaf':continue
        key=(span['function'],span['region_pc'])
        if result and result[-1]['key']==key:
            assert result[-1]['end']==span['offset'],'gap within a region'
            result[-1]['end']=span['end'];result[-1]['spans'].append(span)
        else:
            assert key not in seen,'interleaved native region'
            seen.add(key);result.append(dict(key=key,offset=span['offset'],end=span['end'],spans=[span]))
    return result
