"""Preserve the original failed byte-equality check and every generated artifact."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
RUN='heap-layout-profile-02'
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;outer=ROOT/'.work/experiments'/RUN;out=ROOT/'results'/RUN
    plan=read(raw/'plan.json');rows=read(raw/'records.json');terminal=read(outer/'status.json')
    assert terminal['status']=='finished' and terminal['returncode']==1
    assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
    assert terminal['command'][1:]==plan['controller_command'][1:]
    assert Path(terminal['command'][0]).resolve()==Path(plan['controller_command'][0]).resolve()
    assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
    assert 'AssertionError: native code changed' in (outer/'command.log').read_text()
    assert len(rows)==1 and rows[0]['index']==0 and rows[0]['returncode']==0 and plan['expected_commands']==3
    for stream in ['stdout','stderr']:assert sha(raw/('0.'+stream))==rows[0][stream+'_sha256']
    bindings={}
    for p,h in plan['frozen'].items():
        assert sha(ROOT/p)==h,p
        if not p.startswith(('.work/','results/')):
            assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)).hexdigest()==h
        bindings[p]=dict(sha256=h,revision=plan['source_revision'])
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for p in Path(__file__).parent.iterdir():
        if p.suffix in ['.py','.md']:
            name=str(p.relative_to(ROOT));digest=sha(p)
            assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+name],cwd=ROOT)).hexdigest()==digest
            bindings[name]=dict(sha256=digest,revision=revision)
    evidence={str(p.relative_to(ROOT)):sha(p) for p in [*raw.rglob('*'),outer/'plan.json',outer/'status.json',outer/'command.log'] if p.is_file()}
    assert not any(p.is_symlink() for p in raw.rglob('*'))
    out.mkdir(exist_ok=False);write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'summary.json',dict(status='profile-failed',source_revision=plan['source_revision'],raw=str(raw.relative_to(ROOT)),
        commands=1,returncodes=[0],failed_check='unrelocated native bytes differ',plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
        original_project_guest_commands=1,performance_measurement=False,default_runtime_adoption=False))
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,all_generated_artifacts_retained=True,
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json')))
    print('Closed native byte-equality failure; one guest execution and all generated evidence retained')
