#!/usr/bin/env python3
"""Check fresh-process export repeatability and native callback results.

Run under the task's global benchmark lock, after installing the current tools.
An optional old exporter provides a negative control for callback scheduling.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from interpreter import ROOT, TOOLCHAIN, checked_tools, installed_tools


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool-key')
    parser.add_argument('--baseline-tool-key')
    parser.add_argument('--run-id', default='export-determinism-' + str(time.time_ns()))
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in ['.', '..']:
        parser.error('invalid run id')
    tools, key = installed_tools(args.tool_key) if args.tool_key else checked_tools()
    builds = [('candidate', tools, key, 8)]
    if args.baseline_tool_key:
        baseline, baseline_key = installed_tools(args.baseline_tool_key)
        builds.insert(0, ('baseline', baseline, baseline_key, 3))
    work = ROOT / '.work' / args.run_id
    work.mkdir()
    source = ROOT / 'tests/function_order_fixture.rs'
    frozen = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [source, Path(__file__).resolve()]}
    manifests = {label: json.loads((directory / 'ready.json').read_text())
                 for label, directory, _, _ in builds}
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'CARGO_PROFILE_')) or name in [
            'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
            'RUSTC_WORKSPACE_WRAPPER', 'CARGO_TARGET_DIR', 'CARGO_INCREMENTAL', 'CARGO_BUILD_TARGET',
        ]:
            env.pop(name)
    env.update(RUST_INTERP_ENTRY='rust_interp_entry', RUST_INTERP_DEMAND_BODIES='0',
               RUST_INTERP_DEMAND_CACHE='0', RUST_INTERP_EXPORT_TEST='0')
    records = []

    def run(label, command, extra_env=None):
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in frozen.items())
        command = list(map(str, command))
        start = time.perf_counter()
        p = subprocess.Popen(command, cwd=ROOT, env=env | dict(extra_env or {}),
                             text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        identity = dict(pid=p.pid, parent_pid=os.getpid(), command=command, cwd=str(ROOT),
                        started_at=time.time(), status='running')
        (work / 'active-command.json').write_text(json.dumps(identity))
        stdout, stderr = p.communicate()
        identity.update(status='finished', returncode=p.returncode)
        (work / 'active-command.json').write_text(json.dumps(identity))
        row = dict(label=label, identity=identity, stdout=stdout, stderr=stderr,
                   seconds=time.perf_counter() - start)
        records.append(row)
        with (work / 'commands.jsonl').open('a') as log:
            log.write(json.dumps(row) + '\n')
        assert p.returncode == 0, row
        assert 'internal compiler error' not in stderr, row
        return row

    seeds = [0, 1, 2, 7, 8, 255, 256, 2**63 - 1, 2**63, 2**64 - 1]
    native = work / 'native'
    run('build-native', ['rustc', '+' + TOOLCHAIN, source, '--edition=2024', '-o', native])
    expected = run('native-results', [native, *seeds])['stdout'].splitlines()
    assert len(expected) == len(seeds)
    cases = {}
    for level in [0, 3]:
        for inline in [False, True]:
            case = f'mir{level}-inline{int(inline)}'
            groups = {}
            for label, directory, build_key, repetitions in builds:
                artifacts = []
                for repetition in range(repetitions):
                    output = work / f'{case}-{label}-{repetition}.rbc'
                    variables = dict(RUST_INTERP_OUTPUT=str(output))
                    if inline:
                        variables['RUST_INTERP_INLINE_LEAVES'] = '1'
                    run('export:' + output.stem, [directory / 'rust-interp-mir-export', source,
                        '--crate-name', 'function_order_fixture', '--edition=2024', '--emit=metadata',
                        f'-Zmir-opt-level={level}', '-o', work / 'fixture.rmeta'], variables)
                    digest = hashlib.sha256(output.read_bytes()).hexdigest()
                    artifacts.append(dict(path=str(output.relative_to(ROOT)), sha256=digest))
                    for seed, want in zip(seeds, expected):
                        for engine in ['interpreter', 'jit']:
                            row = run(f'{output.stem}:{engine}:{seed}',
                                      [directory / 'rust-interp-vm', '--engine', engine, output, seed])
                            assert row['stdout'].strip() == want, row
                unique = len({artifact['sha256'] for artifact in artifacts})
                groups[label] = dict(tool_key=build_key, exports=repetitions,
                                     unique_artifacts=unique, artifacts=artifacts)
                if label == 'candidate':
                    assert unique == 1, (case, groups[label])
                print(case, label, 'exports', repetitions, 'unique', unique, flush=True)
            cases[case] = groups
    if args.baseline_tool_key:
        assert any(groups['baseline']['unique_artifacts'] > 1 for groups in cases.values()), 'negative control did not reproduce random scheduling'
    for label, directory, _, _ in builds:
        for name, digest in manifests[label].items():
            assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
    result = dict(status='passed', tool_key=key, commands=len(records), cases=cases,
                  native_seeds=seeds, tool_binaries=manifests, frozen_inputs=frozen,
                  raw=str(work.relative_to(ROOT)))
    (work / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    (work / 'records.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(dict(status='passed', tool_key=key, commands=len(records), raw=result['raw'])))


if __name__ == '__main__':
    main()
