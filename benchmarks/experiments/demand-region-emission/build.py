"""Build a complete immutable demand-region candidate using the adopted compiler."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from interpreter import installed_tools
NAME='demand-region-build-02'
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed,'insufficient conservative build admission'
        integration_path=ROOT/'results/scratch-scalar-main-qualification-01/summary.json'
        integration=read(integration_path);assert integration['status']=='passed' and integration['tool_key']==BASELINE
        retained,key=installed_tools(BASELINE);assert key==BASELINE
        assert all(sha(retained/n)==h for n,h in integration['binaries'].items())
        paths=[integration_path]+[retained/n for n in [*integration['binaries'],'ready.json','source.json','capabilities.json']]
        folder=ROOT/'results/demand-region-diagnostics-01';closed=read(folder/'closure.json')
        assert closed['status']=='closed' and closed['all_hashes_verified']
        assert sha(folder/'summary.json')==closed['summary_sha256']
        binding=ROOT/closed['bindings'];assert sha(binding)==closed['bindings_sha256']
        paths += [folder/n for n in ['summary.json','closure.json','terminal.json','assessment.md']] + [binding]
        for name,digest in read(binding)['artifacts'].items():assert sha(ROOT/name)==digest;paths.append(ROOT/name)
        controls=read(folder/'summary.json')
        assert controls['status']=='passed' and controls['controls_per_profile']==373 and controls['ignored_per_profile']==13
        assert controls['native_unit_tests'] and controls['demand_diagnostics_available']
        assert controls['production_runtime_changes']==1
        native_plan=ROOT/controls['raw']/'plan.json';assert sha(native_plan)==controls['plan_sha256'];paths.append(native_plan)
        # Full workspace checks below qualify the final CLI/statistics source.
        # Prior diagnostics are bound to their original committed source.
        artifact=ROOT/'.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc'
        staging_inputs=[artifact]
        for case in ['block','exhaustive']:
            base=ROOT/'.work'/('scratch-scalar-runtime-sample-'+case+'-01')/'0/jit-code'
            staging_inputs += [base/'operations.json',base/'code.bin']
        for path in staging_inputs:
            assert sha(path)==read(binding)['source'][str(path.relative_to(ROOT))]['sha256']
        paths += staging_inputs
        paths += [ROOT/p for p in subprocess.check_output(['git','ls-files','crates','scripts','tests','Cargo.toml','Cargo.lock','rust-toolchain.toml'],text=True).splitlines()]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            target=str(target.relative_to(ROOT)),same_source_root=True,required_free_bytes=needed,
            allocated_target_bytes=allocated,minimum_child_gib=8,expected_commands=6,
            expected_workspace_tests_per_profile=637,expected_ignored_per_profile=15,
            baseline_tool_key=BASELINE,original_project_guest_commands=0,native_guest_unit_tests=True,
            performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','READONLY_','TRANSACTION_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        common=['--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target)]
        commands=[('test-debug',['cargo','+nightly-2026-09-08','test',*common,'--workspace']),
            ('test-release',['cargo','+nightly-2026-09-08','test','--release',*common,'--workspace']),
            ('python',[sys.executable,'-m','unittest','discover','-s','tests','-v']),
            ('build-vm',['cargo','+nightly-2026-09-08','build','--release',*common,'-p','rust-interp-bytecode','--bin','rust-interp-vm'])]
        observer='jit::code_spans::region_staging::reconstruct_saved_regions_independently'
        for label in ['block','exhaustive']:
            commands.append((label,['cargo','+nightly-2026-09-08','test','--release',*common,'--lib','-p','rust-interp-bytecode',observer,'--','--ignored','--exact']))
        records=[]
        for label,command in commands:
            require_space(ROOT,8)
            if command[0]=='cargo':assert shutil.disk_usage(ROOT).free>=needed,'build reservation no longer holds'
            selected=dict(env)
            if label in ['block','exhaustive']:
                base=ROOT/'.work'/('scratch-scalar-runtime-sample-'+label+'-01')/'0/jit-code'
                selected.update(STAGING_ARTIFACT=str(artifact),STAGING_MAP=str(base/'operations.json'),
                    STAGING_CODE=str(base/'code.bin'),STAGING_OUTPUT=str(work/(label+'.json')))
            start=time.time();child,out,err=capture(command,cwd=ROOT,env=selected,receipt_path=work/'active.json',receipt=dict(label=label))
            for stream,payload in [('stdout',out),('stderr',err)]:(work/(label+'.'+stream)).write_text(payload)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,
                seconds=time.time()-start,stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            if label.startswith('test-'):
                matches=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
                assert matches and all(int(f)==0 for _,f,_ in matches)
                assert (sum(int(p) for p,_,_ in matches),sum(int(i) for _,_,i in matches))==(637,15)
                for test in ['live_demand_loops_preserve_counts_and_omit_cold_regions',
                    'live_demand_dumps_match_executed_code_and_preserve_profiles',
                    'demand_maps_cover_mixed_eager_fallback_and_reject_corrupt_receipts']:
                    assert test+' ... ok' in out
            if label in ['block','exhaustive']:
                assert 'test result: ok. 1 passed; 0 failed; 0 ignored;' in out
                detail=read(work/(label+'.json'))
                assert detail['exact_eager_reconstruction'] and detail['exact_reassembled_regions']
            if label=='python':assert 'Ran 430 tests' in err and err.rstrip().endswith('OK (skipped=22)'),err[-4000:]
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'passed',flush=True)
        binaries=dict(integration['binaries']);binaries['rust-interp-vm']=sha(target/'release/rust-interp-vm')
        assert binaries['rust-interp-vm']!=integration['binaries']['rust-interp-vm']
        composition=dict(kind='demand-region',schema_version=1,source_commit=revision,
            compiler_source_key=BASELINE,binaries=binaries)
        key=hashlib.sha256(json.dumps(composition,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with (ROOT/'.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication,45);installed=ROOT/'.work/interpreter-tools'/key;installed.mkdir(exist_ok=False)
            for n in binaries:shutil.copy2(target/'release'/n if n=='rust-interp-vm' else retained/n,installed/n)
            caps=read(retained/'capabilities.json');caps.update(tool_key=key,exporter_sha256=binaries['rust-interp-mir-export'])
            write(installed/'capabilities.json',caps)
            write(installed/'source.json',dict(tool_key=key,composition=composition,files=frozen,source_commit=revision,
                key_algorithm='SHA256 of canonical composition JSON',source=str(ROOT)))
            assert all(sha(installed/n)==h for n,h in binaries.items());write(installed/'ready.json',binaries)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,tests={'test-debug':637,'test-release':637},
            ignored_per_profile=15,python={'discovered':430,'passed':408,'skipped':22},commands=len(records),
            tool_key=key,binaries=binaries,composition=composition,
            matched_control=dict(tool_key=BASELINE,binaries=integration['binaries'],integration=str(integration_path.relative_to(ROOT))),
            source_manifest=str((work/'plan.json').relative_to(ROOT)),source_manifest_sha256=sha(work/'plan.json'),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),raw=str(work.relative_to(ROOT)),
            setup_seconds=sum(r['seconds'] for r in records),original_project_guest_commands=0,performance_measurement=False,exact_adopted_code_reconstruction=True))
if __name__=='__main__':main()
