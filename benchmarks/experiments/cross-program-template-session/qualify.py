"""Qualify ordinary and experimental template-history API builds."""
import json,os,re,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='cross-program-template-session-api-02'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated);assert shutil.disk_usage(ROOT).free>=needed
        prior=ROOT/'results'/'cross-program-template-suites-01';closed=read(prior/'closure.json')
        assert closed['status']=='closed' and closed['all_hashes_verified'] and sha(prior/'summary.json')==closed['summary_sha256']
        model=read(prior/'summary.json');assert model['status']=='passed' and model['test_invocations']==1824 and model['verified_cache_hits']==16301
        model_plan=ROOT/model['raw']/'plan.json';assert sha(model_plan)==model['plan_sha256']
        paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        for p in [prior/'closure.json',prior/'summary.json',model_plan,
            *(p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']),
            ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py',Path(focus.__file__)]:
            frozen[str(p.relative_to(ROOT))]=sha(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target.relative_to(ROOT)),
            required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,expected_commands=5,
            minimum_tests_per_profile=dict(default=629,feature=633),expected_ignored_per_profile=15,original_project_guest_commands=0,
            native_fixture_execution=True,executable_code_publication=True,experimental_feature=True,default_runtime_adoption=False,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        records=[];totals={};write(raw/'records.json',records)
        names=re.findall(r'^fn (cross_program_template_[a-z_]+)\(', (ROOT/'crates/bytecode/src/jit/cross_program_templates.rs').read_text(),re.M)
        assert len(names)==21
        for label,extra,expected in [('default-debug',[],629),('default-release',['--release'],629),
            ('feature-debug',['--features','rust-interp-bytecode/jit-template-session'],633),
            ('feature-release',['--release','--features','rust-interp-bytecode/jit-template-session'],633),
            ('feature-vm',['--release','--features','jit-template-session'],None)]:
            require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed
            command=['cargo','+nightly-2026-09-08','test' if expected else 'build',*extra,'--locked','--offline','--jobs','2',
                '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target)]
            command+=['--workspace'] if expected else ['-p','rust-interp-bytecode','--bin','rust-interp-vm']
            start=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            if expected:
                counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
                assert counts and all(int(f)==0 for _,f,_ in counts)
                passed=sum(int(p) for p,_,_ in counts);ignored=sum(int(i) for _,_,i in counts)
                assert passed==expected and ignored==15,(passed,ignored,expected)
                for name in names:assert '::'+name+' ... ok' in out,name
                totals[label]=dict(passed=passed,ignored=ignored)
            else:
                shutil.copy2(target/'release/rust-interp-vm',raw/'rust-interp-vm')
                totals[label]=dict(binary_sha256=sha(raw/'rust-interp-vm'))
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,totals[label],flush=True)
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),tests=totals,commands=5,
            outputs={str((raw/'rust-interp-vm').relative_to(ROOT)):sha(raw/'rust-interp-vm')},
            setup_seconds=sum(r['seconds'] for r in records),original_project_guest_commands=0,native_fixture_execution=True,
            executable_code_publication=True,experimental_feature=True,default_runtime_adoption=False,performance_measurement=False))

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()
