import hashlib,subprocess
from qualify import ROOT,RUN,read,sha,write,acquire_lock,require_space
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
    p=read(raw/'plan.json');s=read(out/'summary.json');t=read(outer/'status.json');records=read(raw/'records.json')
    assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==p['owner']==str(ROOT)
    assert t['command'][1:]==p['controller_command'][1:] and sha(outer/'plan.json')==t['plan_sha256'] and sha(outer/'command.log')==t['log_sha256']
    assert sha(raw/'plan.json')==s['plan_sha256'] and sha(raw/'records.json')==s['records_sha256']
    assert len(records)==2 and all(r['returncode']==0 for r in records) and 'Ran 5 tests' in (raw/'controls.stderr').read_text()
    for r in records:
        for stream in ['stdout','stderr']:assert sha(raw/(r['label']+'.'+stream))==r[stream+'_sha256']
    assert read(raw/'retained.stdout')['cases']==s['captured_cases'];bindings={}
    for path,h in p['frozen'].items():
        assert sha(ROOT/path)==h
        if not path.startswith(('.work/','results/')):assert hashlib.sha256(subprocess.check_output(['git','show',p['source_revision']+':'+path],cwd=ROOT)).hexdigest()==h
        bindings[path]=dict(sha256=h,revision=p['source_revision'])
    evidence={str(f.relative_to(ROOT)):sha(f) for f in [*raw.iterdir(),outer/'status.json',outer/'plan.json',outer/'command.log'] if f.is_file()}
    assert not (out/'closure.json').exists();write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,new_guest_commands=0,
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json')))
    failed=ROOT/'results/composed-fre-runtime-sampling-01-analysis-01';failed.mkdir(exist_ok=False)
    write(failed/'summary.json',dict(status='failed',reason='Legacy static ownership reader did not accept resumable_indirect_call regions',
        successful_capture_guests=2,new_guests_during_analysis=0,successful_summary_commands=1,attribution_files_written=0,
        retained_qualification=RUN,performance_measurement=False))
    (failed/'terminal.json').write_bytes((ROOT/'.work/experiments/composed-fre-runtime-sampling-01-analyze/status.json').read_bytes())
    write(failed/'closure.json',dict(status='closed',all_original_capture_hashes_preserved=True,
        summary_sha256=sha(failed/'summary.json'),terminal_sha256=sha(failed/'terminal.json'),
        qualification=RUN,qualification_closure_sha256=sha(out/'closure.json')))
    print('Closed new region-reader qualification and retained original analysis failure')
