"""Source-qualified scalar computation opportunities without executing guests."""
import json,os,re,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
NAME='scalar-computation-census-01'

def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed,'insufficient conservative build admission'
        profile_path=ROOT/'results/scalar-dead-registers-profile-01/summary.json';profile=read(profile_path)
        original_path=ROOT/'results/current-runtime-boundaries-02/summary.json';original=read(original_path)
        assert profile['status']==original['status']=='passed' and profile['commands']==6
        assert profile['exact_per_pc_counts'] and profile['exact_operation_map_reconstruction']
        paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),profile_path,original_path]
        paths += [ROOT/p for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],text=True).splitlines()]
        paths += [ROOT/'scripts'/p for p in ['compare_saved_runtime.py','workflow_io.py','interpreter.py']]
        inputs=[]
        for case in original['profiles']:
            row,=[r for r in profile['comparisons'] if r['index']==case['index'] and r['mode']=='candidate']
            assert row['name']==case['name']
            entry=dict(index=case['index'])
            for key,path,digest in [('artifact',case['artifact'],case['artifact_sha256']),
                ('profile',row['profile_path'],row['profile_sha256']),('code',row['code_path'],row['code_sha256']),
                ('map',str(Path(row['code_path']).with_name('map.json')),row['map_sha256'])]:
                p=ROOT/path;assert sha(p)==digest;entry[key]=str(p);entry[key+'_sha256']=digest;paths.append(p)
            inputs.append(entry)
        assert len(inputs)==3
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False);write(work/'inputs.json',inputs)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,target=str(target.relative_to(ROOT)),
            same_source_root=True,required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,
            expected_bodies=137,inputs_sha256=sha(work/'inputs.json'),guest_commands=0,production_runtime_changes=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
             and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',
            CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1',SCALAR_COMPUTATION_INPUT=str(work/'inputs.json'),SCALAR_COMPUTATION_OUTPUT=str(work/'census.json'))
        base=['cargo','+nightly-2026-09-08','test','--release','--lib','-p','rust-interp-bytecode',
            '--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target)]
        records=[]
        for label,test,extra in [('controls','scalar_computation_facts_preserve_faults_overflow_and_byte_joins',[]),
            ('census','observe_original_scalar_computations',['--ignored'])]:
            assert shutil.disk_usage(ROOT).free>=needed;require_space(ROOT,8)
            cmd=[*base,'scalar_ir::native_leaf::computation_census::'+test,'--','--exact',*extra];start=time.time()
            child,out,err=capture(cmd,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            for stream,text in [('stdout',out),('stderr',err)]:(work/(label+'.'+stream)).write_text(text)
            records.append(dict(label=label,command=cmd,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json',records)
            assert child.returncode==0 and re.search(r'test result: ok\. 1 passed; 0 failed; 0 ignored;',out),(out+err)[-5000:]
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(label,'PASS',flush=True)
        census=read(work/'census.json');assert census['status']=='passed' and len(census['cases'])==3
        assert sum(len(c['functions']) for c in census['cases'])==137
        totals=[]
        for case in census['cases']:
            constants={};pairs=0;dynamic_pairs=0;effects={}
            for f in case['functions']:
                for n in f['constant_nodes']:constants[n['kind']]=constants.get(n['kind'],0)+n['successful_computations']
                for n in f['duplicate_arithmetic_pairs']:
                    pairs+=n['successful_pairs']
                    if not n['both_constant']:dynamic_pairs+=n['successful_pairs']
                for n in f['constant_effects']:effects[n['kind']]=effects.get(n['kind'],0)+n['successful_visits']
            totals.append(dict(index=case['index'],bodies=len(case['functions']),successful_constant_computations=constants,
                successful_duplicate_arithmetic_pairs=pairs,nonconstant_duplicate_pairs=dynamic_pairs,successful_constant_effects=effects))
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=2,controls=1,reconstructed_native_bodies=137,cases=totals,
            setup_seconds=sum(r['seconds'] for r in records),raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),
            records_sha256=sha(work/'records.json'),inputs_sha256=sha(work/'inputs.json'),census_sha256=sha(work/'census.json'),
            source_revision=revision,guest_commands=0,executable_code_publications=0,production_runtime_changes=0,
            performance_measurement=False,scope=census['scope']))
        print(json.dumps(totals),flush=True)
if __name__=='__main__':main()
