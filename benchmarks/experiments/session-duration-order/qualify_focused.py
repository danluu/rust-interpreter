"""Qualify literal parameters, exact restoration and live current-value semantics."""
import json,os,shutil,subprocess,sys,time
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus as closure_support
ROOT=closure_support.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='session-duration-order-focused-01'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated);assert shutil.disk_usage(ROOT).free>=needed
        frozen={}
        def bind(p,h=None):
            actual=sha(p)
            if h is not None:assert actual==h,p
            frozen[str(p.relative_to(ROOT))]=actual
            return read(p) if p.suffix=='.json' else actual
        def closed(name):
            p=ROOT/'results'/name;c=bind(p/'closure.json');assert c['status']=='closed' and c['all_hashes_verified']
            s=bind(p/'summary.json',c['summary_sha256']);t=bind(p/'terminal.json',c['terminal_sha256'])
            assert s['status']=='passed' and t['status']=='finished' and t['returncode']==0 and t['owner']==str(ROOT)
            return s
        previous=closed('parameterized-literals-qualification-02');assert previous['tests']['release']==dict(passed=673,ignored=17)
        census=closed('session-worker-tail-census-01');assert census['reports']==10 and census['test_intervals']==1140
        paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [Path(closure_support.__file__),ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']
        for p in paths:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=3,
            target=str(target),allocated_target_bytes=allocated,required_free_bytes=needed,
            original_project_guest_commands=0,native_fixture_execution=True,executable_code_publication=True,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        records=[]
        for label,extra,feature,expected in [
            ('debug',[],'jit-session-duration-order',10),
            ('release',['--release'],'jit-session-duration-order',10),
            ('feature-off',['--release'],'jit-parameterized-literals',4)]:
            require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed
            command=['cargo','+nightly-2026-09-08','test',*extra,'--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),
                '--target-dir',str(target),'-p','rust-interp-bytecode','--features',feature,'--bin','rust-interp-template-session']
            start=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))));write(raw/'records.json',records)
            assert child.returncode==0 and f'test result: ok. {expected} passed; 0 failed; 0 ignored;' in out,(out+err)[-6000:]
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'passed',flush=True)
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=3,
            controls_per_profile=10,feature_off_controls=4,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            original_project_guest_commands=0,native_fixture_execution=True,performance_measurement=False,
            parameterized_literals=True,shared_literal_keys=False,duration_order=True,default_runtime_adoption=False))
if __name__=='__main__':
    if sys.argv[1:]==['--close']:closure_support.RUN=RUN;closure_support.close()
    else:assert len(sys.argv)==1;main()
