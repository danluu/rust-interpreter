"""Qualify launcher contracts and install the closed feature VM with adopted tools."""
import hashlib,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from interpreter import installed_tools
RUN='cross-program-template-session-launcher-01'
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated);assert shutil.disk_usage(ROOT).free>=needed
        previous=ROOT/'results/cross-program-template-session-client-01';closed=read(previous/'closure.json')
        assert closed['status']=='closed' and closed['all_hashes_verified'] and sha(previous/'summary.json')==closed['summary_sha256']
        client=read(previous/'summary.json');assert client['status']=='passed'
        old_plan=ROOT/client['raw']/'plan.json';assert sha(old_plan)==client['plan_sha256']
        for p,h in read(old_plan)['frozen'].items():
            if p.startswith('crates/') or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:assert sha(ROOT/p)==h
        vm=ROOT/client['raw']/'release-rust-interp-vm';server=ROOT/client['raw']/'release-rust-interp-template-session'
        for p in [vm,server]:assert sha(p)==client['outputs'][str(p.relative_to(ROOT))]
        integration_path=ROOT/'results/scratch-scalar-main-qualification-01/summary.json';integration=read(integration_path)
        assert integration['status']=='passed' and integration['tool_key']==BASELINE
        retained,key=installed_tools(BASELINE);assert key==BASELINE
        assert all(sha(retained/n)==h for n,h in integration['binaries'].items())
        paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','crates','scripts','tests','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [Path(focus.__file__),previous/'closure.json',previous/'summary.json',old_plan,vm,server,integration_path]
        paths += [retained/n for n in [*integration['binaries'],'ready.json','source.json','capabilities.json']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target.relative_to(ROOT)),
            required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,expected_commands=2,
            minimum_python_tests=463,expected_skipped=22,original_project_guest_commands=0,
            default_runtime_adoption=False,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        records=[];outputs={};write(raw/'records.json',records)
        commands=[('python',[sys.executable,'-B','-m','unittest','discover','-s','tests','-v']),
            ('default-vm',['cargo','+nightly-2026-09-08','build','--release','--locked','--offline','--jobs','2',
                '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode','--bin','rust-interp-vm'])]
        for label,command in commands:
            require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed
            start=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))));write(raw/'records.json',records)
            assert child.returncode==0,(out+err)[-6000:]
            if label=='python':
                count,=re.findall(r'Ran (\d+) tests? in ',err);skipped,=re.findall(r'^OK(?: \(skipped=(\d+)\))?$',err,re.M)
                assert int(count)>=463 and int(skipped or 0)==22
                python_counts=dict(discovered=int(count),passed=int(count)-22,skipped=22)
            else:
                default=raw/'default-rust-interp-vm';shutil.copy2(target/'release/rust-interp-vm',default)
                outputs[str(default.relative_to(ROOT))]=sha(default)
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'passed',flush=True)
        binaries=dict(integration['binaries']);binaries['rust-interp-vm']=sha(vm)
        composition=dict(kind='explicit-cross-program-template-session-client',schema_version=1,source_commit=revision,
            compiler_source_key=BASELINE,binaries=binaries,server_executable_sha256=sha(server),server_path=str(server),
            session_required_for_history=True,default_runtime_adoption=False)
        key=hashlib.sha256(json.dumps(composition,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with (ROOT/'.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication,45);installed=ROOT/'.work/interpreter-tools'/key;installed.mkdir(exist_ok=False)
            for name in binaries:shutil.copy2(vm if name=='rust-interp-vm' else retained/name,installed/name)
            caps=read(retained/'capabilities.json');caps.update(tool_key=key,exporter_sha256=binaries['rust-interp-mir-export'])
            write(installed/'capabilities.json',caps)
            write(installed/'source.json',dict(tool_key=key,composition=composition,files=frozen,source_commit=revision,
                key_algorithm='SHA256 of canonical composition JSON',source=str(ROOT)))
            assert all(sha(installed/n)==h for n,h in binaries.items());write(installed/'ready.json',binaries)
        outputs.update({str((installed/n).relative_to(ROOT)):sha(installed/n) for n in [*binaries,'ready.json','source.json','capabilities.json']})
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        destination=ROOT/'results'/RUN;destination.mkdir(exist_ok=False)
        write(destination/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),commands=2,python=python_counts,
            tool_key=key,binaries=binaries,composition=composition,outputs=outputs,
            original_project_guest_commands=0,default_runtime_adoption=False,performance_measurement=False))

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()
