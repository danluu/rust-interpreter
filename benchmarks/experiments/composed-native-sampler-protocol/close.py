import hashlib,subprocess
from qualify import ROOT,RUN,read,sha,write,acquire_lock,require_space
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
    p=read(raw/'plan.json');s=read(out/'summary.json');t=read(outer/'status.json');records=read(raw/'records.json')
    assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==p['owner']==str(ROOT)
    assert t['command'][1:]==p['controller_command'][1:] and sha(outer/'plan.json')==t['plan_sha256'] and sha(outer/'command.log')==t['log_sha256']
    assert sha(raw/'plan.json')==s['plan_sha256'] and sha(raw/'records.json')==s['records_sha256']
    assert len(records)==len(p['commands'])==5 and s['attribution_tests']==11 and s['retained_maps']==14
    for r,command in zip(records,p['commands']):
        assert all(r[k]==v for k,v in command.items()) and r['returncode']==r['expected']
        for stream in ['stdout','stderr']:assert sha(raw/(r['label']+'.'+stream))==r[stream+'_sha256']
    assert 'Ran 11 tests' in (raw/'attribution.stderr').read_text()
    assert read(raw/'retained-maps.stdout')==read(ROOT/'.work/vmmap-label-compatibility-01/retained-maps.stdout')
    bindings={}
    for path,h in p['frozen'].items():
        assert sha(ROOT/path)==h
        if not path.startswith(('.work/','results/')):assert hashlib.sha256(subprocess.check_output(['git','show',p['source_revision']+':'+path],cwd=ROOT)).hexdigest()==h
        bindings[path]=dict(sha256=h,revision=p['source_revision'])
    evidence={str(f.relative_to(ROOT)):sha(f) for f in [*raw.iterdir(),outer/'status.json',outer/'plan.json',outer/'command.log'] if f.is_file()}
    assert not (out/'closure.json').exists();write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,new_guest_commands=0,new_rust_builds=0,
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json')))
    print('Closed indirect-aware sampler protocol; no guest or Rust build commands')
