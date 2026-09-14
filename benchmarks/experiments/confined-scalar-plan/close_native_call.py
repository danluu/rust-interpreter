"""Verify and retain terminal native-Call qualification evidence (pass or fail)."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
    run=sys.argv[1];assert run.startswith('confined-scalar-native-call-') and Path(run).name==run
    raw=ROOT/'.work'/run;outer=ROOT/'.work/experiments'/run
    status=json.loads((outer/'status.json').read_text());assert status['status']=='finished' and status['owner']==str(ROOT)
    assert sha(outer/'command.log')==status['log_sha256']
    plan=json.loads((raw/'plan.json').read_text());assert plan['owner']==str(ROOT)
    revision=plan.get('source_revision') or sys.argv[2]
    bindings={}
    for path,digest in plan['frozen'].items():
        p=ROOT/path
        if path.startswith('.work/'):
            assert sha(p)==digest;bindings[path]=dict(kind='retained',sha256=digest)
        else:
            data=subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==digest,path
            bindings[path]=dict(kind='git',revision=revision,sha256=digest)
    records=json.loads((raw/'records.json').read_text())
    for record in records:
        for stream in ['stdout','stderr']:assert sha(raw/(record['label']+'.'+stream))==record[stream+'_sha256']
    dest=ROOT/'results'/run;dest.mkdir(exist_ok=True)
    assert not (dest/'closure.json').exists()
    if status['returncode']==0:
        summary=json.loads((dest/'summary.json').read_text());assert summary['status']=='passed'
        assert all(r['returncode']==0 for r in records)
        assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'records.json')==summary['records_sha256']
    else:
        assert not (dest/'summary.json').exists()
        write(dest/'summary.json',dict(status='failed',source_revision=revision,commands=len(records),
            command_returncodes=[r['returncode'] for r in records],raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),original_project_guest_commands=0,performance_measurement=False))
    (dest/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(dest/'closure.json',dict(status='closed',source_revision=revision,frozen_inputs=bindings,
        logs_verified=True,terminal_sha256=sha(dest/'terminal.json'),summary_sha256=sha(dest/'summary.json')))
    print(run,status['returncode'],len(bindings),'frozen input bindings verified')
if __name__=='__main__':main()
