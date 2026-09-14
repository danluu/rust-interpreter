"""Qualify direct aggregate native emission and the shared Output ABI."""
import json,os,re,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
NAME='scalar-aggregate-abi-01'
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed,'insufficient conservative build admission'
        paths=[*Path(__file__).parent.glob('*.py'),Path(__file__).with_name('PLAN.md')]
        paths += [ROOT/p for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],text=True).splitlines()]
        paths += [ROOT/'scripts'/p for p in ['compare_saved_runtime.py','workflow_io.py','interpreter.py']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,target=str(target.relative_to(ROOT)),
            required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,expected_commands=4,
            native_controls_per_profile=6,minimum_library_controls=360,guest_commands=0,new_direct_native_publications=True,
            production_selection_changed=False,production_shared_output_layout_changed=True,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
             and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',
            CARGO_TERM_COLOR='never',RUST_TEST_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
        base=['cargo','+nightly-2026-09-08','test','--lib','-p','rust-interp-bytecode','--locked','--offline','--jobs','2',
              '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target)]
        records=[]
        for label,extra,focused in [('native-debug',[],True),('native-release',['--release'],True),
                                    ('library-debug',[],False),('library-release',['--release'],False)]:
            assert shutil.disk_usage(ROOT).free>=needed;require_space(ROOT,8)
            cmd=[*base,*extra,*(['scalar_ir::native_leaf::aggregate_tests::'] if focused else [])];start=time.time()
            child,out,err=capture(cmd,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            for stream,payload in [('stdout',out),('stderr',err)]:(work/(label+'.'+stream)).write_text(payload)
            counts=re.search(r'test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;',out)
            records.append(dict(label=label,command=cmd,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                passed=int(counts[1]) if counts else None,ignored=int(counts[2]) if counts else None,
                stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))));write(work/'records.json',records)
            assert child.returncode==0 and counts,(out+err)[-6500:]
            assert (int(counts[1])==6 and int(counts[2])==0) if focused else int(counts[1])>=360
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,counts[0],flush=True)
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=4,native_controls_per_profile=6,
            library_counts=[dict(label=r['label'],passed=r['passed'],ignored=r['ignored']) for r in records if r['label'].startswith('library-')],
            setup_seconds=sum(r['seconds'] for r in records),raw=str(work.relative_to(ROOT)),source_revision=revision,
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),guest_commands=0,
            new_direct_native_publications=True,production_selection_changed=False,production_shared_output_layout_changed=True,
            performance_measurement=False,scope='Synthetic native aggregate controls and full bytecode suite; wide production Call selection remains disabled. No original-project guest timing.'))
if __name__=='__main__':main()
