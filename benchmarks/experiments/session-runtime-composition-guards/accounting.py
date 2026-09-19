"""Prospective eight-mode project guards with complete session accounting."""
import copy,hashlib,math,statistics

CUSTOM=['baseline','duplicate','candidate','anchor','session-fresh']
MODES=[*CUSTOM,'native','native_lines','check']
SESSION_MODES=['session-fresh','candidate']
STATES=[(c,s) for c in range(3) for s in [0,-1,1,2,3,4,5]]+[(3,0)]

def schedule(states):
    assert [(s['cycle'],s['state']) for s in states]==STATES
    rows=[]
    for state in states:
        cycle,value=state['cycle'],state['state']
        index=cycle*5+value-1 if value>0 else cycle*2+(value==-1)
        custom=CUSTOM[index%5:]+CUSTOM[:index%5]
        native=['native','native_lines'] if (value+cycle)%2 else ['native_lines','native']
        for mode in [native[0],*custom,native[1],'check']:
            rows.append(dict(cycle=cycle,state=value,mode=mode,label=state['label'],
                source_sha256=hashlib.sha256(state['source']).hexdigest()))
    return rows

def nonnegative(value):
    assert type(value) in [int,float] and math.isfinite(value) and value>=0
    return value

def request_cpu(row):
    response=row['launch']['template_session']['response'];cpu=[]
    for field in ['user_us','system_us']:
        before=response['cpu_before'][field];after=response['cpu_after'][field]
        assert type(before) is type(after) is int and 0<=before<=after
        cpu.append((after-before)/1_000_000)
    return sum(cpu)

def account(records,sessions):
    assert len(records)==176 and set(sessions)==set(SESSION_MODES)
    for mode in MODES:
        assert [(r['cycle'],r['state']) for r in records if r['mode']==mode]==STATES
    rows=copy.deepcopy(records);overheads={}
    for row in rows:
        assert row['mode'] in MODES and (row['cycle'],row['state']) in STATES
        for key in ['wall_seconds','cpu_seconds']:assert nonnegative(row[key])>0
        row['accounted_wall_seconds']=row['wall_seconds'];row['accounted_cpu_seconds']=row['cpu_seconds']
    for mode in SESSION_MODES:
        selected=[r for r in rows if r['mode']==mode];session=sessions[mode]
        assert [(r['cycle'],r['state']) for r in selected]==STATES
        assert session['returncode']==0 and session['requests_consumed']==22 and session['verify_hits'] is False
        assert session['history_bytes_per_worker']==(0 if mode=='session-fresh' else 64*1024**2)
        for i,row in enumerate(selected):
            receipt=row['launch']['template_session'];assert receipt['request_id']==i+1 and receipt['server_pid']==session['pid']
            assert receipt['server_executable_sha256']==session['executable_sha256'] and receipt['status']=='completed'
            assert receipt['verify_hits'] is False and receipt['history_bytes_per_worker']==session['history_bytes_per_worker']
            response=receipt['response']
            for field in ['user_us','system_us']:
                previous=selected[i-1]['launch']['template_session']['response']['cpu_after'][field] if i else session['cpu_at_ready'][field]
                assert previous<=response['cpu_before'][field]<=response['cpu_after'][field]<=session['closed']['cpu_at_close'][field]
            row['server_request_cpu_seconds']=request_cpu(row)
            row['accounted_cpu_seconds']+=row['server_request_cpu_seconds']
        captured=sum(r['server_request_cpu_seconds'] for r in selected)
        kernel=sum(nonnegative(session['kernel_cpu'][k]) for k in ['user_seconds','system_seconds'])
        # Snapshots are truncated to microseconds; kernel conversion permits1ms.
        assert kernel+0.001>=captured
        tail=max(0.0,kernel-captured)
        cpu=tail+sum(nonnegative(session[k]) for k in ['startup_parent_cpu_seconds','startup_helper_cpu_seconds','teardown_parent_cpu_seconds'])
        wall=sum(nonnegative(session[k]) for k in ['startup_wall_seconds','teardown_wall_seconds'])
        edited=[r for r in selected if r['state']>0];assert len(edited)==15
        for row in edited:
            row['accounted_cpu_seconds']+=cpu/15;row['accounted_wall_seconds']+=wall/15
        overheads[mode]=dict(kernel_cpu_seconds=kernel,request_cpu_seconds=captured,kernel_remainder_cpu_seconds=tail,
            charged_overhead_cpu_seconds=cpu,charged_overhead_wall_seconds=wall,allocation='all overhead divided equally over the fifteen valid edited commands')
        assert math.isclose(sum(r['accounted_cpu_seconds'] for r in selected),sum(r['cpu_seconds'] for r in selected)+captured+cpu)
    return rows,overheads

def ratios(records,sessions,case):
    assert case in ['token','folded','pgrust']
    rows,overheads=account(records,sessions);pairs=[]
    for cycle,state in STATES:
        selected=[r for r in rows if (r['cycle'],r['state'])==(cycle,state)];modes={r['mode']:r for r in selected}
        assert len(selected)==8 and set(modes)==set(MODES) and len({r['source_sha256'] for r in selected})==1
        if state<=0:continue
        row=dict(cycle=cycle,state=state)
        for key in ['wall_seconds','cpu_seconds']:
            metric='accounted_'+key
            row[key]=dict(candidate_baseline=modes['candidate'][metric]/modes['baseline'][metric],
                candidate_native=modes['candidate'][metric]/modes['native'][metric],
                candidate_native_lines=modes['candidate'][metric]/modes['native_lines'][metric],
                candidate_anchor=modes['candidate'][metric]/modes['anchor'][metric],
                candidate_session_fresh=modes['candidate'][metric]/modes['session-fresh'][metric],
                session_fresh_baseline=modes['session-fresh'][metric]/modes['baseline'][metric],
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
