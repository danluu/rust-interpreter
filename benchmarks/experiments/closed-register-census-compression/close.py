"""Independently re-read compressed profile evidence; never mutate an input."""
from compress_profiles import *

with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
    plan=read(raw/'plan.json');summary=read(out/'summary.json');terminal=read(outer/'status.json')
    assert summary['status']=='passed' and terminal['status']=='finished' and terminal['returncode']==0
    assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
    assert terminal['command'][1:]==plan['controller_command'][1:]
    assert Path(terminal['command'][0]).resolve()==Path(plan['controller_command'][0]).resolve()
    assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
    for n in ['plan','inventory','records','runs']:assert sha(raw/(n+'.json'))==summary[n+'_sha256']
    rows=read(raw/'inventory.json');records=read(raw/'records.json');runs=read(raw/'runs.json')
    assert len(rows)==len(records)==summary['files'] and len(runs)==summary['runs']==6
    assert [r['run'] for r in runs]==RUNS and sum(r['files'] for r in runs)==len(rows)
    final=[];allocation_changes=[]
    for i,(row,record) in enumerate(zip(rows,records)):
        p=ROOT/row['path'];assert record['index']==i and record['path']==row['path'] and record['returncode']==0
        assert record['state'] in ['replaced','original-retained-no-saving']
        current=verify(p,row['sha256'],row['before'])
        assert all(current[k]==v for k,v in record['after'].items() if k!='blocks'),(p,current,record['after'])
        assert 0<current['blocks']<=record['after']['blocks'],(p,current,record['after'])
        if current['blocks']!=record['after']['blocks']:
            allocation_changes.append(dict(path=row['path'],recorded_blocks=record['after']['blocks'],readback_blocks=current['blocks']))
        final.append(dict(path=row['path'],identity=current))
        assert list(birthtime(p))==row['native_birthtime']
        assert not p.with_name('.'+p.name+'.'+RUN+'.tmp').exists()
        for stream in ['stdout','stderr']:assert sha(raw/(str(i)+'.'+stream))==record[stream+'_sha256']
    assert summary['allocated_bytes_before']==sum(r['before']['blocks']*512 for r in rows)
    assert summary['allocated_bytes_after']==sum(r['after']['blocks']*512 for r in records)
    assert summary['compressed_files']==sum(r['state']=='replaced' for r in records)
    bindings={}
    for p,h in plan['frozen'].items():
        assert sha(ROOT/p)==h
        if not p.startswith(('.work/','results/')):
            assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)).hexdigest()==h
        bindings[p]=dict(sha256=h,revision=plan['source_revision'])
    assert sha(Path(plan['tool']))==plan['tool_sha256']
    write(raw/'final-readback.json',dict(files=final,allocation_changes=allocation_changes,allocated_bytes=sum(r['identity']['blocks']*512 for r in final)))
    evidence={str(p.relative_to(ROOT)):sha(p) for p in [*raw.iterdir(),outer/'plan.json',outer/'status.json',outer/'command.log'] if p.is_file()}
    assert not (out/'closure.json').exists()
    write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,all_original_plaintext_hashes_preserved=True,
        exact_native_creation_time_preserved=True,allocation_only_decreases=len(allocation_changes),
        readback_allocated_bytes_after=sum(r['identity']['blocks']*512 for r in final),
        final_readback_sha256=sha(raw/'final-readback.json'),summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json')))
    print('Closed',len(rows),'byte-identical public bytecode/JSON files;',summary['allocated_bytes_before']-summary['allocated_bytes_after'],'bytes reclaimed')
