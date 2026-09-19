"""Preserve the first census's fail-closed unit-variant rejection."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,12)
    run='adopted-hot-loop-census-01';raw=ROOT/'.work'/run;outer=ROOT/'.work/experiments'/run
    t=read(outer/'status.json');plan=read(raw/'plan.json');records=read(raw/'records.json')
    assert t['status']=='finished' and t['returncode']==1 and t['owner']==t['cwd']==str(ROOT)
    assert t['command']==['/opt/homebrew/bin/python3',str(ROOT/'benchmarks/experiments/adopted-hot-loop-census/run.py')]
    assert sha(outer/'plan.json')==t['plan_sha256'] and sha(outer/'command.log')==t['log_sha256']
    assert (outer/'command.log').read_text().rstrip().endswith('ValueError: unknown or malformed operation: ResetThreadLocals')
    assert len(records)==1 and records[0]['returncode']==0
    for stream in ['stdout','stderr']:assert sha(raw/('controls.'+stream))==records[0][stream+'_sha256']
    stderr=(raw/'controls.stderr').read_text();assert 'Ran 16 tests' in stderr and stderr.rstrip().endswith('OK')
    bindings={}
    for p,h in plan['frozen'].items():
        assert sha(ROOT/p)==h
        if p.startswith(('.work/','results/')):bindings[p]=dict(kind='retained',sha256=h)
        else:
            data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==h
            bindings[p]=dict(kind='git',revision=plan['source_revision'],sha256=h)
    assert not list(raw.glob('*-details.json'))
    out=ROOT/'results'/run;out.mkdir(exist_ok=False)
    write(raw/'failure-bindings.json',bindings)
    write(out/'summary.json',dict(status='failed',reason='unrecognized valid unit ResetThreadLocals rendering',
        source_revision=plan['source_revision'],raw=str(raw.relative_to(ROOT)),controls_passed=16,
        plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
        guest_commands=0,host_builds=0,completed_cases=0,performance_measurement=False))
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',failed_attempt_preserved=True,all_hashes_verified=True,
        frozen_inputs=len(bindings),bindings=str((raw/'failure-bindings.json').relative_to(ROOT)),
        bindings_sha256=sha(raw/'failure-bindings.json'),summary_sha256=sha(out/'summary.json'),
        terminal_sha256=sha(out/'terminal.json')))
    print('CLOSED failed unit-variant rejection;',len(bindings),'bindings verified')
