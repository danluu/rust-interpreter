"""Retain the passed allocator prefix and execute only its missing controls."""
import os,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='heap-layout-table-focused-02'
OLD='heap-layout-table-focused-01'
read=focus.read

def prefix():
    out=ROOT/'results'/OLD;raw=ROOT/'.work'/OLD
    closure=read(out/'closure.json');summary=read(out/'summary.json');terminal=read(out/'terminal.json')
    assert closure['status']=='closed' and closure['all_hashes_verified']
    assert sha(out/'summary.json')==closure['summary_sha256'] and sha(out/'terminal.json')==closure['terminal_sha256']
    assert summary['status']=='focused-failed' and terminal['returncode']==1
    assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'records.json')==summary['records_sha256']
    plan=read(raw/'plan.json');records=read(raw/'records.json')
    assert len(records)==3 and summary['returncodes']==[0,0,0]
    paths=[out/'closure.json',out/'summary.json',out/'terminal.json',raw/'plan.json',raw/'records.json']
    for key in ['source_bindings','evidence']:
        path=ROOT/closure[key];assert sha(path)==closure[key+'_sha256'];paths.append(path)
    for p,h in read(ROOT/closure['evidence']).items():assert sha(ROOT/p)==h;paths.append(ROOT/p)
    for p,h in plan['frozen'].items():assert sha(ROOT/p)==h,p;paths.append(ROOT/p)
    for row,(label,pattern,count) in zip(records,[('heap-debug','heap::',16),('heap-release','heap::',16),('c-allocator-debug','c_allocator::tests::',3)]):
        assert row['label']==label and row['command'][-1]==pattern and row['returncode']==0
        assert f'test result: ok. {count} passed; 0 failed; 0 ignored;' in (raw/(label+'.stdout')).read_text()
    assert 'AssertionError' in (ROOT/'.work/experiments'/OLD/'command.log').read_text()
    return plan,records,paths

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);prior,reused,paths=prefix()
        target=Path(prior['target'])
        def admission():
            allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
            needed=max(14*1024**3,8*1024**3+2*allocated);free=shutil.disk_usage(ROOT).free
            assert free>=needed,(free,needed)
            return dict(allocated_target_bytes=allocated,required_free_bytes=needed,free_bytes=free)
        initial=admission()
        paths += [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md')]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target),admission=initial,
            expected_commands=2,reused_commands=3,retained_prefix=OLD,original_project_guest_commands=0,
            performance_measurement=False,runtime_diff_files=prior['runtime_diff_files']))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        records=[]
        for label,extra,pattern,count in [('c-allocation-budget-debug',[],'c_allocator::allocation_budget_boundary_tests::',3),
                                         ('c-allocator-release',['--release'],'c_allocator::',6)]:
            require_space(ROOT,8);current=admission()
            command=['cargo','+nightly-2026-09-08','test',*extra,'--locked','--offline','--jobs','2',
                '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode',
                '--features','heap-layout-hash','--lib',pattern]
            start=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                admission=current,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            assert f'test result: ok. {count} passed; 0 failed; 0 ignored;' in out
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,count,'passed',flush=True)
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=2,
            reused_commands=3,retained_prefix=OLD,heap_tests=dict(debug=16,release=16),c_allocator_tests=dict(debug=6,release=6),
            seeded_trace_operations_per_profile=128000,plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            setup_seconds=sum(r['seconds'] for r in records),reused_setup_seconds=sum(r['seconds'] for r in reused),
            adopted_runtime_source=prior['adopted_runtime_source'],runtime_diff_files=prior['runtime_diff_files'],
            original_project_guest_commands=0,native_fixture_execution=False,performance_measurement=False,default_runtime_adoption=False))

def close():
    prefix()
    raw=ROOT/'.work'/RUN;terminal=read(ROOT/'.work/experiments'/RUN/'status.json')
    if terminal['returncode']==0:
        for label,count in [('c-allocation-budget-debug',3),('c-allocator-release',6)]:
            assert f'test result: ok. {count} passed; 0 failed; 0 ignored;' in (raw/(label+'.stdout')).read_text()
    focus.RUN=RUN;focus.close()

if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:assert len(sys.argv)==1;main()
