#!/usr/bin/env python3
"""Resume the single Nushell case refused before its original disk admission."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scalar-copy-operands'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from large_compare import fingerprint
from full import CASES,next_case

OLD='scalar-copy-operands-full-01'
NU='scalar-copy-operands-edit-nushell-01'
ERROR='ff3e0d19985587b2b459928071bda53d12214c6e163293e63ab0cbdc2169bc06'

def validate_prefix(records,summaries,status,case_exists,result_exists,error_digest):
    assert status['status']=='finished' and status['returncode']==1
    assert len(records)==5 and [r['case'] for r in records]==CASES
    assert all(r['returncode']==0 and 'summary_sha256' in r for r in records[:4])
    assert records[4]['returncode']==1 and 'summary_sha256' not in records[4]
    assert error_digest==records[4]['stderr_sha256']==ERROR
    assert len(summaries)==4 and next_case(summaries)=='nushell'
    assert sum(s['commands'] for s in summaries)==594
    assert not case_exists and not result_exists, 'Nushell already started; cannot retry'
    return True

def verify_manifest(manifest):
    for name,digest in manifest.items():
        actual=fingerprint(ROOT/name) if isinstance(digest,dict) else sha(ROOT/name)
        assert actual==digest, 'frozen input changed: '+name

def case_path(case):
    return ROOT/'results'/('scalar-copy-operands-edit-'+case+'-01')/'summary.json'

def audit_cases(cases):
    merged={};audit=[]
    for case in cases:
        summary_path=case_path(case);result=json.loads(summary_path.read_text())
        assert result['status']=='passed' and result['case']==case and result['source_restored']
        assert result['commands']==(154 if case in CASES[:3] else 132)
        assert result['test_source_unchanged'] and result['candidate_control_bytecode_matches']
        raw=ROOT/result['raw'];plan=json.loads((raw/'plan.json').read_text())
        evidence=result.get('evidence') or {n:result[n+'_sha256'] for n in ['plan','records','transitions','space']}
        for name,digest in evidence.items():assert sha(raw/(name+'.json'))==digest
        assert plan['owner']==str(ROOT)
        for path,digest in plan['frozen'].items():
            canonical=digest if isinstance(digest,dict) else dict(kind='file',sha256=digest)
            assert path not in merged or merged[path]==canonical, 'inconsistent case manifests'
            merged[path]=canonical
        source=ROOT/'.work/sources'/('fre' if case in ['token','folded'] else case)
        marker=json.loads((source/'.rust-interp-owned.json').read_text())
        assert marker['owner']==str(ROOT) and marker['revision']==plan['revision']
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==plan['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        if case in CASES[:3]:
            changed=source/plan['case']['file'];expected=plan['original_source_sha256']
        else:
            if case=='rg-aot':
                adapter=json.loads((ROOT/'.work/private/workflow-rg-aot.json').read_text())
                assert adapter['owner']==str(ROOT) and adapter['revision']==plan['revision']
                file=adapter['case']['file']
            else:
                from workflow_cases import WORKFLOW_VARIANTS
                file=WORKFLOW_VARIANTS['nushell','type-relations']['file']
            changed=source/file;expected=plan['source_sha256']
        assert sha(changed)==expected
        audit.append(dict(case=case,summary_sha256=sha(summary_path),receipt_hashes_verified=True,
            source_restored=True,pinned_revision_verified=True,tracked_source_clean=True))
    verify_manifest(merged)
    return dict(cases=audit,unique_frozen_inputs=len(merged),all_frozen_inputs_verified=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    args=parser.parse_args();assert re.fullmatch(r'scalar-copy-operands-admission-resume-\d{2}',args.run_id)
    old=ROOT/'.work'/OLD
    status_path=ROOT/'.work/experiments'/OLD/'status.json'
    status=json.loads(status_path.read_text());original=json.loads((old/'plan.json').read_text())
    records=json.loads((old/'records.json').read_text())
    summaries=[json.loads(case_path(case).read_text()) for case in CASES[:4]]
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        assert status['owner']==original['owner']==str(ROOT)
        validate_prefix(records,summaries,status,(ROOT/'.work'/NU).exists(),case_path('nushell').exists(),sha(old/'nushell.stderr'))
        for row in records:
            for stream in ['stdout','stderr']:assert sha(old/(row['case']+'.'+stream))==row[stream+'_sha256']
        for row in records[:4]:assert sha(case_path(row['case']))==row['summary_sha256']
        verify_manifest(original['frozen'])
        harness_path=ROOT/'results/scalar-copy-admission-tests-01/summary.json'
        harness=json.loads(harness_path.read_text());assert harness['status']=='passed' and harness['tests']==5
        inputs=ROOT/harness['raw']/'inputs.json';assert sha(inputs)==harness['inputs_sha256']
        verify_manifest(json.loads(inputs.read_text()))
        before=audit_cases(CASES[:4])
        command=records[-1]['command']
        assert command[1:]==[str(ROOT/'benchmarks/experiments/scalar-copy-operands/large_compare.py'),'--case','nushell','--run-id',NU]
        paths=[status_path,old/'plan.json',old/'records.json',old/'nushell.stderr',harness_path,inputs,
            *[p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),original_controller=OLD,frozen=frozen,
            completed_prefix_commands=594,new_commands=132,only_unstarted_case='nushell',
            command=command,pre_resume_audit=before,original_inputs_unchanged=True))
    child,out,err=capture(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
        receipt_path=work/'active.json',receipt=dict(case='nushell'))
    (work/'nushell.stdout').write_text(out);(work/'nushell.stderr').write_text(err)
    new=dict(case='nushell',command=command,pid=child.pid,returncode=child.returncode,
        stdout_sha256=sha(work/'nushell.stdout'),stderr_sha256=sha(work/'nushell.stderr'))
    write(work/'records.json',[*records[:4],new]);assert child.returncode==0,err
    new['summary_sha256']=sha(case_path('nushell'));write(work/'records.json',[*records[:4],new])
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        verify_manifest(original['frozen']);verify_manifest(frozen)
        for row in records[:4]:assert sha(case_path(row['case']))==row['summary_sha256']
        audit=audit_cases(CASES);write(work/'final-audit.json',audit)
        results=[json.loads(case_path(case).read_text()) for case in CASES]
        assert next_case(results) is None
        passed=all(r['gate_passed'] for r in results)
        destination=ROOT/'results'/args.run_id;destination.mkdir(exist_ok=False)
        result=dict(status='passed' if passed else 'rejected',all_five_gates_passed=passed,
            completed_cases=CASES,unstarted_cases=[],commands=726,previous_commands=594,new_commands=132,
            no_completed_case_repeated=True,final_source_and_input_audit_passed=True,
            original_controller_retained=OLD,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            final_audit_sha256=sha(work/'final-audit.json'),private_details_redacted=True)
        write(destination/'summary.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
