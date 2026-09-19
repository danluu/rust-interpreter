"""Preserve focused04's lock timeout; no build/test stage was admitted."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    run='shared-emission-templates-focused-04';outer=ROOT/'.work/experiments'/run
    terminal=read(outer/'status.json');plan=read(outer/'plan.json')
    assert terminal['status']=='finished' and terminal['returncode']==1
    assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
    assert terminal['plan_sha256']==sha(outer/'plan.json') and terminal['log_sha256']==sha(outer/'command.log')
    assert terminal['command']==plan['command']
    assert 'TimeoutError: timed out after 45s waiting for benchmark lock' in (outer/'command.log').read_text()
    assert not (ROOT/'.work'/run).exists()
    revision='f26ae422';paths=['benchmarks/experiments/shared-emission-templates/focus.py','scripts/compare_saved_runtime.py']
    bindings={}
    for p in paths:
        data=subprocess.check_output(['git','show',revision+':'+p],cwd=ROOT)
        assert hashlib.sha256(data).hexdigest()==sha(ROOT/p)
        bindings[p]=dict(revision=revision,sha256=sha(ROOT/p))
    out=ROOT/'results'/run;out.mkdir(exist_ok=False)
    for name in ['status.json','plan.json','command.log']:
        (out/('terminal.json' if name=='status.json' else name)).write_bytes((outer/name).read_bytes())
    write(out/'summary.json',dict(status='not-admitted',reason='Shared lock timed out before plan creation or any child build/test.',
        source_revision=revision,source_bindings=bindings,commands=0,original_project_guest_commands=0,performance_measurement=False))
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,no_stage_directory=True,
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
        outer_plan_sha256=sha(out/'plan.json'),outer_log_sha256=sha(out/'command.log'),auditor_sha256=sha(Path(__file__))))
    print('Preserved unadmitted focused04; zero builds/tests/guests',flush=True)
