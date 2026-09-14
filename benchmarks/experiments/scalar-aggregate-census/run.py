"""Qualify and census bounded aggregate projections using retained public data."""
import collections,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
NAME='scalar-aggregate-census-01'
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
            digest=sha(p)
            if h is not None:assert digest==h,p
            key=str(p.relative_to(ROOT));assert key not in frozen or frozen[key]==digest
            frozen[key]=digest
            return read(p) if p.suffix=='.json' else None
        for p in [*Path(__file__).parent.glob('*.py'),Path(__file__).with_name('PLAN.md')]:bind(p)
        for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],text=True).splitlines():bind(ROOT/p)
        for p in ['compare_saved_runtime.py','workflow_io.py','interpreter.py']:bind(ROOT/'scripts'/p)
        model=ROOT/'results/scalar-aggregate-model-02';closed=bind(model/'closure.json');assert closed['status']=='closed'
        qualified=bind(model/'summary.json',closed['summary_sha256']);bind(model/'terminal.json',closed['terminal_sha256'])
        bind(ROOT/closed['source_bindings'],closed['source_bindings_sha256'])
        assert qualified['status']=='passed' and qualified['commands']==4 and qualified['controls_per_profile']==8
        wide=ROOT/'results/scalar-wide-boundaries-01';closed=bind(wide/'closure.json');assert closed['status']=='closed' and closed['all_hashes_verified']
        prior=bind(wide/'summary.json',closed['summary_sha256']);bind(wide/'terminal.json',closed['terminal_sha256'])
        bind(ROOT/closed['bindings'],closed['bindings_sha256'])
        prior_plan=bind(ROOT/prior['raw']/'plan.json',prior['plan_sha256'])
        ids=prior_plan['candidates']['grid/frame1024/registers512/result64'];assert ids==sorted(set(ids)) and len(ids)==132
        typed=ROOT/'.work/current-call-shapes-01/census.json';metadata=bind(typed,prior_plan['frozen'][str(typed.relative_to(ROOT))])
        artifact=ROOT/'.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc'
        bind(artifact,metadata['artifact_sha256'])
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        inputs=dict(artifact=str(artifact),artifact_sha256=sha(artifact),typed=str(typed),typed_sha256=sha(typed),candidates=ids)
        write(work/'inputs.json',inputs)
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,target=str(target.relative_to(ROOT)),
            required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,expected_commands=2,candidates=132,
            inputs_sha256=sha(work/'inputs.json'),guest_commands=0,executable_code_publications=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
             and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',
            CARGO_TERM_COLOR='never',RUST_TEST_THREADS='2',PYTHONDONTWRITEBYTECODE='1',
            SCALAR_AGGREGATE_INPUT=str(work/'inputs.json'),SCALAR_AGGREGATE_OUTPUT=str(work/'census.json'))
        base=['cargo','+nightly-2026-09-08','test','--lib','-p','rust-interp-bytecode','--locked','--offline','--jobs','2',
              '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'--release']
        records=[]
        for label,filter_,extra,count in [('controls','scalar_ir::aggregate::tests::',[],8),
                ('census','scalar_ir::aggregate::census::observe_saved_aggregate_projections',['--','--ignored','--exact'],1)]:
            assert shutil.disk_usage(ROOT).free>=needed;require_space(ROOT,8)
            cmd=[*base,filter_,*extra];start=time.time()
            child,stdout,stderr=capture(cmd,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            for stream,payload in [('stdout',stdout),('stderr',stderr)]:(work/(label+'.'+stream)).write_text(payload)
            records.append(dict(label=label,command=cmd,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))));write(work/'records.json',records)
            assert child.returncode==0 and f'test result: ok. {count} passed; 0 failed; 0 ignored;' in stdout,(stdout+stderr)[-6500:]
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'PASS',flush=True)
        census=read(work/'census.json');assert census['status']=='passed' and census['candidates']==132 and len(census['policies'])==2
        policies=[]
        for policy in census['policies']:
            rows=policy['rows'];assert [r['function'] for r in rows]==ids
            stages={'memory':{r['function'] for r in rows if r['memory_eligible']},
                    'ir':{r['function'] for r in rows if r.get('ir_eligible')},
                    'native':{r['function'] for r in rows if r.get('all_lanes_native')}}
            assert stages['native']<=stages['ir']<=stages['memory']
            coverage={}
            for case in prior['cases']:
                targets=case['policies']['grid/frame1024/registers512/result64']['sampled_targets']
                coverage[case['case']]={stage:dict(transition_samples=sum(t['transition_samples'] for t in targets if t['function'] in admitted),
                    body_samples=sum(t['body_samples'] for t in targets if t['function'] in admitted),
                    sampled_ids=[t['function'] for t in targets if t['function'] in admitted]) for stage,admitted in stages.items()}
            policies.append(dict(zeroed_frame=policy['zeroed_frame'],ids={k:sorted(v) for k,v in stages.items()},
                coverage=coverage,memory_declines=dict(collections.Counter(r['memory_decline']['reason'] for r in rows if not r['memory_eligible'])),
                ir_declines=dict(collections.Counter(r['ir_decline'] for r in rows if r.get('ir_eligible') is False)),
                native_lane_declines=dict(collections.Counter(l['native_decline'] for r in rows for l in r.get('lanes',[]) if not l['native_eligible'])),
                memory_work_remaining=policy['memory_work_remaining'],lowering_allowance_remaining=policy['lowering_allowance_remaining']))
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=2,controls=8,candidates=132,policies=policies,
            setup_seconds=sum(r['seconds'] for r in records),raw=str(work.relative_to(ROOT)),source_revision=revision,
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),inputs_sha256=sha(work/'inputs.json'),
            census_sha256=sha(work/'census.json'),guest_commands=0,executable_code_publications=0,performance_measurement=False,scope=census['scope']))
        print(json.dumps(policies),flush=True)
if __name__=='__main__':main()
