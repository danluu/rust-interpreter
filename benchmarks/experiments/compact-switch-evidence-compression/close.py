"""Independently verify completed transparent storage conversion."""
import hashlib,subprocess
from compress import ROOT,RUN,PRESERVE,read,sha,write,acquire_lock,require_space,verify,Path,birthtime,METADATA_PROOF
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
    plan=read(raw/'plan.json');rows=read(raw/'inventory.json');records=read(raw/'records.json')
    summary=read(out/'summary.json');terminal=read(outer/'status.json')
    assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
    assert terminal['status']=='finished' and terminal['returncode']==0 and summary['status']=='passed'
    assert terminal['command'][1:]==plan['controller_command'][1:]
    assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
    for name in ['plan','inventory','records']:assert sha(raw/(name+'.json'))==summary[name+'_sha256']
    assert len(rows)==len(records)==summary['files'] and sha(raw/'inventory.json')==plan['inventory_sha256']
    for i,(row,record) in enumerate(zip(rows,records)):
        p=ROOT/row['path'];assert record['index']==i and record['path']==row['path'] and record['returncode']==0
        assert record['state'] in ['replaced','original-retained-no-saving']
        assert verify(p,row['sha256'],row['before'])==record['after']
        assert list(birthtime(p))==row['native_birthtime']
        assert not p.with_name('.'+p.name+'.'+RUN+'.tmp').exists()
        for stream in ['stdout','stderr']:assert sha(raw/(str(i)+'.'+stream))==record[stream+'_sha256']
    assert summary['exact_native_creation_time_preserved'] and summary['qualified_metadata_proof']==METADATA_PROOF
    assert summary['compressed_files']==sum(r['state']=='replaced' for r in records)
    assert summary['allocated_bytes_before']==sum(r['before']['blocks']*512 for r in rows)
    assert summary['allocated_bytes_after']==sum(r['after']['blocks']*512 for r in records)
    bindings={}
    for p,h in plan['frozen'].items():
        assert sha(ROOT/p)==h,p
        if not p.startswith(('.work/','results/')):
            assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)).hexdigest()==h,p
        bindings[p]=dict(sha256=h,revision=plan['source_revision'])
    assert sha(Path(plan['tool']))==plan['tool_sha256']
    evidence={str(p.relative_to(ROOT)):sha(p) for p in [*raw.iterdir(),outer/'plan.json',outer/'status.json',outer/'command.log'] if p.is_file()}
    assert not (out/'closure.json').exists();write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,all_plaintext_hashes_preserved=True,exact_native_creation_time_preserved=True,
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json')))
    print('Closed transparent compression:',len(rows),'complete original plaintext hashes preserved')
