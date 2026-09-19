"""Qualify bounded register map/set models without changing the emitter."""
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='emitter-register-workspace-model-02'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated);assert shutil.disk_usage(ROOT).free>=needed
        paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [ROOT/'scripts'/p for p in ['compare_saved_runtime.py','workflow_io.py']]
        for run in ['preparation-phase-workloads-refined-01']:
            prior=ROOT/'results'/run;closed=read(prior/'closure.json')
            assert closed['status']=='closed' and closed['all_hashes_verified'] and sha(prior/'summary.json')==closed['summary_sha256']
            paths += [prior/'closure.json',prior/'summary.json']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target.relative_to(ROOT)),
            required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,expected_commands=2,
            tests_per_profile=5,original_project_guest_commands=0,native_fixture_execution=False,
            executable_code_publication=False,production_runtime_changes=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        records=[];write(raw/'records.json',records)
        for label,extra in [('debug',[]),('release',['--release'])]:
            require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed
            command=['cargo','+nightly-2026-09-08','test',*extra,'--locked','--offline','--jobs','2',
                '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode',
                '--lib','jit::register_workspace::tests::']
            start=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(stage=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            assert 'test result: ok. 5 passed; 0 failed; 0 ignored;' in out
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'passed',flush=True)
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),tests_per_profile=5,commands=2,
            setup_seconds=sum(r['seconds'] for r in records),original_project_guest_commands=0,native_fixture_execution=False,
            executable_code_publication=False,production_runtime_changes=0,performance_measurement=False))

def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
        plan=read(raw/'plan.json');records=read(raw/'records.json');terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
        assert terminal['command'][1:]==plan['controller_command'][1:]
        assert Path(terminal['command'][0]).resolve()==Path(plan['controller_command'][0]).resolve()
        assert terminal['plan_sha256']==sha(outer/'plan.json') and terminal['log_sha256']==sha(outer/'command.log')
        bindings={};evidence={}
        for p,h in plan['frozen'].items():
            assert sha(ROOT/p)==h
            if p.startswith(('.work/','results/')):evidence[p]=h
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==h;bindings[p]=dict(revision=plan['source_revision'],sha256=h)
        for r in records:
            for stream in ['stdout','stderr']:
                p=raw/(r['label']+'.'+stream);assert sha(p)==r[stream+'_sha256'];evidence[str(p.relative_to(ROOT))]=sha(p)
        out.mkdir(exist_ok=True);assert not (out/'closure.json').exists()
        if terminal['returncode']==0:
            summary=read(out/'summary.json');assert summary['status']=='passed' and len(records)==2
            assert all(r['returncode']==0 for r in records)
            assert summary['plan_sha256']==sha(raw/'plan.json') and summary['records_sha256']==sha(raw/'records.json')
        else:
            assert not (out/'summary.json').exists()
            write(out/'summary.json',dict(status='focused-failed',source_revision=plan['source_revision'],raw=str(raw.relative_to(ROOT)),
                commands=len(records),returncodes=[r['returncode'] for r in records],plan_sha256=sha(raw/'plan.json'),
                records_sha256=sha(raw/'records.json'),original_project_guest_commands=0,performance_measurement=False))
        for p in [raw/'plan.json',raw/'records.json',outer/'status.json',outer/'plan.json',outer/'command.log']:evidence[str(p.relative_to(ROOT))]=sha(p)
        write(raw/'source-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'closure.json',dict(status='closed',all_hashes_verified=True,source_files=len(bindings),frozen_inputs=len(plan['frozen']),
            evidence_files=len(evidence),summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
            source_bindings=str((raw/'source-bindings.json').relative_to(ROOT)),source_bindings_sha256=sha(raw/'source-bindings.json'),
            evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),original_project_guest_commands=0))
        print('Closed emitter register workspace models; terminal',terminal['returncode'],flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:
        assert len(sys.argv)==1
        main()
