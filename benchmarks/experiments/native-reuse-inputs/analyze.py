"""Necessary-input stability, without claiming native cache hits or hot coverage."""
import re


def digest(value):
    assert isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value)
    return value


def checked(report):
    digest(report['artifact_sha256'])
    identities=report['identities'];digest(identities['namespace_sha256'])
    assert type(identities['uses_heap']) is bool
    rows=identities['functions'];assert isinstance(rows,list) and 0<len(rows)<=100_000
    for index,row in enumerate(rows):
        assert type(row['function']) is int and row['function']==index
        for key in ['name_sha256','body_sha256','necessary_inputs_sha256']:digest(row[key])
        for key in ['operations','serialized_bytes']:assert type(row[key]) is int and row[key]>0
        callees=row['direct_callees'];assert isinstance(callees,list)
        assert all(type(c) is int and 0<=c<len(rows) for c in callees)
        assert callees==sorted(set(callees))
    assert sum(f['operations'] for f in rows)<=4_000_000
    assert sum(f['serialized_bytes'] for f in rows)<=128*1024*1024
    return identities


def compare(previous,current):
    before,after=checked(previous),checked(current)
    if previous['artifact_sha256']==current['artifact_sha256']:assert before==after
    old,new=before['functions'],after['functions']
    namespace_same=before['namespace_sha256']==after['namespace_sha256']
    if namespace_same:assert before['uses_heap']==after['uses_heap'] and len(old)==len(new)
    counts=dict(functions=len(new),operations=sum(f['operations'] for f in new),
        serialized_bytes=sum(f['serialized_bytes'] for f in new),
        same_body_at_same_id=0,same_necessary_inputs=0,same_necessary_input_operations=0,
        same_necessary_input_bytes=0,callee_dependent_invalidations=0,identical_body_at_another_id=0)
    by_body={}
    for f in old:by_body.setdefault(f['body_sha256'],set()).add(f['function'])
    for index,now in enumerate(new):
        was=old[index] if index<len(old) else None
        same_body=was is not None and now['body_sha256']==was['body_sha256']
        same_key=was is not None and now['necessary_inputs_sha256']==was['necessary_inputs_sha256']
        if same_body:
            for field in ['name_sha256','operations','serialized_bytes','direct_callees']:assert now[field]==was[field]
            counts['same_body_at_same_id']+=1
        if same_key:
            assert same_body and namespace_same,'key equality contradicts its declared inputs'
            counts['same_necessary_inputs']+=1
            counts['same_necessary_input_operations']+=now['operations']
            counts['same_necessary_input_bytes']+=now['serialized_bytes']
        elif same_body and namespace_same:
            assert now['direct_callees'],'callee-free identity changed with all inputs stable'
            counts['callee_dependent_invalidations']+=1
        if not same_body and by_body.get(now['body_sha256'],set())-{index}:
            counts['identical_body_at_another_id']+=1
    return dict(previous_artifact_sha256=previous['artifact_sha256'],artifact_sha256=current['artifact_sha256'],
        identical_artifact=previous['artifact_sha256']==current['artifact_sha256'],
        namespace_same=namespace_same,**counts)
