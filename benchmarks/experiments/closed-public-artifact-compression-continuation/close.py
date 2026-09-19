import hashlib,importlib.util,subprocess
from pathlib import Path
spec=importlib.util.spec_from_file_location('storage_continuation',Path(__file__).with_name('continue.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ROOT,RUN,ORIGINAL=m.ROOT,m.RUN,m.ORIGINAL
read,sha,write=m.read,m.sha,m.write
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    m.acquire_lock(lock,45);m.require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
    plan=read(raw/'plan.json');summary=read(out/'summary.json');terminal=read(outer/'status.json')
    rows=read(ROOT/'.work'/ORIGINAL/'inventory.json');records=read(raw/'records.json');final=read(raw/'final-identities.json')
    assert terminal['status']=='finished' and terminal['returncode']==0 and summary['status']=='passed'
    assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT) and terminal['command'][1:]==plan['controller_command'][1:]
    assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
    for n in ['plan','records','final-identities']:assert sha(raw/(n+'.json'))==summary[n.replace('-','_')+'_sha256']
    assert sha(ROOT/'.work'/ORIGINAL/'inventory.json')==plan['original_inventory_sha256']
    assert len(rows)==len(final)==373 and len(records)==241
    for i,(row,current) in enumerate(zip(rows,final)):
        p=ROOT/row['path'];assert m.verify(p,row['sha256'],row['before'])==current
        for suffix in [ORIGINAL,RUN]:assert not p.with_name('.'+p.name+'.'+suffix+'.tmp').exists()
        if i<132:continue
        record=records[i-132];assert record['index']==i and record['path']==row['path'] and record['returncode']==0
        assert record['after']==current and record['state'] in ['replaced','original-retained-no-saving']
        assert list(m.birthtime(p))==record['native_creation_time_before']
        assert record['reused_pending_copy']==(i==132)
        if i>132:
            for stream in ['stdout','stderr']:assert sha(raw/(str(i)+'.'+stream))==record[stream+'_sha256']
    assert summary['allocated_bytes_before']==sum(r['before']['blocks']*512 for r in rows)
    assert summary['allocated_bytes_after']==sum(r['blocks']*512 for r in final)
    bindings={}
    for p,h in plan['frozen'].items():
        assert sha(ROOT/p)==h
        if not p.startswith(('.work/','results/')):assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)).hexdigest()==h
        bindings[p]=dict(sha256=h,revision=plan['source_revision'])
    assert sha(Path(plan['tool']))==plan['tool_sha256']
    evidence={str(p.relative_to(ROOT)):sha(p) for p in [*raw.iterdir(),outer/'plan.json',outer/'status.json',outer/'command.log'] if p.is_file()}
    assert not (out/'closure.json').exists();write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,all_original_plaintext_hashes_preserved=True,
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json')))
    print('Closed373 byte-identical public artifacts with complete metadata checks')
