"""Preserve the bounded API01 missing-controller startup failure; no workload."""
import json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from workflow_io import require_space,write_json as write
require_space(ROOT,8)
run='cross-program-template-session-api-01';revision='4d6ffb93'
outer=ROOT/'.work/experiments'/run
for name in ['status.json','plan.json','command.log']:assert (outer/name).stat().st_size<=65536
terminal=json.loads((outer/'status.json').read_text());plan=json.loads((outer/'plan.json').read_text())
assert terminal['status']=='finished' and terminal['returncode']==2
assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
assert terminal['command']==plan['command']
assert terminal['plan_sha256']==sha(outer/'plan.json') and terminal['log_sha256']==sha(outer/'command.log')
assert "can't open file" in (outer/'command.log').read_text() and '[Errno 2] No such file or directory' in (outer/'command.log').read_text()
assert not (ROOT/'.work'/run).exists()
assert subprocess.run(['git','cat-file','-e',revision+':benchmarks/experiments/cross-program-template-session/qualify.py'],cwd=ROOT,capture_output=True).returncode!=0
out=ROOT/'results'/run;out.mkdir(exist_ok=False)
for name in ['status.json','plan.json','command.log']:shutil.copyfile(outer/name,out/('terminal.json' if name=='status.json' else name))
write(out/'summary.json',dict(status='startup-failed',source_revision=revision,commands=0,original_project_guest_commands=0,
    reason='Controller generation failed; supervisor attempted a missing Python file. No controller/build/test ran.',performance_measurement=False))
write(out/'closure.json',dict(status='closed',all_hashes_verified=True,no_stage_directory=True,
    summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
    outer_plan_sha256=sha(out/'plan.json'),outer_log_sha256=sha(out/'command.log'),auditor_sha256=sha(Path(__file__)),
    scope='Bounded terminal-only startup bookkeeping; no benchmark lock or workload.'))
print('Preserved API01 missing-controller failure; no builds/tests/guests')
