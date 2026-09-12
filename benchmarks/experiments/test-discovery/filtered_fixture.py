#!/usr/bin/env python3
"""Qualify same-pass filtered suites with native assertions and actual Rust edits."""
import hashlib,json,os,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools,require_export_option
from test_discovery import read_selection
from native_suite import test_status
from suite_reports import read_report,validate_report,validate_runtime_limits
from workflow_io import capture,require_space,write_json as write,SourceEdit


def main():
    run='filtered-suites-fixture-02'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        build_path=ROOT/'results/filtered-suites-build-02/summary.json';build=json.loads(build_path.read_text())
        assert build['status']=='passed' and all(v==dict(passed=329,ignored=1) for v in build['tests'].values())
        tool,key=installed_tools(build['tool_key']);require_export_option(tool,key,'filtered-tests')
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False);source=work/'source';(source/'src').mkdir(parents=True);(source/'tests').mkdir()
        manifest=source/'Cargo.toml';manifest.write_text('[package]\nname="filtered-fixture"\nversion="0.1.0"\nedition="2024"\n[workspace]\n[features]\nextra=[]\nbroken=[]\n')
        marker=work/'test-body-marker'
        original=('''pub fn successor(value: u64) -> u64 { value + 1 }
#[test] fn same() { assert_eq!(successor(41), 42); }
mod nested {
    #[test] fn same() { assert_eq!(super::successor(7), 8); }
    #[test] #[ignore="manual"] #[should_panic] fn ignored() { panic!("must stay ignored"); }
}
#[test] fn result() -> Result<(), &'static str> { if successor(41)==42 { Ok(()) } else { Err("wrong result") } }
#[test] #[should_panic(expected="expected panic")] fn panics() { panic!("expected panic"); }
#[test] fn marker() { std::fs::write(MARKER, b"ran").unwrap(); }
#[cfg(feature="extra")] #[test] fn same_extra() { assert_eq!(successor(41),42); }
#[cfg(feature="broken")] fn bad_borrow() -> &'static u8 { let value=3; &value }
'''.replace('MARKER',json.dumps(str(marker)))).encode()
        path=source/'src/lib.rs';path.write_bytes(original)
        integration=source/'tests/other.rs';integration.write_text('#[test] fn same() {}\nmod nested { #[test] fn same() {} }\n')
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
        frozen_paths=[Path(__file__),Path(__file__).with_name('FILTERED.md'),build_path,manifest,integration]
        frozen_paths += [ROOT/'scripts'/n for n in ['interpreter.py','test_discovery.py','workflow_io.py','std_mir.py','suite_reports.py','native_suite.py']]
        frozen_paths += [tool/n for n in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}
        write(work/'plan.json',dict(owner=str(ROOT),tool_key=key,frozen=frozen,original_source_sha256=sha(path),minimum_child_gib=8,performance_measurement=False))
        rows=[];suites=[]
        def invoke(label,command,success=True):
            require_space(ROOT,8)
            child,stdout,stderr=capture(command,cwd=source,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            row=dict(label=label,command=command,returncode=child.returncode,stdout=stdout,stderr=stderr);rows.append(row);write(work/'records.json',rows)
            assert (child.returncode==0)==success,stderr
            assert not marker.exists(),'unselected/unsupported suite executed a body'
            return row
        def cargo(action,features=None,target=None):
            command=['cargo','+nightly-2026-09-08',action,'--manifest-path',str(manifest),'--offline','--jobs','2','--target-dir',str(work/'native')]
            command+=['--test',target] if target else ['--lib']
            if features:command+=['--features',features]
            return command
        def native(label,names,success=True,features=None,target=None):
            row=invoke(label+'-native-build',cargo('test',features,target)+['--no-run','--message-format=json-render-diagnostics'])
            events=[json.loads(line) for line in row['stdout'].splitlines() if line.startswith('{')]
            binaries=[Path(e['executable']) for e in events if e.get('reason')=='compiler-artifact' and e.get('executable') and e['target']['kind']==(['test'] if target else ['lib'])]
            assert len(binaries)==1 and binaries[0].is_relative_to(work/'native')
            saved=work/(label+'-native');shutil.copy2(binaries[0],saved)
            for name in names:
                row=invoke(label+'-native-'+name,[str(saved),'--exact',name,'--test-threads=1'],success)
                assert test_status(name,row['returncode'],row['stdout'])==('passed' if success else 'failed')
        base=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',str(manifest),'--package','filtered-fixture','--jobs','2','--tool-key',key,'--cache-namespace',run,'--test-body','--std-mir','--engine','jit','--jit-resumable-calls','--jit-persistent-registers']
        def custom(label,names,pattern=None,exact=False,mode='prepared',success=True,features=None,target=None,reject=None):
            suite_path=work/(label+'-suite.json');command=base+['--isolated-batch',mode,'--suite-report',str(suite_path)]
            if pattern is None:
                for name in names:command+=['--entry',name]
            else:
                command+=['--test-filter',pattern]
                if exact:command+=['--test-exact']
            if features:command+=['--features',features]
            if target:command+=['--test-target',target]
            row=invoke(label,command,success and reject is None)
            if reject:
                assert reject in row['stderr'] and row['stdout']=='' and not suite_path.exists();return None
            suite,suite_sha=read_report(suite_path);validate_report(suite,names,mode,success);validate_runtime_limits(suite,required=True)
            launches=[json.loads(line.removeprefix('rust-interp-launch: ')) for line in row['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
            assert len(launches)==1;launch=launches[0];artifact=Path(launch['artifact_path']);digest=sha(artifact)
            assert digest==launch['artifact_sha256']
            snapshot=work/(label+'.rbc');snapshot.write_bytes(artifact.read_bytes())
            catalog=Path(launch['entry_catalog_path']);assert sha(catalog)==launch['entry_catalog_sha256']
            Path(str(snapshot)+'.entries.json').write_bytes(catalog.read_bytes())
            assert [t['name'] for t in json.loads(catalog.read_text())['entries']]==names
            if pattern is not None:
                selection,d=read_selection(Path(launch['test_selection_path']),artifact,pattern,exact)
                assert selection['selected']==names and d==launch['test_selection_sha256']
                Path(str(snapshot)+'.selection.json').write_bytes(Path(launch['test_selection_path']).read_bytes())
            exports=sum(line.startswith('rust-interp-export: ') for line in row['stderr'].splitlines())
            assert exports<=1
            if label in ['substring-fresh','wrong-filter','good-filter','restored']:assert exports==1
            suites.append(dict(label=label,names=names,artifact_sha256=digest,suite_sha256=suite_sha,mode=mode,passed=success))
            return digest
        both=['nested::same','same'];native('original',both+['result'])
        auto=custom('substring-fresh',both,'same',mode='fresh')
        manual=custom('explicit-prepared',both)
        assert auto==manual
        custom('exact-root',['same'],'same',True)
        custom('exact-nested',['nested::same'],'nested::same',True)
        custom('single-result',['result'],'result',True)
        custom('skip-ignored',['nested::same'],'nested::')
        for label,pattern,reason in [('no-match','absent','no runnable tests'),('only-ignored','ignored','no runnable tests'),
                ('unsupported-panic','panics','unsupported should_panic'),('all-tests','','unsupported should_panic')]:
            custom(label,[],pattern,reject=reason)
        extra=both+['same_extra'];native('feature',extra,features='extra')
        custom('feature',extra,'same',features='extra');custom('feature-restored',both,'same')
        native('integration',both,target='other');custom('integration',both,'same',target='other')
        custom('unused-borrow-error',both,'same',features='broken',reject='E0515')
        failed=invoke('native-unused-borrow-error',cargo('check','broken')+['--profile','test'],False);assert 'E0515' in failed['stderr']
        custom('borrow-restored',both,'same')
        with SourceEdit(path,original) as edit:
            edit.replace(original.replace(b'value + 1',b'value + 2'))
            native('wrong-edit',both+['result'],False)
            auto=custom('wrong-filter',both,'same',success=False)
            assert auto==custom('wrong-explicit',both,success=False)
            custom('wrong-result',['result'],'result',True,success=False)
            edit.replace(original.replace(b'value + 1',b'value.wrapping_add(1)'))
            native('good-edit',both);auto=custom('good-filter',both,'same')
            assert auto==custom('good-explicit',both)
            edit.replace(original+b'\n'+b'\n'.join(f'#[test] fn bulk_{i:03}() {{}}'.encode() for i in range(257)))
            custom('too-many',[],'bulk_',reject='256-entry limit')
        native('restored',both);custom('restored',both,'same')
        assert path.read_bytes()==original and all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/run;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=len(rows),suites=suites,tool_key=key,source_restored=True,
            automatic_explicit_bytecode_identical=True,no_separate_discovery_command=True,
            wrong_edit_native_assertions_match=True,unselected_marker_not_executed=True,performance_measurement=False,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))
        print('PASS: filtered and explicit suites, native edits, single tests, attributes and strict failures',flush=True)


if __name__=='__main__':main()
