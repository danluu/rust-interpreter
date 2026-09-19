"""Close the rejected two-worker assumption before correcting the offline audit."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    run='jit-preparation-costs-01';raw=ROOT/'.work'/run;outer=ROOT/'.work/experiments'/run
    plan=read(raw/'plan.json');terminal=read(outer/'status.json');controls=read(raw/'controls.json')
    assert terminal['status']=='finished' and terminal['returncode']==1 and terminal['owner']==plan['owner']==str(ROOT)
    assert sha(outer/'command.log')==terminal['log_sha256'] and sha(outer/'plan.json')==terminal['plan_sha256']
    assert 'requested_workers' in (outer/'command.log').read_text()
    assert controls['returncode']==0 and 'Ran 6 tests' in (raw/'controls.stderr').read_text()
    bindings={};evidence={}
    for p,h in plan['frozen'].items():
        assert sha(ROOT/p)==h
        if p.startswith(('.work/','results/')):evidence[p]=h
        else:
            data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==h;bindings[p]=dict(revision=plan['source_revision'],sha256=h)
    for stream in ['stdout','stderr']:assert sha(raw/('controls.'+stream))==controls[stream+'_sha256']
    for p in [raw/'plan.json',raw/'controls.json',raw/'controls.stdout',raw/'controls.stderr',outer/'status.json',outer/'plan.json',outer/'command.log']:
        evidence[str(p.relative_to(ROOT))]=sha(p)
    out=ROOT/'results'/run;out.mkdir(exist_ok=False)
    write(raw/'source-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'summary.json',dict(status='observer-failed',controls=6,source_revision=plan['source_revision'],raw=str(raw.relative_to(ROOT)),
        reason='The one-test private history explicitly requested one worker; the observer incorrectly required two for all cases.',
        plan_sha256=sha(raw/'plan.json'),new_guest_commands=0,compiler_build_commands=0,performance_measurement=False))
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,frozen_inputs=len(plan['frozen']),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
        source_bindings=str((raw/'source-bindings.json').relative_to(ROOT)),source_bindings_sha256=sha(raw/'source-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),
        new_guest_commands=0,auditor_sha256=sha(Path(__file__))))
    print('Closed audit01 observer failure; no guest/build was run',flush=True)
