"""Qualify the complete scalar dead-register candidate."""
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write


def main():
    name='scalar-width-aliases-build-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed,'insufficient conservative build admission'
        directory=Path(__file__).parent
        prior_path=ROOT/'results/confined-scalar-native-coverage-01/summary.json';prior=json.loads(prior_path.read_text())
        assert prior['status']=='passed' and prior['controls']==2 and prior['all_frozen_inputs_verified']
        reference_path=ROOT/'results/current-runtime-boundaries-02/summary.json';reference=json.loads(reference_path.read_text())
        assert reference['status']=='passed' and reference['exact_logical_counts_memory_and_entropy']
        one,two=reference['profiles'][:2]
        assert one['artifact']==two['artifact'] and one['artifact_sha256']==two['artifact_sha256']
        artifact=ROOT/one['artifact'];assert sha(artifact)==one['artifact_sha256']
        dependency=[ROOT/p for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock'],text=True).splitlines()]
        paths=[p for p in directory.iterdir() if p.suffix in ['.rs','.py','.md','.toml','.lock']]
        paths += [ROOT/p for p in subprocess.check_output(['git','ls-files','scripts','tests'],text=True).splitlines()]
        paths += [ROOT/'results/guarded-local-facts-main-build-01/summary.json',ROOT/'results/heap-address-build-03/summary.json']
        paths+=dependency+[prior_path,reference_path,artifact,ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py']
        paths += [ROOT/'results/scalar-width-aliases-focused-01'/name for name in ['summary.json','terminal.json','closure.json']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work=ROOT/'.work'/name;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,target=str(target.relative_to(ROOT)),
            same_source_root=True,shared_target_allocated_bytes=allocated,required_free_bytes=needed,
            tests_per_profile=600,oracle_cases_per_profile=6400,scalar_copy_cases_per_profile=2187,synthetic_call_transaction_controls=6,synthetic_native_call_controls=9,original_project_guest_commands=0,guest_commands=0,runtime_changes=1,minimum_child_gib=8))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
             and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        records=[]
        def invoke(label,command,building=True):
            if building:assert shutil.disk_usage(ROOT).free>=needed
            require_space(ROOT,8);started=time.time()
            child,out,err=capture(list(map(str,command)),cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            for stream,text in [('stdout',out),('stderr',err)]:(work/(label+'.'+stream)).write_text(text)
            records.append(dict(label=label,command=list(map(str,command)),pid=child.pid,returncode=child.returncode,
                started_at=started,finished_at=time.time(),stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json',records)
            assert child.returncode==0,(out+err)[-5000:]
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            return out
        focused_path=ROOT/'results/scalar-width-aliases-focused-01/summary.json'
        focused=json.loads(focused_path.read_text());assert focused['status']=='passed' and focused['tests']=={'debug':22,'release':22}
        terminal=json.loads(focused_path.with_name('terminal.json').read_text());assert terminal['status']=='finished' and terminal['returncode']==0
        common=['--locked','--offline','--jobs','2','--manifest-path',ROOT/'Cargo.toml','--target-dir',target,'--workspace']
        totals={}
        for profile,extra in [('debug',[]),('release',['--release'])]:
            out=invoke('test-'+profile,['cargo','+nightly-2026-09-08','test',*extra,*common])
            matches=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
            assert matches and all(int(failed)==0 for _,failed,_ in matches)
            passed=sum(int(passed) for passed,_,_ in matches);ignored=sum(int(ignored) for _,_,ignored in matches)
            assert (passed,ignored)==(600,13),(passed,ignored)
            for required_test in ['scalar_call_transaction_matches_complete_vm_aliases_profiles_and_peak_memory',
                         'scalar_call_transaction_declines_leave_all_guest_visible_memory_unchanged',
                         'native_scalar_2187_copy_cases_in_both_profile_modes',
                         'native_scalar_assertions_address_bits_and_host_registers_are_preserved',
                         'path_byte_oracle_checks_both_sides_of_cfg_joins',
                         'native_scalar_call_commits_every_profile_word_and_exact_budget_boundary',
                         'profile_accepts_legacy_or_inactive_scalar_counts_and_rejects_scalar_weighting']:
                assert required_test+' ... ok' in out,required_test
            totals[profile]=passed;print(profile,passed,'workspace controls PASS;',ignored,'ignored',flush=True)
        pyout=invoke('python-launcher',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_isolated_launcher.py','-v'],False)
        invoke('python-metrics',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_interpreter_build_metrics.py','-v'],False)
        invoke('build-vm',['cargo','+nightly-2026-09-08','build','--release','--locked','--offline','--jobs','2',
            '--manifest-path',ROOT/'Cargo.toml','--target-dir',target,'-p','rust-interp-bytecode','--bin','rust-interp-vm'])
        assert b'--jit-scalar-calls' in (target/'release/rust-interp-vm').read_bytes()
        from interpreter import installed_tools
        import hashlib
        control_path=ROOT/'results/guarded-local-facts-main-build-01/summary.json'
        control=json.loads(control_path.read_text());assert control['status']=='passed'
        retained,key=installed_tools(control['tool_key'])
        assert key=='35df4077b5cfb466cf1a7155374abb867fb8fadeb4f5dbedffe766d5b3621bc1'
        assert all(sha(retained/n)==h for n,h in control['binaries'].items())
        matched_path=ROOT/'results/heap-address-build-03/summary.json'
        matched=json.loads(matched_path.read_text())['matched_control']
        matched_tools,_=installed_tools(matched['tool_key'])
        assert all(sha(matched_tools/n)==h for n,h in matched['binaries'].items())
        assert sha(ROOT/matched['source_manifest'])==matched['source_manifest_sha256']
        assert sha(ROOT/matched['command_record'])==matched['command_record_sha256']
        binaries=dict(control['binaries']);binaries['rust-interp-vm']=sha(target/'release/rust-interp-vm')
        composition=dict(kind='scalar-width-aliases-composition',schema_version=1,source_commit=revision,
            compiler_source_key=key,binaries=binaries)
        key=hashlib.sha256(json.dumps(composition,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with (ROOT/'.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication,45);installed=ROOT/'.work/interpreter-tools'/key;installed.mkdir(exist_ok=False)
            for binary in binaries:shutil.copy2(target/'release'/binary if binary=='rust-interp-vm' else retained/binary,installed/binary)
            caps=json.loads((retained/'capabilities.json').read_text());caps.update(tool_key=key,exporter_sha256=binaries['rust-interp-mir-export'])
            write(installed/'capabilities.json',caps)
            write(installed/'source.json',dict(tool_key=key,composition=composition,files=frozen,source_commit=revision,
                key_algorithm='SHA256 of canonical composition JSON',source=str(ROOT)))
            assert all(sha(installed/n)==h for n,h in binaries.items());write(installed/'ready.json',binaries)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/name;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',tests={'test-'+k:v for k,v in totals.items()},ignored_per_profile=13,commands=len(records),
            tool_key=key,binaries=binaries,composition=composition,matched_control=matched,
            source_manifest=str((work/'plan.json').relative_to(ROOT)),source_manifest_sha256=sha(work/'plan.json'),
            setup_seconds=sum(r['finished_at']-r['started_at'] for r in records),
            focused_summary_sha256=sha(focused_path),focused_terminal_sha256=sha(focused_path.with_name('terminal.json')),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),raw=str(work.relative_to(ROOT)),
            original_project_guest_commands=0,production_runtime_changes=1,performance_measurement=False))

if __name__=='__main__':main()
