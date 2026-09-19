"""Small terminal-only bookkeeping: no build, workload, source scan or lock claim."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from workflow_io import require_space,write_json as write
require_space(ROOT,8)
run='cross-program-template-model-03';revision='153e3057'
outer=ROOT/'.work/experiments'/run
def read(p):
    assert p.stat().st_size<=64*1024
    return json.loads(p.read_text())
terminal=read(outer/'status.json');plan=read(outer/'plan.json')
assert terminal['status']=='finished' and terminal['returncode']==1
assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
assert terminal['command']==plan['command']
assert terminal['plan_sha256']==sha(outer/'plan.json') and terminal['log_sha256']==sha(outer/'command.log')
assert (outer/'command.log').stat().st_size<=64*1024
assert (outer/'command.log').read_text().endswith('TimeoutError: timed out after 45s waiting for benchmark lock '+str(ROOT/'.work/benchmark.lock')+'\n')
assert not (ROOT/'.work'/run).exists()
bindings={}
for name in ['benchmarks/experiments/cross-program-template-model/focus.py','scripts/compare_saved_runtime.py']:
    data=subprocess.check_output(['git','show',revision+':'+name],cwd=ROOT)
    assert len(data)<=1024*1024 and hashlib.sha256(data).hexdigest()==sha(ROOT/name)
    bindings[name]=dict(revision=revision,sha256=sha(ROOT/name))
out=ROOT/'results'/run;out.mkdir(exist_ok=False)
for name in ['status.json','plan.json','command.log']:
    shutil.copyfile(outer/name,out/('terminal.json' if name=='status.json' else name))
write(out/'summary.json',dict(status='not-admitted',reason='Shared lock timeout before plan creation; no child build or test started.',
    source_revision=revision,source_bindings=bindings,commands=0,original_project_guest_commands=0,performance_measurement=False))
write(out/'closure.json',dict(status='closed',all_hashes_verified=True,no_stage_directory=True,
    summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
    outer_plan_sha256=sha(out/'plan.json'),outer_log_sha256=sha(out/'command.log'),auditor_sha256=sha(Path(__file__)),
    scope='Bounded terminal-only metadata bookkeeping; no benchmark lock or workload started.'))
print('Preserved model03 lock timeout; zero build/test/guest commands')
