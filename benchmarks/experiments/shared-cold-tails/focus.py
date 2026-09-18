"""Focused native qualification of the isolated cold-tail candidate."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='shared-cold-tail-focused-01'
BASE='fca687ebac0ea9374a1426addd01169fe707f608'


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed,'insufficient conservative build admission'
        modified=subprocess.check_output(['git','diff','--name-only',BASE,'HEAD','--','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()
        assert sorted(modified)==sorted(['crates/bytecode/src/jit.rs',
            'crates/bytecode/src/jit/shared_fault_tails.rs','crates/bytecode/src/jit/shared_fault_tails_tests.rs']),modified
        paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [ROOT/'scripts'/p for p in ['compare_saved_runtime.py','workflow_io.py']]
        prior=ROOT/'results/shared-cold-tail-census-01'
        closed=json.loads((prior/'closure.json').read_text())
        assert closed['status']=='closed' and closed['all_hashes_verified']
        assert sha(prior/'summary.json')==closed['summary_sha256']
        paths += [prior/'closure.json',prior/'summary.json']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            adopted_rust_base=BASE,modified_rust_inputs=modified,target=str(target.relative_to(ROOT)),
            allocated_target_bytes=allocated,required_free_bytes=needed,minimum_child_gib=8,
            expected_commands=2,tests_per_profile=4,original_project_guest_commands=0,
            native_fixture_execution=True,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        records=[]
        for profile,extra in [('debug',[]),('release',['--release'])]:
            require_space(ROOT,8)
            assert shutil.disk_usage(ROOT).free>=needed,'build admission no longer holds'
            command=['cargo','+nightly-2026-09-08','test',*extra,'--locked','--offline','--jobs','2',
                '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode','--lib','shared_fault_']
            start=time.time()
            child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(stage=profile))
            for stream,value in [('stdout',out),('stderr',err)]: (raw/(profile+'.'+stream)).write_text(value)
            records.append(dict(label=profile,command=command,pid=child.pid,returncode=child.returncode,
                seconds=time.time()-start,stdout_sha256=sha(raw/(profile+'.stdout')),stderr_sha256=sha(raw/(profile+'.stderr'))))
            write(raw/'records.json',records)
            assert child.returncode==0,(out+err)[-5000:]
            assert 'test result: ok. 4 passed; 0 failed; 0 ignored;' in out,out[-3000:]
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(profile,'4 focused cold-tail controls passed',flush=True)
        destination=ROOT/'results'/RUN;destination.mkdir(exist_ok=False)
        write(destination/'summary.json',dict(status='passed',source_revision=revision,
            tests=dict(debug=4,release=4),commands=2,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            setup_seconds=sum(r['seconds'] for r in records),original_project_guest_commands=0,
            production_runtime_changes=1,performance_measurement=False))


if __name__=='__main__': main()
