"""Close expected failures without treating them as accepted qualification."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
RUN='template-callee-initialization-reproduction-01'
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
    plan=read(raw/'plan.json');records=read(raw/'records.json');summary=read(out/'summary.json');terminal=read(outer/'status.json')
    assert terminal['status']=='finished' and terminal['returncode']==0
    assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
    assert terminal['command'][1:]==plan['controller_command'][1:]
    assert Path(terminal['command'][0]).resolve()==Path(plan['controller_command'][0]).resolve()
    assert terminal['plan_sha256']==sha(outer/'plan.json') and terminal['log_sha256']==sha(outer/'command.log')
    assert summary['status']=='reproduced' and summary['expected_failures']==2
    assert summary['plan_sha256']==sha(raw/'plan.json') and summary['records_sha256']==sha(raw/'records.json')
    assert len(records)==plan['expected_commands']==2 and [v['returncode'] for v in records]==[101,101]
    evidence={};bindings={}
    for name,h in plan['frozen'].items():
        assert sha(ROOT/name)==h
        if name.startswith(('.work/','results/')):evidence[name]=h
        else:
            data=subprocess.check_output(['git','show',plan['source_revision']+':'+name],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==h;bindings[name]=dict(revision=plan['source_revision'],sha256=h)
    for row in records:
        for stream in ['stdout','stderr']:
            p=raw/(row['label']+'.'+stream);assert sha(p)==row[stream+'_sha256'];evidence[str(p.relative_to(ROOT))]=sha(p)
    for p in [raw/'plan.json',raw/'records.json',outer/'plan.json',outer/'status.json',outer/'command.log']:evidence[str(p.relative_to(ROOT))]=sha(p)
    assert not (out/'closure.json').exists()
    write(raw/'source-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',source_revision=plan['source_revision'],all_hashes_verified=True,
        expected_failures_reproduced=2,accepted_correctness=False,default_runtime_affected=False,
        bindings=str((raw/'source-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'source-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json')))
    print('Closed both expected failures; uncorrected cache is not qualified')
