"""Preserve a historical-source audit failure before cache enumeration/deletion."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from workflow_io import require_space,write_json as write
run='closed-recent-token-cache-retirement-01';revision='838e9f51';require_space(ROOT,8)
outer=ROOT/'.work/experiments'/run
terminal=json.loads((outer/'status.json').read_text());plan=json.loads((outer/'plan.json').read_text())
assert terminal['status']=='finished' and terminal['returncode']==1
assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT) and terminal['command']==plan['command']
assert terminal['plan_sha256']==sha(outer/'plan.json') and terminal['log_sha256']==sha(outer/'command.log')
log=(outer/'command.log').read_text();assert 'for p,h in evidence.items():bind(ROOT/p,h)' in log and 'AssertionError: '+str(ROOT/'scripts/interpreter.py') in log
assert not (ROOT/'.work'/run).exists()
p='benchmarks/experiments/recent-token-cache-retirement/retire_screen.py'
assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+p],cwd=ROOT)).hexdigest()==sha(ROOT/p)
out=ROOT/'results'/run;out.mkdir(exist_ok=False)
for name in ['status.json','plan.json','command.log']:shutil.copyfile(outer/name,out/('terminal.json' if name=='status.json' else name))
write(out/'summary.json',dict(status='audit-failed-before-removal',source_revision=revision,files_removed=0,
    reason='Historical launcher evidence was compared with the intentionally changed current checkout. Need recorded git-source verification for historical source; retained evidence must still match actual files.',performance_measurement=False))
write(out/'closure.json',dict(status='closed',all_hashes_verified=True,no_stage_directory=True,
    summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
    outer_plan_sha256=sha(out/'plan.json'),outer_log_sha256=sha(out/'command.log'),auditor_sha256=sha(Path(__file__)),files_removed=0))
print('Preserved historical-source audit failure; zero removals')
