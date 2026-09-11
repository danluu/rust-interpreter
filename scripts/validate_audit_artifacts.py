#!/usr/bin/env python3
"""Check retained audit programs, native outcomes, and Cargo cache provenance."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from interpreter import ROOT, TOOLCHAIN, checked_tools


def main():
    tools,key=checked_tools()
    work=ROOT/'.work'/('audit-artifact-validation-'+str(time.time_ns()))
    (work/'src').mkdir(parents=True)
    (work/'Cargo.toml').write_text('[package]\nname="audit-pack-fixture"\nversion="0.1.0"\nedition="2024"\n[workspace]\n[features]\nother=[]\n')
    source='''fn value()->u64 { if cfg!(feature="other") {23} else {13} }
#[cfg(test)] mod tests {
    static STATE: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(9);
    #[test] fn good() { assert_eq!(super::value(),13); }
    #[test] fn panic_body() { panic!("RETAINED_PANIC_BODY"); }
    #[test] fn result_ok()->Result<(),u64> { Ok(()) }
    #[test] fn result_err()->Result<(),u64> { Err(17) }
    #[test] fn mutable_first() { assert_eq!(STATE.fetch_add(1,std::sync::atomic::Ordering::Relaxed),9); }
    #[test] fn mutable_second() { assert_eq!(STATE.load(std::sync::atomic::Ordering::Relaxed),10); }
    #[test] #[ignore = "fixture skip"] fn ignored_named() { panic!("IGNORED_FIXTURE"); }
    #[test] #[should_panic] fn expected_panic() { panic!("EXPECTED_FIXTURE"); }
    #[test] #[should_panic(expected = "NAMED_FIXTURE")] fn expected_named_panic() { panic!("NAMED_FIXTURE"); }
    #[test] #[cfg_attr(feature="other", ignore = "conditional skip")] fn conditional_ignore() {}
    #[test] #[cfg_attr(feature="other", should_panic(expected = "conditional"))] fn conditional_panic() { panic!("conditional"); }
    fn plain() {}
    #[test] fn unsupported() { unsafe extern "C" { fn getpid()->i32; } unsafe { let _=getpid(); } }
}
'''
    source_file=work/'src/lib.rs';source_file.write_text(source)
    env=os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_','CARGO_PROFILE_')) or name in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']:
            env.pop(name,None)
    env.update(CARGO_TERM_COLOR='never',CARGO_TARGET_DIR=str(work/'native-target'))
    records=[]
    def run(label,command,success=True):
        start=time.perf_counter()
        p=subprocess.run(list(map(str,command)),cwd=work,env=env,text=True,capture_output=True)
        row=dict(label=label,command=list(map(str,command)),returncode=p.returncode,
                 stdout=p.stdout,stderr=p.stderr,seconds=time.perf_counter()-start)
        records.append(row);(work/'records.json').write_text(json.dumps(records,indent=2)+'\n')
        assert (p.returncode==0)==success,row
        assert 'internal compiler error' not in p.stderr,row
        return row
    run('lockfile',['cargo','+'+TOOLCHAIN,'generate-lockfile','--offline'])
    outcomes={name:ok for name,ok in [('good',True),('panic_body',False),('result_ok',True),
              ('result_err',False),('mutable_first',True),('mutable_second',False)]}
    metadata_names=['ignored_named','expected_panic','expected_named_panic','conditional_ignore','conditional_panic','plain']
    selected=['tests::'+name for name in [*outcomes,*metadata_names]]+['tests::unsupported','missing']
    expected={name:('blocked' if name in selected[-2:] else 'lowered') for name in selected}
    selection=work/'selection.json';selection.write_text(json.dumps(selected))
    command=[sys.executable,ROOT/'scripts/interpreter.py','--manifest-path',work/'Cargo.toml',
             '--package','audit-pack-fixture','--test-body','--audit-entries',selection,
             '--tool-key',key,'--cache-namespace',work.name]
    def collect(label,extra=(),success=True,retain=True,statuses=None):
        args=[*command,*(['--retain-audit-bodies'] if retain else []),*extra]
        row=run(label,args,success)
        if not success:
            assert not row['stdout'].strip(),row
            return row
        report=json.loads(row['stdout'])
        assert report['executed'] is False and report['strict_frontend'] is True
        assert report['tool_key']==key
        assert {r['entry']:r['status'] for r in report['entries']}==(expected if statuses is None else statuses)
        assert ('artifacts' in report)==retain
        if retain:
            provenance=report['artifact_provenance'];sidecar=Path(provenance['audit_path'])
            assert sidecar.name.endswith('.rmeta.audit.json')
            assert hashlib.sha256(sidecar.read_bytes()).hexdigest()==provenance['audit_sha256']
            assert provenance['tool_binaries']==json.loads((tools/'ready.json').read_text())
            assert provenance['selection_sha256']==hashlib.sha256(json.dumps(list(expected if statuses is None else statuses),separators=(',',':')).encode()).hexdigest()
        return report
    def artifact(report,entry):
        row=next(r for r in report['entries'] if r['entry']==entry)
        path=Path(report['artifacts']['directory'])/row['artifact']['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['artifact']['sha256']
        return path
    def execute(label,report,entry,success):
        for engine in ['interpreter','jit']:
            row=run(label+'-'+engine,[tools/'rust-interp-vm','--engine',engine,artifact(report,entry)],success)
            if success:assert row['stdout'].strip()=='0',row
            else:assert 'guest ' in row['stderr'],row
    def native_binary(label,extra=()):
        row=run(label,['cargo','+'+TOOLCHAIN,'test','--lib','--no-run','--locked','--offline','--jobs','4',
                       '--message-format=json-render-diagnostics',*extra])
        events=[json.loads(line) for line in row['stdout'].splitlines()]
        binaries=[x['executable'] for x in events if x.get('reason')=='compiler-artifact' and x.get('executable')]
        assert len(binaries)==1
        return binaries[0]

    def metadata(report,entry):
        return next(r['test_metadata'] for r in report['entries'] if r['entry']==entry)
    def check_metadata(report,other=False):
        for name in [*outcomes,'unsupported']:
            row=metadata(report,'tests::'+name)
            assert row['status']=='classified' and row['harness']=='libtest' and row['ordinary_test'],row
            assert row['native_name']=='tests::'+name and not row['ignored'] and not row['should_panic'],row
        for name,ignored,panic,reason,message in [
            ('ignored_named',True,False,'fixture skip',None),
            ('expected_panic',False,True,None,None),
            ('expected_named_panic',False,True,None,'NAMED_FIXTURE'),
            ('conditional_ignore',other,False,'conditional skip' if other else None,None),
            ('conditional_panic',False,other,None,'conditional' if other else None),
        ]:
            row=metadata(report,'tests::'+name)
            assert row['status']=='classified' and row['ignored']==ignored and row['should_panic']==panic,row
            assert row['ordinary_test']==(not ignored and not panic),row
            assert row['ignore_reason']==reason and row['panic_message']==message,row
        for name in ['tests::plain','missing']:
            row=metadata(report,name);assert row['status']=='unclassified' and not row['ordinary_test'],row
    original=collect('collect-mixed')
    assert original['artifacts']['files']==list(expected.values()).count('lowered')
    check_metadata(original)
    assert 'RETAINED_PANIC_BODY' not in records[-1]['stderr']
    native=native_binary('build-native')
    for name,ok in outcomes.items():
        run('native-'+name,[native,'--exact','tests::'+name,'--nocapture','--color','never'],ok)
        execute('retained-'+name,original,'tests::'+name,ok)
    for name in ['expected_panic','expected_named_panic']:
        run('native-annotated-'+name,[native,'--exact','tests::'+name,'--color','never'])
        execute('raw-annotated-body-'+name,original,'tests::'+name,False)
    row=run('native-ignored',[native,'--exact','tests::ignored_named','--color','never'])
    assert '1 ignored' in row['stdout']
    cached=collect('cached-pack')
    assert 'Checking audit-pack-fixture ' not in records[-1]['stderr']
    assert cached['artifacts']==original['artifacts']
    collect('dry-audit-after-pack',retain=False)
    current=collect('pack-after-dry-audit')
    execute('after-dry-audit',current,'tests::good',True)

    other=collect('feature-other',['--features','other'])
    check_metadata(other,other=True)
    other_native=native_binary('build-feature-native',['--features','other'])
    run('native-feature-body-fails',[other_native,'--exact','tests::good','--color','never'],False)
    run('native-conditional-panic',[other_native,'--exact','tests::conditional_panic','--color','never'])
    row=run('native-conditional-ignore',[other_native,'--exact','tests::conditional_ignore','--color','never']);assert '1 ignored' in row['stdout']
    execute('feature-body-fails',other,'tests::good',False)
    current=collect('feature-revert')
    check_metadata(current)
    execute('feature-revert',current,'tests::good',True)
    assert artifact(original,'tests::good').read_bytes()==artifact(current,'tests::good').read_bytes()
    assert artifact(other,'tests::good').read_bytes()!=artifact(current,'tests::good').read_bytes()

    selection.write_text(json.dumps(['tests::panic_body']))
    only=collect('selection-change',statuses={'tests::panic_body':'lowered'})
    execute('selection-only-panic',only,'tests::panic_body',False)
    selection.write_text(json.dumps(selected))
    current=collect('selection-revert')
    execute('selection-revert',current,'tests::good',True)
    source_file.write_text(source.replace('assert_eq!(super::value(),13)','assert_eq!(super::value(),99)'))
    edited=collect('body-edit')
    execute('edited-body-fails',edited,'tests::good',False)
    source_file.write_text(source)
    current=collect('body-revert')
    execute('body-revert',current,'tests::good',True)
    source_file.write_text(source+'fn unused_type_error() { let _:u8="bad"; }\n')
    collect('uncalled-type-error',success=False)
    source_file.write_text(source)
    current=collect('type-error-recovery')
    execute('type-error-recovery',current,'tests::good',True)

    # Corrupt only this test's own completed pack, and restore it in every case.
    body=artifact(current,'tests::good');saved=body.read_bytes()
    try:
        body.write_bytes(bytes([saved[0]^1])+saved[1:])
        row=collect('corrupt-body-refused',success=False)
        assert 'artifact digest mismatch' in row['stderr']
    finally:body.write_bytes(saved)
    collect('restored-body')
    moved=body.with_suffix('.test-backup');body.rename(moved)
    try:
        row=collect('missing-body-refused',success=False)
        assert 'missing or resized artifact' in row['stderr']
    finally:moved.rename(body)
    current=collect('missing-body-recovery')
    sidecar=Path(current['artifact_provenance']['audit_path']);saved_manifest=sidecar.read_bytes()
    damaged=json.loads(saved_manifest);damaged['entries'][0]['artifact']['file']='../outside.rbc'
    try:
        sidecar.write_text(json.dumps(damaged))
        row=collect('invalid-filename-refused',success=False)
        assert 'unexpected artifact filename' in row['stderr']
    finally:sidecar.write_bytes(saved_manifest)
    current=collect('manifest-recovery')
    execute('manifest-recovery',current,'tests::good',True)
    collect('instruction-limit-with-audit-refused',['--instruction-limit','1'],success=False)
    row=run('retention-without-audit-refused',[sys.executable,ROOT/'scripts/interpreter.py',
        '--manifest-path',work/'Cargo.toml','--package','audit-pack-fixture','--entry','value','--retain-audit-bodies'],False)
    assert '--retain-audit-bodies requires --audit-entries' in row['stderr']
    # Custom runners can use built-in descriptors but choose different behavior.
    source_file.write_text('#![feature(custom_test_frameworks)]\n#![test_runner(crate::custom_runner)]\n'+source+'fn custom_runner<T>(_: &[&T]) {}\n')
    custom=collect('custom-runner-unclassified')
    assert all(r['test_metadata']['status']=='unclassified' and not r['test_metadata']['ordinary_test'] for r in custom['entries'])
    source_file.write_text(source)
    current=collect('builtin-runner-recovery');check_metadata(current)
    manifest=work/'Cargo.toml';saved_cargo=manifest.read_text()
    manifest.write_text(saved_cargo+'[lib]\nharness=false\n')
    source_file.write_text(source+'#[cfg(test)] fn main() {}\n')
    selection.write_text(json.dumps(['tests::plain']))
    custom=collect('harness-false-unclassified',statuses={'tests::plain':'lowered'})
    assert metadata(custom,'tests::plain')['status']=='unclassified'
    manifest.write_text(saved_cargo);source_file.write_text(source);selection.write_text(json.dumps(selected))
    current=collect('builtin-harness-recovery');check_metadata(current)
    execute('builtin-harness-recovery',current,'tests::good',True)
    assert source_file.read_text()==source
    # Old packs remain intact after every Cargo configuration/source transition.
    execute('original-pack-still-valid',original,'tests::good',True)
    execute('feature-pack-still-distinct',other,'tests::good',False)
    summary=dict(raw=str(work.relative_to(ROOT)),tool_key=key,commands=len(records),
        passed=[r['label'] for r in records],native_outcomes=outcomes,
        source_restored=True,executed_during_collection=False,builtin_test_metadata_checked=True,
        cfg_dependent_ignore_and_panic_checked=True,custom_harnesses_unclassified=True,
        scripts_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__).resolve(),ROOT/'scripts/interpreter.py']})
    (ROOT/'results/audit-artifact-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
