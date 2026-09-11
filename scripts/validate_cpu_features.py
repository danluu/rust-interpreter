#!/usr/bin/env python3
"""Compare checked CPU queries and ordinary feature-detection MIR with native Rust.

Run under the global benchmark lock after installing the candidate tools.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import time
from interpreter import ROOT, TOOLCHAIN, checked_tools, installed_tools
from std_mir import checked_std_mir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default='cpu-feature-focused-' + str(time.time_ns()))
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in ['.', '..']: parser.error('invalid run id')
    tools, key = checked_tools()
    old, old_key = installed_tools('07d14b7319a258900c1501322e65f3e43cd0977334920c8044035b42bfed9c9f')
    work = ROOT / '.work' / args.run_id; work.mkdir()
    source = ROOT / 'tests/cpu_feature_fixture.rs'
    frozen = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [source, Path(__file__).resolve()]}
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'CARGO_PROFILE_')) or name in [
            'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
            'RUSTC_WORKSPACE_WRAPPER', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET', 'CARGO_INCREMENTAL',
        ]: env.pop(name)
    env.update(RUST_INTERP_DEMAND_BODIES='0', RUST_INTERP_DEMAND_CACHE='0', RUST_INTERP_EXPORT_TEST='0')
    records = []
    def run(label, command, variables=None, success=True):
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in frozen.items())
        command = list(map(str, command)); start = time.perf_counter()
        p = subprocess.Popen(command, cwd=ROOT, env=env | dict(variables or {}), text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        active = dict(pid=p.pid, parent_pid=os.getpid(), command=command, cwd=str(ROOT),
                      started_at=time.time(), status='running')
        (work / 'active-command.json').write_text(json.dumps(active))
        stdout, stderr = p.communicate(); active.update(status='finished', returncode=p.returncode)
        (work / 'active-command.json').write_text(json.dumps(active))
        row = dict(label=label, identity=active, stdout=stdout, stderr=stderr, seconds=time.perf_counter()-start)
        records.append(row)
        with (work / 'commands.jsonl').open('a') as log: log.write(json.dumps(row)+'\n')
        assert (p.returncode == 0) == success and 'internal compiler error' not in stderr, row
        return row
    std_root, _, std_key, _ = checked_std_mir(TOOLCHAIN)
    seeds = [0, 1, 2, 3, 127, 128, 255, 256, 2**63-1, 2**63, 2**64-1]
    seeds += [random.Random(i).getrandbits(64) for i in range(100)]
    artifacts = []; outputs = {}
    def export(label, entry, path=source, flags=(), metadata=False, inline=False, trap=False, success=True):
        output = work / (label+'.rbc')
        variables = dict(RUST_INTERP_ENTRY=entry, RUST_INTERP_OUTPUT=str(output))
        if inline: variables['RUST_INTERP_INLINE_LEAVES'] = '1'
        if trap: variables['RUST_INTERP_TRAP_UNSUPPORTED_CALLS'] = '1'
        command = [tools/'rust-interp-mir-export', path, '--crate-name', 'cpu_feature_fixture',
                   '--edition=2024', '--emit=metadata', *flags, '-o', work/(label+'.rmeta')]
        if metadata: command += ['--sysroot', std_root]
        row = run('export:'+label, command, variables, success)
        assert output.exists() == success
        if success: artifacts.append(dict(configuration=label,path=str(output.relative_to(ROOT)),sha256=hashlib.sha256(output.read_bytes()).hexdigest()))
        return output, row
    for mode, flags in [('mir0',['-Zmir-opt-level=0']), ('mir3',['-Zmir-opt-level=3']), ('optimized',['-O'])]:
        native = work/('native-'+mode)
        run('build-native:'+mode,['rustc','+'+TOOLCHAIN,source,'--edition=2024',*flags,'-o',native])
        expected={name:run('native:'+mode+':'+name,[native,name,*seeds])['stdout'].splitlines() for name in ['query','detect','local']}
        for values in expected.values(): assert len(values)==len(seeds)
        if outputs: assert outputs==expected
        outputs=expected
        for inline in [False,True]:
            for name,entry,metadata in [('query','rust_interp_entry',False),('query','rust_interp_entry',True),
                                        ('detect','detected_entry',True),('local','local_entry',False)]:
                label=f'{mode}-{name}-std{int(metadata)}-inline{int(inline)}'
                output,_=export(label,entry,flags=flags,metadata=metadata,inline=inline)
                for seed,want in zip(seeds,expected[name]):
                    for engine in ['interpreter','jit']:
                        row=run(f'{label}:{engine}:{seed}',[tools/'rust-interp-vm','--engine',engine,output,seed])
                        assert row['stdout'].strip()==want,row
                print('PASS',label,'111 seeds, both engines',flush=True)
    for entry,message in [('rejected_name','unsupported CPU-feature query name'),
                          ('rejected_length','four-byte output buffer'),('rejected_write','does not support writes')]:
        for inline in [False,True]:
            output,_=export(entry+str(inline),entry,flags=['-Zmir-opt-level=0'],inline=inline)
            for engine in ['interpreter','jit']:
                row=run(entry+':'+engine,[tools/'rust-interp-vm','--engine',engine,output,0],success=False)
                assert message in row['stderr'],row
    invalids = {
        'return-width': ('extern "C"', '*const i8, p:*mut u8, l:*mut usize, n:*mut u8, z:usize', 'i64', 'std::ptr::null(), std::ptr::null_mut(), std::ptr::null_mut(), std::ptr::null_mut(), 0'),
        'length-pointee': ('extern "C"', '*const i8, p:*mut u8, l:*mut u32, n:*mut u8, z:usize', 'i32', 'std::ptr::null(), std::ptr::null_mut(), std::ptr::null_mut(), std::ptr::null_mut(), 0'),
        'wide-name': ('extern "C"', '*const [u8], p:*mut u8, l:*mut usize, n:*mut u8, z:usize', 'i32', 'std::ptr::slice_from_raw_parts(std::ptr::null(), 0), std::ptr::null_mut(), std::ptr::null_mut(), std::ptr::null_mut(), 0'),
        'unwind-abi': ('extern "C-unwind"', '*const i8, p:*mut u8, l:*mut usize, n:*mut u8, z:usize', 'i32', 'std::ptr::null(), std::ptr::null_mut(), std::ptr::null_mut(), std::ptr::null_mut(), 0'),
    }
    for label,(abi,signature,result,arguments) in invalids.items():
        path=work/(label+'.rs')
        path.write_text(f'unsafe {abi} {{ fn sysctlbyname(name:{signature})->{result}; }}\npub fn rust_interp_entry(_:u64)->u64 {{ unsafe {{ sysctlbyname({arguments}) as u64 }} }}\nfn main() {{}}\n')
        for trap in [False,True]:
            _,row=export(label+str(trap),'rust_interp_entry',path=path,trap=trap,success=False)
            assert 'invalid sysctlbyname signature' in row['stderr'],row
    # Old V5 programs remain usable. New opcodes cannot silently run on old VMs.
    legacy=ROOT/'.work/wide-pointer-focused-02/mir3-metadata-inline0.rbc'
    for seed in [0,255,2**64-1]:
        for engine in ['interpreter','jit']:
            before=run('legacy-old',[old/'rust-interp-vm','--engine',engine,legacy,seed])
            after=run('legacy-new',[tools/'rust-interp-vm','--engine',engine,legacy,seed])
            assert before['stdout']==after['stdout']
    new=ROOT/artifacts[0]['path']
    for engine in ['interpreter','jit']:
        row=run('new-opcode-old-vm',[old/'rust-interp-vm','--engine',engine,new,0],success=False)
        assert 'variant' in row['stderr'],row
    summary=dict(status='passed',tool_key=key,tool_binaries=json.loads((tools/'ready.json').read_text()),commands=len(records),
                 inputs_per_configuration=len(seeds),positive_configurations=24,artifacts=artifacts,std_mir_key=std_key,
                 native_feature_results=outputs,raw=str(work.relative_to(ROOT)),frozen_inputs=frozen,
                 baseline_tool_key=old_key,strict_frontend=True,legacy_v5_compatible=True,new_opcode_rejected_by_old_vm=True)
    (work/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (work/'records.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(dict(status='passed',commands=len(records),raw=summary['raw'])))


if __name__=='__main__': main()
