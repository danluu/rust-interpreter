"""Qualify static entry obligations on exact archived store-log bodies."""
import collections,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
NAME='scalar-path-guard-census-01'

def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed,'insufficient conservative build admission'
        profile_path=ROOT/'results/scalar-store-log-profile-01/summary.json';profile=read(profile_path)
        original_path=ROOT/'results/current-runtime-boundaries-02/summary.json';original=read(original_path)
        assert profile['status']==original['status']=='passed' and profile['commands']==3 and profile['tool_key']=='5b86b3abc7f059c44914a065d9a53fb8679abafdb2832a7d0a27cab38999b2a3'
        assert profile['exact_per_pc_counts'] and profile['exact_operation_map_reconstruction']
        paths=[*Path(__file__).parent.glob('*.py'),Path(__file__).with_name('PLAN.md'),profile_path,original_path]
        closure_path=profile_path.with_name('closure.json');closed=read(closure_path)
        assert closed['status']=='closed' and closed['all_hashes_verified'] and sha(profile_path)==closed['summary_sha256']
        binding=ROOT/closed['bindings'];assert sha(binding)==closed['bindings_sha256'];paths += [closure_path,binding]
        for name,digest in read(binding)['artifacts'].items():
            assert sha(ROOT/name)==digest;paths.append(ROOT/name)
        paths += [ROOT/p for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],text=True).splitlines()]
        paths += [ROOT/'scripts'/p for p in ['compare_saved_runtime.py','workflow_io.py','interpreter.py']]
        model=ROOT/'results/scalar-path-guard-model-01'
        model_summary=read(model/'summary.json');model_closed=read(model/'closure.json')
        assert model_summary['status']=='passed' and model_closed['status']=='closed' and model_closed['logs_verified']
        assert sha(model/'summary.json')==model_closed['summary_sha256']
        paths += [model/'summary.json',model/'closure.json']
        model_binding=ROOT/model_closed['source_bindings'];assert sha(model_binding)==model_closed['source_bindings_sha256']
        paths.append(model_binding)
        for path,binding in read(model_binding).items():
            if not path.startswith('crates/'):continue
            current=(ROOT/path).read_bytes()
            if path=='crates/bytecode/src/scalar/path_entry.rs':
                current=current.replace(b'\n#[cfg(test)]\n#[path="path_entry_census.rs"]\nmod census;\n',b'')
            import hashlib
            assert hashlib.sha256(current).hexdigest()==binding['sha256'],'model source changed: '+path

        archive='8f51e4c31912728fec71b8c71f81227bc0a52967'
        archived=subprocess.check_output(['git','ls-tree','-r','--name-only',archive,'crates/bytecode'],text=True).splitlines()
        for name in archived:
            if name=='crates/bytecode/src/scalar_call_model.rs':continue # Entire module is cfg(test).
            expected=subprocess.check_output(['git','show',archive+':'+name])
            current=(ROOT/name).read_bytes()
            if name=='crates/bytecode/src/scalar/native_transaction.rs':
                current=current.replace(b'#[cfg(test)]\n#[path="native_entry_guards.rs"]\nmod entry_guards;\n',b'')
            if name=='crates/bytecode/src/scalar/scalar_ir.rs':
                current=current.replace(b'\n#[cfg(test)]\n#[path="path_entry.rs"]\nmod path_entry;\n',b'')
            assert current==expected, 'archived production source changed: '+name
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
            CARGO_TERM_COLOR='never',RUST_TEST_THREADS='2',PYTHONDONTWRITEBYTECODE='1',SCALAR_PATH_INPUT=str(work/'inputs.json'),SCALAR_PATH_OUTPUT=str(work/'census.json'))
        base=['cargo','+nightly-2026-09-08','test','--lib','-p','rust-interp-bytecode',
            '--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target)]
        records=[]
        for label,test,extra,count,ignored,release in [
            ('census','scalar_ir::path_entry::census::observe_saved_path_guard_scope',['--ignored','--exact'],1,0,True)]:
            assert shutil.disk_usage(ROOT).free>=needed;require_space(ROOT,8)
            cmd=[*base,*(['--release'] if release else []),test,'--',*extra];start=time.time()
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
            rows=case['functions']; eligible=[f for f in rows if f['eligible']]
            totals.append(dict(index=case['index'],reconstructed_bodies=case['reconstructed_bodies'],
                eligible_functions=len(eligible),eligible_ids=[f['function'] for f in eligible],
                eligible_successful_calls=sum(f['successful_calls'] for f in eligible),
                eligible_successful_read_occurrences=sum(f['successful_read_occurrences'] for f in eligible),
                eligible_successful_write_occurrences=sum(f['successful_write_occurrences'] for f in eligible),
                rejection_counts=dict(collections.Counter(f['decline'] for f in rows if not f['eligible']))))
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=1,controls_reused_per_profile=31,reconstructed_native_bodies=expected,cases=totals,
            setup_seconds=sum(r['seconds'] for r in records),raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),
            records_sha256=sha(work/'records.json'),inputs_sha256=sha(work/'inputs.json'),census_sha256=sha(work/'census.json'),
            source_revision=revision,guest_commands=0,executable_code_publications=0,production_runtime_changes=0,
            performance_measurement=False,scope=census['scope']))
        print(json.dumps(totals),flush=True)
if __name__=='__main__':main()
