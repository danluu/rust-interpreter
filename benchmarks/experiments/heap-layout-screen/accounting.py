"""Prospective fre primary pairing using complete ordinary-process commands."""
import copy,hashlib,math,statistics

CUSTOM=['baseline','duplicate','candidate','anchor']
MODES=['native',*CUSTOM]
SESSION_MODES=[]
STATES=[(0,s) for s in [0,-1,1,2,3,4,5]]+[(1,0)]

def schedule(states):
    assert [(s['cycle'],s['state']) for s in states]==STATES
    rows=[]
    for i,state in enumerate(states):
        for offset in range(len(MODES)):
            rows.append(dict(cycle=state['cycle'],state=state['state'],mode=MODES[(i+offset)%len(MODES)],
                label=state['label'],source_sha256=hashlib.sha256(state['source']).hexdigest()))
    return rows

def nonnegative(value):
    assert type(value) in [int,float] and math.isfinite(value) and value>=0
    return value

def account(records,sessions):
    assert len(records)==40 and not sessions
    rows=copy.deepcopy(records)
    for row in rows:
        assert row['mode'] in MODES and (row['cycle'],row['state']) in STATES
        assert 'template_session' not in row.get('launch',{})
        for key in ['wall_seconds','cpu_seconds']:assert nonnegative(row[key])>0
        row['accounted_wall_seconds']=row['wall_seconds'];row['accounted_cpu_seconds']=row['cpu_seconds']
    return rows,{}

def ratios(records,sessions,case='token'):
    assert case=='token'
    rows,overheads=account(records,sessions);pairs=[]
    for cycle,state in STATES:
        selected=[r for r in rows if (r['cycle'],r['state'])==(cycle,state)];modes={r['mode']:r for r in selected}
        assert len(selected)==5 and set(modes)==set(MODES) and len({r['source_sha256'] for r in selected})==1
        if state<=0:continue
        row=dict(cycle=cycle,state=state)
        for key in ['wall_seconds','cpu_seconds']:
            metric='accounted_'+key
            row[key]=dict(candidate_baseline=modes['candidate'][metric]/modes['baseline'][metric],
                candidate_native=modes['candidate'][metric]/modes['native'][metric],
                candidate_anchor=modes['candidate'][metric]/modes['anchor'][metric],
                aa=modes['duplicate'][metric]/modes['baseline'][metric])
        pairs.append(row)
    medians={}
    for key in ['wall_seconds','cpu_seconds']:
        ratio=statistics.median(r[key]['candidate_baseline'] for r in pairs);aa=max(abs(r[key]['aa']-1) for r in pairs)
        medians[key]=dict(candidate_baseline=ratio,candidate_native=statistics.median(r[key]['candidate_native'] for r in pairs),
            candidate_anchor=statistics.median(r[key]['candidate_anchor'] for r in pairs),aa_envelope=aa,with_noise_margin=ratio+aa)
    wall,cpu=medians['wall_seconds'],medians['cpu_seconds']
    passed=wall['with_noise_margin']<1 and cpu['candidate_baseline']<=1 and cpu['with_noise_margin']<=1.05
    totals={mode:{key:sum(r['accounted_'+key] for r in rows if r['mode']==mode) for key in ['wall_seconds','cpu_seconds']} for mode in MODES}
    return dict(pairs=pairs,medians=medians,session_overheads=overheads,full_history_totals=totals,edited_pairs=5,aa_pairs=5,
        gate_passed=passed,verdict='passed' if passed else ('unmeasurable' if max(wall['aa_envelope'],cpu['aa_envelope'])>.08 else 'failed'),adoption=False)
