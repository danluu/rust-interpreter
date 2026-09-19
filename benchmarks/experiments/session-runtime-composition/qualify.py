"""Qualify the actual composed sources; all workspace and Python tests are fresh."""
import json,os,re,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='session-runtime-composition-qualification-02'
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
        focused=ROOT/'results/session-runtime-composition-focused-01';closure=read(focused/'closure.json');proof=read(focused/'summary.json')
        assert closure['status']=='closed' and closure['all_hashes_verified'] and sha(focused/'summary.json')==closure['summary_sha256']
        assert proof['status']=='passed' and proof['tests']==dict(python=8,debug=6,release=6)
        focused_plan=ROOT/proof['raw']/'plan.json';assert sha(focused_plan)==proof['plan_sha256']
        for p,h in read(focused_plan)['frozen'].items():
            # This module was not imported/executed by the focused eight-test
            # command. Its updated launcher contract runs fresh below.
            if p=='tests/test_interpreter_build_metrics.py':continue
            if p.startswith(('crates/','scripts/','tests/')) or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:assert sha(ROOT/p)==h,p
        paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','crates','scripts','tests','Cargo.toml','Cargo.lock','rust-toolchain.toml'],text=True).splitlines()]
        paths += list(Path(__file__).parent.glob('*.py'))+list(Path(__file__).parent.glob('*.md'))
        paths += [Path(focus.__file__),focused/'closure.json',focused/'summary.json',focused_plan]
        failed=ROOT/'results/session-runtime-composition-qualification-01'
        previous=read(failed/'summary.json');previous_closure=read(failed/'closure.json')
        assert previous_closure['status']=='closed' and previous_closure['all_hashes_verified']
        assert sha(failed/'summary.json')==previous_closure['summary_sha256']
        assert previous['status']=='focused-failed' and previous['commands']==1 and previous['returncodes']==[1]
        paths += [failed/'summary.json',failed/'closure.json',failed/'terminal.json']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        sockets=ROOT/'.work/ts';assert sockets.is_dir()
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target),admission=initial,
            expected_commands=7,owned_session_processes=52,owned_vm_clients=108,
            original_project_guest_commands=0,native_fixture_execution=True,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        common=['--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target)]
        commands=[('python',[sys.executable,'-B','-m','unittest','discover','-s','tests','-v'])]
        for label,extra in [('debug',[]),('release',['--release'])]:
            commands.append((label,['cargo','+nightly-2026-09-08','test',*extra,*common,'--workspace','--features','rust-interp-bytecode/jit-session-duration-order']))
        commands.append(('diagnostic',['cargo','+nightly-2026-09-08','test','--release',*common,'-p','rust-interp-bytecode',
            '--features','jit-session-duration-order,jit-preparation-observer','--test','prepared','--test','template_history','--test','template_session','--bin','rust-interp-template-session']))
        commands.append(('feature-off',['cargo','+nightly-2026-09-08','test','--release',*common,'-p','rust-interp-bytecode',
            '--features','jit-parameterized-literals','--test','template_session']))
        commands.append(('ordinary-model',['cargo','+nightly-2026-09-08','test','--release',*common,'-p','rust-interp-bytecode',
            '--features','jit-parameterized-literals','--lib','jit::cross_program_templates::tests::']))
        commands.append(('default-vm',['cargo','+nightly-2026-09-08','build','--release',*common,'-p','rust-interp-bytecode','--bin','rust-interp-vm']))
        records=[];totals={};outputs={}
        for label,command in commands:
            require_space(ROOT,8);current=admission();folder=raw/label;folder.mkdir()
            child_env=dict(env,RUST_INTERP_SESSION_FIXTURES=str(folder),RUST_INTERP_SOCKET_FIXTURES=str(sockets))
            started=time.time();child,out,err=capture(command,cwd=ROOT,env=child_env,receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            retained={str(p.relative_to(ROOT)):sha(p) for p in folder.rglob('*') if p.is_file()}
            for receipt in folder.glob('*/child.json'):
                args=read(receipt)['args']
                if args[0]=='--serve-socket':
                    endpoint=Path(args[1]);assert endpoint.parent==sockets
                    for p in endpoint.iterdir():
                        if p.is_file():retained[str(p.relative_to(ROOT))]=sha(p)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-started,
                admission=current,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr')),outputs=retained))
            write(raw/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            if label=='python':
                count,=re.findall(r'Ran (\d+) tests? in ',err);skipped,=re.findall(r'^OK(?: \(skipped=(\d+)\))?$',err,re.M)
                assert int(count)>=468 and int(skipped or 0)==22
                totals[label]=dict(discovered=int(count),passed=int(count)-int(skipped),skipped=int(skipped))
                assert 'test_session_composition_' in err
            elif label!='default-vm':
                counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
                assert counts and all(int(f)==0 for _,f,_ in counts)
                totals[label]=dict(passed=sum(int(p) for p,_,_ in counts),ignored=sum(int(i) for _,_,i in counts))
                if label in ['debug','release']:
                    assert totals[label]['passed']>=679 and totals[label]['ignored']>=17
                    for name in ['composed_indirect_readonly_and_dead_branch_preserve_full_memory',
                        'composed_indirect_readonly_all_budgets_and_resource_tails_match',
                        'session_composition_verified_history_preserves_readonly_indirect_memory_and_faults',
                        'session_composition_keys_bind_changed_indirect_signature_ordinals_and_missing_targets',
                        'session_composition_dynamic_layouts_reuse_exact_staging_with_current_owner_tables',
                        'session_composition_option_and_spill_model_changes_cannot_alias_history',
                        'native_readonly_heap_free_context_never_uses_uninitialized_heap_registers',
                        'native_readonly_result_can_alias_its_external_source_after_private_reads',
                        'cross_program_template_callee_initial_zero_requirement_is_an_emission_input',
                        'successor_flush_preserves_wide_values_live_through_both_join_edges']:
                        assert name+' ... ok' in out,name
                elif label=='diagnostic':assert totals[label]==dict(passed=41,ignored=0)
                elif label=='feature-off':assert totals[label]==dict(passed=11,ignored=0)
                else:assert totals[label]==dict(passed=34,ignored=0)
                if label!='ordinary-model':
                    assert 'session_composition_client_transports_and_reports_explicit_indirect_options ... ok' in out
                    terminals=list(folder.glob('*/terminal.json'));assert len(terminals)==13
                    assert sorted(read(p)['returncode'] for p in terminals)==[0]*11+[1]*2
                    clients=list(folder.glob('*/client-*.json'));assert len(clients)==27
                    assert all(type(read(p)['returncode']) is int for p in clients)
                    for name in ['rust-interp-template-session','rust-interp-vm']:
                        binary=raw/(label+'-'+name);shutil.copy2(target/('debug' if label=='debug' else 'release')/name,binary)
                        outputs[str(binary.relative_to(ROOT))]=sha(binary)
            else:
                binary=raw/'default-rust-interp-vm';shutil.copy2(target/'release/rust-interp-vm',binary);outputs[str(binary.relative_to(ROOT))]=sha(binary)
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'passed',totals.get(label),flush=True)
        assert totals['debug']==totals['release']
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=len(records),reused_commands=0,
            tests=totals,outputs=outputs,plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            setup_seconds=sum(r['seconds'] for r in records),owned_session_processes=52,owned_vm_clients=108,
            original_project_guest_commands=0,native_fixture_execution=True,performance_measurement=False,
            template_key_domain='cross-program-staging-literals-v3',parameterized_literals=True,shared_literal_keys=False,
            buffered_template_keys=False,duration_order=True,indirect_calls_supported=True,
            readonly_scalar_leaves=True,successor_only_spills=True,large_function_interpreter_threshold=65536,
            artifact_digest_reuse=True,default_runtime_adoption=False))
if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()
