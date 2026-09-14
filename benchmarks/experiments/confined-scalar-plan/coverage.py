"""Join exact typed access plans to previously closed native-call evidence."""
from collections import Counter


def analyze(typed, previous):
    assert typed['status']=='passed' and typed['guest_commands']==typed['runtime_changes']==0
    assert typed['address_nonescape_proved'] is False
    functions=typed['functions'];assert [f['function'] for f in functions]==list(range(len(functions)))
    groups={};selected=[];seen=set()
    for row in previous['selected']:
        fid=row['function'];assert type(fid) is int and 0<=fid<len(functions) and fid not in seen;seen.add(fid)
        f=functions[fid]
        for field in ['name','frame_size','registers','bytecode_operations']:assert f[field]==row[field]
        plan=f['plan']
        assert bool(plan['eligible'])==(plan['decline'] is None)
        if not plan['eligible']:assert plan['accesses']==[]
        widths=Counter();last=-1
        for access in plan['accesses']:
            pc=access['pc'];assert type(pc) is int and last<pc<f['bytecode_operations'];last=pc
            for side in ['reads','writes']:
                for extent in access[side]:
                    size=extent['size'];offset=extent['offset'];assert type(size) is int and size>=0
                    if size==0:assert offset is None
                    else:assert type(offset) is int and offset>=0 and offset+size<=max(1,f['frame_size'])
                    widths[side+':'+str(size)]+=1
        category='resolved_accesses' if plan['eligible'] else plan['decline']['reason']
        counts=groups.setdefault(category,Counter())
        for key in ['native_incoming_calls','call_samples','return_samples','whole_function_native_operations','whole_function_interpreted_operations']:
            counts[key]+=row[key]
        counts['functions']+=1
        if plan['eligible']:
            selected.append(dict(row,arguments=f['arguments'],result=f['result'],
                annotated_pcs=len(plan['accesses']),access_widths=dict(widths),proof_work=plan['work']))
    expected=previous['groups']['bounded_confined_leaf']
    for key,value in expected.items():assert sum(g[key] for g in groups.values())==value
    return dict(case=previous['case'],groups={k:dict(v) for k,v in groups.items()},selected=selected,
        generated_samples=previous['generated_samples'],performance_measurement=False,
        guest_commands=0,runtime_changes=0,address_nonescape_proved=False)
