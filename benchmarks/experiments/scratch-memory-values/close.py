"""Verify and retain terminal native-Call qualification evidence (pass or fail)."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
    run=sys.argv[1];assert run.startswith('scratch-memory-values-') and Path(run).name==run
    raw=ROOT/'.work'/run;outer=ROOT/'.work/experiments'/run
    status=json.loads((outer/'status.json').read_text());assert status['status']=='finished' and status['owner']==str(ROOT)
    assert sha(outer/'command.log')==status['log_sha256']
    plan=json.loads((raw/'plan.json').read_text());assert plan['owner']==str(ROOT)
    revision=plan.get('source_revision') or sys.argv[2]
    bindings={}
    for path,digest in plan['frozen'].items():
        p=ROOT/path
        if path.startswith(('.work/','results/')):
            assert sha(p)==digest;bindings[path]=dict(kind='retained',sha256=digest)
        else:
            for candidate in dict.fromkeys([revision,*sys.argv[2:]]):
                result=subprocess.run(['git','show',candidate+':'+path],cwd=ROOT,capture_output=True)
                if result.returncode==0 and hashlib.sha256(result.stdout).hexdigest()==digest:
                    bindings[path]=dict(kind='git',revision=candidate,sha256=digest);break
            else:raise AssertionError('unbound source: '+path)
    records=json.loads((raw/'records.json').read_text())
    for record in records:
        for stream in ['stdout','stderr']:assert sha(raw/(record['label']+'.'+stream))==record[stream+'_sha256']
    dest=ROOT/'results'/run;dest.mkdir(exist_ok=True)
    assert not (dest/'closure.json').exists()
    if status['returncode']==0:
        summary=json.loads((dest/'summary.json').read_text());assert summary['status']=='passed'
        if '-qualification-' not in run:assert all(r['returncode']==0 for r in records)
        else:
            expected={'scalar-actual-demand-rejection','reject-getenv-signature','reject-strlen-signature',
                'cargo-reject-type','cargo-reject-borrow','cargo-forced-reuse-no-incremental',
                'cargo-auto-no-incremental-reject-type','cargo-auto-no-incremental-reject-borrow'}
            expected.update('invalid-strlen-'+engine+'-'+pointer for engine in ['interpreter','jit'] for pointer in ['0',str(2**64-1)])
            assert {r['label'] for r in records if r['returncode']!=0}==expected
            assert summary['commands']==len(records)
        assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'records.json')==summary['records_sha256']
        if 'census_sha256' in summary:
            assert sha(raw/'storage.json')==summary['census_sha256']
            assert sha(raw/'references.json')==summary['references_sha256']
            census=json.loads((raw/'storage.json').read_text())
            assert census['status']=='passed' and len(census['functions'])==478
            assert census['old_bodies_reconstructed']==71
            assert census['guest_commands']==census['executable_code_publications']==0
    else:
        assert not (dest/'summary.json').exists()
        write(dest/'summary.json',dict(status='failed',source_revision=revision,commands=len(records),
            command_returncodes=[r['returncode'] for r in records],raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),original_project_guest_commands=0,performance_measurement=False))
    (dest/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(raw/'source-bindings.json',bindings)
    write(dest/'closure.json',dict(status='closed',source_revision=revision,bound_source_revisions=sorted({b['revision'] for b in bindings.values() if b['kind']=='git'}),frozen_input_count=len(bindings),source_bindings=str((raw/'source-bindings.json').relative_to(ROOT)),source_bindings_sha256=sha(raw/'source-bindings.json'),
        logs_verified=True,terminal_sha256=sha(dest/'terminal.json'),summary_sha256=sha(dest/'summary.json')))
    print(run,status['returncode'],len(bindings),'frozen input bindings verified')
if __name__=='__main__':
    sys.path.insert(0,str(ROOT/'scripts'))
    from compare_saved_runtime import acquire_lock
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        main()
