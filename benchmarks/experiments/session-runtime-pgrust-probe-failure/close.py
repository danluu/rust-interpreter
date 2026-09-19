"""Close the strict-probe-only failure; prove that no timing or guest ran."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
RUN='session-runtime-composition-edit-pgrust-01'
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;outer=ROOT/'.work/experiments'/RUN;out=ROOT/'results'/RUN
    plan=read(raw/'plan.json');terminal=read(outer/'status.json');strict=read(raw/'strict.json');sessions=read(raw/'sessions.json')
    assert terminal['status']=='finished' and terminal['returncode']==1
    assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
    assert terminal['command'][1:]==plan['controller_command'][1:]
    assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
    assert plan['case_name']==plan['project']=='pgrust' and plan['expected_commands']==176
    assert read(raw/'records.json')==[] and [(r['label'],r['returncode']) for r in strict]==[('type',101),('borrow',101)]
    assert strict[0]['next_session_request_id']==1 and 'next_session_request_id' not in strict[1]
    for row,expected in zip(strict,['E0308','E0433']):
        for stream in ['stdout','stderr']:assert sha(raw/('strict-'+row['label']+'.'+stream))==row[stream+'_sha256']
        err=(raw/('strict-'+row['label']+'.stderr')).read_text()
        assert expected in err and 'rust-interp-launch: ' not in err
        assert not (raw/('strict-'+row['label']+'-suite.json')).exists()
        assert not (raw/('strict-'+row['label']+'-suite.json.session.json')).exists()
    error=(raw/'strict-borrow.stderr').read_text()
    assert 'cannot find module or crate `std` in this scope' in error and 'E0499' not in error
    assert set(sessions)=={'candidate','session-fresh'}
    evidence={};bindings={}
    for mode,session in sessions.items():
        assert session['returncode']==0 and session['requests_consumed']==0 and session['error'] is None
        assert session==read(raw/mode/'terminal.json')
        assert session['closed']['requests_consumed']==0
        for stream in ['stdout','stderr']:assert sha(raw/mode/stream)==session[stream+'_sha256']
        endpoint=Path(session['command'][session['command'].index('--serve-socket')+1])
        assert endpoint==ROOT/'.work/ts'/('composition-projects-pgrust-01-'+mode)
        ready=read(endpoint/'ready.json');assert ready['pid']==session['pid'] and ready['executable_sha256']==session['executable_sha256']
        evidence[str((endpoint/'ready.json').relative_to(ROOT))]=sha(endpoint/'ready.json')
    source=ROOT/plan['source'];changed=source/plan['case']['file']
    assert sha(changed)==plan['original_source_sha256']
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==plan['revision']
    owner=read(source/'.rust-interp-owned.json');assert owner['owner']==str(ROOT) and owner['revision']==plan['revision']
    for name,h in plan['frozen'].items():
        assert sha(ROOT/name)==h,name
        if name.startswith(('.work/','results/')):bindings[name]=dict(kind='retained',sha256=h)
        else:
            data=subprocess.check_output(['git','show',plan['source_revision']+':'+name],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==h,name
            bindings[name]=dict(kind='git',revision=plan['source_revision'],sha256=h)
    for p in raw.rglob('*'):
        if p.is_file():assert not p.is_symlink();evidence[str(p.relative_to(ROOT))]=sha(p)
    for name in ['status.json','plan.json','command.log']:evidence[str((outer/name).relative_to(ROOT))]=sha(outer/name)
    out.mkdir(exist_ok=False);write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'summary.json',dict(status='strict-probe-failed',reason='Borrow probe referred to std in a no_std crate; rejected with E0433 instead of E0499.',
        source_revision=plan['source_revision'],raw=str(raw.relative_to(ROOT)),commands=0,strict_controls=2,owned_sessions=2,
        session_requests=0,original_project_guest_commands=0,source_restored=True,performance_measurement=False,adoption=False,
        plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),strict_sha256=sha(raw/'strict.json'),sessions_sha256=sha(raw/'sessions.json')))
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,frozen_inputs=len(bindings),evidence_files=len(evidence),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),
        no_timed_commands=True,no_guest_execution=True,auditor_sha256=sha(Path(__file__))))
    print('Closed strict-probe failure: two compiler rejections; zero timed commands and zero session requests')
