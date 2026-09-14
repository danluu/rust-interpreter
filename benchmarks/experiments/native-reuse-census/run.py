"""Inspect closed real-edit artifacts; run no guest and publish no native code."""
import json, os, shutil, statistics, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/jit-preparation-census'))
from accounting import analyze
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from observe import compare,aggregate,native_weights
NAME='native-reuse-identity-census-01'
ADOPTED='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
def read(p):return json.loads(p.read_text())


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed,'insufficient conservative build admission'
        frozen={}
        def bind(p,h=None):
            p=Path(p);actual=sha(p)
            if h is not None:assert actual==h,p
            frozen[str(p.relative_to(ROOT))]=actual
            return read(p) if p.suffix=='.json' else actual
        cases=[];artifacts={};work=ROOT/'.work'/NAME
        def artifact(item):
            bind(ROOT/item['path'],item['sha256']);artifacts.setdefault(item['sha256'],item)
            return item['sha256']
        for case,run in [('token','retained-region-values-screen-token-01'),('parser','indexed-switches-parser-screen-incremental-01')]:
            folder=ROOT/'results'/run;closed=bind(folder/'closure.json')
            if case=='token':
                assert closed['status']=='passed' and closed['parked']
                evidence=bind(ROOT/closed['evidence_path'],closed['evidence_sha256'])
                summary=bind(folder/'summary.json',evidence[str((folder/'summary.json').relative_to(ROOT))])
                assert summary['source_restored'] and summary['candidate_control_bytecode_matches']
            else:
                assert closed['status']=='closed' and closed['all_hashes_verified'] and closed['verdict']=='failed'
                summary=bind(folder/'summary.json',closed['summary_sha256'])
                bind(folder/'terminal.json',closed['terminal_sha256'])
                evidence=bind(ROOT/closed['evidence'],closed['evidence_sha256'])
                assert summary['source_restored'] and summary['candidate_control_artifacts_match']
            assert summary['status']=='passed' and summary['commands']==40
            raw=ROOT/summary['raw'];plan=bind(raw/'plan.json',summary['plan_sha256'])
            assert (summary if case=='token' else plan)['tool_keys']['baseline']==ADOPTED
            rows=bind(raw/'records.json',summary['records_sha256'])
            selected=[r for r in rows if r['mode']=='baseline']
            assert [(r['cycle'],r['state']) for r in selected]==[(0,s) for s in [0,-1,1,2,3,4,5]]+[(1,0)]
            states=[]
            for row in selected:
                assert row['source_sha256']!=row['previous_source_sha256']
                assert row['launch']['tool_key']==ADOPTED and (row['returncode']==0)==(row['state']!=-1)
                item=row['artifact'];assert evidence[item['path']]==item['sha256']
                entry=dict(cycle=row['cycle'],state=row['state'],artifact_sha256=artifact(item),source_sha256=row['source_sha256'])
                if row['state']>0:
                    command=row['command'];suite=bind(Path(command[command.index('--suite-report')+1]),row['suite_sha256'])
                    entry['retained_costs']=analyze(suite,row['seconds'] if case=='token' else row['wall_seconds'],row['launch']['execution_seconds'])
                states.append(entry)
            cases.append(dict(case=case,run=run,states=states))
        # Both code maps are already closed adopted unprofiled captures.
        closure=bind(ROOT/'results/scalar-protocol-census-03/closure.json')
        assert closure['status']=='closed' and closure['all_hashes_verified']
        saved=bind(ROOT/'results/scalar-protocol-census-03/summary.json',closure['summary_sha256'])
        old_plan=bind(ROOT/'.work/scalar-protocol-census-03/plan.json',saved['plan_sha256'])
        token_map='.work/scratch-scalar-runtime-sample-block-01/0/jit-code/map.json'
        bind(ROOT/token_map,old_plan['frozen'][token_map])
        cases[0].update(map=token_map,reference_artifact_sha256=cases[0]['states'][0]['artifact_sha256'])
        closure=bind(ROOT/'results/parser-runtime-sampling-02/closure.json')
        assert closure['status']=='closed' and closure['all_hashes_verified']
        bind(ROOT/'results/parser-runtime-sampling-02/summary.json',closure['summary_sha256'])
        old_artifacts=bind(ROOT/closure['artifact_bindings'],closure['artifact_bindings_sha256'])
        parser_map='.work/parser-runtime-sample-01/0/jit-code/map.json'
        bind(ROOT/parser_map,old_artifacts[parser_map])
        parser_artifact=dict(path='.work/guarded-local-facts-main-parser-01/artifact.rbc',sha256='a157f60c0356ae2498eaa94a1133e2257c8ee220bcfd3b24ca969525fe5f9a61')
        cases[1].update(map=parser_map,reference_artifact_sha256=artifact(parser_artifact))
        for case in cases:
            sample='scratch-scalar-runtime-sample-block-01' if case['case']=='token' else 'parser-runtime-sample-01'
            report=bind(ROOT/'results'/sample/'summary.json')
            assert report['tool_key']==ADOPTED and report['artifact_sha256']==case['reference_artifact_sha256']
        paths=subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],text=True).splitlines()
        paths += [str(p.relative_to(ROOT)) for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += ['scripts/compare_saved_runtime.py','scripts/workflow_io.py','benchmarks/experiments/jit-preparation-census/accounting.py']
        for p in paths:bind(ROOT/p)
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work.mkdir(exist_ok=False)
        inputs=[dict(artifact=str(ROOT/item['path']),sha256=h,output=str(work/(h+'.json'))) for h,item in artifacts.items()]
        write(work/'inputs.json',inputs)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,cases=cases,
            inputs_sha256=sha(work/'inputs.json'),artifacts=len(inputs),target=str(target.relative_to(ROOT)),
            required_free_bytes=needed,allocated_target_bytes=allocated,expected_commands=2,python_controls=4,rust_controls=1,
            guest_commands=0,code_publications=0,production_changes=0,minimum_child_gib=8,performance_measurement=False))
        records=[];write(work/'records.json',records)
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','NATIVE_IDENTITY_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',
            CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1',RUST_TEST_THREADS='2',NATIVE_IDENTITY_INPUT=str(work/'inputs.json'))
        commands=[([sys.executable,'-m','unittest','test_observe','-v'],Path(__file__).parent),
            (['cargo','+nightly-2026-09-08','test','--release','--lib','-p','rust-interp-bytecode','--locked','--offline','--jobs','2',
                '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'native_identity_census::','--','--include-ignored'],ROOT)]
        for i,(command,cwd) in enumerate(commands):
            require_space(ROOT,8)
            if i==1:assert shutil.disk_usage(ROOT).free>=needed,'build admission no longer holds'
            started=time.time();child,out,err=capture(command,cwd=cwd,env=env,receipt_path=work/'active.json',receipt=dict(label=str(i)))
            for stream,data in [('stdout',out),('stderr',err)]:(work/f'{i}.{stream}').write_text(data)
            records.append(dict(label=str(i),command=command,cwd=str(cwd),pid=child.pid,returncode=child.returncode,seconds=time.time()-started,
                stdout_sha256=sha(work/f'{i}.stdout'),stderr_sha256=sha(work/f'{i}.stderr')))
            write(work/'records.json',records);assert child.returncode==0,(out+err)[-4500:]
            assert ('Ran 4 tests' in err and err.rstrip().endswith('OK')) if i==0 else 'test result: ok. 2 passed; 0 failed; 0 ignored;' in out
        described={h:read(work/(h+'.json')) for h in artifacts}
        for h,report in described.items():assert report['artifact_sha256']==h and not report['complete_cache_key']
        comparisons=[];groups=[]
        for case in cases:
            reference=described[case['reference_artifact_sha256']];mapping=read(ROOT/case['map']);previous=None;group=[]
            for state in case['states']:
                current=described[state['artifact_sha256']]
                if previous is not None:
                    conditions=compare(previous,current);weights=native_weights(mapping,reference,current)
                    row=dict(case=case['case'],cycle=state['cycle'],state=state['state'],artifact_sha256=state['artifact_sha256'],
                        previous_artifact_sha256=previous['artifact_sha256'],data_equal=previous['data_sha256']==current['data_sha256'],
                        statics_equal=previous['statics_sha256']==current['statics_sha256'],
                        thread_locals_equal=previous['thread_locals_sha256']==current['thread_locals_sha256'],
                        identities=conditions,metrics=aggregate(current,conditions,weights))
                    comparisons.append(row)
                    if state['state']>0:group.append(row)
                previous=current
            assert len(group)==5
            labels=['self_equal','self_and_call_layouts','self_and_direct_bodies','transitive_direct_bodies']
            groups.append(dict(case=case['case'],edited_states=5,map_code_bytes=mapping['code_bytes'],
                metrics=[dict(state=r['state'],**r['metrics']) for r in group],
                median_conditions={label:{field:statistics.median(r['metrics']['conditions'][label][field] for r in group)
                    for field in ['functions','operations','serialized_bytes','reference_native_bytes']} for label in labels},
                retained_cost_medians={k:statistics.median(s['retained_costs'][k] for s in case['states'] if s['state']>0)
                    for k in ['command_seconds','compile_sum_seconds','largest_worker_compile_seconds','constructor_sum_seconds']},
                diagnostic_describe_median_seconds=statistics.median(described[s['artifact_sha256']]['diagnostic_stage_ns']['describe']/1e9
                    for s in case['states'] if s['state']>0)))
        write(work/'comparisons.json',comparisons)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,commands=2,controls=5,artifacts=len(inputs),
            retained_history_commands=80,new_guest_commands=0,production_changes=0,code_publications=0,complete_cache_key=False,
            cases=groups,setup_seconds=sum(r['seconds'] for r in records),raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            artifacts_sha256={str(p.relative_to(ROOT)):sha(p) for p in [work/'inputs.json',work/'comparisons.json',*[work/(h+'.json') for h in artifacts]]},
            performance_measurement=False,scope='Necessary identity conditions on validated saved real edits. Direct transitive closure is conservative; indirect calls, scalar proof/admission state, assertion relocation and code options still need complete treatment. Saved native bytes are not compile time or future cache hits.'))
        print(json.dumps(dict(cases=[{k:v for k,v in c.items() if k!='metrics'} for c in groups],artifacts=len(inputs))),flush=True)


if __name__=='__main__':main()
