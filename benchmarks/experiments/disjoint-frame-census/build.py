#!/usr/bin/env python3
"""Qualify and snapshot only the offline census executable."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from build_runtime_candidate import test_counts

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    assert args.run_id in ['disjoint-frame-build-01','disjoint-frame-build-02']
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        paths=[ROOT/p for p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml','scripts/build_runtime_candidate.py','scripts/workflow_io.py','scripts/compare_saved_runtime.py']]
        paths += [p for p in (ROOT/'crates').rglob('*') if p.is_file() and (p.suffix=='.rs' or p.name=='Cargo.toml')]
        paths += [Path(__file__),Path(__file__).with_name('PLAN.md')]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        write(work/'plan.json',dict(owner=str(ROOT),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),frozen=frozen,target=str(target),tests_per_profile=470,ignored_per_profile=1,cargo_workers=2,guest_executions=0))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']}
        env.update(CARGO_TERM_COLOR='never',CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',CARGO_PROFILE_RELEASE_DEBUG='1')
        records=[];counts={}
        for label,action,flags in [('debug','test',[]),('release','test',['--release']),('census','build',['--release'])]:
            require_space(ROOT,8)
            command=['cargo','+nightly-2026-09-08',action,*flags,'--locked','--offline','--jobs','2','--target-dir',str(target)]
            command += ['--workspace'] if action=='test' else ['-p','rust-interp-bytecode','--bin','rust-interp-address-census']
            child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            (work/(label+'.stdout')).write_text(out);(work/(label+'.stderr')).write_text(err)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json',records)
            assert child.returncode==0,err
            if action=='test':
                counts[label]=test_counts(out+err);assert counts[label]==dict(passed=470,ignored=1),counts
            print(label,'PASS',flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        binary=work/'rust-interp-address-census';shutil.copy2(target/'release/rust-interp-address-census',binary)
        output=ROOT/'results'/args.run_id;output.mkdir(exist_ok=False)
        result=dict(status='passed',tests=counts,binary=str(binary.relative_to(ROOT)),binary_sha256=sha(binary),raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),performance_measurement=False,execution_paths_changed=False)
        write(output/'summary.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
