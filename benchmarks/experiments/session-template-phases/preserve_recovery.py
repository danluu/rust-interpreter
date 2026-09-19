"""Preserve the pre-build auditor failure on an intentionally invalid JSON fixture."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from workflow_io import require_space,write_json as write
run='session-template-phases-qualification-02';revision='c94bac0c'
require_space(ROOT,8);outer=ROOT/'.work/experiments'/run
for name in ['status.json','plan.json','command.log']:assert (outer/name).stat().st_size<=65536
terminal=json.loads((outer/'status.json').read_text());plan=json.loads((outer/'plan.json').read_text())
assert terminal['status']=='finished' and terminal['returncode']==1
assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT) and terminal['command']==plan['command']
assert terminal['plan_sha256']==sha(outer/'plan.json') and terminal['log_sha256']==sha(outer/'command.log')
log=(outer/'command.log').read_text();assert "for p,h in r['outputs'].items():bind(ROOT/p,h)" in log and 'JSONDecodeError' in log
assert not (ROOT/'.work'/run).exists()
p='benchmarks/experiments/session-template-phases/qualify_completed.py'
assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+p],cwd=ROOT)).hexdigest()==sha(ROOT/p)
old=ROOT/'.work/session-template-phases-qualification-01';rows=json.loads((old/'records.json').read_text());invalid=None
for row in rows:
    for path,digest in row['outputs'].items():
        if invalid is not None:break
        file=ROOT/path;assert sha(file)==digest
        if file.suffix=='.json':
            try:json.loads(file.read_text())
            except json.JSONDecodeError:
                invalid=dict(path=path,sha256=digest);assert file.is_relative_to(old)
assert invalid is not None
out=ROOT/'results'/run;out.mkdir(exist_ok=False)
for name in ['status.json','plan.json','command.log']:shutil.copyfile(outer/name,out/('terminal.json' if name=='status.json' else name))
write(out/'summary.json',dict(status='pre-build-audit-failed',source_revision=revision,commands=0,original_project_guest_commands=0,
    rejected_fixture=invalid,reason='Hash-matched negative-test output was accidentally JSON-decoded while binding opaque fixture bytes. Failed before stage creation/build/test/guest.',performance_measurement=False))
write(out/'closure.json',dict(status='closed',all_hashes_verified=True,no_stage_directory=True,
    summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
    outer_plan_sha256=sha(out/'plan.json'),outer_log_sha256=sha(out/'command.log'),auditor_sha256=sha(Path(__file__)),
    scope='Bounded terminal/fixture bookkeeping; no workload.'))
print('Preserved pre-build audit failure; zero new workload commands')
