#!/usr/bin/env python3
"""Verify additive effective-limit receipts without changing guest execution."""
import json,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools
from workflow_io import capture,require_space,write_json as write
from suite_reports import read_report,validate_report,validate_runtime_limits


def main():
    run='prepared-limits-replay-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        build_path=ROOT/'results/prepared-limits-build-01/summary.json';build=json.loads(build_path.read_text())
        assert build['status']=='passed' and all(v==dict(passed=323,ignored=1) for v in build['tests'].values())
        current,key=installed_tools(build['tool_key']);old,old_key=installed_tools(build['composition']['exporter_and_wrapper_key'])
        for name in ['rust-interp-mir-export','rust-interp-rustc-wrapper']:assert sha(current/name)==sha(old/name)
        entropy_path=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json';entropy=json.loads(entropy_path.read_text())
        library=ROOT/entropy['library'];assert entropy['status']=='passed' and sha(library)==entropy['library_sha256']
        cases=[('pgrust','.work/prepared-catalog-pgrust-02/candidate-restored.rbc','results/prepared-catalog-pgrust-02/summary.json'),
               ('token','.work/prepared-catalog-token-diagnose-01/program.rbc','results/export-reuse-screen-token-01/summary.json'),
               ('ruff','.work/prepared-catalog-ruff-01/program.rbc','results/aggregate-relocation-heldout-01-ruff-retry-01/summary.json')]
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        paths=[Path(__file__),Path(__file__).with_name('LIMITS.md'),build_path,entropy_path,library,current/'rust-interp-vm',old/'rust-interp-vm']
        paths += [ROOT/'scripts'/n for n in ['suite_reports.py','workflow_io.py','compare_saved_runtime.py','interpreter.py']]
        for _,artifact,reference in cases:paths += [ROOT/artifact,ROOT/(artifact+'.entries.json'),ROOT/reference]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths};write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,cases=cases,tool_key=key,control_tool_key=old_key,performance_measurement=False))
        base_env={k:v for k,v in os.environ.items() if not k.startswith('RUST_INTERP_')}
        assert not any(k.startswith('DYLD_') for k in base_env)
        records=[];results=[]
        for name,relative,reference in cases:
            artifact=ROOT/relative;catalog=Path(str(artifact)+'.entries.json');descriptor=json.loads(catalog.read_text())
            assert descriptor['artifact_sha256']==sha(artifact)
            names=[e['name'] for e in descriptor['entries']]
            ref=json.loads((ROOT/reference).read_text());limit=ref['instruction_limit'];allocations=ref.get('allocation_limit')
            exact=[];consumption=[]
            for label,tool,mode,action,required in [('old-fresh',old,'fresh','record',False),('old-prepared',old,'prepared','replay',False),('new-fresh',current,'fresh','replay',True),('new-prepared',current,'prepared','replay',True)]:
                output=work/(name+'-'+label+'.json')
                command=[str(tool/'rust-interp-vm'),'--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--instruction-limit',str(limit),
                         '--isolated-batch',mode,'--suite-report',str(output),'--suite-catalog',str(catalog)]
                if allocations is not None:command+=['--allocation-limit',str(allocations)]
                command.append(str(artifact));env=dict(base_env,DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_ENTROPY_MODE=action,RUST_INTERP_ENTROPY_TAPE=str(work/(name+'.tape')))
                require_space(ROOT,8)
                child,stdout,stderr=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(case=name,label=label))
                records.append(dict(case=name,label=label,command=command,returncode=child.returncode,stdout=stdout,stderr=stderr));write(work/'records.json',records)
                assert child.returncode==0 and stdout=='0\n',stderr
                report,digest=read_report(output);validate_report(report,names,mode,True);validate_runtime_limits(report,limit,allocations,required=required)
                assert report['entry_source']=='artifact-bound catalog'
                records[-1]['suite_sha256']=digest
                exact.append([{k:t[k] for k in ['name','function','status','instructions','peak_guest_memory']} for t in report['tests']])
                consumption.append(re.findall(r'entropy_calls=(\d+) entropy_bytes=(\d+)',stderr))
                print(name,label,'passed',flush=True)
            assert exact.count(exact[0])==4 and consumption.count(consumption[0])==4 and len(consumption[0])==1
            results.append(dict(case=name,tests=len(names),commands=4,effective_limits=report['runtime_limits'],artifact_sha256=sha(artifact),catalog_sha256=sha(catalog),logical_execution_identical=True,entropy=consumption[0]))
        write(work/'records.json',records)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/run;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=len(records),cases=results,tool_key=key,control_tool_key=old_key,performance_measurement=False,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))


if __name__=='__main__':main()
