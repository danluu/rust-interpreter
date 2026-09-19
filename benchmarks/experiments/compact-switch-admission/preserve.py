"""Preserve the empty protocol admission; no lock claim or workload execution."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from workflow_io import require_space,write_json as write
require_space(ROOT,8)
RUN='compact-native-switch-screen-protocol-01'
outer=ROOT/'.work/experiments'/RUN
def read(p):
    assert p.stat().st_size<=64*1024
    return json.loads(p.read_text())
t=read(outer/'status.json');p=read(outer/'plan.json')
assert t['status']=='finished' and t['returncode']==1 and t['owner']==t['cwd']==p['owner']==str(ROOT)
assert t['command']==p['command'] and t['command'][1:]==['-B','benchmarks/experiments/compact-native-switch-screen/qualify.py']
assert sha(outer/'plan.json')==t['plan_sha256'] and sha(outer/'command.log')==t['log_sha256']
assert (outer/'command.log').stat().st_size<64*1024
assert (outer/'command.log').read_text().endswith('TimeoutError: timed out after 45s waiting for benchmark lock '+str(ROOT/'.work/benchmark.lock')+'\n')
assert not (ROOT/'.work'/RUN).exists() and not (ROOT/'results'/RUN).exists()
revision='5ba6a5b1';bindings={}
for path in ['benchmarks/experiments/compact-native-switch-screen/qualify.py','scripts/compare_saved_runtime.py']:
    blob=subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT)
    assert hashlib.sha256(blob).hexdigest()==sha(ROOT/path)
    bindings[path]=dict(revision=revision,sha256=sha(ROOT/path))
out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
for name in ['status.json','plan.json','command.log']:(out/('terminal.json' if name=='status.json' else name)).write_bytes((outer/name).read_bytes())
write(out/'summary.json',dict(status='not-admitted',reason='Shared benchmark lock timeout before protocol stage creation.',
    commands=0,original_project_guest_commands=0,source_bindings=bindings,no_stage_directory=True,
    source_revision=revision,performance_measurement=False))
write(out/'closure.json',dict(status='closed',all_hashes_verified=True,no_stage_directory=True,
    summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
    outer_plan_sha256=sha(out/'plan.json'),outer_log_sha256=sha(out/'command.log'),
    auditor_sha256=sha(Path(__file__)),scope='Bounded admission metadata; no benchmark lock claim or workload.'))
print('Preserved empty protocol admission; zero tests, guests, builds or timings')
