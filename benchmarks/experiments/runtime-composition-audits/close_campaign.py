"""Close the completed five-case campaign and bind both full-parser guards."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/runtime-composition-full'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
from full import audit_cases,CASES,next_case
from parser_decision import parser_decision

with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45)
    name='runtime-composition-full-02';supervisor,revision=sys.argv[1:3]
    assert supervisor.startswith('runtime-composition-full-') and Path(supervisor).name==supervisor
    raw=ROOT/'.work'/name;out=ROOT/'results'/name
    outer=ROOT/'.work/experiments'/supervisor
    terminal=json.loads((outer/'status.json').read_text());summary=json.loads((out/'summary.json').read_text())
    assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==terminal['cwd']==str(ROOT)
    assert sha(outer/'command.log')==terminal['log_sha256'] and sha(outer/'plan.json')==terminal['plan_sha256']
    assert summary['status'] in ['passed','rejected']
    passed=summary['all_five_gates_passed'];completed=summary['completed_cases']
    assert completed==CASES[:len(completed)] and completed
    assert summary['commands']==sum(154 if c in CASES[:3] else 132 for c in completed)
    assert passed==(len(completed)==5 and summary['status']=='passed')
    assert summary['unstarted_cases']==CASES[len(completed):] and summary['final_source_and_input_audit_passed']
    case_proofs=[json.loads((ROOT/'results'/('runtime-composition-edit-'+c+'-02')/'summary.json').read_text()) for c in completed]
    assert next_case(case_proofs) is None
    assert passed==all(c['gate_passed'] for c in case_proofs)
    for file,key in [('plan.json','plan_sha256'),('records.json','records_sha256'),(summary['final_audit_path'],'final_audit_sha256')]:
        assert sha(raw/file)==summary[key]
    audit=json.loads((raw/summary['final_audit_path']).read_text());assert audit_cases(completed)==audit
    records=json.loads((raw/'records.json').read_text());assert [r['case'] for r in records]==completed
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
        p=ROOT/'results'/('runtime-composition-edit-'+row['case']+'-02')/'summary.json'
        assert sha(p)==row['summary_sha256'];evidence[str(p.relative_to(ROOT))]=sha(p)
    parser=[]
    for profile in (['incremental','repository'] if passed else []):
        p=ROOT/'results'/('runtime-composition-parser-edits-'+profile+'-01');s=json.loads((p/'summary.json').read_text());c=json.loads((p/'closure.json').read_text())
        assert s['status']=='passed' and s['commands']==88 and s['original_tests']==114
        assert c['status']=='closed' and c['all_hashes_verified'] and sha(p/'summary.json')==c['summary_sha256'] and sha(p/'terminal.json')==c['terminal_sha256']
        assert c['performance_gate_passed']==s['measurement']['gate_passed']
        for field in ['bindings','evidence']:assert sha(ROOT/c[field])==c[field+'_sha256']
        for path,digest in json.loads((ROOT/c['evidence']).read_text()).items():assert sha(ROOT/path)==digest
        for file in ['summary.json','closure.json','terminal.json']:evidence[str((p/file).relative_to(ROOT))]=sha(p/file)
        parser.append(dict(profile=profile,commands=88,tests=114,gate_passed=s['measurement']['gate_passed'],summary_sha256=sha(p/'summary.json')))
        if not s['measurement']['gate_passed']:break
    parser_result=parser_decision(parser) if passed else dict(passed=False,unstarted=['incremental','repository'])
    for profile in parser_result['unstarted']:
        assert not (ROOT/'.work'/('runtime-composition-parser-edits-'+profile+'-01')).exists()
        assert not (ROOT/'results'/('runtime-composition-parser-edits-'+profile+'-01')).exists()
    dest=raw/'closed-final';dest.mkdir(exist_ok=False)
    for file in ['plan.json','records.json',summary['final_audit_path']]:
        (dest/file).write_bytes((raw/file).read_bytes());evidence[str((dest/file).relative_to(ROOT))]=sha(dest/file)
    write(dest/'sources.json',bindings);write(dest/'evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    closure=dict(status='closed',source_revision=revision,performance_gate_passed=passed,completed_cases=completed,unstarted_cases=summary['unstarted_cases'],commands=summary['commands'],
        frozen_sources=len(bindings),unique_frozen_inputs=audit['unique_frozen_inputs'],all_retained_artifacts_and_sources_verified=True,
        snapshot=str(dest.relative_to(ROOT)),evidence_sha256=sha(dest/'evidence.json'),sources_sha256=sha(dest/'sources.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),parser_guards=parser,
        full_campaign_complete=passed,campaign_terminal=True,runtime_adopted=False,
        parser_gates_passed=parser_result['passed'],unstarted_parser_profiles=parser_result['unstarted'],
        candidate_qualified=passed and parser_result['passed'])
    assert not (out/'closure.json').exists();write(out/'closure.json',closure)
    nu=ROOT/'results'/('runtime-composition-edit-'+completed[-1]+'-02');assert not (nu/'closure.json').exists()
    (nu/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(nu/'closure.json',dict(status='closed',performance_gate_passed=passed,commands=154 if completed[-1] in CASES[:3] else 132,
        full_closure=str((out/'closure.json').relative_to(ROOT)),full_closure_sha256=sha(out/'closure.json'),
        summary_sha256=sha(nu/'summary.json'),terminal_sha256=sha(nu/'terminal.json'),all_retained_artifacts_and_sources_verified=True))
    print('Closed',summary['commands'],'project-history commands; gates',passed,'parser guards',len(parser),';',audit['unique_frozen_inputs'],'unique frozen inputs')
