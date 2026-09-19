"""Qualify immutable request validation and reduced redundant session I/O."""
import json,os,re,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='session-large-function-tier-qualification-01'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated);assert shutil.disk_usage(ROOT).free>=needed
        paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','crates','scripts','tests','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [Path(focus.__file__)]
        for name in ['cross-program-template-parser-screen-incremental-02','session-preparation-observer-parser-01','session-request-costs-qualification-01']:
            prior=ROOT/'results'/name;c=read(prior/'closure.json')
            assert c['status']=='closed' and c['all_hashes_verified'] and sha(prior/'summary.json')==c['summary_sha256']
            paths += [prior/'closure.json',prior/'summary.json']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        sockets=ROOT/'.work/ts';assert sockets.is_dir() and sockets.resolve()==sockets
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target.relative_to(ROOT)),
            required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,expected_commands=4,
            owned_session_processes=24,owned_vm_clients=46,original_project_guest_commands=0,
            native_fixture_execution=True,diagnostic_feature=False,large_function_interpreter_threshold=65536,experimental_feature=True,default_runtime_adoption=False,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        common=['--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target)]
        commands=[('python',[sys.executable,'-B','-m','unittest','discover','-s','tests','-v'])]
        for profile,extra in [('debug',[]),('release',['--release'])]:
            commands.append((profile,['cargo','+nightly-2026-09-08','test',*extra,*common,'--workspace',
                '--features','rust-interp-bytecode/jit-large-function-interpreter']))
        commands.append(('default-vm',['cargo','+nightly-2026-09-08','build','--release',*common,'-p','rust-interp-bytecode','--bin','rust-interp-vm']))
        records=[];totals={};outputs={};write(raw/'records.json',records)
        for label,command in commands:
            require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed
            folder=raw/label;folder.mkdir();child_env=dict(env,RUST_INTERP_SESSION_FIXTURES=str(folder),RUST_INTERP_SOCKET_FIXTURES=str(sockets))
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
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr')),outputs=retained))
            write(raw/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            if label=='python':
                count,=re.findall(r'Ran (\d+) tests? in ',err);skipped,=re.findall(r'^OK(?: \(skipped=(\d+)\))?$',err,re.M)
                assert int(count)==464 and int(skipped or 0)==22
                totals[label]=dict(discovered=int(count),passed=int(count)-int(skipped),skipped=int(skipped))
            elif label in ['debug','release']:
                counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
                assert counts and all(int(f)==0 for _,f,_ in counts)
                passed=sum(int(p) for p,_,_ in counts);ignored=sum(int(i) for _,_,i in counts)
                assert passed==652 and ignored==16,(label,passed,ignored)
                for test in ['size_tier_preserves_current_results_budgets_and_independently_compiled_callees',
                        'shared_validation_preserves_worker_environments_budgets_and_fresh_guests',
                        'shared_validation_cannot_admit_invalid_programs_or_bypass_current_runtime_limits',
                        'socket::vm_client_catalog_declarations_never_replace_server_input_validation']:
                    assert f'test {test} ... ok' in out,test
                totals[label]=dict(passed=passed,ignored=ignored)
                terminals=list(folder.glob('*/terminal.json'));assert len(terminals)==12
                assert sorted(read(p)['returncode'] for p in terminals)==[0]*10+[1]*2
                clients=list(folder.glob('*/client-*.json'));assert len(clients)==23
                assert all(type(read(p)['returncode']) is int for p in clients)
                for name in ['rust-interp-template-session','rust-interp-vm']:
                    binary=raw/(label+'-'+name);shutil.copy2(target/label/name,binary);outputs[str(binary.relative_to(ROOT))]=sha(binary)
            else:
                binary=raw/'default-rust-interp-vm';shutil.copy2(target/'release/rust-interp-vm',binary);outputs[str(binary.relative_to(ROOT))]=sha(binary)
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'passed',totals.get(label),flush=True)
        destination=ROOT/'results'/RUN;destination.mkdir(exist_ok=False)
        write(destination/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),tests=totals,commands=len(records),outputs=outputs,
            setup_seconds=sum(r['seconds'] for r in records),owned_session_processes=24,owned_vm_clients=46,
            original_project_guest_commands=0,native_fixture_execution=True,diagnostic_feature=False,large_function_interpreter_threshold=65536,experimental_feature=True,
            default_runtime_adoption=False,performance_measurement=False))

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()
