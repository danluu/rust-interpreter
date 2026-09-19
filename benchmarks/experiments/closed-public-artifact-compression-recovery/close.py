import hashlib,subprocess
from qualify import ROOT,RUN,ORIGINAL,prefix,sha,read,write,acquire_lock,require_space,Path,verify
from birthtime import birthtime
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
    plan=read(raw/'plan.json');summary=read(out/'summary.json');terminal=read(outer/'status.json')
    assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
    assert terminal['command'][1:]==plan['controller_command'][1:] and sha(outer/'command.log')==terminal['log_sha256'] and sha(outer/'plan.json')==terminal['plan_sha256']
    for n in ['plan','prefix','copy','fixture']:assert sha(raw/(n+'.json'))==summary[n+'_sha256']
    assert prefix()==read(raw/'prefix.json')
    f=read(raw/'fixture.json');assert verify(raw/'copy.tmp',f['sha256'],f['source'])==f['copy']
    assert list(birthtime(raw/'source.fixture'))==list(birthtime(raw/'copy.tmp'))==f['original_creation_time']==f['restored_creation_time']
    copy=read(raw/'copy.json');assert copy['returncode']==0
    for stream in ['stdout','stderr']:assert sha(raw/('copy.'+stream))==copy[stream+'_sha256']
    assert sha(Path(plan['header']))==plan['header_sha256'];bindings={}
    for p,h in plan['frozen'].items():
        assert sha(ROOT/p)==h
        if not p.startswith(('.work/','results/')):assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)).hexdigest()==h
        bindings[p]=dict(sha256=h,revision=plan['source_revision'])
    evidence={str(p.relative_to(ROOT)):sha(p) for p in [*raw.iterdir(),outer/'plan.json',outer/'status.json',outer/'command.log'] if p.is_file()}
    assert not (out/'closure.json').exists();write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,existing_evidence_modified=0,
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json')))
    failed=ROOT/'results'/ORIGINAL;failed.mkdir(exist_ok=False)
    saved=read(raw/'prefix.json');write(failed/'summary.json',{k:v for k,v in saved.items() if k!='frozen'}|dict(status='partial-stopped',reason='ditto creation-time mismatch before replacement',performance_measurement=False))
    (failed/'terminal.json').write_bytes((ROOT/'.work/experiments'/ORIGINAL/'status.json').read_bytes())
    write(failed/'closure.json',dict(status='closed',all_original_plaintext_hashes_preserved=True,
        summary_sha256=sha(failed/'summary.json'),terminal_sha256=sha(failed/'terminal.json'),
        recovery_qualification=RUN,recovery_closure_sha256=sha(out/'closure.json')))
    print('Closed partial prefix and exact creation-time recovery qualification')
