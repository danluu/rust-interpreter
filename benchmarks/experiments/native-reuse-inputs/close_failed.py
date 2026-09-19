"""Preserve the first diagnostic's invalid TLS fixture before correcting it."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    run='native-reuse-inputs-01';raw=ROOT/'.work'/run;outer=ROOT/'.work/experiments'/run
    plan=read(raw/'plan.json');terminal=read(outer/'status.json');records=read(raw/'records.json')
    assert terminal['status']=='finished' and terminal['returncode']==1
    assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
    assert terminal['command'][1:]==['-B',*plan['controller_command'][1:]]
    assert terminal['log_sha256']==sha(outer/'command.log') and terminal['plan_sha256']==sha(outer/'plan.json')
    assert sha(raw/'artifacts.json')==plan['artifacts_sha256']
    assert [(r['label'],r['returncode']) for r in records]==[('python',0),('debug',101)]
    assert 'invalid or overlapping thread-local initializer' in (raw/'debug.stdout').read_text()
    assert not (raw/'typed').exists()
    bindings={};evidence={}
    for p,h in plan['frozen'].items():
        assert sha(ROOT/p)==h
        if p.startswith(('.work/','results/')):evidence[p]=h
        else:
            data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==h;bindings[p]=dict(revision=plan['source_revision'],sha256=h)
    for r in records:
        for stream in ['stdout','stderr']:
            p=raw/(r['label']+'.'+stream);assert sha(p)==r[stream+'_sha256'];evidence[str(p.relative_to(ROOT))]=sha(p)
    for p in [raw/'plan.json',raw/'records.json',raw/'artifacts.json',outer/'status.json',outer/'plan.json',outer/'command.log']:
        evidence[str(p.relative_to(ROOT))]=sha(p)
    out=ROOT/'results'/run;out.mkdir(exist_ok=False)
    write(raw/'source-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'summary.json',dict(status='fixture-failed',source_revision=plan['source_revision'],raw=str(raw.relative_to(ROOT)),
        reason='The diagnostic TLS fixture used reserved offset zero; valid TLS initializers start at offset16.',
        python_controls=4,rust_passed=6,rust_failed=1,rust_ignored=1,commands=2,
        guest_commands=0,typed_artifacts=0,production_runtime_changes=0,performance_measurement=False,
        plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json')))
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,frozen_inputs=len(plan['frozen']),
        source_files=len(bindings),evidence_files=len(evidence),summary_sha256=sha(out/'summary.json'),
        terminal_sha256=sha(out/'terminal.json'),source_bindings=str((raw/'source-bindings.json').relative_to(ROOT)),
        source_bindings_sha256=sha(raw/'source-bindings.json'),evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),
        evidence_sha256=sha(raw/'closed-evidence.json'),auditor_sha256=sha(Path(__file__)),guest_commands=0))
    print('Closed failed TLS fixture; no saved artifact census or guest ran',flush=True)
