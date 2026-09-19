"""Reuse the closed passing test prefix and run only its unstarted VM build."""
import os,re,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='branch-budget-native-workspace-02'
OLD='branch-budget-native-workspace-01'
read=focus.read

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8);frozen={}
        def bind(p,h=None):
            digest=sha(p)
            if h is not None:assert digest==h,p
            frozen[str(p.relative_to(ROOT))]=digest
            return read(p) if p.suffix=='.json' else digest
        out=ROOT/'results'/OLD;closed=bind(out/'closure.json')
        assert closed['status']=='closed' and closed['all_hashes_verified']
        summary=bind(out/'summary.json',closed['summary_sha256']);terminal=bind(out/'terminal.json',closed['terminal_sha256'])
        assert summary['status']=='focused-failed' and terminal['status']=='finished' and terminal['returncode']==1
        assert terminal['owner']==terminal['cwd']==str(ROOT)
        old=ROOT/summary['raw'];plan=bind(old/'plan.json',summary['plan_sha256']);rows=bind(old/'records.json',summary['records_sha256'])
        assert [(r['label'],r['returncode']) for r in rows]==[('python',0),('debug',0),('release',0)]
        outer=ROOT/'.work/experiments'/OLD
        bind(outer/'command.log',terminal['log_sha256']);bind(outer/'plan.json',terminal['plan_sha256'])
        assert 'assert free>=needed,(free,needed)' in (outer/'command.log').read_text()
        assert not (old/'rust-interp-vm').exists() and plan['expected_commands']==4
        for path,h in plan['frozen'].items():bind(ROOT/path,h)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target';assert plan['target']==str(target)
        common=['--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),
                '--features','rust-interp-bytecode/branch-budget-reservation']
        totals={}
        for row in rows:
            label=row['label']
            for stream in ['stdout','stderr']:bind(old/(label+'.'+stream),row[stream+'_sha256'])
            stdout=(old/(label+'.stdout')).read_text();stderr=(old/(label+'.stderr')).read_text()
            if label=='python':
                expected=[row['command'][0],'-B','-m','unittest','discover','-s','tests','-v']
                assert Path(row['command'][0]).resolve()==Path(sys.executable).resolve()
                count,=re.findall(r'Ran (\d+) tests? in ',stderr);skipped,=re.findall(r'^OK(?: \(skipped=(\d+)\))?$',stderr,re.M)
                assert int(count)==468 and int(skipped)==22
                totals[label]=dict(discovered=468,passed=446,skipped=22)
            else:
                expected=['cargo','+nightly-2026-09-08','test',*(['--release'] if label=='release' else []),*common,'--workspace']
                counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',stdout)
                assert counts and all(int(f)==0 for _,f,_ in counts)
                totals[label]=dict(passed=sum(int(p) for p,_,_ in counts),ignored=sum(int(i) for _,_,i in counts))
                assert totals[label]==dict(passed=622,ignored=13)
                for test in ['branch_reservation_external_entries_refund_unequal_paths_and_preserve_abi',
                    'branch_reservation_faults_refund_only_the_unentered_suffix',
                    'branch_reservation_guard_declines_never_refund_unreserved_steps']:
                    assert test+' ... ok' in stdout,test
            assert row['command']==expected
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),Path(focus.__file__)]:bind(p)
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated);free=shutil.disk_usage(ROOT).free;assert free>=needed,(free,needed)
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,controller_command=[sys.executable,*sys.orig_argv[1:]],
            expected_commands=1,reused_commands=3,original_workspace_prefix=OLD,target=str(target),
            admission=dict(allocated_target_bytes=allocated,required_free_bytes=needed,free_bytes=free),
            original_project_guest_commands=0,native_fixture_execution=False,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        command=['cargo','+nightly-2026-09-08','build','--release',*common,'-p','rust-interp-bytecode','--bin','rust-interp-vm']
        started=time.time();child,stdout,stderr=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label='vm'))
        for stream,value in [('stdout',stdout),('stderr',stderr)]:(raw/('vm.'+stream)).write_text(value)
        records=[dict(label='vm',command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-started,
            stdout_sha256=sha(raw/'vm.stdout'),stderr_sha256=sha(raw/'vm.stderr'))]
        write(raw/'records.json',records);assert child.returncode==0,(stdout+stderr)[-6000:]
        require_space(ROOT,8);binary=raw/'rust-interp-vm';shutil.copy2(target/'release/rust-interp-vm',binary)
        outputs={str(binary.relative_to(ROOT)):sha(binary)};assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=1,reused_commands=3,
            original_workspace_prefix=OLD,tests=totals,outputs=outputs,plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            setup_seconds=sum(r['seconds'] for r in records),reused_setup_seconds=sum(r['seconds'] for r in rows),
            adopted_runtime_source=plan['adopted_runtime_source'],runtime_diff_files=plan['runtime_diff_files'],
            original_project_guest_commands=0,native_fixture_execution=False,reused_native_fixture_execution=True,
            performance_measurement=False,branch_budget_reservation=True,cargo_features=['rust-interp-bytecode/branch-budget-reservation'],
            experimental_template_session=False,default_runtime_adoption=False))
        print('Retained feature-enabled VM; three closed passing test commands reused',flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()
