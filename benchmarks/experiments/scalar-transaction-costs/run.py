"""Source-qualified private-store body costs without executing guests."""
import json,os,re,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
NAME='scalar-transaction-costs-01'

def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed,'insufficient conservative build admission'
        profile_path=ROOT/'results/scalar-transaction-native-profile-01/summary.json';profile=read(profile_path)
        original_path=ROOT/'results/current-runtime-boundaries-02/summary.json';original=read(original_path)
        assert profile['status']==original['status']=='passed' and profile['commands']==3 and profile['reused_control_profiles']==3
        assert profile['exact_per_pc_counts'] and profile['exact_operation_map_reconstruction']
        paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),profile_path,original_path]
        closure_path=profile_path.with_name('closure.json');closed=read(closure_path)
        assert closed['status']=='closed' and closed['all_hashes_verified'] and sha(profile_path)==closed['summary_sha256']
        binding=ROOT/closed['bindings'];assert sha(binding)==closed['bindings_sha256'];paths += [closure_path,binding]
        for name,digest in read(binding)['artifacts'].items():
            assert sha(ROOT/name)==digest;paths.append(ROOT/name)
        paths += [ROOT/p for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],text=True).splitlines()]
        paths += [ROOT/'scripts'/p for p in ['compare_saved_runtime.py','workflow_io.py','interpreter.py']]
        inputs=[]
        for case in original['profiles']:
            row,=[r for r in profile['comparisons'] if r['index']==case['index'] and r['mode']=='candidate']
            control,=[r for r in profile['comparisons'] if r['index']==case['index'] and r['mode']=='control']
            assert row['name']==control['name']==case['name']
            entry=dict(index=case['index'],expected_scalar_bodies=row['scalar_bodies'])
            for key,path,digest in [('artifact',case['artifact'],case['artifact_sha256']),
                ('profile',row['profile_path'],row['profile_sha256']),('code',row['code_path'],row['code_sha256']),
                ('operations',row['operations_path'],row['operations_sha256']),
                ('control_operations',control['operations_path'],control['operations_sha256'])]:
                p=ROOT/path;assert sha(p)==digest;entry[key]=str(p);entry[key+'_sha256']=digest;paths.append(p)
            inputs.append(entry)
        assert len(inputs)==3
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False);write(work/'inputs.json',inputs)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,target=str(target.relative_to(ROOT)),
            same_source_root=True,required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,
            expected_bodies=sum(i['expected_scalar_bodies'] for i in inputs),inputs_sha256=sha(work/'inputs.json'),guest_commands=0,production_runtime_changes=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
             and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',
            CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1',TRANSACTION_COSTS_INPUT=str(work/'inputs.json'),TRANSACTION_COSTS_OUTPUT=str(work/'census.json'))
        base=['cargo','+nightly-2026-09-08','test','--release','--lib','-p','rust-interp-bytecode',
            '--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target)]
        records=[]
        for label,test,extra,count,ignored in [
            ('controls','scalar_ir::native_leaf::transaction::',[],2,1),
            ('census','scalar_ir::native_leaf::transaction::costs::observe_saved_native_store_costs',['--ignored','--exact'],1,0)]:
            assert shutil.disk_usage(ROOT).free>=needed;require_space(ROOT,8)
            cmd=[*base,test,'--',*extra];start=time.time()
            child,out,err=capture(cmd,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            for stream,text in [('stdout',out),('stderr',err)]:(work/(label+'.'+stream)).write_text(text)
            records.append(dict(label=label,command=cmd,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json',records)
            assert child.returncode==0 and f'test result: ok. {count} passed; 0 failed; {ignored} ignored;' in out,(out+err)[-5000:]
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(label,'PASS',flush=True)
        census=read(work/'census.json');assert census['status']=='passed' and len(census['cases'])==3
        expected=sum(i['expected_scalar_bodies'] for i in inputs)
        assert sum(c['reconstructed_bodies'] for c in census['cases'])==expected
        totals=[]
        for case in census['cases']:
            stores=[s for f in case['functions'] for s in f['stores']]
            visits=lambda predicate:sum(s['successful_visits'] for s in stores if predicate(s))
            totals.append(dict(index=case['index'],reconstructed_bodies=case['reconstructed_bodies'],store_bodies=len(case['functions']),
                successful_store_calls=sum(f['successful_calls'] for f in case['functions']),store_visits=visits(lambda s:True),
                reusable_store_guard_visits=visits(lambda s:s['prior_same_block_containing_store'] is not None),
                coalescible_store_visits=visits(lambda s:s['later_same_block_containing_store'] is not None),
                unneeded_high_lane_visits=visits(lambda s:s['high_lane_unneeded']),
                unneeded_logical_address_visits=visits(lambda s:s['logical_address_slot_unneeded'])))
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=2,controls=2,reconstructed_native_bodies=expected,cases=totals,
            setup_seconds=sum(r['seconds'] for r in records),raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),
            records_sha256=sha(work/'records.json'),inputs_sha256=sha(work/'inputs.json'),census_sha256=sha(work/'census.json'),
            source_revision=revision,guest_commands=0,executable_code_publications=0,production_runtime_changes=0,
            performance_measurement=False,scope=census['scope']))
        print(json.dumps(totals),flush=True)
if __name__=='__main__':main()
