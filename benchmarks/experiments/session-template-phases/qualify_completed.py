"""Preserve five completed test commands; correct only diagnostic-off count."""
import json,os,re,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='session-template-phases-qualification-03'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated);assert shutil.disk_usage(ROOT).free>=needed
        frozen={}
        def bind(p,expected=None,decode=True):
            h=sha(p)
            if expected is not None:assert h==expected,p
            frozen[str(p.relative_to(ROOT))]=h
            return read(p) if decode and p.suffix=='.json' else h
        prior=ROOT/'results/session-template-phases-qualification-01';c=bind(prior/'closure.json')
        assert c['status']=='closed' and c['all_hashes_verified']
        s=bind(prior/'summary.json',c['summary_sha256']);terminal=bind(prior/'terminal.json',c['terminal_sha256'])
        assert s['status']=='focused-failed' and s['commands']==5 and s['returncodes']==[0]*5
        assert terminal['returncode']==1
        old=ROOT/s['raw'];plan=bind(old/'plan.json',s['plan_sha256']);previous=bind(old/'records.json',s['records_sha256'])
        for p,h in plan['frozen'].items():
            if p.startswith('crates/') or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:bind(ROOT/p,h)
        expected={'debug-model':22,'debug-integration':33,'release-model':22,'release-integration':33,'feature-off-integration':32}
        assert [r['label'] for r in previous]==list(expected)
        totals={};names={}
        for r in previous:
            label=r['label'];assert r['returncode']==0
            for stream in ['stdout','stderr']:bind(old/(label+'.'+stream),r[stream+'_sha256'])
            out=(old/(label+'.stdout')).read_text()
            counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
            assert counts and all(int(f)==int(i)==0 for _,f,i in counts)
            count=sum(int(n) for n,_,_ in counts);assert count==expected[label];totals[label]=count
            names[label]={x.split(' ... ')[0] for x in out.splitlines() if x.startswith('test ') and x.endswith(' ... ok')}
            for p,h in r['outputs'].items():bind(ROOT/p,h,decode=False)
            if label.endswith('integration'):
                folder=old/label;terminals=list(folder.glob('*/terminal.json'));assert len(terminals)==12
                assert sorted(read(p)['returncode'] for p in terminals)==[0]*10+[1]*2
                clients=list(folder.glob('*/client-*.json'));assert len(clients)==23
                assert all(type(read(p)['returncode']) is int for p in clients)
        assert names['release-integration']-names['feature-off-integration']=={'test preparation_observer_reports_actual_budget_declines_without_changing_execution'}
        assert not names['feature-off-integration']-names['release-integration']
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),Path(focus.__file__),ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=6,
            required_free_bytes=needed,allocated_target_bytes=allocated,reused_commands=5,new_commands=1,
            original_project_guest_commands=0,native_fixture_execution=False,performance_measurement=False))
        records=[]
        for r in previous:
            row=dict(r,reused_from=str((old/'records.json').relative_to(ROOT)))
            for stream in ['stdout','stderr']:(raw/(r['label']+'.'+stream)).write_bytes((old/(r['label']+'.'+stream)).read_bytes())
            records.append(row)
        write(raw/'records.json',records)
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        command=['cargo','+nightly-2026-09-08','build','--release','--locked','--offline','--jobs','2',
            '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode',
            '--features','jit-artifact-digest-reuse,jit-preparation-observer','--bin','rust-interp-vm','--bin','rust-interp-template-session']
        require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed
        start=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label='diagnostic-build'))
        for stream,value in [('stdout',out),('stderr',err)]:(raw/('diagnostic-build.'+stream)).write_text(value)
        records.append(dict(label='diagnostic-build',command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
            stdout_sha256=sha(raw/'diagnostic-build.stdout'),stderr_sha256=sha(raw/'diagnostic-build.stderr')))
        write(raw/'records.json',records);assert child.returncode==0,(out+err)[-4096:]
        outputs={}
        for name in ['rust-interp-vm','rust-interp-template-session']:
            p=raw/('release-'+name);shutil.copy2(target/'release'/name,p);outputs[str(p.relative_to(ROOT))]=sha(p)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),tests=totals,commands=1,reused_commands=5,validated_commands=6,
            outputs=outputs,setup_seconds=records[-1]['seconds'],reused_session_processes=36,reused_vm_clients=69,
            owned_session_processes=0,original_project_guest_commands=0,native_fixture_execution=False,
            diagnostic_feature=True,default_runtime_adoption=False,performance_measurement=False))
        print('All five completed test commands retained; correct feature-off count32; diagnostic binaries bound',flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()
