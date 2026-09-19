"""Qualify the new composition's cross-program identity and session transport."""
import json,os,re,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='session-runtime-composition-focused-01'
def read(p):return json.loads(p.read_text())
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
        paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','crates','scripts','tests','Cargo.toml','Cargo.lock','rust-toolchain.toml'],text=True).splitlines()]
        paths += list(Path(__file__).parent.glob('*.py'))+list(Path(__file__).parent.glob('*.md'))+[Path(focus.__file__)]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        sockets=ROOT/'.work/ts';assert sockets.is_dir()
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=3,target=str(target),
            admission=initial,original_project_guest_commands=0,native_fixture_execution=True,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        common=['--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target)]
        commands=[('python',[sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_template_session_receipt.py','-v'])]
        for profile,extra in [('debug',[]),('release',['--release'])]:
            commands.append((profile,['cargo','+nightly-2026-09-08','test',*extra,*common,'-p','rust-interp-bytecode',
                '--features','jit-session-duration-order','--lib','--bin','rust-interp-template-session','--test','template_session','session_composition_']))
        records=[];totals={}
        for label,command in commands:
            require_space(ROOT,8);current=admission();folder=raw/label;folder.mkdir()
            child_env=dict(env,RUST_INTERP_SESSION_FIXTURES=str(folder),RUST_INTERP_SOCKET_FIXTURES=str(sockets))
            start=time.time();child,out,err=capture(command,cwd=ROOT,env=child_env,receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            retained={str(p.relative_to(ROOT)):sha(p) for p in folder.rglob('*') if p.is_file()}
            for receipt in folder.glob('*/child.json'):
                args=read(receipt)['args']
                if args[0]=='--serve-socket':
                    endpoint=Path(args[1]);assert endpoint.parent==sockets
                    for p in endpoint.iterdir():
                        if p.is_file():retained[str(p.relative_to(ROOT))]=sha(p)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                admission=current,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr')),outputs=retained))
            write(raw/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            if label=='python':
                assert re.search(r'Ran 8 tests',err) and err.rstrip().endswith('OK');totals[label]=8
            else:
                counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
                assert counts and sum(int(p) for p,_,_ in counts)==6 and all(int(f)==int(i)==0 for _,f,i in counts)
                terminals=list(folder.glob('*/terminal.json'));assert len(terminals)==1 and read(terminals[0])['returncode']==0
                clients=list(folder.glob('*/client-*.json'));assert len(clients)==4
                assert sorted(read(p)['returncode'] for p in clients)==[0,0,0,1]
                totals[label]=6
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'passed',flush=True)
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=len(records),
            tests=totals,plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            setup_seconds=sum(r['seconds'] for r in records),owned_session_processes=2,owned_vm_clients=8,
            original_project_guest_commands=0,native_fixture_execution=True,performance_measurement=False,
            template_key_domain='cross-program-staging-literals-v3',default_runtime_adoption=False))
if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()
