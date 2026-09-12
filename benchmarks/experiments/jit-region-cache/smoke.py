#!/usr/bin/env python3
"""Replay qualified real suites under exact entropy before the runtime screen."""
import json
import os
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools
from workflow_io import capture,require_space,write_json as write
from suite_reports import read_report,validate_report,validate_runtime_limits


def main():
    run='jit-region-cache-smoke-02'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        control_path=ROOT/'results/jit-register-width-build-02/summary.json'
        build_path=ROOT/'results/jit-region-cache-build-01/summary.json'
        control=json.loads(control_path.read_text());build=json.loads(build_path.read_text())
        assert control['status']==build['status']=='passed'
        assert build['tests']['test-debug']==build['tests']['test-release']==dict(passed=339,ignored=1)
        tools={mode:installed_tools(s['tool_key'])[0] for mode,s in [('baseline',control),('candidate',build)]}
        qualification=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json'
        q=json.loads(qualification.read_text());assert q['status']=='passed' and q['commands']==17 and q['expected_rejections']==10
        library=(ROOT/q['library']).resolve(strict=True);assert sha(library)==q['library_sha256']
        frozen_paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),control_path,build_path,qualification,library]
        frozen_paths += [tool/'rust-interp-vm' for tool in tools.values()]
        inputs=[]
        for case,reference in [('pgrust','filtered-workflow-pgrust-01'),('folded','filtered-workflow-folded-01'),('token','filtered-workflow-token-02')]:
            summary_path=ROOT/'results'/reference/'summary.json';summary=json.loads(summary_path.read_text());assert summary['status']=='passed'
            records_path=ROOT/summary['raw']/'records.json';assert sha(records_path)==summary['records_sha256']
            reference_records=json.loads(records_path.read_text());frozen_paths += [summary_path,records_path]
            for state in ([6,-1] if case=='pgrust' else [6]):
                row=next(r for r in reference_records if r['state']==state and r['mode']=='automatic')
                artifact=ROOT/row['artifact_path'];catalog=Path(str(artifact)+'.entries.json')
                assert sha(artifact)==row['artifact_sha256'] and sha(catalog)==row['launch']['entry_catalog_sha256']
                suite_path=ROOT/summary['raw']/f'{state}-automatic-suite.json'
                suite,_=read_report(suite_path,row['suite_sha256']);names=[t['name'] for t in suite['tests']]
                outcomes=validate_report(suite,names,'prepared',state!=-1)
                frozen_paths += [artifact,catalog,suite_path]
                inputs.append(dict(case=case,state=state,artifact=str(artifact.relative_to(ROOT)),artifact_sha256=sha(artifact),
                    catalog=str(catalog.relative_to(ROOT)),names=names,outcomes=outcomes,limits=suite['runtime_limits']))
        frozen={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),baseline_key=control['tool_key'],candidate_key=build['tool_key'],
            frozen=frozen,inputs=inputs,performance_measurement=False,scope='saved real suites; baseline records entropy, candidate replays; no edited compilation'))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env['DYLD_INSERT_LIBRARIES']=str(library)
        records=[]
        for item in inputs:
            label=item['case']+'-'+str(item['state']);tape=work/(label+'.tape');pair={}
            for mode in ['baseline','candidate']:
                require_space(ROOT,8)
                suite_path=work/(label+'-'+mode+'.json')
                command=[str(tools[mode]/'rust-interp-vm'),'--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
                    '--isolated-batch','prepared','--suite-report',str(suite_path),'--suite-catalog',str(ROOT/item['catalog']),
                    '--instruction-limit',str(item['limits']['instructions']),'--allocation-limit',str(item['limits']['allocations']),
                    str(ROOT/item['artifact'])]
                child_env=dict(env,RUST_INTERP_ENTROPY_MODE='record' if mode=='baseline' else 'replay',RUST_INTERP_ENTROPY_TAPE=str(tape))
                child,stdout,stderr=capture(command,cwd=ROOT,env=child_env,receipt_path=work/'active.json',receipt=dict(case=label,mode=mode))
                record=dict(case=label,mode=mode,command=command,pid=child.pid,returncode=child.returncode,stdout=stdout,stderr=stderr)
                records.append(record);write(work/'records.json',records)
                assert child.returncode==(1 if item['state']==-1 else 0),stderr
                suite,digest=read_report(suite_path);outcomes=validate_report(suite,item['names'],'prepared',item['state']!=-1)
                assert outcomes==[tuple(o) for o in item['outcomes']]
                validate_runtime_limits(suite,item['limits']['instructions'],item['limits']['allocations'],required=True)
                counts={k:int(v) for k,v in re.findall(r'\b(entropy_calls|entropy_bytes)=(\d+)\b',stderr)}
                assert set(counts)=={'entropy_calls','entropy_bytes'}
                record.update(suite_sha256=digest,tape_sha256=sha(tape),entropy=counts)
                observed=[{k:t[k] for k in ['name','status']+(['instructions','peak_guest_memory'] if t['status']=='passed' else ['error'])} for t in suite['tests']]
                assert all(t.get('jit_declined_functions',0)==0 for t in suite['tests'])
                pair[mode]=dict(outcomes=observed,entropy=counts,stdout=stdout,tape_sha256=sha(tape))
                write(work/'records.json',records)
            assert pair['baseline']==pair['candidate'],label+' changed exact execution'
            print(label,'PASS',len(item['names']),'tests, exact entropy and logical counts',flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/run;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=len(records),suite_pairs=len(inputs),
            passing_tests=34,wrong_edit_tests=4,baseline_key=control['tool_key'],candidate_key=build['tool_key'],
            exact_logical_counts_and_entropy=True,native_outcomes_match=True,jit_declines=0,performance_measurement=False,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))


if __name__=='__main__':main()
