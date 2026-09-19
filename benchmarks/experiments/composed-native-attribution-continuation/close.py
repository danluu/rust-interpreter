"""Independently close original captures and analysis-only continuation."""
import hashlib
import subprocess
from analyze import ROOT,RUN,PARENT,QUAL,KEY,VM,read,verify,terminal,acquire_lock,sha,require_space,write

with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;parent=ROOT/'.work'/PARENT;out=ROOT/'results'/PARENT
    p=read(raw/'plan.json');original=read(parent/'plan.json');s=read(out/'summary.json');verify(original)
    assert s['status']=='passed' and s['tool_key']==KEY and s['vm_sha256']==VM
    assert s['guest_commands']==2 and s['new_guests_during_analysis']==0 and not s['performance_measurement']
    assert s['new_summary_commands']==s['reused_successful_summary_commands']==1
    assert sha(raw/'plan.json')==s['plan_sha256'] and sha(parent/'plan.json')==s['original_plan_sha256']==p['original_plan_sha256']
    assert sha(raw/'records.json')==s['records_sha256'] and sha(raw/'attributions.json')==s['attributions_sha256']
    assert read(raw/'attributions.json')==s['cases'] and len(s['cases'])==2
    evidence={};bindings={}
    for path,h in p['frozen'].items():
        assert sha(ROOT/path)==h,path
        if path.startswith(('.work/','results/')):evidence[path]=h
        else:
            assert hashlib.sha256(subprocess.check_output(['git','show',p['source_revision']+':'+path],cwd=ROOT)).hexdigest()==h
            bindings[path]=dict(revision=p['source_revision'],sha256=h)
    archived=ROOT/original['archived_vm_sources']
    assert sha(archived)==s['archived_vm_sources_sha256']==original['archived_vm_sources_sha256']
    for path,row in read(archived).items():
        assert hashlib.sha256(subprocess.check_output(['git','show',row['revision']+':'+path],cwd=ROOT)).hexdigest()==row['sha256']
    evidence[str(archived.relative_to(ROOT))]=sha(archived)
    for name in [PARENT+'-prepare',QUAL,QUAL+'-close',RUN,*[c['run_id'] for c in original['cases']]]:
        folder,t=terminal(name)
        if name==RUN:assert t['command'][1:]==p['controller_command'][1:]
        for filename in ['status.json','plan.json','command.log']:
            path=folder/filename;evidence[str(path.relative_to(ROOT))]=sha(path)
    prior,=read(parent/'analysis-records.json');new,=read(raw/'records.json')
    assert prior['label']=='block' and new['label']=='exhaustive'
    for record,folder,case in zip([prior,new],[parent,raw],original['cases']):
        assert record['returncode']==0 and record['command']==case['summary_command']
        for stream in ['stdout','stderr']:
            path=folder/(record['label']+'.'+stream);assert sha(path)==record[stream+'_sha256']
            evidence[str(path.relative_to(ROOT))]=sha(path)
        captured,=read(ROOT/'.work'/case['run_id']/'records.json')
        assert captured['identity']['returncode']==0 and captured['mapped'] and captured['sample_returncode']==0
        assert captured['statistics']['jit_declined_functions']==0
        for rel,h in captured['files'].items():
            path=ROOT/'.work'/case['run_id']/'0'/rel;assert sha(path)==h;evidence[str(path.relative_to(ROOT))]=h
    for case in s['cases']:
        path=ROOT/case['report'];assert sha(path)==case['report_sha256'];report=read(path)
        assert report['status']=='passed' and report['reconstructed_same_process_code']
        assert report['profile_used_for_static_identity_only'] and not report['performance_measurement']
        assert sum(report['by_label'].values())==report['attributed_generated_samples']>0
        assert sum(r['count'] for r in report['unresolved'])==report['unassigned_generated_samples']
        assert report['attributed_generated_samples']+report['unassigned_generated_samples']==sum(
            report['disjoint_counts'].get(k,0) for k in ['generated_code','unresolved_unknown_binary'])
        evidence[str(path.relative_to(ROOT))]=sha(path);evidence.update(report['evidence'])
    for path in raw.iterdir():
        if path.is_file():evidence[str(path.relative_to(ROOT))]=sha(path)
    assert all(sha(ROOT/path)==h for path,h in evidence.items())
    assert not (out/'closure.json').exists()
    write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((ROOT/'.work/experiments'/RUN/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',source_revision=p['source_revision'],all_hashes_verified=True,
        frozen_inputs=len(p['frozen']),archived_vm_sources=len(read(archived)),
        source_bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),source_bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
        new_guest_commands=0,performance_measurement=False))
    print('Closed both original diagnostic captures and analysis continuation;',len(evidence),'evidence files')
