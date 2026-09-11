#!/usr/bin/env python3
"""Validate opt-in export, Cargo invalidation, diagnostics and native results.

Run under the task's global benchmark lock, after installing the current tools.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from interpreter import ROOT, TOOLCHAIN, checked_tools, require_export_option


def main():
    tools,key=checked_tools()
    require_export_option(tools,key,'inline-leaves')
    work=ROOT/'.work'/('leaf-inline-launcher-validation-'+str(time.time_ns()))
    (work/'src').mkdir(parents=True)
    (work/'Cargo.toml').write_text('[package]\nname="leaf-inline-fixture"\nversion="0.1.0"\nedition="2024"\n[workspace]\n')
    source='''#[inline(never)]
fn leaf(a:u64)->u64 {
    if a==9 { panic!("INLINE_COLD_FAILURE"); }
    if a & 1 == 0 { a.wrapping_mul(3) } else { a.wrapping_add(7) }
}
pub fn entry(a:u64)->u64 { leaf(a).wrapping_add(leaf(a.wrapping_add(2))) }
#[cfg(test)] mod tests {
    #[test] fn results() { assert_eq!(super::entry(2),18); assert_eq!(super::entry(3),22); }
}
'''
    file=work/'src/lib.rs';file.write_text(source)
    env=os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_','CARGO_PROFILE_')) or name in [
            'RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER',
            'RUSTC_WORKSPACE_WRAPPER','CARGO_TARGET_DIR','CARGO_BUILD_TARGET','CARGO_INCREMENTAL']:
            env.pop(name,None)
    # Keep fixture leaf calls intact; their optimization is the pass under test.
    env.update(RUSTFLAGS='-Zmir-opt-level=0',CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
    records=[]
    def run(label,command,want=0,expected=None,extra_env=None):
        child_env=env|dict(extra_env or {})
        started=time.perf_counter()
        p=subprocess.Popen(list(map(str,command)),cwd=work,env=child_env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        active=dict(pid=p.pid,parent_pid=os.getpid(),command=list(map(str,command)),cwd=str(work),started_at=time.time(),status='running')
        (work/'active-command.json').write_text(json.dumps(active))
        stdout,stderr=p.communicate();active.update(status='finished',returncode=p.returncode)
        (work/'active-command.json').write_text(json.dumps(active))
        row=dict(label=label,command=list(map(str,command)),returncode=p.returncode,stdout=stdout,stderr=stderr,seconds=time.perf_counter()-started)
        records.append(row);(work/'records.json').write_text(json.dumps(records,indent=2))
        assert (p.returncode==0)==(want==0),row
        if expected is not None:assert stdout.strip()==expected,row
        return row
    cargo=['cargo','+'+TOOLCHAIN]
    run('lockfile',[*cargo,'generate-lockfile','--offline'])
    base=[sys.executable,ROOT/'scripts/interpreter.py','--manifest-path',work/'Cargo.toml',
          '--package','leaf-inline-fixture','--tool-key',key]
    def entry(label,flags=(),argument='2',want=0,expected='18',extra_env=None):
        row=run(label,[*base,'--entry','entry',*flags,'--',argument],want,expected,extra_env)
        if want==0:
            traces=[json.loads(line.split(': ',1)[1]) for line in row['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
            assert len(traces)==1
            row['launch']=traces[0]
            content=Path(traces[0]['artifact_path']).read_bytes()
            assert hashlib.sha256(content).hexdigest()==traces[0]['artifact_sha256']
        return row
    normal=entry('normal')
    on=entry('inline-jit',['--inline-leaves','--engine','jit'])
    assert on['launch']['inline_leaves'] is True
    assert normal['launch']['artifact_path']==on['launch']['artifact_path']
    assert normal['launch']['artifact_sha256']!=on['launch']['artifact_sha256']
    assert 'rust-interp-inline: sites=0 ' not in on['stderr'] and 'rust-interp-inline: sites=' in on['stderr']
    warm=entry('inline-fresh',['--inline-leaves','--engine','jit'])
    assert warm['launch']['artifact_sha256']==on['launch']['artifact_sha256']
    assert 'Checking leaf-inline-fixture' not in warm['stderr']
    off=entry('off-again')
    assert off['launch']['artifact_sha256']==normal['launch']['artifact_sha256']
    assert 'Checking leaf-inline-fixture' in off['stderr']
    ambient=entry('ambient-option-sanitized',extra_env={'RUST_INTERP_INLINE_LEAVES':'1'})
    assert ambient['launch']['artifact_sha256']==normal['launch']['artifact_sha256']
    assert ambient['launch']['inline_leaves'] is False
    for engine in ['interpreter','jit']:
        entry('odd-'+engine,['--inline-leaves','--engine',engine],argument='3',expected='22')
        failed=entry('cold-panic-'+engine,['--inline-leaves','--engine',engine],argument='9',want=1,expected='')
        assert 'rust-interp-vm: guest trap:' in failed['stderr']
        assert 'std::rt::panic_fmt' in failed['stderr'] and 'in leaf[]' in failed['stderr']
        control=entry('cold-panic-control-'+engine,['--engine',engine],argument='9',want=1,expected='')
        assert 'std::rt::panic_fmt' in control['stderr'] and 'in leaf[]' in control['stderr']
    native=[*cargo,'test','--manifest-path',work/'Cargo.toml','--lib','--locked','--offline','--jobs','4',
            '--target-dir',work/'native','--','--exact','tests::results','--test-threads=1']
    # Native controls use the same source but no experimental MIR flags.
    run('native-control',native,extra_env={'RUSTFLAGS':''})
    for engine in ['interpreter','jit']:
        run('test-body-'+engine,[*base,'--test-body','--entry','tests::results','--inline-leaves','--engine',engine],expected='0')
    try:
        file.write_text(source.replace('wrapping_mul(3)','wrapping_mul(4)'))
        run('native-semantic-edit-fails',native,want=1,extra_env={'RUSTFLAGS':''})
        for engine in ['interpreter','jit']:
            failed=run('semantic-edit-fails-'+engine,[*base,'--test-body','--entry','tests::results','--inline-leaves','--engine',engine],want=1,expected='')
            assert 'guest trap:' in failed['stderr']
        file.write_text(source+'\nfn uncalled_type_error() { let _: u32 = false; }\n')
        failed=entry('strict-uncalled-error',['--inline-leaves'],want=1,expected='')
        assert 'mismatched types' in failed['stderr'] and 'rust-interp-vm:' not in failed['stderr']
    finally:file.write_text(source)
    entry('source-revert',['--inline-leaves','--engine','jit'])
    # The old qualified build has no capability manifest. Do not launch Cargo.
    old='0d0d7b9092fe9e29320b35d7b04eed4655a81b7d21e0cd90bff9abaecf85ed34'
    if (ROOT/'.work/interpreter-tools'/old/'ready.json').exists():
        failed=run('unsupported-old-exporter',[*base,'--tool-key',old,'--entry','entry','--inline-leaves','--','2'],want=1,expected='')
        assert 'does not support --inline-leaves' in failed['stderr'] and 'Checking ' not in failed['stderr']
    selection=work/'selection.json';selection.write_text(json.dumps(['tests::results']))
    row=run('retained-audit',[*base,'--test-body','--audit-entries',selection,'--retain-audit-bodies','--inline-leaves'])
    audit=json.loads(row['stdout']);assert audit['inline_leaves'] is True and audit['lowered']==1
    pack=Path(audit['artifacts']['directory'])
    for engine in ['interpreter','jit']:
        run('retained-audit-'+engine,[tools/'rust-interp-vm','--engine',engine,pack/audit['entries'][0]['artifact']['file']],expected='0')
    (work/'records.json').write_text(json.dumps(records,indent=2))
    print(json.dumps(dict(tool_key=key,commands=len(records),work=str(work),status='passed'),indent=2))


if __name__=='__main__':main()
