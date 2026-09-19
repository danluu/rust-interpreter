import hashlib,subprocess
from analyze import ROOT,RUN,derive,read,sha,write,acquire_lock,require_space
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
    p=read(raw/'plan.json');s=read(out/'summary.json');t=read(outer/'status.json')
    assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==p['owner']==str(ROOT)
    assert t['command'][1:]==p['controller_command'][1:] and sha(outer/'plan.json')==t['plan_sha256'] and sha(outer/'command.log')==t['log_sha256']
    assert sha(raw/'plan.json')==s['plan_sha256'] and sha(raw/'derived.json')==s['derived_sha256']
    d,inputs=derive();assert d==read(raw/'derived.json') and all(p['frozen'][k]==v for k,v in inputs.items())
    assert s['largest_wall_variation']==d['largest_wall_variation'] and s['descriptive_medians']==d['descriptive_medians']
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
    print('Closed all15 parser A/A pairs and60 original suite reports; no new timings')
