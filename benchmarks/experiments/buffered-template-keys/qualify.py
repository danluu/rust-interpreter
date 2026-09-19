"""Qualify bounded buffering with identical template key bytes and limits."""
import json,os,re,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='buffered-template-keys-qualification-01'
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
        for name in ['session-template-phases-qualification-03','session-template-phases-parser-01','session-artifact-digest-full-costs-01']:
            prior=ROOT/'results'/name;c=read(prior/'closure.json')
            assert c['status']=='closed' and c['all_hashes_verified'] and sha(prior/'summary.json')==c['summary_sha256']
            paths += [prior/'closure.json',prior/'summary.json']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        prior=ROOT/'results/session-large-function-tier-qualification-03';c=read(prior/'closure.json')
        assert c['status']=='closed' and c['all_hashes_verified'] and sha(prior/'summary.json')==c['summary_sha256']
        previous=read(prior/'summary.json');old_raw=ROOT/previous['raw'];old_plan=read(old_raw/'plan.json')
        assert sha(old_raw/'plan.json')==previous['plan_sha256'] and sha(old_raw/'records.json')==previous['records_sha256']
        previous_python=read(old_raw/'records.json')[0]
        assert previous_python['label']=='python' and previous_python['returncode']==0
        for p,h in old_plan['frozen'].items():
            if p.startswith(('scripts/','tests/')):assert sha(ROOT/p)==h,p
        for stream in ['stdout','stderr']:assert sha(old_raw/('python.'+stream))==previous_python[stream+'_sha256']
        for p in [prior/'summary.json',prior/'closure.json',old_raw/'plan.json',old_raw/'records.json',old_raw/'python.stdout',old_raw/'python.stderr']:
            frozen[str(p.relative_to(ROOT))]=sha(p)
        red=ROOT/'results/template-callee-initialization-reproduction-01';c=read(red/'closure.json')
        assert c['status']=='closed' and c['all_hashes_verified'] and c['expected_failures_reproduced']==2
        assert sha(red/'summary.json')==c['summary_sha256']
        for p in [red/'closure.json',red/'summary.json']:frozen[str(p.relative_to(ROOT))]=sha(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        sockets=ROOT/'.work/ts';assert sockets.is_dir() and sockets.resolve()==sockets
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target.relative_to(ROOT)),
            required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,expected_commands=7,
            owned_session_processes=48,owned_vm_clients=92,original_project_guest_commands=0,
            native_fixture_execution=True,experimental_feature=True,default_runtime_adoption=False,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        common=['--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target)]
        commands=[('python',[sys.executable,'-B','-m','unittest','discover','-s','tests','-v'])]
        for profile,extra in [('debug',[]),('release',['--release'])]:
            commands.append((profile,['cargo','+nightly-2026-09-08','test',*extra,*common,'--workspace',
                '--features','rust-interp-bytecode/jit-buffered-template-keys']))
        commands.append(('diagnostic',['cargo','+nightly-2026-09-08','test','--release',*common,'-p','rust-interp-bytecode',
            '--features','jit-buffered-template-keys,jit-preparation-observer',
            '--test','prepared','--test','template_history','--test','template_session','--bin','rust-interp-template-session']))
        commands.append(('feature-off',['cargo','+nightly-2026-09-08','test','--release',*common,'-p','rust-interp-bytecode',
            '--features','jit-artifact-digest-reuse','--test','template_session']))
        commands.append(('unbuffered-model',['cargo','+nightly-2026-09-08','test','--release',*common,'-p','rust-interp-bytecode',
            '--features','jit-artifact-digest-reuse','--lib','jit::cross_program_templates::tests::']))
        commands.append(('default-vm',['cargo','+nightly-2026-09-08','build','--release',*common,'-p','rust-interp-bytecode','--bin','rust-interp-vm']))
        records=[];totals={};outputs={};write(raw/'records.json',records)
        for label,command in commands:
            require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed
            folder=raw/label;folder.mkdir();child_env=dict(env,RUST_INTERP_SESSION_FIXTURES=str(folder),RUST_INTERP_SOCKET_FIXTURES=str(sockets))
            if label=='python':
                assert command==previous_python['command']
                out=(old_raw/'python.stdout').read_text();err=(old_raw/'python.stderr').read_text()
                from types import SimpleNamespace
                child=SimpleNamespace(pid=previous_python['pid'],returncode=0);elapsed=previous_python['seconds']
            else:
                start=time.time();child,out,err=capture(command,cwd=ROOT,env=child_env,receipt_path=raw/'active.json',receipt=dict(label=label))
                elapsed=time.time()-start
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            retained={str(p.relative_to(ROOT)):sha(p) for p in folder.rglob('*') if p.is_file()}
            for receipt in folder.glob('*/child.json'):
                args=read(receipt)['args']
                if args[0]=='--serve-socket':
                    endpoint=Path(args[1]);assert endpoint.parent==sockets
                    for p in endpoint.iterdir():
                        if p.is_file():retained[str(p.relative_to(ROOT))]=sha(p)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=elapsed,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr')),outputs=retained))
            if label=='python':records[-1]['reused_from']=str((old_raw/'records.json').relative_to(ROOT))
            write(raw/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            if label=='python':
                count,=re.findall(r'Ran (\d+) tests? in ',err);skipped,=re.findall(r'^OK(?: \(skipped=(\d+)\))?$',err,re.M)
                assert int(count)==464 and int(skipped or 0)==22
                totals[label]=dict(discovered=int(count),passed=int(count)-int(skipped),skipped=int(skipped))
            elif label=='unbuffered-model':
                assert 'test result: ok. 24 passed; 0 failed; 0 ignored;' in out
                for test in ['key_hash_preserves_streamed_bytes_and_flush_boundaries','key_hash_rejects_oversize_writes_without_accepting_their_prefix']:
                    assert f'test jit::cross_program_templates::tests::{test} ... ok' in out,test
                totals[label]=dict(passed=24,ignored=0)
            elif label in ['debug','release','diagnostic','feature-off']:
                counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
                assert counts and all(int(f)==0 for _,f,_ in counts)
                passed=sum(int(p) for p,_,_ in counts);ignored=sum(int(i) for _,_,i in counts)
                assert (passed,ignored)==((10,0) if label=='feature-off' else (33,0) if label=='diagnostic' else (658,16)),(label,passed,ignored)
                if label!='feature-off':assert 'test changed_callee_initial_registers_cannot_reuse_stale_caller_templates ... ok' in out
                if label in ['debug','release']:assert 'test jit::cross_program_templates::tests::cross_program_template_callee_initial_zero_requirement_is_an_emission_input ... ok' in out
                for test in ['shared_validation_preserves_worker_environments_budgets_and_fresh_guests',
                        'shared_validation_cannot_admit_invalid_programs_or_bypass_current_runtime_limits',
                        'socket::vm_client_catalog_declarations_never_replace_server_input_validation']:
                    if label!='feature-off' or test.startswith('socket::'):assert f'test {test} ... ok' in out,test
                if label in ['debug','release']:
                    for test in ['hashed_artifact_catalog_binds_actual_owned_bytes_across_body_edits','hashed_artifact_catalog_retains_header_and_entry_validation']:
                        assert f'test entry_catalog::tests::{test} ... ok' in out,test
                    for test in ['key_hash_preserves_streamed_bytes_and_flush_boundaries','key_hash_rejects_oversize_writes_without_accepting_their_prefix']:
                        assert f'test jit::cross_program_templates::tests::{test} ... ok' in out,test
                totals[label]=dict(passed=passed,ignored=ignored)
                terminals=list(folder.glob('*/terminal.json'));assert len(terminals)==12
                assert sorted(read(p)['returncode'] for p in terminals)==[0]*10+[1]*2
                clients=list(folder.glob('*/client-*.json'));assert len(clients)==23
                assert all(type(read(p)['returncode']) is int for p in clients)
                for name in ['rust-interp-template-session','rust-interp-vm']:
                    binary=raw/(label+'-'+name);shutil.copy2(target/('release' if label in ['diagnostic','feature-off'] else label)/name,binary);outputs[str(binary.relative_to(ROOT))]=sha(binary)
            else:
                binary=raw/'default-rust-interp-vm';shutil.copy2(target/'release/rust-interp-vm',binary);outputs[str(binary.relative_to(ROOT))]=sha(binary)
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'passed',totals.get(label),flush=True)
        destination=ROOT/'results'/RUN;destination.mkdir(exist_ok=False)
        write(destination/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),tests=totals,commands=6,reused_commands=1,validated_commands=len(records),outputs=outputs,
            setup_seconds=sum(r['seconds'] for r in records if 'reused_from' not in r),owned_session_processes=48,owned_vm_clients=92,
            original_project_guest_commands=0,native_fixture_execution=True,experimental_feature=True,
            buffered_template_keys=True,artifact_digest_reuse=True,template_key_version=3,large_function_interpreter_threshold=65536,diagnostic_feature=False,
            default_runtime_adoption=False,performance_measurement=False))

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()
