#!/usr/bin/env python3
"""Compare guest C/System allocation with native Rust, including ABI and V5 checks."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from interpreter import ROOT, TOOLCHAIN, checked_tools, installed_tools
from std_mir import checked_std_mir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in ['.', '..']:
        parser.error('invalid run id')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    tools, key = checked_tools()
    baseline, baseline_key = installed_tools('76af5541c56a2cd58ad9eae75b91ee9f3c6ad4327f0a8d082cde19573a2d6404')
    work = ROOT / '.work' / args.run_id
    work.mkdir()
    source = ROOT / 'tests/c_allocator_fixture.rs'
    paths = [source, Path(__file__).resolve(), ROOT / 'scripts/interpreter.py', ROOT / 'scripts/std_mir.py']
    for folder in ['bytecode', 'mir-export']:
        paths += sorted((ROOT / 'crates' / folder).rglob('*.rs'))
    frozen = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'CARGO_PROFILE_')) or name in [
            'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
            'RUSTC_WORKSPACE_WRAPPER', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET', 'CARGO_INCREMENTAL',
        ]:
            env.pop(name)
    env.update(RUST_INTERP_DEMAND_BODIES='0', RUST_INTERP_DEMAND_CACHE='0', RUST_INTERP_EXPORT_TEST='0')
    records = []

    def run(label, command, variables=None, success=True):
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest for p, digest in frozen.items())
        command = list(map(str, command))
        start = time.perf_counter()
        process = subprocess.Popen(command, cwd=ROOT, env=env | dict(variables or {}),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        identity = dict(pid=process.pid, parent_pid=os.getpid(), command=command, cwd=str(ROOT),
                        started_at=time.time(), status='running')
        (work / 'active-command.json').write_text(json.dumps(identity, indent=2) + '\n')
        stdout, stderr = process.communicate()
        identity.update(status='finished', returncode=process.returncode)
        (work / 'active-command.json').write_text(json.dumps(identity, indent=2) + '\n')
        row = dict(label=label, identity=identity, stdout=stdout, stderr=stderr, seconds=time.perf_counter() - start)
        records.append(row)
        with (work / 'commands.jsonl').open('a') as log:
            log.write(json.dumps(row) + '\n')
        assert (process.returncode == 0) == success and 'internal compiler error' not in stderr, row
        return row

    std_root, _, std_key, _ = checked_std_mir(TOOLCHAIN)
    seeds = [0, 1, 2, 7, 31, 63, 79, 126, 127, 255, 2**63, 2**64 - 1]
    artifacts = []
    outputs = None

    def export(label, entry, flags, metadata, inline, path=source, trap=False, success=True):
        output = work / (label + '.rbc')
        variables = dict(RUST_INTERP_ENTRY=entry, RUST_INTERP_OUTPUT=str(output))
        if inline:
            variables['RUST_INTERP_INLINE_LEAVES'] = '1'
        if trap:
            variables['RUST_INTERP_TRAP_UNSUPPORTED_CALLS'] = '1'
        command = [tools / 'rust-interp-mir-export', path, '--crate-name', 'c_allocator_fixture',
                   '--edition=2024', '--emit=metadata', *flags, '-o', work / (label + '.rmeta')]
        if metadata:
            command += ['--sysroot', std_root]
        row = run('export:' + label, command, variables, success)
        assert output.exists() == success
        if success:
            artifacts.append(dict(configuration=label, path=str(output.relative_to(ROOT)),
                                  sha256=hashlib.sha256(output.read_bytes()).hexdigest()))
        return output, row

    for mode, flags in [('mir0', ['-Zmir-opt-level=0']), ('mir3', ['-Zmir-opt-level=3']), ('optimized', ['-O'])]:
        native = work / ('native-' + mode)
        run('build-native:' + mode, ['rustc', '+' + TOOLCHAIN, source, '--edition=2024', *flags, '-o', native])
        expected = {name: run('native:' + mode + ':' + name, [native, name, *seeds])['stdout'].splitlines()
                    for name in ['raw', 'system']}
        assert all(len(values) == len(seeds) for values in expected.values())
        if outputs is not None:
            assert outputs == expected
        outputs = expected
        for inline in [False, True]:
            for name, entry, metadata in [('raw', 'rust_interp_entry', False), ('raw', 'rust_interp_entry', True),
                                          ('system', 'system_entry', True)]:
                label = f'{mode}-{name}-std{int(metadata)}-inline{int(inline)}'
                output, _ = export(label, entry, flags, metadata, inline)
                for seed, want in zip(seeds, expected[name]):
                    for engine in ['interpreter', 'jit']:
                        row = run(f'{label}:{engine}:{seed}', [tools / 'rust-interp-vm', '--engine', engine, output, seed])
                        assert row['stdout'].strip() == want, row
                print('PASS', label, '12 seeds, both engines', flush=True)

    invalids = [
        ('malloc-size', 'malloc', 'extern "C"', 'n:u32', '*mut u8', '1'),
        ('calloc-return', 'calloc', 'extern "C"', 'n:usize, s:usize', 'u64', '1, 1'),
        ('free-return', 'free', 'extern "C"', 'p:*mut u8', 'i32', 'std::ptr::null_mut()'),
        ('realloc-size', 'realloc', 'extern "C"', 'p:*mut u8, n:u32', '*mut u8', 'std::ptr::null_mut(), 1'),
        ('posix-output', 'posix_memalign', 'extern "C"', 'p:*mut u8, a:usize, n:usize', 'i32', 'std::ptr::null_mut(), 16, 1'),
        ('errno-pointee', '__error', 'extern "C"', '', '*mut u64', ''),
        ('malloc-unwind', 'malloc', 'extern "C-unwind"', 'n:usize', '*mut u8', '1'),
        ('malloc-fat-pointer', 'malloc', 'extern "C"', 'n:usize', '*mut [u8]', '1'),
    ]
    for label, symbol, abi, signature, output_type, arguments in invalids:
        path = work / (label + '.rs')
        path.write_text(f'unsafe {abi} {{ fn {symbol}({signature}) -> {output_type}; }}\n'
                        f'pub fn rust_interp_entry(_:u64)->u64 {{ unsafe {{ let _ = {symbol}({arguments}); }} 0 }}\nfn main() {{}}\n')
        for trap in [False, True]:
            _, row = export(label + str(trap), 'rust_interp_entry', ['-Zmir-opt-level=0'], False, False,
                            path=path, trap=trap, success=False)
            assert f'invalid {symbol} signature for guest C allocator' in row['stderr'], row

    legacy = ROOT / '.work/wide-pointer-focused-02/mir3-metadata-inline0.rbc'
    for seed in [0, 255, 2**64 - 1]:
        for engine in ['interpreter', 'jit']:
            before = run('legacy-before', [baseline / 'rust-interp-vm', '--engine', engine, legacy, seed])
            after = run('legacy-after', [tools / 'rust-interp-vm', '--engine', engine, legacy, seed])
            assert before['stdout'] == after['stdout']
    for engine in ['interpreter', 'jit']:
        row = run('new-opcode-old-vm', [baseline / 'rust-interp-vm', '--engine', engine, ROOT / artifacts[0]['path'], 0], success=False)
        assert 'variant' in row['stderr'], row
    summary = dict(status='passed', tool_key=key, tool_binaries=json.loads((tools / 'ready.json').read_text()),
                   commands=len(records), positive_configurations=18, inputs_per_configuration=len(seeds),
                   native_results=outputs, artifacts=artifacts, std_mir_key=std_key, frozen_inputs=frozen,
                   baseline_tool_key=baseline_key, strict_frontend=True, legacy_v5_compatible=True,
                   new_opcode_rejected_by_old_vm=True, guest_tls_destructors_implemented=False)
    (work / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('C_ALLOCATOR_NATIVE_PASS', len(records), key, flush=True)


if __name__ == '__main__':
    main()
