"""Qualify the typed planner before it is connected to native emission."""
import os,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='branch-budget-typed-planner-01'
BASE='fca687ebac0ea9374a1426addd01169fe707f608'
read=focus.read

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        def admission():
            allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
            needed=max(14*1024**3,8*1024**3+2*allocated);free=shutil.disk_usage(ROOT).free
            assert free>=needed,(free,needed)
            return dict(allocated_target_bytes=allocated,required_free_bytes=needed,free_bytes=free)
        initial=admission()
        prior=ROOT/'results/branch-budget-reservation-01';closed=read(prior/'closure.json')
        assert closed['status']=='closed' and closed['all_hashes_verified']
        assert sha(prior/'summary.json')==closed['summary_sha256']
        runtime_diff=subprocess.check_output(['git','diff','--name-only',BASE,'--','crates'],cwd=ROOT,text=True).splitlines()
        assert runtime_diff==['crates/bytecode/Cargo.toml','crates/bytecode/src/jit.rs','crates/bytecode/src/jit/budget_reservations.rs']
        paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
        paths += [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),Path(focus.__file__),prior/'closure.json',prior/'summary.json']
        paths += [ROOT/'scripts'/name for name in ['compare_saved_runtime.py','workflow_io.py','supervise_experiment.py']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target),admission=initial,
            expected_commands=2,tests_per_profile=6,adopted_runtime_source=BASE,runtime_diff_files=runtime_diff,
            original_project_guest_commands=0,native_fixture_execution=False,emitter_wiring=False,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        records=[]
        for label,extra in [('debug',[]),('release',['--release'])]:
            require_space(ROOT,8);current=admission()
            command=['cargo','+nightly-2026-09-08','test',*extra,'--locked','--offline','--jobs','2',
                '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode',
                '--features','branch-budget-reservation','--lib','jit::budget_reservations::tests::']
            started=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-started,
                admission=current,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            assert 'test result: ok. 6 passed; 0 failed; 0 ignored;' in out
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'six planner controls passed',flush=True)
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=len(records),
            tests=dict(debug=6,release=6),plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            setup_seconds=sum(r['seconds'] for r in records),adopted_runtime_source=BASE,runtime_diff_files=runtime_diff,
            original_project_guest_commands=0,native_fixture_execution=False,emitter_wiring=False,
            performance_measurement=False,default_runtime_adoption=False))

if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()
