"""Feasibility ceilings: no native key or executable cache is constructed."""
import hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native-reuse-inputs'))
from analyze import checked


def stable_inputs(previous,current):
    old,new=checked(previous),checked(current)
    bodies=set();dependencies=set()
    for i,now in enumerate(new['functions']):
        if i>=len(old['functions']):continue
        was=old['functions'][i]
        if was['body_sha256']!=now['body_sha256']:continue
        for key in ['name_sha256','operations','serialized_bytes','direct_callees']:assert was[key]==now[key]
        bodies.add(i)
        if all(c<len(old['functions']) and old['functions'][c]['body_sha256']==new['functions'][c]['body_sha256']
               for c in now['direct_callees']):dependencies.add(i)
    heap_same=old['uses_heap']==new['uses_heap'];count_same=len(old['functions'])==len(new['functions'])
    # Preserve both conservative global shape constraints in the reported ceiling.
    scoped=dependencies if heap_same and count_same else set()
    return bodies,dependencies,scoped,dict(namespace_same=old['namespace_sha256']==new['namespace_sha256'],
        heap_mode_same=heap_same,function_count_same=count_same)


def compare(previous,current):
    bodies,deps,scoped,flags=stable_inputs(previous,current);rows=current['identities']['functions']
    return dict(previous_artifact_sha256=previous['artifact_sha256'],artifact_sha256=current['artifact_sha256'],
        **flags,functions=len(rows),same_body=len(bodies),same_body_and_direct_callees=len(deps),
        same_body_callees_heap_count=len(scoped),operations=sum(r['operations'] for r in rows),
        stable_scope_operations=sum(rows[i]['operations'] for i in scoped))


def native_pool(mapping,original):
    rows=checked(original)['functions']
    assert mapping['schema_version']==1 and mapping['architecture']=='aarch64' and mapping['byte_order']=='little'
    assert mapping['profiled'] is False and mapping['native_call_stubs'] is False
    assert mapping['persistent_registers'] is True and mapping['resumable_calls'] is True
    assert type(mapping['code_bytes']) is int and 0<mapping['code_bytes']<=16*1024**2
    end=0;weights={};kinds={}
    for r in mapping['ranges']:
        start,stop,i=r['offset'],r['end'],r['function']
        assert all(type(v) is int for v in [start,stop,i])
        assert start==end and start<stop<=mapping['code_bytes'] and start%4==stop%4==0
        assert 0<=i<len(rows) and hashlib.sha256(r['name'].encode()).hexdigest()==rows[i]['name_sha256']
        assert r['kind'] in ['resumable_call','resumable_return','resumable_region','scalar_leaf']
        if r['kind']=='scalar_leaf':assert r['pc'] is None and r['pc_end'] is None
        else:assert type(r['pc']) is int and type(r['pc_end']) is int and 0<=r['pc']<r['pc_end']<=rows[i]['operations']
        weights[i]=weights.get(i,0)+stop-start;kinds[r['kind']]=kinds.get(r['kind'],0)+stop-start;end=stop
    assert end==mapping['code_bytes'] and sum(weights.values())==end
    return weights,kinds


def anchored_pool(original,current,weights):
    bodies,deps,scoped,flags=stable_inputs(original,current)
    assert weights and all(type(i) is int and 0<=i<len(original['identities']['functions']) for i in weights)
    assert all(type(n) is int and n>0 for n in weights.values())
    return dict(original_artifact_sha256=original['artifact_sha256'],artifact_sha256=current['artifact_sha256'],
        **flags,original_compiled_functions=len(weights),original_compiled_bytes=sum(weights.values()),
        original_bytes_with_same_body=sum(n for i,n in weights.items() if i in bodies),
        original_bytes_with_same_body_and_callees=sum(n for i,n in weights.items() if i in deps),
        original_bytes_with_stable_scope=sum(n for i,n in weights.items() if i in scoped))
