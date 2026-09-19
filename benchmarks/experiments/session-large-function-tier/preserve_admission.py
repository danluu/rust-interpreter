"""Retain the failed resource admission; no compiler, test or guest started."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from workflow_io import require_space,write_json as write
run='session-large-function-tier-qualification-01';revision='30b70404'
require_space(ROOT,8);outer=ROOT/'.work/experiments'/run
for name in ['status.json','plan.json','command.log']:assert (outer/name).stat().st_size<=65536
terminal=json.loads((outer/'status.json').read_text());plan=json.loads((outer/'plan.json').read_text())
assert terminal['status']=='finished' and terminal['returncode']==1
assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT) and terminal['command']==plan['command']
assert terminal['plan_sha256']==sha(outer/'plan.json') and terminal['log_sha256']==sha(outer/'command.log')
log=(outer/'command.log').read_text();assert 'shutil.disk_usage(ROOT).free>=needed' in log and 'AssertionError' in log
assert not (ROOT/'.work'/run).exists()
p='benchmarks/experiments/session-large-function-tier/qualify.py'
assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+p],cwd=ROOT)).hexdigest()==sha(ROOT/p)
out=ROOT/'results'/run;out.mkdir(exist_ok=False)
for name in ['status.json','plan.json','command.log']:shutil.copyfile(outer/name,out/('terminal.json' if name=='status.json' else name))
write(out/'summary.json',dict(status='admission-failed',source_revision=revision,commands=0,original_project_guest_commands=0,
    reason='Fresh disk headroom below max(14GiB,8GiB+2*allocated shared target). Admission stopped before stage creation or any compiler/test/guest.',performance_measurement=False))
write(out/'closure.json',dict(status='closed',all_hashes_verified=True,no_stage_directory=True,
    summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
    outer_plan_sha256=sha(out/'plan.json'),outer_log_sha256=sha(out/'command.log'),auditor_sha256=sha(Path(__file__)),
    scope='Bounded terminal-only admission bookkeeping; no workload.'))
print('Preserved disk admission failure; zero workload commands')
