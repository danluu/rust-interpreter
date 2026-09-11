#!/usr/bin/env python3
"""Native/interpreter/JIT table and integer ordered-reduction semantics."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from interpreter import ROOT, TOOLCHAIN, checked_tools


def main():
    tools, key = checked_tools()
    work = ROOT / '.work' / ('simd-table-validation-' + str(time.time_ns()))
    work.mkdir()
    source = ROOT / 'tests/simd_fixture.rs'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    records = []

    def run(command, env=None, success=True):
        command = list(map(str, command))
        start = time.perf_counter()
        p = subprocess.Popen(command, cwd=ROOT, env=env, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        identity = dict(pid=p.pid, parent_pid=os.getpid(), command=command,
                        cwd=str(ROOT), started_at=time.time(), status='running')
        (work / 'active-command.json').write_text(json.dumps(identity))
        stdout, stderr = p.communicate()
        identity.update(status='finished', returncode=p.returncode)
        (work / 'active-command.json').write_text(json.dumps(identity))
        record = dict(command=command, pid=p.pid, returncode=p.returncode,
                      seconds=time.perf_counter()-start, stdout=stdout, stderr=stderr)
        records.append(record)
        with (work / 'commands.jsonl').open('a') as output:
            output.write(json.dumps(record) + '\n')
        assert (p.returncode == 0) == success, record
        return stdout.strip()

    seeds = [0, 1, 15, 16, 127, 128, 255, 256, 2**63-1, 2**63, 2**64-1]
    native = work / 'native'
    run(['rustc', '+'+TOOLCHAIN, source, '--edition=2024', '-o', native])
    expected = run([native, *seeds]).splitlines()
    env = os.environ.copy()
    for name in list(env):
        if name.startswith('RUST_INTERP_'):
            env.pop(name)
    env.update(RUST_INTERP_ENTRY='rust_interp_entry', RUST_INTERP_DEMAND_BODIES='0')
    modes = {
        'default': [],
        'mir3': ['-Zmir-opt-level=3'],
        'mir3-inline8': ['-Zmir-opt-level=3', '-Zinline-mir-threshold=400',
                        '-Zinline-mir-hint-threshold=800', '-Zinline-mir-forwarder-threshold=240'],
    }
    for mode, flags in modes.items():
        bytecode = work / (mode + '.rbc')
        env['RUST_INTERP_OUTPUT'] = str(bytecode)
        run([tools/'rust-interp-mir-export', source, '--crate-name', 'simd_table',
             '--edition=2024', '--emit=metadata', '-o', work/(mode+'.rmeta'), *flags], env)
        for seed, want in zip(seeds, expected):
            for engine in ['interpreter', 'jit']:
                assert run([tools/'rust-interp-vm', '--engine', engine, bytecode, seed]) == want
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    result = dict(tool_key=key, commands=len(records), native_inputs=len(seeds),
                  modes=modes, all_256_indices_in_every_lane=True,
                  integer_ordered_reductions_with_initial_accumulator=True,
                  signed_data_and_aliases_checked=True, raw=str(work.relative_to(ROOT)),
                  fixture_sha256=source_hash)
    (work/'records.json').write_text(json.dumps(records, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
