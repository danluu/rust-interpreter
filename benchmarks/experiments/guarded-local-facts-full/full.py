#!/usr/bin/env python3
"""Run required guarded local-fact cases in order, stopping at the first failed gate."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from large_compare import fingerprint

CASES=['token','folded','pgrust','rg-aot','nushell']


def next_case(completed):
    assert len(completed)<=len(CASES)
    for index,result in enumerate(completed):
        assert result['case']==CASES[index]
        assert result['status']=='passed' and result['source_restored']
        assert result['commands']==(154 if index<3 else 132)
        if not result['gate_passed']:
            assert index==len(completed)-1, 'a case started after a failed guard'
            return None
    return CASES[len(completed)] if len(completed)<len(CASES) else None


def verify_manifest(manifest):
    for name,digest in manifest.items():
        actual=fingerprint(ROOT/name) if isinstance(digest,dict) else sha(ROOT/name)
        assert actual==digest, 'frozen input changed: '+name

def case_path(case):
    return ROOT/'results'/('guarded-local-facts-edit-'+case+'-01')/'summary.json'

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
        retained={}
        for row in json.loads((raw/'records.json').read_text()):
            for kind in ['artifact','catalog','entry_catalog','selection','native_executable','cargo_timing']:
                if kind not in row: continue
                item=row[kind]
                assert item['path'] not in retained or retained[item['path']]==item['sha256']
                retained[item['path']]=item['sha256']
        assert retained and all(sha(ROOT/p)==h for p,h in retained.items())
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
            source_restored=True,pinned_revision_verified=True,tracked_source_clean=True,
            retained_artifacts_verified=len(retained)))
    verify_manifest(merged)
    return dict(cases=audit,unique_frozen_inputs=len(merged),all_frozen_inputs_verified=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args();assert re.fullmatch(r'guarded-local-facts-full-\d{2}',args.run_id)
    work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
    directory=Path(__file__).parent
    paths=[p for p in directory.iterdir() if p.suffix in ['.py','.md']]
    paths+=list((ROOT/'scripts').glob('*.py'))
    harness=ROOT/'results/guarded-local-facts-full-protocol-01/summary.json'
    proof=json.loads(harness.read_text());assert proof['status']=='passed' and proof['tests']==21
    inputs=ROOT/proof['raw']/'inputs.json';assert sha(inputs)==proof['inputs_sha256']
    assert all(sha(ROOT/p)==h for p,h in json.loads(inputs.read_text()).items())
    paths += [harness,inputs]
    frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
    write(work/'plan.json',dict(owner=str(ROOT),cases=CASES,frozen=frozen,maximum_commands=726,
        stop_on_failed_gate=True,all_five_required_for_adoption=True))
    completed=[];records=[]
    while (case:=next_case(completed)) is not None:
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        run='guarded-local-facts-edit-'+case+'-01'
        script='workflows.py' if case in CASES[:3] else 'large_compare.py'
        command=[sys.executable,str(directory/script),'--case',case,'--run-id',run]
        if case in CASES[:3]:
            command+=['--build','results/guarded-local-facts-build-03/summary.json']
        child,out,err=capture(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=work/'active.json',receipt=dict(case=case))
        (work/(case+'.stdout')).write_text(out);(work/(case+'.stderr')).write_text(err)
        records.append(dict(case=case,command=command,pid=child.pid,returncode=child.returncode,
            stdout_sha256=sha(work/(case+'.stdout')),stderr_sha256=sha(work/(case+'.stderr'))))
        write(work/'records.json',records)
        assert child.returncode==0,err
        result_path=ROOT/'results'/run/'summary.json';result=json.loads(result_path.read_text())
        completed.append(result);next_case(completed)
        records[-1]['summary_sha256']=sha(result_path);write(work/'records.json',records)
        print(case,'correctness passed; gate',result['gate_passed'],flush=True)
    assert all(sha(ROOT/p)==h for p,h in frozen.items())
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        verify_manifest(frozen)
        for row in records:
            assert sha(case_path(row['case']))==row['summary_sha256']
        audit=audit_cases([r['case'] for r in completed])
        write(work/'final-audit.json',audit)
    passed=len(completed)==len(CASES) and all(r['gate_passed'] for r in completed)
    destination=ROOT/'results'/args.run_id;destination.mkdir(exist_ok=False)
    write(destination/'summary.json',dict(status='passed' if passed else 'rejected',
        all_five_gates_passed=passed,completed_cases=[r['case'] for r in completed],
        unstarted_cases=CASES[len(completed):],commands=sum(r['commands'] for r in completed),
        raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
        final_source_and_input_audit_passed=True,final_audit_sha256=sha(work/'final-audit.json'),
        private_details_redacted=True))


if __name__=='__main__':main()
