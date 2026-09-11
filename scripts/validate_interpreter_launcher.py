#!/usr/bin/env python3
"""Prevent stale-bytecode execution across Cargo configuration and source edits."""
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
from interpreter import ROOT, TOOLCHAIN, checked_tools


def main():
    work=ROOT/'.work'/('interpreter-launcher-validation-'+str(time.time_ns()))
    (work/'src').mkdir(parents=True)
    (work/'Cargo.toml').write_text('[package]\nname="interpreter-launcher-fixture"\nversion="0.1.0"\nedition="2024"\n[dependencies]\ndependency={path="dependency"}\n[workspace]\n[features]\nother=[]\n')
    (work/'dependency/src').mkdir(parents=True)
    (work/'dependency/Cargo.toml').write_text('[package]\nname="dependency"\nversion="0.1.0"\nedition="2024"\n')
    dependency=work/'dependency/src/lib.rs'
    dependency_source='#[inline(never)] pub fn add(a:u64)->u64 { a+10 }\n'
    dependency.write_text(dependency_source)
    source='pub fn entry(a:u64)->u64 { a + if cfg!(feature="other") {20} else {10} + if cfg!(second) {30} else {0} }\npub fn dependency_entry(a:u64)->u64 { dependency::add(a) }\n#[cfg(test)] mod tests { #[test] fn body() { assert_eq!(super::entry(3),13); } }\n'
    source+='#[cfg(test)] fn second_body() { assert_eq!(dependency::add(3),13); }\n'
    source+='pub fn selection_probe(a:u64)->u64 { a+60 }\n'
    source+='#[cfg(test)] fn audit_panic() { panic!("audit must not execute me"); }\n'
    source+='#[cfg(test)] fn audit_unsupported() { unsafe extern "C" { fn getpid()->i32; } unsafe { let _=getpid(); } }\n'
    result_source=(ROOT/'tests/result_test_fixture.rs').read_text()
    result_file=work/'result_tests.rs';result_file.write_text(result_source)
    source+='#[cfg(test)] #[path="../result_tests.rs"] mod result_tests;\n'
    source+='#[cfg(test)] static GUEST_STATE: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(9);\n'
    source+='#[cfg(test)] fn mutable_first() { assert_eq!(GUEST_STATE.fetch_add(1,std::sync::atomic::Ordering::Relaxed),9); }\n'
    source+='#[cfg(test)] fn mutable_second() { assert_eq!(GUEST_STATE.load(std::sync::atomic::Ordering::Relaxed),10); }\n'
    source+='#[track_caller] fn caller_line()->u64 { std::panic::Location::caller().line() as u64 }\n'
    source+='pub fn location_entry(_:u64)->u64 { caller_line() }\n'
    (work/'src/lib.rs').write_text(source)
    subprocess.run(['cargo','+'+TOOLCHAIN,'generate-lockfile','--offline'],cwd=work,check=True)
    records=[]
    def run(label,extra=(),flags=None,want='13',entry='entry',arguments=('3',),extra_env=None):
        env=os.environ.copy();env.pop('RUSTFLAGS',None);env.pop('CARGO_ENCODED_RUSTFLAGS',None)
        if flags:env['RUSTFLAGS']=flags
        if extra_env:env.update(extra_env)
        command=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',str(work/'Cargo.toml'),'--package','interpreter-launcher-fixture']
        if entry is not None:command+=['--entry',entry]
        command+=extra
        if arguments:command+=['--',*arguments]
        start=time.perf_counter()
        p=subprocess.run(command,env=env,text=True,capture_output=True)
        records.append(dict(label=label,command=command,extra_env=extra_env,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr,seconds=time.perf_counter()-start))
        (work/'records.json').write_text(json.dumps(records,indent=2))
        if want is None:
            assert p.returncode!=0 and not p.stdout.strip(),p.stderr
        elif isinstance(want,dict):
            assert p.returncode==0,p.stderr
            audit=json.loads(p.stdout)
            assert audit['executed'] is False and audit['strict_frontend'] is True
            assert {r['entry']:r['status'] for r in audit['entries']}==want,audit
            assert audit['requested']==len(want) and audit['lowered']==list(want.values()).count('lowered')
        else:assert p.returncode==0 and p.stdout.strip()==want,p.stderr
    run('initial')
    _,pinned_key=checked_tools()
    for engine in ['interpreter','jit']:
        run('pinned-build-'+engine,['--tool-key',pinned_key,'--engine',engine],extra_env={'RUST_INTERP_LAUNCH_STATS':'1'})
        traces=[json.loads(line.split('rust-interp-launch: ',1)[1]) for line in records[-1]['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
        assert len(traces)==1
        trace=traces[0];assert trace['tool_key']==pinned_key and trace['engine']==engine
        artifact=Path(trace['artifact_path'])
        assert artifact.is_absolute() and artifact.is_relative_to(ROOT/'.work/interpreter-workspaces'/pinned_key)
        assert 0<trace['artifact_bytes']<=64*1024*1024
        contents=artifact.read_bytes()
        assert len(contents)==trace['artifact_bytes'] and hashlib.sha256(contents).hexdigest()==trace['artifact_sha256']
        assert 0<=trace['artifact_hash_seconds']<=trace['launcher_seconds']
    for label,bad_key in [('path','../tools'),('length','a'*63),('alphabet','z'*64)]:
        run('reject-tool-key-'+label,['--tool-key',bad_key],want=None)
        assert 'tool key must contain 64 lowercase hexadecimal characters' in records[-1]['stderr']
        assert 'Checking interpreter-launcher-fixture' not in records[-1]['stderr']
    missing_key=hashlib.sha256(('absent-installed-tools:'+str(work)).encode()).hexdigest()
    assert not (ROOT/'.work/interpreter-tools'/missing_key).exists()
    run('reject-uninstalled-tool-key',['--tool-key',missing_key],want=None)
    assert 'cannot read installed tool build' in records[-1]['stderr']
    assert 'Checking interpreter-launcher-fixture' not in records[-1]['stderr']
    caller_line=next(i+1 for i,line in enumerate(source.splitlines()) if line.startswith('pub fn location_entry'))
    run('caller-location',entry='location_entry',want=str(caller_line))
    (work/'src/lib.rs').write_text('\n\n'+source)
    run('caller-location-line-edit',['--engine','jit'],entry='location_entry',want=str(caller_line+2))
    (work/'src/lib.rs').write_text(source)
    run('caller-location-revert',entry='location_entry',want=str(caller_line))
    root_line=next(i+1 for i,line in enumerate(source.splitlines()) if line.startswith('#[track_caller] fn caller_line'))
    run('tracked-cli-root',entry='caller_line',arguments=(),want=str(root_line))
    run('cargo-timing-report',['--timings','--cache-namespace','timing-validation'])
    timing=re.search(r'Timing report saved to (.+\.html)',records[-1]['stderr'])
    assert timing,records[-1]['stderr']
    report=Path(timing.group(1).strip('`'))
    assert report.is_file() and 'const UNIT_DATA = ' in report.read_text()
    run('fresh')
    run('switch-selection',entry='selection_probe',want='63')
    assert 'Checking interpreter-launcher-fixture ' in records[-1]['stderr']
    assert 'Checking dependency ' not in records[-1]['stderr']
    run('selection-revert')
    run('switch-selection-jit',['--engine','jit'],entry='selection_probe',want='63')
    run('second-selection-revert')
    run('feature-other',['--features','other'],want='23')
    run('feature-revert')
    run('rustflags-second',flags='--cfg second',want='43')
    run('rustflags-revert')
    run('feature-again',['--features','other'],want='23')
    run('feature-second-revert')
    run('test-body',['--test-body'],entry='body',arguments=(),want='0')
    for engine in ['interpreter','jit']:
        run('mutable-statics-batch-'+engine,['--test-body','--engine',engine,'--entry','mutable_second'],
            entry='mutable_first',arguments=(),want='0')
        run('mutable-statics-reset-'+engine,['--test-body','--engine',engine],
            entry='mutable_first',arguments=(),want='0')
    (work/'src/lib.rs').write_text(source.replace('AtomicU64::new(9)','AtomicU64::new(17)'))
    run('mutable-static-initializer-edit',['--test-body'],entry='mutable_first',arguments=(),want=None)
    assert 'guest trap:' in records[-1]['stderr']
    (work/'src/lib.rs').write_text(source)
    run('mutable-static-initializer-revert',['--test-body'],entry='mutable_first',arguments=(),want='0')
    result_batch=['--test-body','--entry','result_tests::tagged_ok','--entry','result_tests::large_ok',
                  '--entry','result_tests::niche_ok','--entry','result_tests::empty_error']
    for engine in ['interpreter','jit']:
        run('result-batch-'+engine,[*result_batch,'--engine',engine],entry='body',arguments=(),want='0')
        run('result-failure-stops-batch-'+engine,
            ['--test-body','--engine',engine,'--entry','result_tests::later_panic'],
            entry='result_tests::tagged_err',arguments=(),want=None)
        assert 'test result_tests::tagged_err returned Err' in records[-1]['stderr']
        assert 'RESULT_BATCH_CONTINUED' not in records[-1]['stderr']
    result_file.write_text(result_source.replace('fn tagged_ok() -> Result<(), u64> { Ok(()) }',
                                                'fn tagged_ok() -> Result<(), u64> { Err(23) }'))
    run('result-body-edit-fails',['--test-body'],entry='result_tests::tagged_ok',arguments=(),want=None)
    assert 'test result_tests::tagged_ok returned Err' in records[-1]['stderr']
    result_file.write_text(result_source.replace('fn tagged_ok() -> Result<(), u64>',
                                                'fn tagged_ok() -> Result<(), [u8;64]>'))
    run('result-layout-edit',['--test-body','--engine','jit'],entry='result_tests::tagged_ok',arguments=(),want='0')
    result_file.write_text(result_source)
    run('result-body-and-layout-revert',['--test-body'],entry='result_tests::tagged_ok',arguments=(),want='0')
    result_selection=work/'result-selection.json'
    result_selection.write_text(json.dumps(['result_tests::tagged_ok','result_tests::tagged_err']))
    run('result-audit-does-not-execute',['--test-body','--audit-entries',str(result_selection)],entry=None,arguments=(),
        want={'result_tests::tagged_ok':'lowered','result_tests::tagged_err':'lowered'})
    selection=work/'audit-selection.json'
    expected={'tests::body':'lowered','audit_unsupported':'blocked','audit_panic':'lowered','second_body':'lowered','missing':'blocked'}
    selection.write_text(json.dumps(list(expected)))
    audit_args=['--test-body','--audit-entries',str(selection)]
    run('audit-mixed-bodies',audit_args,entry=None,arguments=(),want=expected)
    run('audit-cached-report',audit_args,entry=None,arguments=(),want=expected)
    assert 'Checking interpreter-launcher-fixture ' not in records[-1]['stderr']
    run('execution-after-audit',['--test-body'],entry='body',arguments=(),want='0')
    run('panic-body-after-audit',['--test-body'],entry='audit_panic',arguments=(),want=None)
    selection.write_text(json.dumps(['audit_panic']))
    run('audit-selection-change',audit_args,entry=None,arguments=(),want={'audit_panic':'lowered'})
    selection.write_text(json.dumps(list(expected)))
    run('audit-selection-revert',audit_args,entry=None,arguments=(),want=expected)
    # A body edit must invalidate its report, even if the selection is unchanged.
    (work/'src/lib.rs').write_text(source.replace('unsafe { let _=getpid(); }','let _=7;'))
    edited_expected={**expected,'audit_unsupported':'lowered'}
    run('audit-body-edit',audit_args,entry=None,arguments=(),want=edited_expected)
    (work/'src/lib.rs').write_text(source)
    run('audit-body-revert',audit_args,entry=None,arguments=(),want=expected)
    (work/'src/lib.rs').write_text(source+'fn unused_type_error() { let _:u8="bad"; }\n')
    run('audit-rejects-uncalled-type-error',audit_args,entry=None,arguments=(),want=None)
    (work/'src/lib.rs').write_text(source)
    run('audit-error-recovery',audit_args,entry=None,arguments=(),want=expected)
    selection.write_text(json.dumps(['audit_panic','audit_panic']))
    run('audit-duplicate-rejected',audit_args,entry=None,arguments=(),want=None)
    selection.write_text(json.dumps([]))
    run('audit-empty-rejected',audit_args,entry=None,arguments=(),want=None)
    selection.write_text(json.dumps(['audit_panic']))
    run('audit-arguments-rejected',audit_args,entry=None,want=None)
    run('audit-entry-conflict',audit_args,entry='body',arguments=(),want=None)
    run('execution-after-audit-errors',['--test-body'],entry='body',arguments=(),want='0')
    batch=['--test-body','--entry','second_body']
    run('batch-two-tests',batch,entry='body',arguments=(),want='0')
    run('batch-two-tests-jit',[*batch,'--engine','jit'],entry='body',arguments=(),want='0')
    run('batch-duplicate-entry',['--test-body','--entry','body'],entry='body',arguments=(),want=None)
    run('batch-duplicate-alias',['--test-body','--entry','tests::body'],entry='body',arguments=(),want=None)
    run('batch-rejects-arguments',batch,entry='body',want=None)
    (work/'src/lib.rs').write_text(source.replace('assert_eq!(dependency::add(3),13)','assert_eq!(dependency::add(3),99)'))
    run('unselected-second-test',['--test-body'],entry='body',arguments=(),want='0')
    run('batch-second-test-fails',batch,entry='body',arguments=(),want=None)
    run('batch-second-test-fails-jit',[*batch,'--engine','jit'],entry='body',arguments=(),want=None)
    (work/'src/lib.rs').write_text(source)
    run('batch-error-recovery',batch,entry='body',arguments=(),want='0')
    (work/'src/main.rs').write_text('fn main() { let _: u8 = "invalid unrelated binary"; }\n')
    (work/'tests').mkdir()
    (work/'tests/unrelated.rs').write_text('#[test] fn body() { panic!("unselected integration test"); }\n')
    with (work/'Cargo.toml').open('a') as f:f.write('\n[lib]\nname="renamed_library"\n[profile.test]\nopt-level=1\ndebug-assertions=false\n')
    (work/'src/lib.rs').write_text(source+'\n#[cfg(test)] fn profile_probe() -> u64 { cfg!(debug_assertions) as u64 }\n')
    run('renamed-library-test-only',['--test-body'],entry='body',arguments=(),want='0')
    run('test-profile',['--test-body'],entry='profile_probe',arguments=(),want='0')
    run('batch-rejects-non-unit',['--test-body','--entry','profile_probe'],entry='body',arguments=(),want=None)
    run('jit-test-body',['--test-body','--engine','jit'],entry='body',arguments=(),want='0')
    (work/'src/lib.rs').write_text(source)
    (work/'src/lib.rs').write_text(source.replace('{10}','{15}'))
    run('body-edit',want='18')
    (work/'src/lib.rs').write_text(source)
    run('body-revert')
    (work/'src/lib.rs').write_text(source+'fn unused() { let _: u8 = "wrong"; }\n')
    run('compile-error',want=None)
    (work/'src/lib.rs').write_text(source)
    run('error-recovery')
    run('independent-cache',['--cache-namespace','alternate'],flags='--cfg second',want='43')
    run('default-after-independent-cache')
    run('non-inline-dependency',entry='dependency_entry')
    run('non-inline-dependency-jit',['--engine','jit'],entry='dependency_entry')
    dependency.write_text('struct Pair(u8,u64); #[inline(never)] pub fn add(a:u64)->u64 { let p=Pair(15,a); p.1+p.0 as u64 }\n')
    run('dependency-callee-layout-edit',entry='dependency_entry',want='18')
    dependency.write_text(dependency_source)
    run('dependency-revert',entry='dependency_entry')
    dependency.write_text(dependency_source+'fn wrong() { let _:u8="error"; }\n')
    run('dependency-compile-error',entry='dependency_entry',want=None)
    dependency.write_text(dependency_source)
    run('dependency-error-recovery',entry='dependency_entry')
    # Host macro/build-script binaries use the installed sysroot; the checked
    # target and its dependencies use metadata-only standard-library artifacts.
    (work/'macro-fixture/src').mkdir(parents=True)
    (work/'macro-fixture/Cargo.toml').write_text('[package]\nname="macro-fixture"\nversion="0.1.0"\nedition="2024"\n[lib]\nproc-macro=true\n')
    (work/'macro-fixture/src/lib.rs').write_text('use proc_macro::TokenStream; #[proc_macro] pub fn value(_:TokenStream)->TokenStream { "63u64".parse().unwrap() }\n#[proc_macro] pub fn profile(_:TokenStream)->TokenStream { if cfg!(debug_assertions) { "1u64" } else { "0u64" }.parse().unwrap() }\n')
    manifest=work/'Cargo.toml'
    manifest.write_text(manifest.read_text().replace('[dependencies]\n','[dependencies]\nmacro-fixture={path="macro-fixture"}\n'))
    (work/'build.rs').write_text('fn main() { let out=std::path::PathBuf::from(std::env::var_os("OUT_DIR").unwrap()); std::fs::write(out.join("probe.rs"), "7u64").unwrap(); println!("cargo:rerun-if-changed=build.rs"); }\n')
    subprocess.run(['cargo','+'+TOOLCHAIN,'generate-lockfile','--offline'],cwd=work,check=True)
    std_source=source+'\n#[cfg(test)] fn std_body() { assert!("hay needle stack".contains("needle")); let names:Vec<_>=["one","two words","three"].into_iter().filter(|s|!s.contains(\' \')).collect(); assert_eq!(names.len(),2); assert_eq!(macro_fixture::value!(),63); assert_eq!(include!(concat!(env!("OUT_DIR"),"/probe.rs")),7); }\n'
    std_source+='\n#[cfg(test)] fn host_profile() -> u64 { (macro_fixture::profile!()<<1) | (cfg!(debug_assertions) as u64) }\n'
    (work/'src/lib.rs').write_text(std_source)
    std_batch=['--std-mir','--test-body','--entry','std_body']
    run('std-mir-host-tools-and-batch',std_batch,entry='body',arguments=(),want='0')
    run('std-mir-host-tools-and-batch-jit',[*std_batch,'--engine','jit'],entry='body',arguments=(),want='0')
    run('host-profile-baseline',['--std-mir','--test-body'],entry='host_profile',arguments=(),want='0')
    host_options={'CARGO_PROFILE_DEV_BUILD_OVERRIDE_OPT_LEVEL':'1','CARGO_PROFILE_TEST_BUILD_OVERRIDE_OPT_LEVEL':'1','CARGO_PROFILE_TEST_BUILD_OVERRIDE_DEBUG_ASSERTIONS':'true'}
    run('host-profile-change',['--std-mir','--test-body'],entry='host_profile',arguments=(),want='2',extra_env=host_options)
    run('host-profile-change-jit',['--std-mir','--test-body','--engine','jit'],entry='host_profile',arguments=(),want='2',extra_env=host_options)
    run('host-profile-revert',['--std-mir','--test-body'],entry='host_profile',arguments=(),want='0')
    run('std-mir-selection',['--std-mir'],entry='selection_probe',want='63')
    run('std-mir-rustflags',['--std-mir'],flags='--cfg second',want='43')
    run('std-mir-flags-revert',['--std-mir'])
    (work/'src/lib.rs').write_text(std_source+'fn wrong() {let _:u8="wrong";}\n')
    run('std-mir-rejects-uncalled-error',['--std-mir'],want=None)
    (work/'src/lib.rs').write_text(std_source)
    run('std-mir-error-recovery',std_batch,entry='body',arguments=(),want='0')
    installed_sysroot=subprocess.check_output(['rustc','+'+TOOLCHAIN,'--print','sysroot'],text=True).strip()
    run('std-mir-rejects-conflicting-sysroot',['--std-mir'],flags='--sysroot '+installed_sysroot,want=None)
    # Custom harnesses receive --cfg test, and their attribute macros preserve
    # real bodies without rustc's built-in test harness transformation.
    manifest.write_text(manifest.read_text().replace('[lib]\n','[lib]\nharness=false\n'))
    macro_file=work/'macro-fixture/src/lib.rs'
    macro_file.write_text(macro_file.read_text()+'\n#[proc_macro_attribute] pub fn body(_:TokenStream,item:TokenStream)->TokenStream { item }\n')
    custom_source=std_source+'\n#[cfg(test)] fn main() {}\n#[cfg(test)] #[macro_fixture::body] fn custom_one() { assert_eq!(entry(3),13); }\n#[cfg(test)] #[macro_fixture::body] fn custom_two() { assert_eq!(macro_fixture::value!(),63); }\n'
    (work/'src/lib.rs').write_text(custom_source)
    custom_batch=['--std-mir','--test-body','--entry','custom_two']
    run('custom-harness-batch',custom_batch,entry='custom_one',arguments=(),want='0')
    run('custom-harness-batch-jit',[*custom_batch,'--engine','jit'],entry='custom_one',arguments=(),want='0')
    (work/'src/lib.rs').write_text(custom_source.replace('fn custom_two() { assert_eq!(macro_fixture::value!(),63); }','fn custom_two() { assert_eq!(macro_fixture::value!(),99); }'))
    run('custom-harness-second-failure',custom_batch,entry='custom_one',arguments=(),want=None)
    run('custom-harness-second-failure-jit',[*custom_batch,'--engine','jit'],entry='custom_one',arguments=(),want=None)
    (work/'src/lib.rs').write_text(custom_source)
    run('custom-harness-recovery',custom_batch,entry='custom_one',arguments=(),want='0')
    run('custom-harness-selection',['--std-mir','--test-body'],entry='host_profile',arguments=(),want='0')
    manifest.write_text(manifest.read_text().replace('[lib]\nharness=false\n','[lib]\n'))
    (work/'src/lib.rs').write_text(std_source)
    run('builtin-harness-revert',std_batch,entry='body',arguments=(),want='0')
    # Select the original entry after dependency edits; otherwise Cargo would
    # legitimately regenerate the removed sidecar on an entry change.
    run('refresh-before-missing-sidecar')
    _,key=checked_tools()
    identity=hashlib.sha256(('shared-entries-v1\0'+str(work/'Cargo.toml')+'\0interpreter-launcher-fixture\0False').encode()).hexdigest()[:24]
    own=ROOT/'.work/interpreter-workspaces'/key/identity
    sidecars=list(own.rglob('*.rmeta.rbc'))
    assert sidecars
    for path in sidecars:path.unlink()
    run('missing-sidecar-refuses-run',want=None)
    (ROOT/'results/interpreter-launcher-validation.json').write_text(json.dumps(dict(raw=str(work.relative_to(ROOT)),tool_key=key,passed=[r['label'] for r in records],scripts_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__).resolve(),ROOT/'scripts/interpreter.py',ROOT/'scripts/std_mir.py']}),indent=2)+'\n')
    print('passed',len(records),'launcher checks')


if __name__=='__main__':main()
