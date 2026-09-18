"""Preserve a completed passing case without making a live campaign look finished."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/runtime-composition-full'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
from full import audit_cases,validate_checkpoint,CASES

def main():
    count=int(sys.argv[1]);supervisor=sys.argv[2];revision=sys.argv[3]
    assert 1<=count<len(CASES) and supervisor.startswith('runtime-composition-full-') and Path(supervisor).name==supervisor
    raw=ROOT/'.work/runtime-composition-full-02';outer=ROOT/'.work/experiments'/supervisor
    terminal=json.loads((outer/'status.json').read_text());assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==terminal['cwd']==str(ROOT)
    assert sha(outer/'command.log')==terminal['log_sha256'] and sha(outer/'plan.json')==terminal['plan_sha256']
    checkpoint=json.loads((raw/f'checkpoint-{count}.json').read_text());rows=json.loads((raw/'records.json').read_text())
    completed=[json.loads((ROOT/'results'/('runtime-composition-edit-'+case+'-02')/'summary.json').read_text()) for case in CASES[:count]]
    assert len(rows)==count and validate_checkpoint(checkpoint,sha(raw/'plan.json'),sha(raw/'records.json'),completed)
    assert sha(raw/checkpoint['audit_path'])==checkpoint['audit_sha256']
    assert audit_cases(CASES[:count])==json.loads((raw/checkpoint['audit_path']).read_text())
    evidence={};bindings={}
    if 'audit_recovery' in checkpoint:
        assert checkpoint['audit_recovery']==supervisor
        recovery_path=ROOT/'results'/supervisor/'summary.json';recovery=json.loads(recovery_path.read_text())
        assert recovery['status']=='passed' and recovery['new_guest_commands']==recovery['repeated_commands']==0
        assert recovery['checkpoint_sha256']==sha(raw/f'checkpoint-{count}.json') and recovery['audit_sha256']==checkpoint['audit_sha256']
        recovery_plan_path=ROOT/recovery['raw']/'plan.json';assert sha(recovery_plan_path)==recovery['plan_sha256']
        recovery_plan=json.loads(recovery_plan_path.read_text());assert recovery_plan['owner']==str(ROOT)
        for path,h in recovery_plan['evidence'].items():assert sha(ROOT/path)==h;evidence[path]=h
        path=recovery_plan['script'];source=recovery_plan['source_revision'];digest=recovery_plan['script_sha256']
        assert sha(ROOT/path)==digest and hashlib.sha256(subprocess.check_output(['git','show',source+':'+path])).hexdigest()==digest
        bindings[path]=dict(revision=source,sha256=digest)
        evidence[str(recovery_path.relative_to(ROOT))]=sha(recovery_path)
        evidence[str(recovery_plan_path.relative_to(ROOT))]=sha(recovery_plan_path)
    frozen=json.loads((raw/'plan.json').read_text())['frozen']
    for p,h in frozen.items():
        assert sha(ROOT/p)==h
        if p.startswith(('.work/','results/')):evidence[p]=h
        else:
            assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+p])).hexdigest()==h
            bindings[p]=dict(revision=revision,sha256=h)
    dest=raw/f'closed-checkpoint-{count}';dest.mkdir(exist_ok=False)
    for name in ['plan.json','records.json',f'checkpoint-{count}.json',checkpoint['audit_path']]:
        (dest/name).write_bytes((raw/name).read_bytes());evidence[str((dest/name).relative_to(ROOT))]=sha(dest/name)
    for row in rows:
        assert row['returncode']==0
        for stream in ['stdout','stderr']:
            p=raw/(row['case']+'.'+stream);assert sha(p)==row[stream+'_sha256'];evidence[str(p.relative_to(ROOT))]=sha(p)
        p=ROOT/'results'/('runtime-composition-edit-'+row['case']+'-02')/'summary.json';assert sha(p)==row['summary_sha256'];evidence[str(p.relative_to(ROOT))]=sha(p)
    write(dest/'sources.json',bindings);write(dest/'evidence.json',evidence)
    out=ROOT/'results'/('runtime-composition-edit-'+CASES[count-1]+'-02')
    assert not (out/'closure.json').exists();(out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',performance_gate_passed=True,completed_cases=CASES[:count],next_case=CASES[count],
        snapshot=str(dest.relative_to(ROOT)),evidence_sha256=sha(dest/'evidence.json'),sources_sha256=sha(dest/'sources.json'),
        terminal_sha256=sha(out/'terminal.json'),summary_sha256=sha(out/'summary.json'),frozen_sources=len(bindings),verified_files=len(evidence),
        all_retained_artifacts_and_sources_verified=True,full_campaign_complete=False))
    print('Closed',CASES[:count],'checkpoint;',len(evidence),'retained files;',len(bindings),'Git sources')
if __name__=='__main__':
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);main()
