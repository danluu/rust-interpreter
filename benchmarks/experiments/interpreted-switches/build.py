"""Qualify an independent indexed-switch runtime and install immutable tools."""
import hashlib,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from interpreter import installed_tools
NAME='indexed-switches-build-01'
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed,'insufficient conservative build admission'
        adopted_path=ROOT/'results/scratch-scalar-main-qualification-01/summary.json';adopted=read(adopted_path)
        assert adopted['status']=='passed' and adopted['tool_key']==BASELINE
        retained,_=installed_tools(BASELINE);assert all(sha(retained/n)==h for n,h in adopted['binaries'].items())
        paths=[adopted_path]+[retained/n for n in [*adopted['binaries'],'ready.json','source.json','capabilities.json']]
        paths += [ROOT/p for p in subprocess.check_output(['git','ls-files','crates','scripts','tests','Cargo.toml','Cargo.lock','rust-toolchain.toml'],text=True).splitlines()]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,target=str(target.relative_to(ROOT)),
            same_source_root=True,required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,
            expected_commands=4,minimum_workspace_tests_per_profile=612,expected_index_controls=4,
            baseline_tool_key=BASELINE,original_project_guest_commands=0,native_guest_unit_tests=True,performance_measurement=False))
        records=[];write(work/'records.json',records)
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        common=['--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target)]
        commands=[('test-debug',['cargo','+nightly-2026-09-08','test','--workspace',*common]),
            ('test-release',['cargo','+nightly-2026-09-08','test','--workspace','--release',*common]),
            ('python',[sys.executable,'-m','unittest','discover','-s','tests','-v']),
            ('build-vm',['cargo','+nightly-2026-09-08','build','--release',*common,'-p','rust-interp-bytecode','--bin','rust-interp-vm'])]
        tests={};ignored={};python={}
        for label,command in commands:
            require_space(ROOT,8)
            if command[0]=='cargo':assert shutil.disk_usage(ROOT).free>=needed,'build admission no longer holds'
            start=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            for stream,payload in [('stdout',out),('stderr',err)]:(work/(label+'.'+stream)).write_text(payload)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            if label.startswith('test-'):
                rows=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
                assert rows and all(int(f)==0 for _,f,_ in rows)
                tests[label]=sum(int(n) for n,_,_ in rows);ignored[label]=sum(int(n) for _,_,n in rows)
                assert tests[label]>=612
                for name in ['dense_sparse_duplicates_and_full_width_match_first_case_oracle',
                    'resource_refusals_and_cache_capacity_preserve_linear_semantics',
                    'execution_budget_profile_and_validation_match_without_indices',
                    'prepared_invocations_keep_indices_local_and_match_alternate_entries']:assert name+' ... ok' in out
            if label=='python':
                count=re.search(r'Ran (\d+) tests',err);skips=re.search(r'OK \(skipped=(\d+)\)',err)
                assert count and skips and err.rstrip().endswith(skips[0])
                python=dict(discovered=int(count[1]),skipped=int(skips[1]),passed=int(count[1])-int(skips[1]));assert python['passed']>=408
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'passed',flush=True)
        binaries=dict(adopted['binaries']);binaries['rust-interp-vm']=sha(target/'release/rust-interp-vm')
        assert binaries['rust-interp-vm']!=adopted['binaries']['rust-interp-vm']
        composition=dict(kind='indexed-switches',schema_version=1,source_commit=revision,compiler_source_key=BASELINE,binaries=binaries)
        key=hashlib.sha256(json.dumps(composition,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with (ROOT/'.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication,45);installed=ROOT/'.work/interpreter-tools'/key;installed.mkdir(exist_ok=False)
            for n in binaries:shutil.copy2(target/'release'/n if n=='rust-interp-vm' else retained/n,installed/n)
            caps=read(retained/'capabilities.json');caps.update(tool_key=key,exporter_sha256=binaries['rust-interp-mir-export'])
            write(installed/'capabilities.json',caps)
            write(installed/'source.json',dict(tool_key=key,composition=composition,files=frozen,source_commit=revision,
                key_algorithm='SHA256 of canonical composition JSON',source=str(ROOT)))
            assert all(sha(installed/n)==h for n,h in binaries.items());write(installed/'ready.json',binaries)
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,commands=len(records),tests=tests,ignored=ignored,
            python=python,tool_key=key,binaries=binaries,composition=composition,
            matched_control=dict(tool_key=BASELINE,binaries=adopted['binaries'],integration=str(adopted_path.relative_to(ROOT))),
            source_manifest=str((work/'plan.json').relative_to(ROOT)),source_manifest_sha256=sha(work/'plan.json'),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),raw=str(work.relative_to(ROOT)),
            setup_seconds=sum(r['seconds'] for r in records),original_project_guest_commands=0,performance_measurement=False))
if __name__=='__main__':main()
