#!/usr/bin/env python3
"""Qualify owned persistent-cache faults, policy changes and failed publication."""
import argparse
import hashlib
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
from reuse_check import observation, reconstruction, persistent_cache


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--qualification', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'export-cache-fixture-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        build = json.loads(args.build.read_text())
        qualified = json.loads(args.qualification.read_text())
        assert build['status'] == 'passed' and set(build['tests'].values()) == {50}
        assert qualified['commands'] == 229 and qualified['persistent_cache']
        assert qualified['candidate_dependency_boundary_supported'] and qualified['all_lowering_executed']
        assert qualified['tool_key'] == build['tool_key']
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
        edited = original.replace(b'seed.wrapping_add(7)', b'seed.wrapping_add(3).wrapping_add(4)')
        assert edited != original
        paths = [Path(__file__), HERE / 'reuse_check.py', HERE / 'PERSISTENT-REUSE.md',
                 args.build.resolve(), args.qualification.resolve(),
                 HERE / 'dependency_fixture/main.rs', HERE / 'dependency_fixture/model.rs']
        paths += [p / n for p in [tool, baseline] for n in ['rust-interp-mir-export', 'rust-interp-vm', 'rust-interp-rustc-wrapper']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        write(work / 'plan.json', dict(frozen=frozen, source_commit=build['source_commit'], tool_key=key,
              performance_measurement=False, all_original_lowering_executed=True,
              faults=['body checksum', 'header namespace', 'missing cache', 'trap policy', 'callback policy',
                      'bytecode publication after cache staging'], compiler_cache_mutation_scope=str(work)))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL']}
        records, reports = [], []
        def invoke(label, command, selected=env, success=True):
            require_space(ROOT, 8)
            child, stdout, stderr = capture(list(map(str, command)), cwd=ROOT, env=selected,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            row = dict(label=label, command=list(map(str, command)), pid=child.pid,
                       returncode=child.returncode, source_sha256=sha(source / 'model.rs'))
            for suffix, value in [('stdout', stdout), ('stderr', stderr)]:
                path = work / (label + '.' + suffix)
                path.write_text(value)
                row[suffix] = str(path.relative_to(ROOT))
                row[suffix + '_sha256'] = sha(path)
            records.append(row)
            write(work / 'records.json', records)
            assert (child.returncode == 0) == success, label
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            return stdout, stderr
        seeds = ['0', '7', str(2**64 - 1)]
        native = work / 'native'
        invoke('native-build', ['rustc', '+' + TOOLCHAIN, source / 'main.rs', '--edition=2024', '-o', native])
        expected = {seed: invoke('native-' + seed, [native, seed])[0] for seed in seeds}
        assert all(re.fullmatch(r'\d+\n', value) for value in expected.values())
        def command(compiler):
            return [compiler / 'rust-interp-mir-export', source / 'main.rs', '--crate-name', 'cache_case',
                    '--edition=2024', '--emit=metadata', '--sysroot', sysroot,
                    '-C', 'incremental=' + str(work / ('incremental' if compiler == tool else 'control-incremental')),
                    '-o', work / ('program.rmeta' if compiler == tool else 'control.rmeta')]
        def finalized():
            return {str(p.relative_to(ROOT)): sha(p) for p in (work / 'incremental').glob('*/s-*/rust-interp-functions-v1.bin')
                    if not p.parent.name.endswith('-working')}
        control = work / 'control.rbc'
        def reference(label):
            invoke(label + '-control', command(baseline), dict(env, RUST_INTERP_ENTRY='rust_interp_entry', RUST_INTERP_OUTPUT=str(control)))
            saved = work / (label + '-control.rbc')
            shutil.copy2(control, saved)
            return sha(saved)
        def verify(label, digest, policy=None):
            artifact = work / (label + '.rbc')
            selected = dict(env, RUST_INTERP_ENTRY='rust_interp_entry', RUST_INTERP_OUTPUT=str(artifact),
                RUST_INTERP_FUNCTION_COSTS='1', RUST_INTERP_EXPORT_TIMINGS='1',
                RUST_INTERP_FUNCTION_DEPENDENCIES='1', RUST_INTERP_BINDING_REPLAY='1', RUST_INTERP_FUNCTION_CACHE='verify')
            selected.update(policy or {})
            before = finalized()
            _, stderr = invoke(label + '-export', command(tool), selected)
            assert sha(artifact) == digest, 'cache control changed the bytecode'
            census, _ = observation(stderr, artifact)
            replay = reconstruction(stderr, census)
            cached = persistent_cache(stderr, census)
            after = finalized()
            assert after and all(after[p] == h for p, h in before.items() if p in after)
            # Retain bytes independently of rustc's generation collection and
            # the following deliberate faults; never mutate an inherited inode.
            inventory = {}
            for n, (path, h) in enumerate(sorted(after.items())):
                saved = work / (label + '-cache-' + str(n) + '.bin')
                shutil.copy2(ROOT / path, saved)
                inventory[path] = dict(sha256=h, snapshot=str(saved.relative_to(ROOT)))
            write(work / (label + '-cache-files.json'), inventory)
            write(work / (label + '.census.json'), census)
            for engine in ['interpreter', 'jit']:
                flags = ['--jit-resumable-calls', '--jit-persistent-registers'] if engine == 'jit' else []
                for seed in seeds:
                    output, _ = invoke(label + '-' + engine + '-' + seed,
                        [tool / 'rust-interp-vm', '--engine', engine, *flags, artifact, seed])
                    assert output == expected[seed]
            reports.append(dict(label=label, cache=cached, reconstruction=replay,
                                nodes=[f['dependency']['node'] for f in census['functions']]))
            write(work / 'reports.json', reports)
            print('PASS', label, cached['previous_payload_uses'], 'prior payloads', flush=True)
            return cached, selected
        def fault(kind):
            before = finalized()
            assert before
            for relative in before:
                path = ROOT / relative
                assert work in path.parents and path.is_file() and not path.is_symlink()
                if kind == 'missing':
                    path.unlink()
                else:
                    data = bytearray(path.read_bytes())
                    data[-1 if kind == 'corrupt' else 8] ^= 1
                    temp = path.with_suffix('.control-new')
                    with temp.open('xb') as stream:
                        stream.write(data)
                    os.replace(temp, path)
            write(work / (kind + '-fault.json'), dict(before=before, after=finalized()))
        first, _ = verify('original', reference('original'))
        assert first['loaded_entries'] == first['previous_payload_uses'] == 0
        with SourceEdit(source / 'model.rs', original) as edit:
            edit.replace(edited)
            digest = reference('edited')
            cached, _ = verify('edited', digest)
            assert cached['previous_payload_uses'] > 0
            for kind, note in [('corrupt', 'cache integrity check'), ('namespace', 'cache namespace changed'), ('missing', 'No such file')]:
                fault(kind)
                cached, _ = verify(kind, digest)
                assert cached['loaded_entries'] == cached['previous_payload_uses'] == 0 and note in cached['load_note']
                assert cached['green_missing'] == cached['staged_entries'] == 20
                repaired, _ = verify(kind + '-repaired', digest)
                assert repaired['previous_payload_uses'] == 20
            for label, policy in [('trap', {'RUST_INTERP_TRAP_UNSUPPORTED_CALLS': '1'}), ('trap-restored', {}),
                                  ('callback', {'RUST_INTERP_TRAP_UNSUPPORTED_CALLS': '1', 'RUST_INTERP_RUN_TRY_CALLBACKS': '1'}),
                                  ('callback-restored', {})]:
                previous = reports[-1]
                cached, selected = verify(label, digest, policy)
                assert cached['namespace'] != previous['cache']['namespace']
                assert cached['loaded_entries'] == cached['previous_payload_uses'] == 0 and cached['red_functions'] == 20
                assert set(previous['nodes']).isdisjoint(reports[-1]['nodes'])
            before = finalized()
            latest = max(before, key=lambda p: (ROOT / p).parent.name)
            missing_output = work / 'absent-parent' / 'failed.rbc'
            assert not missing_output.parent.exists()
            _, stderr = invoke('publication-failure', command(tool), dict(selected, RUST_INTERP_OUTPUT=str(missing_output)), success=False)
            staged = [json.loads(l.split(': ', 1)[1]) for l in stderr.splitlines() if l.startswith('rust-interp-function-cache: ')]
            assert len(staged) == 1 and staged[0]['staged_entries'] == 20 and staged[0]['previous_payload_uses'] == 20
            assert 'No such file or directory' in stderr and not missing_output.exists()
            after = finalized()
            assert latest in after and all(before.get(p) == h for p, h in after.items())
            write(work / 'publication-failure-cache-files.json', dict(before=before, after=after, staged_report=staged[0]))
            recovered, _ = verify('publication-recovered', digest)
            assert recovered['loaded_entries'] == recovered['previous_payload_uses'] == 20
        assert (source / 'model.rs').read_bytes() == original
        result = dict(status='passed', commands=len(records), tool_key=key, source_commit=build['source_commit'],
            all_artifact_hashes_identical=True, original_assertions_unchanged=True, source_restored=True,
            checksum_namespace_missing_controls=True, both_policy_namespaces_and_nodes_invalidated=True,
            failed_publication_after_staging_published_no_session=True, cache_recovery=True,
            all_original_lowering_executed=True, performance_measurement=False, reports=reports, frozen=frozen,
            raw=str(work.relative_to(ROOT)), records_sha256=sha(work / 'records.json'))
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', result)
        print('COMPLETE', len(records), 'commands; persistent fault and publication controls passed', flush=True)


if __name__ == '__main__':
    main()
