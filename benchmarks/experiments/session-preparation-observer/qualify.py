"""Qualify bounded diagnostic preparation phases without changing admission."""
import json,os,re,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='session-preparation-observer-qualification-01'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated);assert shutil.disk_usage(ROOT).free>=needed
        prior=ROOT/'results/session-request-costs-qualification-01'
        closed=read(prior/'closure.json');assert closed['status']=='closed' and closed['all_hashes_verified']
        assert sha(prior/'summary.json')==closed['summary_sha256'];assert read(prior/'summary.json')['status']=='passed'
        paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [prior/'closure.json',prior/'summary.json',Path(focus.__file__),ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        sockets=ROOT/'.work/ts';sockets.mkdir(exist_ok=True);assert sockets.resolve()==sockets
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target.relative_to(ROOT)),
            required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,expected_commands=2,
            tests_per_profile=31,owned_session_processes=24,original_project_guest_commands=0,native_fixture_execution=True,
            executable_code_publication=True,diagnostic_feature=True,experimental_feature=True,default_runtime_adoption=False,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        records=[];totals={};outputs={};write(raw/'records.json',records)
        for profile,extra in [('debug',[]),('release',['--release'])]:
            for group,select,expected in [('integration',['--test','prepared','--test','template_history','--test','template_session','--bin','rust-interp-template-session'],31)]:
                label=profile+'-'+group;require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed
                folder=raw/label;folder.mkdir();child_env=dict(env,RUST_INTERP_SESSION_FIXTURES=str(folder),RUST_INTERP_SOCKET_FIXTURES=str(sockets))
                command=['cargo','+nightly-2026-09-08','test',*extra,'--locked','--offline','--jobs','2',
                    '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode',
                    '--features','jit-preparation-observer',*select]
                start=time.time();child,out,err=capture(command,cwd=ROOT,env=child_env,receipt_path=raw/'active.json',receipt=dict(label=label))
                for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
                retained={str(p.relative_to(ROOT)):sha(p) for p in folder.rglob('*') if p.is_file()}
                # Private credentials remain in their mode-0600 endpoint files.
                # Bind their hashes without copying or printing their contents.
                for receipt in folder.glob('*/child.json'):
                    args=read(receipt)['args']
                    if args[0]=='--serve-socket':
                        endpoint=Path(args[1]);assert endpoint.parent==sockets
                        for p in endpoint.iterdir():
                            if p.is_file():retained[str(p.relative_to(ROOT))]=sha(p)
                record=dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                    stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr')),outputs=retained)
                records.append(record);write(raw/'records.json',records);assert record['returncode']==0,(out+err)[-6000:]
                counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
                assert counts and all(int(f)==int(i)==0 for _,f,i in counts)
                passed=sum(int(p) for p,_,_ in counts);assert passed==expected,(label,passed,expected);totals[label]=passed
                if group=='integration':
                    terminals=list(folder.glob('*/terminal.json'));assert len(terminals)==12
                    assert sorted(read(p)['returncode'] for p in terminals)==[0]*10+[1]*2
                    for name in ['rust-interp-template-session','rust-interp-vm']:
                        binary=raw/(profile+'-'+name);shutil.copy2(target/profile/name,binary)
                        outputs[str(binary.relative_to(ROOT))]=sha(binary)
                    clients=list(folder.glob('*/client-*.json'));assert len(clients)==23
                    assert all(type(read(p)['returncode']) is int for p in clients)
                assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'passed',passed,flush=True)
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),tests=totals,commands=2,outputs=outputs,
            setup_seconds=sum(r['seconds'] for r in records),original_project_guest_commands=0,native_fixture_execution=True,
            owned_session_processes=24,owned_vm_clients=46,expected_startup_or_protocol_rejections=4,diagnostic_feature=True,experimental_feature=True,
            default_runtime_adoption=False,performance_measurement=False))

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()
