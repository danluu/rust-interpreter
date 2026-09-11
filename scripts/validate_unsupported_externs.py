#!/usr/bin/env python3
"""Check explicit unavailable-call traps, strict checking and cache transitions.

Run under the caller's global benchmark lock. This is a correctness fixture;
its unchanged commands test cache invalidation and are not speed measurements.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from interpreter import ROOT, TOOLCHAIN, checked_tools, require_export_option, unavailable_call_failure


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',default='unsupported-extern-validation-'+str(time.time_ns()))
    args=parser.parse_args()
    if Path(args.run_id).name!=args.run_id or args.run_id in ['.','..']:parser.error('invalid run id')
    tools,key=checked_tools()
    require_export_option(tools,key,'trap-unsupported-calls')
    work=ROOT/'.work'/args.run_id
    (work/'src').mkdir(parents=True)
    (work/'Cargo.toml').write_text('[package]\nname="unsupported-extern-fixture"\nversion="0.1.0"\nedition="2024"\n[workspace]\n')
    source=(ROOT/'tests/extern_fixture.rs').read_text()
    file=work/'src/lib.rs';file.write_text(source)
    env=os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_','CARGO_PROFILE_')) or name in [
            'RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER',
            'RUSTC_WORKSPACE_WRAPPER','CARGO_TARGET_DIR','CARGO_BUILD_TARGET','CARGO_INCREMENTAL']:
            env.pop(name,None)
    env.update(RUSTFLAGS='-Zmir-opt-level=0',CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
    inputs=[ROOT/'tests/extern_fixture.rs',ROOT/'scripts/interpreter.py',Path(__file__).resolve()]
    for folder in ['bytecode','mir-export']:
        inputs+=sorted((ROOT/'crates'/folder).rglob('*.rs'))
        inputs.append(ROOT/'crates'/folder/'Cargo.toml')
    inputs += [ROOT/'Cargo.toml',ROOT/'Cargo.lock']
    frozen={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    records=[]
    def run(label,command,ok=True,expected=None,extra_env=None):
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in frozen.items())
        child_env=env|dict(extra_env or {})
        command=list(map(str,command));started=time.perf_counter()
        p=subprocess.Popen(command,cwd=work,env=child_env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        active=dict(pid=p.pid,parent_pid=os.getpid(),command=command,cwd=str(work),started_at=time.time(),status='running')
        (work/'active-command.json').write_text(json.dumps(active))
        stdout,stderr=p.communicate();active.update(status='finished',returncode=p.returncode)
        (work/'active-command.json').write_text(json.dumps(active))
        row=dict(label=label,command=command,returncode=p.returncode,stdout=stdout,stderr=stderr,seconds=time.perf_counter()-started)
        records.append(row);(work/'records.json').write_text(json.dumps(records,indent=2))
        assert (p.returncode==0)==ok,row
        if expected is not None:assert stdout.strip()==expected,row
        launches=[json.loads(line.split(': ',1)[1]) for line in stderr.splitlines() if line.startswith('rust-interp-launch: ')]
        if launches:
            assert len(launches)==1
            row['launch']=launches[0]
        diagnostics=[json.loads(line.split(': ',1)[1]) for line in stderr.splitlines() if line.startswith('rust-interp-unavailable: ')]
        if diagnostics:
            assert len(diagnostics)==1
            row['unavailable']=diagnostics[0]
        return row
    cargo=['cargo','+'+TOOLCHAIN]
    run('lockfile',[*cargo,'generate-lockfile','--offline'])
    base=[sys.executable,ROOT/'scripts/interpreter.py','--manifest-path',work/'Cargo.toml',
          '--package','unsupported-extern-fixture','--tool-key',key]
    def entry(label,name='entry',value='0',flags=(),ok=True,expected='17',extra_env=None):
        return run(label,[*base,'--entry',name,*flags,'--',*([value] if value is not None else [])],ok,expected,extra_env)
    option=['--trap-unsupported-calls']
    native=[*cargo,'test','--manifest-path',work/'Cargo.toml','--lib','--locked','--offline','--jobs','4',
            '--target-dir',work/'native','--','--test-threads=1']
    run('native-all',native,extra_env={'RUSTFLAGS':''})
    off=entry('default-rejects',ok=False,expected='')
    assert 'rust-interp-vm:' not in off['stderr'] and 'cannot lower' in off['stderr']
    on=entry('enabled-cold',flags=[*option,'--engine','jit'])
    assert on['launch']['trap_unsupported_calls'] is True
    assert [s['name'] for s in on['unavailable']['unavailable_calls']]==['getpid']
    assert on['unavailable']['unavailable_calls'][0]['kind']=='foreign'
    warm=entry('enabled-fresh',flags=[*option,'--engine','jit'])
    assert 'Checking unsupported-extern-fixture' not in warm['stderr']
    assert warm['unavailable']==on['unavailable']
    assert warm['launch']['artifact_sha256']==on['launch']['artifact_sha256']
    # A mismatched diagnostic sidecar must fail before guest execution.
    sidecar=Path(warm['launch']['call_report_path']);saved=sidecar.read_bytes()
    try:
        bad=json.loads(saved);bad['artifact_sha256']='0'*64;sidecar.write_text(json.dumps(bad))
        rejected=entry('mismatched-sidecar',flags=option,ok=False,expected='')
        assert 'incompatible unavailable-call report' in rejected['stderr']
        assert 'rust-interp-vm:' not in rejected['stderr']
    finally:sidecar.write_bytes(saved)
    for inline in [False,True]:
        flags=option+(['--inline-leaves'] if inline else [])
        for engine in ['interpreter','jit']:
            variant=f'{engine}-inline-{inline}'
            cold=entry('cold-'+variant,flags=[*flags,'--engine',engine])
            hot=entry('hot-'+variant,value='1',flags=[*flags,'--engine',engine],ok=False,expected='')
            sites=hot['unavailable']['unavailable_calls']
            assert unavailable_call_failure(hot['stderr'],sites)['name']=='getpid'
            if inline:assert '[inlined from ' in hot['stderr']
            local=entry('local-name-'+variant,name='local_name',value='3',flags=[*flags,'--engine',engine],expected='26')
            assert local['unavailable']['unavailable_calls']==[]
            arg=entry('argument-before-call-'+variant,name='argument_order',value='7',flags=[*flags,'--engine',engine],ok=False,expected='')
            assert [s['name'] for s in arg['unavailable']['unavailable_calls']]==['abs']
            assert 'guest trap:' in arg['stderr'] and unavailable_call_failure(arg['stderr'],arg['unavailable']['unavailable_calls']) is None
            boundary=entry('argument-call-'+variant,name='argument_order',value='8',flags=[*flags,'--engine',engine],ok=False,expected='')
            assert unavailable_call_failure(boundary['stderr'],boundary['unavailable']['unavailable_calls'])['name']=='abs'
            entry('intrinsic-cold-'+variant,name='intrinsic_entry',flags=[*flags,'--engine',engine],expected='31')
            intrinsic=entry('intrinsic-hot-'+variant,name='intrinsic_entry',value='1',flags=[*flags,'--engine',engine],ok=False,expected='')
            site=unavailable_call_failure(intrinsic['stderr'],intrinsic['unavailable']['unavailable_calls'])
            assert site['kind']=='intrinsic' and site['name']=='catch_unwind'
            if inline:assert '[inlined from ' in intrinsic['stderr']
            arg=entry('intrinsic-argument-before-call-'+variant,name='intrinsic_argument_order',value='7',flags=[*flags,'--engine',engine],ok=False,expected='')
            assert 'guest trap:' in arg['stderr'] and unavailable_call_failure(arg['stderr'],arg['unavailable']['unavailable_calls']) is None
            boundary=entry('intrinsic-argument-call-'+variant,name='intrinsic_argument_order',value='8',flags=[*flags,'--engine',engine],ok=False,expected='')
            assert unavailable_call_failure(boundary['stderr'],boundary['unavailable']['unavailable_calls'])['name']=='catch_unwind'
    # Return to exactly the same entry and settings before the on/off transition.
    entry('on-before-off',flags=option)
    off=entry('off-again',ok=False,expected='')
    assert 'Checking unsupported-extern-fixture' in off['stderr'] and 'rust-interp-vm:' not in off['stderr']
    entry('on-again',flags=option)
    entry('intrinsic-on-before-off',name='intrinsic_entry',flags=option,expected='31')
    failed=entry('intrinsic-off-rejects',name='intrinsic_entry',ok=False,expected='')
    assert 'unsupported intrinsic catch_unwind' in failed['stderr'] and 'rust-interp-vm:' not in failed['stderr']
    entry('intrinsic-on-again',name='intrinsic_entry',flags=option,expected='31')
    ambient=entry('ambient-option-sanitized',ok=False,expected='',extra_env={'RUST_INTERP_TRAP_UNSUPPORTED_CALLS':'1'})
    assert 'cannot lower' in ambient['stderr'] and 'rust-interp-vm:' not in ambient['stderr']
    indirect=entry('indirect-remains-blocked',name='indirect',value=None,flags=option,ok=False,expected='')
    assert 'cannot lower' in indirect['stderr'] and 'rust-interp-vm:' not in indirect['stderr']
    try:
        file.write_text(source.replace('if mode == 0 { 17 }','if mode == 0 { 18 }'))
        failed=run('native-wrong-production-edit',native,ok=False,extra_env={'RUSTFLAGS':''})
        assert 'test result: FAILED.' in failed['stdout']
        for engine in ['interpreter','jit']:
            failed=run('wrong-production-edit-'+engine,[*base,'--test-body','--entry','tests::cold',*option,'--engine',engine],ok=False,expected='')
            assert 'guest trap:' in failed['stderr'] or 'guest assertion:' in failed['stderr']
            assert unavailable_call_failure(failed['stderr'],failed['unavailable']['unavailable_calls']) is None
        for label,extra,diagnostic in [
            ('strict-type','\nfn unused_type_error() { let _:u32=false; }\n','mismatched types'),
            ('strict-borrow','\nfn unused_borrow_error() { let mut v=0; let a=&mut v; let b=&mut v; *a+=*b; }\n','cannot borrow'),
        ]:
            file.write_text(source+extra)
            failed=entry(label,flags=option,ok=False,expected='')
            assert diagnostic in failed['stderr'] and 'rust-interp-vm:' not in failed['stderr']
        # Invalid declaration is checked only by export; never invoke it natively.
        file.write_text(source+'''\nunsafe extern "C" {
    #[link_name="CCRandomGenerateBytes"] fn bad_random(value:u64)->i32;
}
pub fn wrong_signature()->i32 { unsafe { bad_random(0) } }
''')
        failed=entry('known-primitive-signature',name='wrong_signature',value=None,flags=option,ok=False,expected='')
        assert 'invalid CCRandomGenerateBytes signature' in failed['stderr'] and 'rust-interp-vm:' not in failed['stderr']
    finally:file.write_text(source)
    entry('source-revert',flags=[*option,'--inline-leaves','--engine','jit'])
    old='67a3a330361963416e615816c84c0f80cf2dae3d865e5d41a9e5e97e285ac71e'
    if (ROOT/'.work/interpreter-tools'/old/'ready.json').exists():
        failed=entry('old-exporter-rejected',flags=[*option,'--tool-key',old],ok=False,expected='')
        assert 'does not support --trap-unsupported-calls' in failed['stderr'] and 'Checking ' not in failed['stderr']
    selection=work/'selection.json';selection.write_text(json.dumps(['tests::cold','tests::hot','tests::intrinsic_cold','tests::intrinsic_hot']))
    for inline in [False,True]:
        flags=option+(['--inline-leaves'] if inline else [])
        row=run('audit-inline-'+str(inline),[*base,'--test-body','--audit-entries',selection,'--retain-audit-bodies',*flags])
        audit=json.loads(row['stdout']);assert audit['trap_unsupported_calls'] is True and audit['lowered']==4
        pack=Path(audit['artifacts']['directory'])
        for body in audit['entries']:
            cold=body['entry'].endswith('cold')
            for engine in ['interpreter','jit']:
                r=run(f'audit-{body["entry"]}-{engine}-{inline}',[tools/'rust-interp-vm','--engine',engine,pack/body['artifact']['file']],ok=cold,expected='0' if cold else '')
                if not cold:
                    expected_name='catch_unwind' if 'intrinsic' in body['entry'] else 'getpid'
                    assert unavailable_call_failure(r['stderr'],body['unavailable_calls'])['name']==expected_name
    assert file.read_text()==source
    (work/'records.json').write_text(json.dumps(records,indent=2)+'\n')
    summary=dict(tool_key=key,commands=len(records),work=str(work),status='passed',frozen_inputs=frozen)
    (work/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
