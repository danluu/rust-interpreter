#!/usr/bin/env python3
"""Compare checked compiler discovery with native libtest listing and edit controls."""
import hashlib,json,os,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools,require_export_option
from test_discovery import read_listing
from workflow_io import capture,require_space,write_json as write,SourceEdit


def main():
    run='test-discovery-fixture-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        build_path=ROOT/'results/test-discovery-build-01/summary.json';build=json.loads(build_path.read_text())
        assert build['status']=='passed' and all(v==dict(passed=325,ignored=1) for v in build['tests'].values())
        tool,key=installed_tools(build['tool_key']);require_export_option(tool,key,'list-tests')
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False);source=work/'source';(source/'src').mkdir(parents=True);(source/'tests').mkdir()
        (source/'Cargo.toml').write_text('[package]\nname="discovery-fixture"\nversion="0.1.0"\nedition="2024"\n[workspace]\n[features]\nextra=[]\nbroken=[]\n')
        marker=work/'test-body-was-executed'
        original=('''pub fn successor(value: u64) -> u64 { value + 1 }
#[test] fn same() { assert_eq!(successor(41), 42); }
mod nested { #[test] fn same() { assert_eq!(super::successor(7), 8); } }
#[test] fn result() -> Result<(), &'static str> { Ok(()) }
#[test] #[ignore = "manual qualification"] fn ignored() { panic!("ignored body executed"); }
#[test] #[should_panic(expected = "expected panic")] fn panics() { panic!("expected panic"); }
#[test] fn must_not_run() { std::fs::write(MARKER, b"ran").unwrap(); }
#[cfg(feature = "extra")] #[test] fn gated() {}
#[cfg(feature = "broken")] fn bad_borrow() -> &'static u8 { let value = 3; &value }
'''.replace('MARKER',json.dumps(str(marker)))).encode()
        path=source/'src/lib.rs';path.write_bytes(original)
        (source/'tests/other.rs').write_text('#[test] fn same() {}\nmod nested { #[test] fn same() {} }\n')
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
        frozen_paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),build_path,source/'Cargo.toml',source/'tests/other.rs']
        frozen_paths += [ROOT/'scripts'/name for name in ['interpreter.py','test_discovery.py','workflow_io.py','std_mir.py']]
        frozen_paths += [tool/name for name in ['rust-interp-mir-export','rust-interp-rustc-wrapper','rust-interp-vm']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}
        write(work/'plan.json',dict(owner=str(ROOT),tool_key=key,frozen=frozen,original_source_sha256=sha(path),minimum_child_gib=8,performance_measurement=False))
        rows=[];listings=[]
        def invoke(label,command,success=True):
            require_space(ROOT,8)
            child,stdout,stderr=capture(command,cwd=source,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            row=dict(label=label,command=command,returncode=child.returncode,stdout=stdout,stderr=stderr);rows.append(row);write(work/'records.json',rows)
            assert (child.returncode==0)==success,stderr
            assert not marker.exists(),'listing executed a test body'
            return row
        def cargo(action,target='lib',features=None):
            command=['cargo','+nightly-2026-09-08',action,'--manifest-path',str(source/'Cargo.toml'),'--package','discovery-fixture','--offline','--jobs','2','--target-dir',str(work/'native')]
            command+=['--lib'] if target=='lib' else ['--test',target]
            if features:command+=['--features',features]
            return command
        def native(label,target='lib',features=None):
            row=invoke(label+'-native-build',cargo('test',target,features)+['--no-run','--message-format=json-render-diagnostics'])
            events=[json.loads(line) for line in row['stdout'].splitlines() if line.startswith('{')]
            binaries=[Path(e['executable']) for e in events if e.get('reason')=='compiler-artifact' and e.get('executable') and e['target']['kind']==(['lib'] if target=='lib' else ['test'])]
            assert len(binaries)==1 and binaries[0].is_relative_to(work/'native') and not binaries[0].is_symlink()
            saved=work/(label+'-native');shutil.copy2(binaries[0],saved)
            row=invoke(label+'-native-list',[str(saved),'--list','--format=terse'])
            names=sorted(line.removesuffix(': test') for line in row['stdout'].splitlines() if line.endswith(': test'))
            assert len(names)==len(set(names));return names
        base=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',str(source/'Cargo.toml'),'--package','discovery-fixture','--jobs','2','--tool-key',key,'--cache-namespace',run,'--test-body','--std-mir']
        def listing(label,expected,target='lib',features=None):
            command=base+['--list-tests']
            if target!='lib':command+=['--test-target',target]
            if features:command+=['--features',features]
            row=invoke(label+'-custom-list',command);report=json.loads(row['stdout'])
            assert report['tool_key']==key and report['executed'] is False
            provenance=report['discovery_provenance'];selected=Path(provenance['path']);checked,digest=read_listing(selected)
            assert digest==provenance['sha256'] and provenance['exporter_sha256']==sha(tool/'rust-interp-mir-export')
            assert [t['name'] for t in checked['tests']]==expected
            snapshot=work/(label+'-tests.json');snapshot.write_bytes(selected.read_bytes())
            listings.append(dict(label=label,names=expected,path=str(snapshot.relative_to(ROOT)),sha256=sha(snapshot)))
            return checked
        expected=sorted(['same','nested::same','result','ignored','panics','must_not_run'])
        assert native('original')==expected
        initial=listing('original',expected);attributes={t['name']:t for t in initial['tests']}
        assert attributes['ignored']['ignored'] and attributes['ignored']['ignore_reason']=='manual qualification'
        assert attributes['panics']['should_panic'] and attributes['panics']['panic_message']=='expected panic'
        assert attributes['result']['ordinary_test']
        for name in ['same','nested::same']:
            assert invoke('execute-'+name,base+['--entry',name])['stdout']=='0\n'
        listing('after-execution',expected)
        extra=sorted(expected+['gated']);assert native('feature',features='extra')==extra
        listing('feature',extra,features='extra');listing('feature-restored',expected)
        integration=['nested::same','same'];assert native('integration',target='other')==integration
        listing('integration',integration,target='other')
        failed=invoke('borrow-error-custom',base+['--list-tests','--features','broken'],False)
        assert 'E0515' in failed['stderr'] and failed['stdout']==''
        failed=invoke('borrow-error-native',cargo('check',features='broken')+['--profile','test'],False)
        assert 'E0515' in failed['stderr']
        listing('after-borrow-error',expected)
        with SourceEdit(path,original) as edit:
            edit.replace(original+b'\n#[test] fn added_by_edit() {}\n')
            edited=sorted(expected+['added_by_edit']);assert native('edited')==edited;listing('edited',edited)
            edit.replace(b'pub fn no_tests() {}\n')
            assert native('empty')==[];listing('empty',[])
        listing('source-restored',expected)
        custom=work/'custom-harness';(custom/'src').mkdir(parents=True)
        (custom/'Cargo.toml').write_text('[package]\nname="custom-harness"\nversion="0.1.0"\nedition="2024"\n[workspace]\n')
        (custom/'src/lib.rs').write_text('#![feature(custom_test_frameworks)]\n#![test_runner(runner)]\nfn runner(_: &[&dyn Fn()]) {}\n#[test_case] fn custom_test() {}\n')
        native_custom=['cargo','+nightly-2026-09-08','check','--manifest-path',str(custom/'Cargo.toml'),'--lib','--profile','test','--offline','--jobs','2','--target-dir',str(work/'custom-native')]
        invoke('custom-harness-native-check',native_custom)
        command=list(base);command[command.index('--manifest-path')+1]=str(custom/'Cargo.toml');command[command.index('--package')+1]='custom-harness'
        failed=invoke('custom-harness-rejected',command+['--list-tests'],False)
        assert 'built-in libtest harness' in failed['stderr'] and failed['stdout']==''
        assert path.read_bytes()==original and all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/run;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=len(rows),expected_rejections=3,listings=listings,
            names_match_native=True,attributes_verified=True,source_restored=True,listing_did_not_execute_tests=True,
            qualified_root_and_nested_name_execution=True,tool_key=key,performance_measurement=False,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))
        print('PASS: checked discovery, native name controls, attributes, target/features, edits and strict errors',flush=True)


if __name__=='__main__':main()
