import hashlib,statistics,subprocess
from analyze import ROOT,RUN,CASES,MODES,read,sha,write,acquire_lock,require_space,accounting
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
    p=read(raw/'plan.json');s=read(out/'summary.json');t=read(outer/'status.json');d=read(raw/'derived.json')
    assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==p['owner']==str(ROOT)
    assert t['command'][1:]==p['controller_command'][1:] and sha(outer/'plan.json')==t['plan_sha256'] and sha(outer/'command.log')==t['log_sha256']
    assert sha(raw/'plan.json')==s['plan_sha256'] and sha(raw/'derived.json')==s['derived_sha256']
    assert s['new_compiler_or_guest_commands']==s['new_timing_samples']==0 and s['original_verdicts_reproduced']==4 and s['suite_reports']==240
    for case,name in CASES.items():
        original=read(ROOT/'results'/name/'summary.json');stage=ROOT/original['raw']
        module,_=accounting(case);rows,_=module.account(read(stage/'records.json'),read(stage/'sessions.json'))
        assert {k:v for k,v in d[case].items() if k!='paired_observations'}==s['cases'][case]
        assert len(d[case]['paired_observations'])==15
        for mode in MODES:
            selected=[r for r in rows if r['state']>0 and r['mode']==mode];assert len(selected)==15
            values=d[case]['medians'][mode]
            for metric in ['wall_seconds','cpu_seconds']:
                assert values['command_'+metric]==statistics.median(r['accounted_'+metric] for r in selected)
            for metric in ['build_to_ready_seconds','execution_seconds']:
                assert values[metric]==statistics.median(r['launch'][metric] for r in selected)
            reports=[read(stage/(str(r['index'])+'-suite.json')) for r in selected]
            assert values['longest_guest_test_seconds']==statistics.median(max(t['seconds'] for t in j['tests']) for j in reports)
            assert values['jit_compile_work_seconds']==statistics.median(sum(t['jit_compile_ns'] for t in j['tests'])/1e9 for j in reports)
        for pair in d[case]['paired_observations']:
            for metric in ['wall_seconds','cpu_seconds']:
                old=next(r for r in original['measurement']['pairs'] if r['cycle']==pair['cycle'] and r['state']==pair['state'])
                assert pair['ratios']['baseline']['command_'+metric]==old[metric]['candidate_baseline']
    bindings={}
    for path,h in p['frozen'].items():
        assert sha(ROOT/path)==h
        if not path.startswith(('.work/','results/')):assert hashlib.sha256(subprocess.check_output(['git','show',p['source_revision']+':'+path],cwd=ROOT)).hexdigest()==h
        bindings[path]=dict(sha256=h,revision=p['source_revision'])
    evidence={str(f.relative_to(ROOT)):sha(f) for f in [raw/'plan.json',raw/'derived.json',outer/'status.json',outer/'plan.json',outer/'command.log']}
    assert not (out/'closure.json').exists();write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,new_timing_samples=0,
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json')))
    print('Closed four original histories and240 suite reports; no new timing samples')
