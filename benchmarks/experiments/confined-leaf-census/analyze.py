"""Join completed typed proofs to saved, separately scoped protocol measurements."""
from collections import Counter


def analyze(typed,cost):
    functions=typed['functions'];assert [f['function'] for f in functions]==list(range(len(functions)))
    assert typed['status']=='passed' and typed['guest_commands']==typed['runtime_changes']==0
    assert cost['status']=='passed' and cost['guest_commands']==0
    seen=set();groups={};selected=[]
    for row in cost['callees']:
        fid=row['function'];assert isinstance(fid,int) and 0<=fid<len(functions) and fid not in seen;seen.add(fid)
        proof=functions[fid]
        assert (row['name'],row['frame_size'])==(proof['name'],proof['frame_size'])
        assert row['call_samples']==sum(row['call_parts'].values())
        assert row['return_samples']==sum(row['return_parts'].values())
        if not proof['confined']['eligible']:category='unconfined'
        elif proof['calls']:category='has_direct_callee'
        elif not proof['cfg_without_callee_effects']['eligible']:category='needs_initial_zeroes'
        elif row['frame_size']>512 or row['bytecode_operations']>512 or row['registers']>512:category='outside_small_shape'
        else:category='bounded_confined_leaf'
        if not proof['calls']:assert row['native_outgoing_calls']==0
        total=groups.setdefault(category,Counter())
        total['functions']+=1;total['native_incoming_calls']+=row['native_incoming_calls']
        total['call_samples']+=row['call_samples'];total['return_samples']+=row['return_samples']
        total['whole_function_native_operations']+=row['whole_function_native_operations']
        total['whole_function_interpreted_operations']+=row['whole_function_interpreted_operations']
        if category=='bounded_confined_leaf':selected.append(row)
    return dict(case=cost['case'],generated_samples=cost['generated_samples'],groups={k:dict(v) for k,v in groups.items()},
        incoming_calls=sum(v['native_incoming_calls'] for v in groups.values()),
        protocol_samples=sum(v['call_samples']+v['return_samples'] for v in groups.values()),
        selected=sorted(selected,key=lambda r:(-r['call_samples']-r['return_samples'],-r['native_incoming_calls'],r['function'])))
