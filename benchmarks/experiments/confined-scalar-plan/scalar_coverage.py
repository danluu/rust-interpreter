"""Weight scalar-node locations by original counts; this is not a timing model."""
from collections import Counter


def analyze(typed,prior,profile):
    assert typed['status']=='passed' and typed['guest_commands']==typed['runtime_changes']==0
    functions=typed['functions'];assert [f['function'] for f in functions]==list(range(len(functions)))
    assert len(functions)==len(profile['functions'])
    groups={};selected=[];seen=set()
    for row in prior['selected']:
        fid=row['function'];assert type(fid) is int and 0<=fid<len(functions) and fid not in seen;seen.add(fid)
        f=functions[fid];p=profile['functions'][fid];s=f['scalar'];count=f['bytecode_operations']
        for field in ['name','frame_size','registers']:assert row[field]==f[field]==p[field]
        assert row['bytecode_operations']==len(p['operations'])==count
        assert len(p['jit_blocks'])==len(p['jit_block_ends'])==len(p['interpreted'])==count
        assert not any(p['jit_tree_blocks'])
        deltas=[0]*(count+1)
        for pc,hits in enumerate(p['jit_blocks']):
            assert type(hits) is int and hits>=0
            if hits:
                end=p['jit_block_ends'][pc];assert type(end) is int and pc<end<=count
                deltas[pc]+=hits;deltas[end]-=hits
        native=[];running=0
        for delta in deltas[:-1]:running+=delta;assert running>=0;native.append(running)
        assert running+deltas[-1]==0
        assert sum(native)==row['whole_function_native_operations']
        assert sum(p['interpreted'])==row['whole_function_interpreted_operations']
        assert s['eligible']==(s['decline'] is None)
        category='scalar_ir' if s['eligible'] else s['decline'];g=groups.setdefault(category,Counter())
        for key in ['native_incoming_calls','call_samples','return_samples','whole_function_native_operations','whole_function_interpreted_operations']:g[key]+=row[key]
        g['functions']+=1
        if s['eligible']:
            nodes=s['live_computations_per_pc'];assert len(nodes)==count and all(type(n) is int and n>=0 for n in nodes)
            assert 1<=s['maximum_steps']<=s['reachable_operations']<=count and s['live_phis']<=s['live_nodes']<=s['nodes']
            weighted=sum(n*h for n,h in zip(nodes,native))
            g['weighted_native_scalar_computation_nodes']+=weighted
            selected.append(dict(row,scalar=s,weighted_native_scalar_computation_nodes=weighted))
        else:assert s['live_computations_per_pc']==[]
    for key,value in prior['groups']['resolved_accesses'].items():assert sum(g[key] for g in groups.values())==value
    return dict(case=prior['case'],groups={k:dict(v) for k,v in groups.items()},selected=selected,
        performance_measurement=False,guest_commands=0,runtime_changes=0,
        limitation='Scalar computation nodes exclude inputs, phis, control flow, profile/budget work, register allocation and call protocol; counts do not predict native instructions or time.')
