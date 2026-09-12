#!/usr/bin/env python3
"""Inspect typed constant arguments against current, provenance-bound real profiles."""
import json,os,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from profile_vm_transitions import counts as checked_counts
from workflow_io import capture,require_space,write_json as write

def main():
    run='constant-call-arguments-census-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        build_path=ROOT/'results/constant-call-arguments-build-01/summary.json';build=json.loads(build_path.read_text())
        assert build['status']=='passed' and build['source_commit'].startswith('a5d249d')
        assert build['tests']['test-debug']==build['tests']['test-release']==dict(passed=357,ignored=1)
        build_work=ROOT/build['raw'];build_plan=json.loads((build_work/'plan.json').read_text())
        assert sha(build_work/'plan.json')==build['source_manifest_sha256']
        status_path=ROOT/'.work/experiments/constant-call-arguments-build-01/status.json';status=json.loads(status_path.read_text())
        assert status['status']=='finished' and status['returncode']==0 and status['owner']==str(ROOT)
        assert sha(status_path.with_name('command.log'))==status['log_sha256']
        assert all(sha(ROOT/p)==h for p,h in build_plan['frozen'].items())
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        binary=work/'rust-interp-call-census';original=Path(build_plan['target'])/'release'/binary.name
        shutil.copy2(original,binary);assert sha(binary)==sha(original)
        reference_path=ROOT/'results/suite-profiling-real-01/summary.json';reference=json.loads(reference_path.read_text())
        assert reference['status']=='passed' and reference['exact_logical_counts_and_entropy']
        frozen_paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),build_path,build_work/'plan.json',build_work/'commands.json',
            status_path,status_path.with_name('command.log'),binary,reference_path,ROOT/'scripts/profile_vm_transitions.py',ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py']
        inputs=[]
        for item in reference['profiles']:
            if item['index'] not in [0,1,2,5]:continue
            artifact=ROOT/item['artifact'];catalog=ROOT/item['catalog'];profile=ROOT/reference['raw']/f"{item['index']}-profile.json"
            assert sha(artifact)==item['artifact_sha256'] and sha(catalog)==item['catalog_sha256'] and sha(profile)==item['profile_sha256']
            frozen_paths += [artifact,catalog,profile]
            inputs.append(dict(index=item['index'],case=item['case'],name=item['name'],artifact=str(artifact.relative_to(ROOT)),profile=str(profile.relative_to(ROOT)),
                artifact_sha256=sha(artifact),profile_sha256=sha(profile),statistics=item['statistics']))
        frozen={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,inputs=inputs,binary_sha256=sha(binary),performance_measurement=False,
            scope='Offline constant direct-call argument bytes, current token/folded/pgrust profiles; no original artifact mutation or guest execution. Coverage is not predicted performance or a specialization safety proof.'))
        rows=[];reports=[]
        for item in inputs:
            profile=json.loads((ROOT/item['profile']).read_text());checked_counts(profile,item['statistics'])
            output=work/(str(item['index'])+'.json');command=[str(binary),str(ROOT/item['artifact']),str(output),str(ROOT/item['profile'])]
            require_space(ROOT,8)
            child,stdout,stderr=capture(command,cwd=ROOT,env=os.environ.copy(),receipt_path=work/'active.json',receipt=dict(index=item['index']))
            row=dict(index=item['index'],command=command,pid=child.pid,returncode=child.returncode,stdout=stdout,stderr=stderr)
            rows.append(row);write(work/'records.json',rows);assert child.returncode==0,stderr
            report=json.loads(output.read_text());assert report['artifact_sha256']==item['artifact_sha256'] and report['profile_sha256']==item['profile_sha256']
            assert len(report['functions'])==len(profile['functions'])
            total_sites=total_calls=constant_sites=constant_calls=declined_calls=0
            callees={};patterns={}
            for f in report['functions']:
                observed=profile['functions'][f['function']];n=len(observed['operations'])
                starts=[0]*(n+1);ends=[0]*(n+1)
                for pc,(hits,end) in enumerate(zip(observed['jit_blocks'],observed['jit_block_ends'])):
                    if hits:starts[pc]+=hits;ends[end]+=hits
                count=0;counts=[]
                for pc in range(n):
                    count+=starts[pc]-ends[pc];assert count>=0
                    counts.append(count+observed['interpreted'][pc])
                # Rendered labels independently count observations only; the
                # Rust diagnostic supplies typed operands and byte proofs.
                call_pcs=[pc for pc,op in enumerate(observed['operations']) if op.startswith('Call {')]
                assert f['direct_call_sites']==len(call_pcs)
                assert f['direct_call_executions']==sum(counts[pc] for pc in call_pcs)
                total_sites+=len(call_pcs);total_calls+=f['direct_call_executions']
                if f['declined']:
                    declined_calls+=f['direct_call_executions'];continue
                assert [s['pc'] for s in f['sites']]==call_pcs
                for site in f['sites']:
                    assert site['executions']==counts[site['pc']]
                    fid=site['callee'];callee=callees.setdefault(fid,dict(function=fid,all_calls=0,constant_calls=0,static_sites=0,constant_sites=0))
                    callee['all_calls']+=site['executions'];callee['static_sites']+=1
                    if not site['arguments']:continue
                    constant_sites+=1;constant_calls+=site['executions'];callee['constant_calls']+=site['executions'];callee['constant_sites']+=1
                    key=(fid,tuple((a['index'],a['bytes'],a['value']) for a in site['arguments']))
                    pattern=patterns.setdefault(key,dict(callee=fid,arguments=site['arguments'],calls=0,sites=0,example_caller=f['function'],example_pc=site['pc']))
                    pattern['calls']+=site['executions'];pattern['sites']+=1
            for key,value in [('direct_call_sites',total_sites),('sites_with_constant_arguments',constant_sites),
                ('direct_call_executions',total_calls),('executions_with_constant_arguments',constant_calls),('declined_direct_call_executions',declined_calls)]:
                assert report[key]==value
            for f in callees.values():
                observed=profile['functions'][f['function']]
                f['name_prefix']=observed['name'][:200]
                f['native_operations']=sum(hits*(end-pc) for pc,(hits,end) in enumerate(zip(observed['jit_blocks'],observed['jit_block_ends'])) if hits)
                f['constant_fraction_of_admitted_incoming_calls']=f['constant_calls']/f['all_calls'] if f['all_calls'] else None
            part=dict(index=item['index'],case=item['case'],name=item['name'],direct_call_sites=total_sites,sites_with_constants=constant_sites,
                direct_calls=total_calls,calls_with_constants=constant_calls,constant_call_fraction=constant_calls/total_calls if total_calls else None,
                declined_functions=report['declined_functions'],declined_calls=declined_calls,
                top_callees=sorted(callees.values(),key=lambda x:-x['constant_calls'])[:20],
                top_patterns=sorted(patterns.values(),key=lambda x:-x['calls'])[:20],
                report_sha256=sha(output),artifact_sha256=item['artifact_sha256'],profile_sha256=item['profile_sha256'])
            reports.append(part);row['report_sha256']=sha(output);write(work/'records.json',rows);write(work/'reports.json',reports)
            print(item['index'],item['case'],'constant direct-call fraction',part['constant_call_fraction'],flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/run;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=len(rows),cases=reports,binary_sha256=sha(binary),
            source_commit=build['source_commit'],performance_measurement=False,original_artifacts_unchanged=True,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))

if __name__=='__main__':main()
