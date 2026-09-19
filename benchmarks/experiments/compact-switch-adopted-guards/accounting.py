"""Prospective seven-arm ordinary-VM project guards."""
import copy,hashlib,math,statistics

CUSTOM=['baseline','duplicate','candidate','anchor']
MODES=[*CUSTOM,'native','native_lines','check']
SESSION_MODES=[]
STATES=[(c,s) for c in range(3) for s in [0,-1,1,2,3,4,5]]+[(3,0)]

def schedule(states):
    assert [(s['cycle'],s['state']) for s in states]==STATES
    rows=[]
    for state in states:
        cycle,value=state['cycle'],state['state']
        index=cycle*5+value-1 if value>0 else cycle*2+(value==-1)
        custom=[CUSTOM[int(i)] for i in ['0132','1203','2310','3021'][index%4]]
        native=['native','native_lines'] if (value+cycle)%2 else ['native_lines','native']
        for mode in [native[0],*custom,native[1],'check']:
            rows.append(dict(cycle=cycle,state=value,mode=mode,label=state['label'],
                source_sha256=hashlib.sha256(state['source']).hexdigest()))
    return rows

def nonnegative(value):
    assert type(value) in [int,float] and math.isfinite(value) and value>=0
    return value

def account(records,sessions):
    assert len(records)==154 and not sessions
    for mode in MODES:
        assert [(r['cycle'],r['state']) for r in records if r['mode']==mode]==STATES
    rows=copy.deepcopy(records)
    for row in rows:
        assert row['mode'] in MODES and (row['cycle'],row['state']) in STATES
        assert 'template_session' not in row.get('launch',{})
        for key in ['wall_seconds','cpu_seconds']:assert nonnegative(row[key])>0
        row['accounted_wall_seconds']=row['wall_seconds'];row['accounted_cpu_seconds']=row['cpu_seconds']
    return rows,{}

def ratios(records,sessions,case):
    assert case in ['token','folded','pgrust']
    rows,overheads=account(records,sessions);pairs=[]
    for cycle,state in STATES:
        selected=[r for r in rows if (r['cycle'],r['state'])==(cycle,state)];modes={r['mode']:r for r in selected}
        assert len(selected)==7 and set(modes)==set(MODES) and len({r['source_sha256'] for r in selected})==1
        if state<=0:continue
        row=dict(cycle=cycle,state=state)
        for key in ['wall_seconds','cpu_seconds']:
            metric='accounted_'+key
            row[key]=dict(candidate_baseline=modes['candidate'][metric]/modes['baseline'][metric],
                candidate_native=modes['candidate'][metric]/modes['native'][metric],
                candidate_native_lines=modes['candidate'][metric]/modes['native_lines'][metric],
                candidate_anchor=modes['candidate'][metric]/modes['anchor'][metric],
                aa=modes['duplicate'][metric]/modes['baseline'][metric])
        pairs.append(row)
    medians={}
    for key in ['wall_seconds','cpu_seconds']:
        values={field:statistics.median(r[key][field] for r in pairs) for field in pairs[0][key] if field!='aa'}
        aa=max(abs(statistics.median(r[key]['aa'] for r in pairs if r['state']==state)-1) for state in range(1,6))
        worst=max(abs(r[key]['aa']-1) for r in pairs)
        medians[key]=dict(**values,aa_envelope=aa,worst_individual_aa=worst,
            with_noise_margin=max(values['candidate_baseline'],values['candidate_anchor'])+aa)
    wall,cpu=medians['wall_seconds'],medians['cpu_seconds']
    if case=='token':
        wall_ok=wall['candidate_anchor']<=.92 and wall['candidate_baseline']<1-wall['aa_envelope']
        cpu_ok=max(cpu['candidate_baseline'],cpu['candidate_anchor'])<=1 and cpu['with_noise_margin']<=1.05
    else:
        wall_ok=wall['with_noise_margin']<=1.05;cpu_ok=cpu['with_noise_margin']<=1.05
    passed=wall_ok and cpu_ok
    totals={mode:{key:sum(r['accounted_'+key] for r in rows if r['mode']==mode) for key in ['wall_seconds','cpu_seconds']} for mode in MODES}
    return dict(case=case,pairs=pairs,medians=medians,session_overheads=overheads,full_history_totals=totals,edited_pairs=15,aa_pairs=15,
        gate_passed=passed,verdict='passed' if passed else ('unmeasurable' if max(wall['aa_envelope'],cpu['aa_envelope'])>.08 else 'failed'),adoption=False)
