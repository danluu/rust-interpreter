"""Partition qualified scalar coverage by explicit native emission admission."""
from collections import Counter

def analyze(typed,prior):
    assert typed['status']=='passed' and typed['guest_commands']==typed['runtime_changes']==0
    functions=typed['functions'];assert [f['function'] for f in functions]==list(range(len(functions)))
    groups={};selected=[];seen=set()
    for row in prior['selected']:
        fid=row['function'];assert type(fid) is int and 0<=fid<len(functions) and fid not in seen;seen.add(fid)
        f=functions[fid]
        for field in ['name','frame_size','registers','bytecode_operations','scalar']:assert f[field]==row[field]
        native=f['native'];assert len(native)==2 and [n['profiled'] for n in native]==[False,True]
        assert native[0]['eligible']==native[1]['eligible']
        if native[0]['eligible']:
            for n in native:
                assert type(n['code_bytes']) is int and 0<n['code_bytes']<=65536*4 and n['code_bytes']%4==0
                assert type(n['stack_bytes']) is int and 0<=n['stack_bytes']<=32752 and n['stack_bytes']%16==0
                assert 'decline' not in n
            assert native[0]['stack_bytes']==native[1]['stack_bytes']
            category='native_scalar';selected.append(dict(row,native=native))
        else:
            assert native[0]['decline']==native[1]['decline'];category=native[0]['decline']
        g=groups.setdefault(category,Counter());g['functions']+=1
        for key in ['native_incoming_calls','call_samples','return_samples','whole_function_native_operations',
            'whole_function_interpreted_operations','weighted_native_scalar_computation_nodes']:g[key]+=row[key]
    for key,value in prior['groups']['scalar_ir'].items():assert sum(g[key] for g in groups.values())==value
    return dict(case=prior['case'],groups={k:dict(v) for k,v in groups.items()},selected=selected,
        performance_measurement=False,guest_commands=0,runtime_changes=0,
        limitation='Native emission eligibility and synthetic native tests do not qualify the original guest Call transaction or predict complete-command speed.')
