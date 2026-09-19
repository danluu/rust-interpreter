"""Qualify the exact-key heap layout table across the whole workspace."""
import json,os,re,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='heap-layout-workspace-01'
BASE='fca687ebac0ea9374a1426addd01169fe707f608'
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
        focused=ROOT/'results/heap-layout-table-focused-03'
        closure=read(focused/'closure.json');proof=read(focused/'summary.json')
        assert closure['status']=='closed' and closure['all_hashes_verified']
        assert sha(focused/'summary.json')==closure['summary_sha256']
        assert proof['status']=='passed' and proof['heap_tests']==dict(debug=16,release=16) and proof['c_allocator_tests']==dict(debug=6,release=6)
        focused_plan=ROOT/proof['raw']/'plan.json';assert sha(focused_plan)==proof['plan_sha256']
        for p,h in read(focused_plan)['frozen'].items():
            if p.startswith(('crates/','scripts/','tests/')) or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:assert sha(ROOT/p)==h,p
        runtime_diff=subprocess.check_output(['git','diff','--name-only',BASE,'--','crates'],cwd=ROOT,text=True).splitlines()
        assert runtime_diff==['crates/bytecode/Cargo.toml','crates/bytecode/src/heap.rs','crates/bytecode/src/heap_layout_reference.rs','crates/bytecode/src/heap_layout_tests.rs']
        paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','crates','scripts','tests','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
        paths += [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),Path(focus.__file__),focused/'closure.json',focused/'summary.json',focused_plan]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target),admission=initial,
            expected_commands=4,adopted_runtime_source=BASE,runtime_diff_files=runtime_diff,
            original_project_guest_commands=0,native_fixture_execution=True,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        common=['--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),
            '--features','rust-interp-bytecode/heap-layout-hash']
        commands=[('python',[sys.executable,'-B','-m','unittest','discover','-s','tests','-v'])]
        for label,extra in [('debug',[]),('release',['--release'])]:
            commands.append((label,['cargo','+nightly-2026-09-08','test',*extra,*common,'--workspace']))
        commands.append(('vm',['cargo','+nightly-2026-09-08','build','--release',*common,'-p','rust-interp-bytecode','--bin','rust-interp-vm']))
        records=[];totals={};outputs={}
        for label,command in commands:
            require_space(ROOT,8);current=admission()
            started=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-started,
                admission=current,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            if label=='python':
                count,=re.findall(r'Ran (\d+) tests? in ',err);skipped,=re.findall(r'^OK(?: \(skipped=(\d+)\))?$',err,re.M)
                assert int(count)==468 and int(skipped or 0)==22
                totals[label]=dict(discovered=int(count),passed=int(count)-int(skipped),skipped=int(skipped))
            elif label in ['debug','release']:
                counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
                assert counts and all(int(f)==0 for _,f,_ in counts)
                totals[label]=dict(passed=sum(int(p) for p,_,_ in counts),ignored=sum(int(i) for _,_,i in counts))
                assert totals[label]==dict(passed=618,ignored=13),totals[label]
                for name in ['first_fit_alignment_and_coalescing_ignore_hash_iteration_order',
                    'seeded_allocator_traces_match_all_addresses_bytes_errors_and_limits',
                    'invalid_layouts_and_failed_growth_preserve_original_allocation',
                    'scratch_memory_overlapping_reused_copy_invalidates_its_original_source',
                    'native_scalar_2187_copy_cases_in_both_profile_modes',
                    'native_scalar_call_commits_every_profile_word_and_exact_budget_boundary']:
                    assert name+' ... ok' in out,name
            else:
                binary=raw/'rust-interp-vm';shutil.copy2(target/'release/rust-interp-vm',binary)
                outputs[str(binary.relative_to(ROOT))]=sha(binary)
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'passed',totals.get(label),flush=True)
        assert totals['debug']==totals['release']
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=len(records),reused_commands=0,
            tests=totals,outputs=outputs,plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            setup_seconds=sum(r['seconds'] for r in records),adopted_runtime_source=BASE,runtime_diff_files=runtime_diff,
            original_project_guest_commands=0,native_fixture_execution=True,performance_measurement=False,
            heap_layout_hash=True,cargo_features=["rust-interp-bytecode/heap-layout-hash"],experimental_template_session=False,default_runtime_adoption=False))
if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()
