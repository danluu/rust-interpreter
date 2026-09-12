#!/usr/bin/env python3
"""Exercise compiler dependency observation across owned semantic edit histories."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools, TOOLCHAIN
from std_mir import checked_std_mir
from workflow_io import SourceEdit, capture, require_space, write_json as write
from reuse_build import CONTROL
from reuse_check import observation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'export-dependency-fixture-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        build_path = ROOT / 'results/export-reuse-build-03/summary.json'
        build = json.loads(build_path.read_text())
        assert build['status'] == 'passed' and set(build['tests'].values()) == {44}
        tool, key = installed_tools(build['tool_key'])
        baseline, _ = installed_tools(CONTROL)
        sysroot, _, std_key, _ = checked_std_mir(TOOLCHAIN)
        assert std_key == 'bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef'
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        source = work / 'source'
        source.mkdir()
        for name in ['main.rs', 'model.rs']:
            shutil.copy2(HERE / 'dependency_fixture' / name, source / name)
        write(source / '.rust-interp-owned.json', dict(owner=str(ROOT), run=args.run_id))
        original = (source / 'model.rs').read_bytes()
        text = original.decode()
        states = [('original', text)]
        changes = [
            ('body', 'seed.wrapping_add(7)', 'seed.wrapping_add(3).wrapping_add(4)'),
            ('layout', '#[repr(C)]', '#[repr(C, align(64))]'),
            ('constant', 'pub const SCALE: u64 = 3;', 'pub const SCALE: u64 = 5;'),
            ('signature', 'pub type Word = u64;', 'pub type Word = u32;'),
            ('generic', 'pub type GenericWord = u64;', 'pub type GenericWord = u32;'),
            ('data', 'pub const LABEL: &[u8] = b"abc";', 'pub const LABEL: &[u8] = b"xyz";'),
        ]
        for name, before, after in changes:
            assert text.count(before) == 1
            text = text.replace(before, after)
            states.append((name, text))
        states += [('restored', original.decode()),
                   ('invalid-type', original.decode() + '\nfn unused() { let _: u64 = "wrong"; }\n')]
        paths = [Path(__file__), HERE / 'reuse_check.py', HERE / 'DEPENDENCIES.md', build_path,
                 HERE / 'dependency_fixture/main.rs', HERE / 'dependency_fixture/model.rs']
        paths += [p / name for p in [tool, baseline] for name in ['rust-interp-mir-export', 'rust-interp-vm', 'rust-interp-rustc-wrapper']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        write(work / 'plan.json', dict(frozen=frozen, tool_key=key, source_commit=build['source_commit'],
              std_mir_key=std_key, states=[name for name, _ in states] + ['restored-after-error'],
              all_lowering_executed=True, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL']}
        stages = {}
        for mode in ['native', 'retained', 'off', 'on']:
            stage = work / mode
            stage.mkdir()
            stages[mode] = stage
        records, observations, seen = [], [], {}
        def invoke(label, command, selected=env, success=True):
            require_space(ROOT, 8)
            child, stdout, stderr = capture(list(map(str, command)), cwd=ROOT, env=selected,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            row = dict(label=label, command=list(map(str, command)), pid=child.pid, returncode=child.returncode,
                       source_sha256=sha(source / 'model.rs'))
            for suffix, text in [('stdout', stdout), ('stderr', stderr)]:
                path = work / (label + '.' + suffix)
                path.write_text(text)
                row[suffix] = str(path.relative_to(ROOT))
                row[suffix + '_sha256'] = sha(path)
            records.append(row)
            write(work / 'records.json', records)
            assert (child.returncode == 0) == success, label
            return stdout, stderr
        seeds = ['0', '7', str(2**64 - 1)]
        def execute(name):
            valid = name != 'invalid-type'
            native = stages['native'] / 'program'
            invoke(name + '-native-build', ['rustc', '+' + TOOLCHAIN, source / 'main.rs', '--crate-name',
                'dependency_case', '--edition=2024', '-C', 'incremental=' + str(stages['native'] / 'incremental'),
                '-o', native], success=valid)
            expected = {}
            if valid:
                expected = {seed: invoke(name + '-native-' + seed, [native, seed])[0] for seed in seeds}
                assert all(re.fullmatch(r'\d+\n', value) for value in expected.values())
            hashes = []
            for mode, compiler in [('retained', baseline), ('off', tool), ('on', tool)]:
                stage = stages[mode]
                artifact = stage / 'program.rbc'
                selected = dict(env, RUST_INTERP_OUTPUT=str(artifact), RUST_INTERP_ENTRY='rust_interp_entry')
                if mode in ['off', 'on']:
                    selected.update(RUST_INTERP_FUNCTION_COSTS='1', RUST_INTERP_EXPORT_TIMINGS='1')
                if mode == 'on':
                    selected['RUST_INTERP_FUNCTION_DEPENDENCIES'] = '1'
                _, stderr = invoke(name + '-export-' + mode, [compiler / 'rust-interp-mir-export', source / 'main.rs',
                    '--crate-name', 'dependency_case', '--edition=2024', '--emit=metadata', '--sysroot', sysroot,
                    '-C', 'incremental=' + str(stage / 'incremental'), '-o', stage / 'program.rmeta'], selected, success=valid)
                if not valid:
                    assert 'mismatched types' in stderr and not artifact.exists()
                    continue
                saved = work / (name + '-' + mode + '.rbc')
                shutil.copy2(artifact, saved)
                hashes.append(sha(saved))
                if mode in ['off', 'on']:
                    report, scopes = observation(stderr, saved)
                    assert report['schema_version'] == (3 if mode == 'on' else 2)
                    write(work / (name + '-' + mode + '.census.json'), report)
                    if mode == 'on':
                        functions = report['functions']
                        assert len({f['dependency']['node'] for f in functions}) == len(functions)
                        green = [f for f in functions if f['dependency']['previous_green']]
                        if name == 'original':
                            assert not green, 'fresh compiler namespace reused prior mono-item nodes'
                        unknown = [f for f in green if f['dependency']['node'] not in seen]
                        mismatches = [dict(node=f['dependency']['node'], name=f['name'], index=f['index'],
                            previous=seen[f['dependency']['node']]) for f in green
                            if f['dependency']['node'] in seen and seen[f['dependency']['node']]['template'] != f['typed_template_sha256']]
                        observations.append(dict(state=name, functions=len(functions), green=len(green),
                            unknown_green=len(unknown), changed_green_templates=mismatches,
                            green_check_seconds=sum(f['dependency']['green_check_seconds'] for f in functions)))
                        seen.update({f['dependency']['node']: dict(state=name, name=f['name'], index=f['index'],
                                     template=f['typed_template_sha256']) for f in functions})
                        write(work / 'observations.json', observations)
                for engine in ['interpreter', 'jit']:
                    flags = ['--jit-resumable-calls', '--jit-persistent-registers'] if engine == 'jit' else []
                    for seed in seeds:
                        stdout, _ = invoke(name + '-' + mode + '-' + engine + '-' + seed,
                            [tool / 'rust-interp-vm', '--engine', engine, *flags, saved, seed])
                        assert stdout == expected[seed]
            assert not valid or len(set(hashes)) == 1, 'dependency observation changed the artifact'
            assert all(sha(ROOT / p) == digest for p, digest in frozen.items())
            print('PASS', name, 'original assertions and artifacts' if valid else 'strict rejection', flush=True)
        with SourceEdit(source / 'model.rs', original) as edit:
            for name, text in states:
                edit.replace(text.encode())
                execute(name)
        assert (source / 'model.rs').read_bytes() == original
        execute('restored-after-error')
        mismatches = sum(len(r['changed_green_templates']) for r in observations)
        unknown = sum(r['unknown_green'] for r in observations)
        green = sum(r['green'] for r in observations)
        result = dict(status='completed diagnostic', performance_measurement=False, tool_key=key,
              source_commit=build['source_commit'], commands=len(records), observations=observations,
              all_artifact_hashes_identical=True, source_restored=True, original_assertions_unchanged=True,
              strict_invalid_source_rejected=True, green_functions=green, changed_green_templates=mismatches,
              unknown_green=unknown, candidate_dependency_boundary_supported=green > 0 and mismatches == unknown == 0,
              all_lowering_executed=True, frozen=frozen, raw=str(work.relative_to(ROOT)),
              records_sha256=sha(work / 'records.json'), observations_sha256=sha(work / 'observations.json'),
              scope='No cached output or skipped lowering. Green status is tested against actual typed templates; binding and shared exporter state remain separate requirements.')
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', result)
        print('COMPLETE', len(records), 'commands;', green, 'green;', mismatches, 'changed green templates;', unknown, 'unknown green')


if __name__ == '__main__':
    main()
