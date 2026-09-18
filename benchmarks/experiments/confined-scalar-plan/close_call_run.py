import hashlib,json,subprocess
from pathlib import Path
R=Path('/Users/danluu/dev/rust-interp')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
for run in ['confined-scalar-call-focused-01','confined-scalar-call-workspace-01']:
    work=R/'.work'/run;dest=R/'results'/run
    if run.endswith('workspace-01'):
        old=R/'results/path_byte_oracle_checks_both_sides_of_cfg_joins'
        assert sorted(p.name for p in old.iterdir())==['summary.json'] and not dest.exists()
        assert json.loads((old/'summary.json').read_text())['raw']==str(work.relative_to(R))
        old.rename(dest)
    summary=json.loads((dest/'summary.json').read_text())
    assert sha(work/'plan.json')==summary['plan_sha256']
    assert sha(work/'records.json')==summary['records_sha256']
    plan=json.loads((work/'plan.json').read_text());bindings={}
    for path,h in plan['frozen'].items():
        assert sha(R/path)==h,path
        bindings[path]={'kind':'git' if not path.startswith('.work/') else 'retained','sha256':h}
        if not path.startswith('.work/'):
            b=subprocess.check_output(['git','show',plan['source_revision']+':'+path],cwd=R)
            assert hashlib.sha256(b).hexdigest()==h,path
            bindings[path]['revision']=plan['source_revision']
    artifacts={}
    for record in json.loads((work/'records.json').read_text()):
        assert record['returncode']==0
        for stream in ['stdout','stderr']:
            path=work/(record['label']+'.'+stream);h=sha(path)
            assert h==record[stream+'_sha256'];artifacts[str(path.relative_to(R))]=h
    terminal=R/'.work/experiments'/run/'status.json';status=json.loads(terminal.read_text())
    assert status['status']=='finished' and status['returncode']==0 and status['owner']==str(R)
    assert sha(terminal.with_name('command.log'))==status['log_sha256']
    if (dest/'terminal.json').exists():assert (dest/'terminal.json').read_bytes()==terminal.read_bytes()
    else:(dest/'terminal.json').write_bytes(terminal.read_bytes())
    write(dest/'closure.json',dict(status='passed',source_revision=plan['source_revision'],summary_sha256=sha(dest/'summary.json'),
        terminal_sha256=sha(dest/'terminal.json'),frozen_inputs=bindings,artifacts=artifacts,
        result_path_correction='workspace runner shadowed run name with final required test name' if run.endswith('workspace-01') else None))
    print(run,len(bindings),'frozen inputs verified;',len(artifacts),'logs verified')
p=R/'benchmarks/experiments/confined-scalar-plan/workspace_run.py'
s=p.read_text().replace('for name in [','for required_test in [').replace("assert name+' ... ok' in out,name","assert required_test+' ... ok' in out,required_test")
assert s!=p.read_text();p.write_text(s)
