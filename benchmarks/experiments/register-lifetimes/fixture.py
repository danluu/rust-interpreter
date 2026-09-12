#!/usr/bin/env python3
"""Qualify exact allocation with native Rust assertions and the unchanged VM."""
import json,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools
from suite_reports import read_report,validate_report,validate_runtime_limits
from workflow_io import capture,require_space,write_json as write,SourceEdit


def main():
    run='register-allocation-fixture-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        builds={mode:ROOT/'results'/name/'summary.json' for mode,name in [
            ('baseline','suite-profiling-build-02'),('candidate','register-allocation-compose-01')]}
        summaries={mode:json.loads(path.read_text()) for mode,path in builds.items()}
        assert summaries['baseline']['status']=='passed' and summaries['candidate']['status']=='composed'
        compiler_build=ROOT/summaries['candidate']['build'];compiled=json.loads(compiler_build.read_text());assert compiled['tests']['test-debug']==compiled['tests']['test-release']==dict(passed=352,ignored=1)
        verifier=ROOT/summaries['candidate']['verifier'];assert sha(verifier)==summaries['candidate']['verifier_sha256']
        assert summaries['baseline']['binaries']['rust-interp-vm']==summaries['candidate']['binaries']['rust-interp-vm']
        tools={mode:installed_tools(s['tool_key'])[0] for mode,s in summaries.items()}
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False);project=work/'project';(project/'src').mkdir(parents=True)
        source=project/'src/lib.rs';original=Path(__file__).with_name('fixture.rs').read_bytes();source.write_bytes(original)
        manifest=project/'Cargo.toml';manifest.write_text('[package]\nname = "register-allocation-fixture"\nversion = "0.0.0"\nedition = "2024"\n[workspace]\n')
        (project/'Cargo.lock').write_text('version = 4\n\n[[package]]\nname = "register-allocation-fixture"\nversion = "0.0.0"\n')
        write(project/'.rust-interp-owned.json',dict(owner=str(ROOT),run=run,purpose='typed pointer compiler fixture'))
        frozen_paths=[Path(__file__),Path(__file__).with_name('fixture.rs'),Path(__file__).with_name('PLAN.md'),*builds.values(),compiler_build,verifier,manifest,project/'Cargo.lock']
        frozen_paths += [tool/name for tool in tools.values() for name in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,tools={m:s['tool_key'] for m,s in summaries.items()},
            original_source_sha256=sha(source),performance_measurement=False,scope='native original assertions, both exports and unchanged VM, strict uncalled borrow/type errors'))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
        native=['cargo','+nightly-2026-09-08','test','--manifest-path',str(manifest),'--target-dir',str(work/'native'),'--lib','--locked','--offline','--jobs','2']
        records=[];artifacts={};profile_paths={}
        def execute(label,command,success=True,error=None):
            require_space(ROOT,8)
            child,stdout,stderr=capture(command,cwd=project,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            row=dict(label=label,command=command,pid=child.pid,returncode=child.returncode,stdout=stdout,stderr=stderr,source_sha256=sha(source))
            records.append(row);write(work/'records.json',records)
            assert (child.returncode==0)==success,stderr
            if error:assert error in stderr
            print(label,'PASS',flush=True);return row
        def exported(mode,label,success=True,error=None):
            suite_path=work/(label+'.json')
            command=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',str(manifest),'--package','register-allocation-fixture','--jobs','2',
                '--tool-key',summaries[mode]['tool_key'],'--cache-namespace',run+':'+mode,'--test-body','--std-mir',
                '--test-filter','tests::','--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
                '--isolated-batch','prepared','--suite-report',str(suite_path),'--trap-unsupported-calls','--run-try-callbacks',
                '--instruction-limit','10000000']
            row=execute(label,command,success,error)
            if not success:
                assert not suite_path.exists();return row
            launch=[json.loads(line.removeprefix('rust-interp-launch: ')) for line in row['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
            assert len(launch)==1;launch=launch[0];artifact=Path(launch['artifact_path']);assert sha(artifact)==launch['artifact_sha256']
            snapshot=work/(label+'.rbc');snapshot.write_bytes(artifact.read_bytes())
            catalog=Path(launch['entry_catalog_path']);assert sha(catalog)==launch['entry_catalog_sha256']
            Path(str(snapshot)+'.entries.json').write_bytes(catalog.read_bytes())
            names=[e['name'] for e in json.loads(catalog.read_text())['entries']];assert len(names)==8
            suite,digest=read_report(suite_path);validate_report(suite,names,'prepared',True);validate_runtime_limits(suite,10000000,required=True)
            row.update(artifact_sha256=sha(snapshot),suite_sha256=digest,catalog_sha256=sha(catalog));write(work/'records.json',records)
            if mode=='candidate':
                values=re.findall(r'rust-interp-register-lifetimes: before=(\d+) after=(\d+)',row['stderr']);assert len(values)==1 and int(values[0][0])>int(values[0][1]),'no register storage reduction reached actual export'
                row['register_slots']=list(map(int,values[0]));write(work/'records.json',records)
            artifacts[mode]=snapshot;return row
        row=execute('native-original',native+['--','--test-threads=1']);assert '8 passed; 0 failed;' in row['stdout']
        for mode in ['baseline','candidate']:
            exported(mode,mode+'-original')
            execute(mode+'-interpreter',[str(tools[mode]/'rust-interp-vm'),'--engine','interpreter','--instruction-limit','10000000',str(artifacts[mode])])
            profile=work/(mode+'-profile.json');profile_paths[mode]=profile
            execute(mode+'-profile',[str(tools[mode]/'rust-interp-vm'),'--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
                '--instruction-limit','10000000','--profile',str(profile),'--profile-test','tests::pointer_values_across_branches_and_wrapping_arithmetic',
                '--suite-catalog',str(artifacts[mode])+'.entries.json',str(artifacts[mode])])
        profiles={m:json.loads(p.read_text()) for m,p in profile_paths.items()}
        selected={m:next(f for f in p['functions'] if f['name']=='address_choice[]') for m,p in profiles.items()}
        assert selected['baseline']['operations']!=selected['candidate']['operations'],'typed fixture body did not change'
        def verify_artifacts(label):
            report=work/(label+'.json')
            execute(label,[str(verifier),'--verify',str(artifacts['baseline']),str(artifacts['candidate']),str(report)])
            assert json.loads(report.read_text())['exact_allocation']
        verify_artifacts('verify-original')
        with SourceEdit(source,original) as edit:
            for label,addition,error in [('borrow',b'\npub fn bad_borrow() -> &\'static u64 { let local = 7; &local }\n','E0515'),
                                         ('type',b'\npub fn bad_type() { let _: u64 = "wrong"; }\n','E0308')]:
                edit.replace(original+addition)
                execute('native-'+label,native,False,error)
                for mode in ['baseline','candidate']:exported(mode,mode+'-'+label,False,error)
            edit.replace(original)
            row=execute('native-restored',native+['--','--test-threads=1']);assert '8 passed; 0 failed;' in row['stdout']
            for mode in ['baseline','candidate']:exported(mode,mode+'-restored')
            verify_artifacts('verify-restored')
        assert source.read_bytes()==original and all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/run;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=len(records),original_tests=8,strict_errors=['E0515','E0308'],
            native_and_both_engines_pass=True,vm_bytes_identical=True,typed_body_changed=True,exact_whole_artifact_allocation=True,
            source_restored=True,register_slots=[r['register_slots'] for r in records if 'register_slots' in r],
            tools={m:s['tool_key'] for m,s in summaries.items()},raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),performance_measurement=False))


if __name__=='__main__':main()
