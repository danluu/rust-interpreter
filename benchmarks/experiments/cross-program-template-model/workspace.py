"""Qualify the complete workspace after opt-in lazy preparation integration."""
import json,os,re,shutil,subprocess,sys,time
from pathlib import Path
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='cross-program-template-workspace-01'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated);assert shutil.disk_usage(ROOT).free>=needed
        prior=ROOT/'results/cross-program-template-model-08';closed=read(prior/'closure.json')
        assert closed['status']=='closed' and closed['all_hashes_verified'] and sha(prior/'summary.json')==closed['summary_sha256']
        model=read(prior/'summary.json');assert model['status']=='passed' and model['tests_per_profile']==20
        model_plan=ROOT/model['raw']/'plan.json';assert sha(model_plan)==model['plan_sha256']
        frozen={}
        for p,h in read(model_plan)['frozen'].items():
            if p.startswith('crates/') or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:
                assert sha(ROOT/p)==h;frozen[p]=h
        for p in [prior/'closure.json',prior/'summary.json',model_plan,
            *(p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']),
            ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']:
            frozen[str(p.relative_to(ROOT))]=sha(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target.relative_to(ROOT)),
            required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,expected_commands=2,
            minimum_tests_per_profile=628,expected_ignored_per_profile=15,original_project_guest_commands=0,
            native_fixture_execution=True,executable_code_publication=True,production_runtime_changes=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        records=[];totals={};write(raw/'records.json',records)
        names=re.findall(r'^fn (cross_program_template_[a-z_]+)\(', (ROOT/'crates/bytecode/src/jit/cross_program_templates.rs').read_text(),re.M)
        assert len(names)==20
        for label,extra in [('debug',[]),('release',['--release'])]:
            require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed
            command=['cargo','+nightly-2026-09-08','test',*extra,'--locked','--offline','--jobs','2',
                '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'--workspace']
            start=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
            assert counts and all(int(f)==0 for _,f,_ in counts)
            passed=sum(int(p) for p,_,_ in counts);ignored=sum(int(i) for _,_,i in counts)
            assert passed>=628 and ignored==15,(passed,ignored)
            for name in names:assert '::'+name+' ... ok' in out,name
            totals[label]=dict(passed=passed,ignored=ignored)
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,totals[label],flush=True)
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),tests=totals,commands=2,
            setup_seconds=sum(r['seconds'] for r in records),original_project_guest_commands=0,native_fixture_execution=True,
            executable_code_publication=True,production_runtime_changes=0,performance_measurement=False))

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()
