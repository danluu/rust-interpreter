"""Receipt-only closure: no lock entry, model control, case or guest ran."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from workflow_io import write_json as write
RUN='linear-budget-reservation-01'
REV='459468b5'
outer=ROOT/'.work/experiments'/RUN
t=json.loads((outer/'status.json').read_text())
assert t['status']=='finished' and t['returncode']==1 and t['owner']==t['cwd']==str(ROOT)
assert t['supervisor_pid']==17317 and t['child_pid']==17320
assert t['command']==['/opt/homebrew/bin/python3',str(ROOT/'benchmarks/experiments/linear-budget-reservation/analyze.py'),'--run-id',RUN]
assert sha(outer/'plan.json')==t['plan_sha256'] and sha(outer/'command.log')==t['log_sha256']
assert not (ROOT/'.work'/RUN).exists()
log=(outer/'command.log').read_text()
assert log.rstrip().endswith('TimeoutError: timed out after 45s waiting for benchmark lock '+str(ROOT/'.work/benchmark.lock'))
assert 'acquire_lock(lock,45);require_space(ROOT,12)' in log
bindings={}
for name in ['PLAN.md','analyze.py','model.py','scope.py','test_model.py']:
    p=ROOT/'benchmarks/experiments/linear-budget-reservation'/name
    historical=subprocess.check_output(['git','show',REV+':'+str(p.relative_to(ROOT))],cwd=ROOT)
    assert historical==p.read_bytes()
    bindings[str(p.relative_to(ROOT))]=hashlib.sha256(historical).hexdigest()
out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
(out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
(out/'command.log').write_bytes((outer/'command.log').read_bytes())
write(out/'summary.json',dict(status='admission_blocked',source_revision=subprocess.check_output(['git','rev-parse',REV],cwd=ROOT,text=True).strip(),
    source_bindings=bindings,raw_directory_absent=True,controls=0,cases=0,guest_commands=0,host_builds=0,performance_measurement=False))
write(out/'closure.json',dict(status='closed',admission_failure_only=True,all_hashes_verified=True,
    summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),log_sha256=sha(out/'command.log'),
    controls=0,cases=0,guest_commands=0,performance_measurement=False))
print('CLOSED admission only',len(bindings),'source files; zero controls/cases/guests')
