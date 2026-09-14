"""Close the completed five-case campaign and bind both full-parser guards."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scratch-memory-values-full'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
from full import audit_cases,CASES

with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45)
    name='scratch-memory-values-full-01';revision='c88d1ead'
    raw=ROOT/'.work'/name;out=ROOT/'results'/name
    outer=ROOT/'.work/experiments/scratch-memory-values-full-nushell-01'
    terminal=json.loads((outer/'status.json').read_text());summary=json.loads((out/'summary.json').read_text())
    assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==terminal['cwd']==str(ROOT)
    assert sha(outer/'command.log')==terminal['log_sha256'] and sha(outer/'plan.json')==terminal['plan_sha256']
    assert summary['status']=='passed' and summary['all_five_gates_passed'] and summary['commands']==726
    assert summary['completed_cases']==CASES and summary['unstarted_cases']==[] and summary['final_source_and_input_audit_passed']
    for file,key in [('plan.json','plan_sha256'),('records.json','records_sha256'),(summary['final_audit_path'],'final_audit_sha256')]:
        assert sha(raw/file)==summary[key]
    audit=json.loads((raw/summary['final_audit_path']).read_text());assert audit_cases(CASES)==audit
    records=json.loads((raw/'records.json').read_text());assert [r['case'] for r in records]==CASES
    evidence={};bindings={}
    for p,h in json.loads((raw/'plan.json').read_text())['frozen'].items():
        assert sha(ROOT/p)==h
        if p.startswith(('.work/','results/')):evidence[p]=h
        else:
            assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+p],cwd=ROOT)).hexdigest()==h
            bindings[p]=dict(revision=revision,sha256=h)
    for row in records:
        assert row['returncode']==0
        for stream in ['stdout','stderr']:
            p=raw/(row['case']+'.'+stream);assert sha(p)==row[stream+'_sha256'];evidence[str(p.relative_to(ROOT))]=sha(p)
        p=ROOT/'results'/('scratch-memory-values-edit-'+row['case']+'-01')/'summary.json'
        assert sha(p)==row['summary_sha256'];evidence[str(p.relative_to(ROOT))]=sha(p)
    parser=[]
    for profile in ['incremental','repository']:
        p=ROOT/'results'/('scratch-memory-values-parser-edits-'+profile+'-01');s=json.loads((p/'summary.json').read_text());c=json.loads((p/'closure.json').read_text())
        assert s['status']=='passed' and s['commands']==88 and s['original_tests']==114 and s['measurement']['gate_passed']
        assert c['status']=='closed' and c['all_hashes_verified'] and sha(p/'summary.json')==c['summary_sha256'] and sha(p/'terminal.json')==c['terminal_sha256']
        for field in ['bindings','evidence']:assert sha(ROOT/c[field])==c[field+'_sha256']
        for path,digest in json.loads((ROOT/c['evidence']).read_text()).items():assert sha(ROOT/path)==digest
        for file in ['summary.json','closure.json','terminal.json']:evidence[str((p/file).relative_to(ROOT))]=sha(p/file)
        parser.append(dict(profile=profile,commands=88,tests=114,gate_passed=True,summary_sha256=sha(p/'summary.json')))
    dest=raw/'closed-final';dest.mkdir(exist_ok=False)
    for file in ['plan.json','records.json',summary['final_audit_path']]:
        (dest/file).write_bytes((raw/file).read_bytes());evidence[str((dest/file).relative_to(ROOT))]=sha(dest/file)
    write(dest/'sources.json',bindings);write(dest/'evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    closure=dict(status='closed',source_revision=revision,performance_gate_passed=True,completed_cases=CASES,commands=726,
        frozen_sources=len(bindings),unique_frozen_inputs=audit['unique_frozen_inputs'],all_retained_artifacts_and_sources_verified=True,
        snapshot=str(dest.relative_to(ROOT)),evidence_sha256=sha(dest/'evidence.json'),sources_sha256=sha(dest/'sources.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),parser_guards=parser,
        full_campaign_complete=True,runtime_adopted=False)
    assert not (out/'closure.json').exists();write(out/'closure.json',closure)
    nu=ROOT/'results/scratch-memory-values-edit-nushell-01';assert not (nu/'closure.json').exists()
    (nu/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(nu/'closure.json',dict(status='closed',performance_gate_passed=True,commands=132,
        full_closure=str((out/'closure.json').relative_to(ROOT)),full_closure_sha256=sha(out/'closure.json'),
        summary_sha256=sha(nu/'summary.json'),terminal_sha256=sha(nu/'terminal.json'),all_retained_artifacts_and_sources_verified=True))
    print('Closed 726 project-history commands and both 88-command parser guards;',audit['unique_frozen_inputs'],'unique frozen inputs')
