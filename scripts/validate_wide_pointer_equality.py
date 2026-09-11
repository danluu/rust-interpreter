#!/usr/bin/env python3
"""Native differential checks for address-and-metadata pointer equality.

Run under the global benchmark lock after installing the current tools.
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
    parser.add_argument('--run-id', default='wide-pointer-equality-' + str(time.time_ns()))
    parser.add_argument('--baseline-tool-key')
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in ['.', '..']:
        parser.error('invalid run id')
    tools, key = checked_tools()
    work = ROOT / '.work' / args.run_id
    work.mkdir()
    source = ROOT / 'tests/wide_pointer_fixture.rs'
    frozen = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [source, Path(__file__).resolve()]}
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'CARGO_PROFILE_')) or name in [
            'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
            'RUSTC_WORKSPACE_WRAPPER', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET', 'CARGO_INCREMENTAL',
        ]:
            env.pop(name)
    env.update(RUST_INTERP_ENTRY='rust_interp_entry', RUST_INTERP_DEMAND_BODIES='0',
               RUST_INTERP_DEMAND_CACHE='0', RUST_INTERP_EXPORT_TEST='0')
    records = []

    def run(label, command, variables=None, success=True):
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in frozen.items())
        command = list(map(str, command))
        start = time.perf_counter()
        p = subprocess.Popen(command, cwd=ROOT, env=env | dict(variables or {}),
                             text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        active = dict(pid=p.pid, parent_pid=os.getpid(), command=command, cwd=str(ROOT),
                      started_at=time.time(), status='running')
        (work / 'active-command.json').write_text(json.dumps(active))
        stdout, stderr = p.communicate()
        active.update(status='finished', returncode=p.returncode)
        (work / 'active-command.json').write_text(json.dumps(active))
        row = dict(label=label, identity=active, stdout=stdout, stderr=stderr,
                   seconds=time.perf_counter() - start)
        records.append(row)
        with (work / 'commands.jsonl').open('a') as log:
            log.write(json.dumps(row) + '\n')
        assert (p.returncode == 0) == success and 'internal compiler error' not in stderr, row
        return row

    std_root, _, std_key, _ = checked_std_mir(TOOLCHAIN)
    seeds = [0, 1, 2, 3, 127, 128, 255, 256, 2**63-1, 2**63, 2**64-1]
    seeds += [random.Random(i).getrandbits(64) for i in range(100)]
    modes = dict(mir0=['-Zmir-opt-level=0'], mir1=['-Zmir-opt-level=1'],
                 mir3=['-Zmir-opt-level=3'], optimized=['-O'])
    expected = None
    artifacts = []
    for mode, flags in modes.items():
        native = work / ('native-' + mode)
        run('build-native:' + mode, ['rustc', '+' + TOOLCHAIN, source, '--edition=2024', '--cfg', 'with_arc', *flags, '-o', native])
        values = run('native:' + mode, [native, *seeds])['stdout'].splitlines()
        assert len(values) == len(seeds)
        if expected is not None: assert values == expected
        expected = values
        for sysroot, path in [('installed', None), ('metadata', std_root)]:
            for inline in [False, True]:
                label = f'{mode}-{sysroot}-inline{int(inline)}'
                output = work / (label + '.rbc')
                variables = dict(RUST_INTERP_OUTPUT=str(output))
                if inline: variables['RUST_INTERP_INLINE_LEAVES'] = '1'
                command = [tools / 'rust-interp-mir-export', source, '--crate-name', 'wide_pointer_fixture',
                           '--edition=2024', '--emit=metadata', *flags, '-o', work / (label + '.rmeta')]
                if path: command += ['--sysroot', path, '--cfg', 'with_arc']
                run('export:' + label, command, variables)
                artifacts.append(dict(configuration=label, sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                                      path=str(output.relative_to(ROOT))))
                for seed, want in zip(seeds, values):
                    for engine in ['interpreter', 'jit']:
                        row = run(f'{label}:{engine}:{seed}', [tools / 'rust-interp-vm', '--engine', engine, output, seed])
                        assert row['stdout'].strip() == want, row
                print('PASS', label, len(seeds), 'seeds, both engines', flush=True)
    if args.baseline_tool_key:
        old, _ = installed_tools(args.baseline_tool_key)
        row = run('old-exporter-rejects', [old / 'rust-interp-mir-export', source,
                  '--crate-name', 'wide_pointer_fixture', '--edition=2024', '--emit=metadata',
                  '-Zmir-opt-level=0', '--sysroot', std_root, '-o', work / 'old.rmeta'],
                  {'RUST_INTERP_OUTPUT': str(work / 'old.rbc')}, success=False)
        assert 'expected integer or thin pointer' in row['stderr'] and not (work / 'old.rbc').exists()
    ordering = work / 'ordering.rs'
    ordering.write_text('''#![allow(ambiguous_wide_pointer_comparisons)]
#[inline(never)] fn less(a:*const [u8],b:*const [u8])->bool { a < b }
pub fn rust_interp_entry(seed:u64)->u64 {
 let data=[0u8;8]; let p=std::ptr::slice_from_raw_parts(data.as_ptr(),seed as usize);
 let q=std::ptr::slice_from_raw_parts(data.as_ptr(),3); less(p,q) as u64
}
fn main() {}
''')
    row = run('ordering-still-rejected', [tools / 'rust-interp-mir-export', ordering,
              '--crate-name', 'ordering', '--edition=2024', '--emit=metadata', '-Zmir-opt-level=0',
              '-o', work / 'ordering.rmeta'], {'RUST_INTERP_OUTPUT': str(work / 'ordering.rbc')}, success=False)
    assert 'expected integer or thin pointer' in row['stderr'] and not (work / 'ordering.rbc').exists()
    summary = dict(status='passed', tool_key=key, tool_binaries=json.loads((tools / 'ready.json').read_text()),
                   commands=len(records), inputs_per_configuration=len(seeds), configurations=len(artifacts),
                   arc_comparisons_sysroot='metadata (installed std omits Arc allocation MIR)',
                   engines=['interpreter','jit'], strict_frontend=True, std_mir_key=std_key,
                   artifacts=artifacts, frozen_inputs=frozen, raw=str(work.relative_to(ROOT)),
                   checks=['address and metadata equality/inequality', 'const/mut slices', 'full-width lengths',
                           'null and overlong raw values without dereferencing', 'str and nested DST pointers',
                           'trait-object aliases and distinct addresses', 'Arc<str> and Arc<[u8]> value equality',
                           'wide-pointer ordering remains unsupported'])
    (work / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (work / 'records.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(dict(status='passed', commands=len(records), raw=summary['raw'])))


if __name__ == '__main__':
    main()
