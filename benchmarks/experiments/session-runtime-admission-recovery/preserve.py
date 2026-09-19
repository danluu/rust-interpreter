"""Bounded admission bookkeeping; no benchmark lock, build, guest or source scan."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from workflow_io import require_space,write_json as write
require_space(ROOT,8)
def read(p):
    assert p.stat().st_size<=64*1024
    return json.loads(p.read_text())
def bind_attempt(name,expected):
    folder=ROOT/'.work/experiments'/name;terminal=read(folder/'status.json');plan=read(folder/'plan.json')
    assert terminal['status']=='finished' and terminal['returncode']==1 and terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
    assert terminal['command']==plan['command'] and terminal['command'][2:]==expected
    assert sha(folder/'plan.json')==terminal['plan_sha256'] and sha(folder/'command.log')==terminal['log_sha256']
    assert (folder/'command.log').stat().st_size<=64*1024
    assert (folder/'command.log').read_text().endswith('TimeoutError: timed out after 45s waiting for benchmark lock '+str(ROOT/'.work/benchmark.lock')+'\n')
    return folder,terminal
name='session-runtime-composition-edit-rg-aot-01'
folder,terminal=bind_attempt(name,['benchmarks/experiments/session-runtime-composition-large-guards/benchmark.py','--case','rg-aot','--run-id',name])
assert not (ROOT/'.work'/name).exists() and not (ROOT/'results'/name).exists()
assert not any((ROOT/'.work/ts'/('composition-large-rg-aot-01-'+mode)).exists() for mode in ['candidate','session-fresh'])
revision='7f762c5e';path='benchmarks/experiments/session-runtime-composition-large-guards/benchmark.py'
data=subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT)
assert hashlib.sha256(data).hexdigest()==sha(ROOT/path)
out=ROOT/'results/session-runtime-composition-rg-aot-admission-01';out.mkdir(exist_ok=False)
for part in ['status.json','plan.json','command.log']:(out/('terminal.json' if part=='status.json' else part)).write_bytes((folder/part).read_bytes())
write(out/'summary.json',dict(status='not-admitted',reason='Shared benchmark lock timed out before stage creation; no compiler, session, source edit or timing started.',
    attempted_run=name,source_revision=revision,controller=path,controller_sha256=sha(ROOT/path),commands=0,original_project_guest_commands=0,
    no_stage_directory=True,no_session_endpoints=True,performance_measurement=False))
write(out/'closure.json',dict(status='closed',all_hashes_verified=True,no_stage_directory=True,no_session_endpoints=True,
    summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),outer_plan_sha256=sha(out/'plan.json'),outer_log_sha256=sha(out/'command.log'),
    auditor_sha256=sha(Path(__file__)),scope='Bounded terminal admission metadata only; no benchmark lock was claimed.'))
folder,_=bind_attempt('session-runtime-composition-large-protocol-02-close',['benchmarks/experiments/session-runtime-composition-large-guards/qualify.py','--close'])
out=ROOT/'results/session-runtime-composition-large-protocol-02/audit-admission-01';out.mkdir(exist_ok=False)
for part in ['status.json','plan.json','command.log']:(out/part).write_bytes((folder/part).read_bytes())
write(out/'assessment.json',dict(status='not-admitted',audit_lock_acquired=False,protocol_tests_repeated=False,performance_measurement=False,
    terminal_sha256=sha(out/'status.json'),plan_sha256=sha(out/'plan.json'),log_sha256=sha(out/'command.log')))
print('Preserved both lock-admission timeouts; no workload or audit mutation ran')
