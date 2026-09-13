#!/usr/bin/env python3
"""Qualify real std::env/C strings, legacy dispatch, caches and strict Cargo edits."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools, require_export_option, TOOLCHAIN
from std_mir import checked_std_mir
from workflow_io import capture, require_space, write_json as write, SourceEdit


def report(stderr, prefix):
    rows = [json.loads(line[len(prefix):]) for line in stderr.splitlines()
            if line.startswith(prefix)]
    assert len(rows) == 1, (prefix, len(rows))
    return rows[0]


def cache_report(stderr):
    row = report(stderr, 'rust-interp-function-cache: ')
    assert row['schema_version'] == 1 and row['mode'] == 'reuse'
    assert row['staged_in_incremental_session']
    assert row['skipped_functions'] == row['previous_payload_uses']
    assert row['lowered_functions'] == row['red_functions'] + row['green_missing']
    assert row['lowered_functions'] + row['skipped_functions'] > 0
    assert re.fullmatch('[0-9a-f]{64}', row['namespace'])
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    args.automatic_cache = True
    assert re.fullmatch(r'tree-bridge-qualification-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        build_path = args.build.resolve(strict=True)
        build = json.loads(build_path.read_text())
        assert build['status'] == 'passed'
        assert build['tests']['test-debug'] == build['tests']['test-release'] == 556
        assert build['composition']['kind'] == 'resumable-tree-bridge-composition'
        compiler_proof = json.loads((ROOT / 'results/guarded-local-facts-main-build-01/summary.json').read_text())
        assert compiler_proof['status'] == 'passed'
        assert build['composition']['compiler_source_key'] == compiler_proof['tool_key']
        for name in ['rust-interp-mir-export', 'rust-interp-rustc-wrapper']:
            assert build['binaries'][name] == compiler_proof['binaries'][name]
        source_manifest = ROOT / build['source_manifest']
        assert sha(source_manifest) == build['source_manifest_sha256']
        assert all(sha(ROOT/p)==h for p,h in json.loads(source_manifest.read_text())['frozen'].items())
        tools, key = installed_tools(build['tool_key'])
        assert all(sha(tools/name)==h for name,h in build['binaries'].items())
        require_export_option(tools, key, 'function-cache-reuse')
        require_export_option(tools, key, 'function-cache-auto')
        sysroot, _, std_key, _ = checked_std_mir(TOOLCHAIN)
        assert std_key == 'bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef'
        fixtures = ['environment', 'dynamic', 'closure_pointer']
        paths = [Path(__file__), Path(__file__).with_name('PLAN.md'), Path(__file__).with_name('QUALIFICATION.md'), build_path, ROOT / 'tests/scalar_constant_fixture.rs', ROOT / 'results/guarded-local-facts-main-build-01/summary.json', source_manifest]
        paths += [ROOT / 'tests' / (name + '_fixture.rs') for name in fixtures]
        paths += [tools / name for name in build['binaries']]
        paths += [ROOT / 'scripts' / name for name in ['interpreter.py', 'std_mir.py',
            'workflow_io.py', 'workspace_cache.py', 'compare_saved_runtime.py']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, tool_key=key,
            fixtures=fixtures, minimum_free_gib=8, performance_measurement=False,
            changes='original fixtures plus scalar helper edit, unreachable type/borrow errors and restoration',
            entropy='ordinary OS; fixture assertions avoid comparing random hash keys'))
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']}
        assert not any(k.startswith('DYLD_') for k in env)
        env['CARGO_TERM_COLOR'] = 'never'
        env.update(RI_ENV_TEXT='hello=λ', RI_ENV_EMPTY='', RI_ENV_RAW=os.fsdecode(bytes([0x80, 61, 0xfe])))
        env[os.fsdecode(b'RI_ENV_\xff')] = 'raw-name'
        env.pop('RI_ENV_MISSING', None)
        rows, fixture_results, cache_rows = [], [], []

        def invoke(label, command, selected=env, success=True):
            require_space(ROOT, 8)
            command = list(map(str, command))
            child, stdout, stderr = capture(command, cwd=ROOT, env=selected,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            row = dict(label=label, command=command, pid=child.pid, returncode=child.returncode)
            for suffix, value in [('stdout', stdout), ('stderr', stderr)]:
                path = work / (label + '.' + suffix)
                path.write_text(value)
                row[suffix] = str(path.relative_to(ROOT))
                row[suffix + '_sha256'] = sha(path)
            rows.append(row)
            write(work / 'records.json', rows)
            assert (child.returncode == 0) == success, (label, stderr[-3000:])
            return stdout, stderr

        seeds = ['0', '7', str(2**64 - 1)]
        for name in fixtures:
            source = ROOT / 'tests' / (name + '_fixture.rs')
            native = work / (name + '-native')
            invoke(name + '-native-build', ['rustc', '+' + TOOLCHAIN, source, '--edition=2024', '-o', native])
            expected = {seed: invoke(name + '-native-' + seed,
                [native, *(['raw'] if name == 'c_allocator' else []), seed])[0] for seed in seeds}
            digests, cached = [], []
            for mode in ['off', 'reuse-cold', 'reuse-warm']:
                artifact = work / (name + '-' + mode + '.rbc')
                selected = dict(env, RUST_INTERP_TRAP_UNSUPPORTED_CALLS='1', RUST_INTERP_RUN_TRY_CALLBACKS='1', RUST_INTERP_ENTRY='rust_interp_entry',
                                RUST_INTERP_OUTPUT=str(artifact), RUST_INTERP_INLINE_LEAVES='1')
                extra = []
                if mode != 'off':
                    selected['RUST_INTERP_FUNCTION_CACHE'] = 'reuse'
                    extra = ['-C', 'incremental=' + str(work / (name + '-incremental'))]
                _, stderr = invoke(name + '-export-' + mode,
                    [tools / 'rust-interp-mir-export', source, '--crate-name', 'composed_case',
                     '--edition=2024', '--emit=metadata', '--sysroot', sysroot, *extra,
                     '-o', work / (name + '.rmeta')], selected)
                digests.append(sha(artifact))
                if mode != 'off':
                    row = cache_report(stderr)
                    assert (row['skipped_functions'] == 0 if mode == 'reuse-cold'
                            else row['skipped_functions'] > 0)
                    cached.append(row)
                    cache_rows.append(dict(fixture=name, phase=mode, **row))
                for engine in (['interpreter', 'jit', 'ordinary-jit'] if name == 'environment' else ['interpreter', 'jit']):
                    flags = ['--jit-resumable-calls', '--jit-tree-bridge', '--jit-persistent-registers'] if engine == 'jit' else []
                    selected_engine = 'jit' if engine == 'ordinary-jit' else engine
                    for seed in seeds:
                        stdout, _ = invoke(name + '-' + mode + '-' + engine + '-' + seed,
                            [tools / 'rust-interp-vm', '--engine', selected_engine, *flags, artifact, seed])
                        assert stdout == expected[seed], (name, mode, engine, seed)
            assert len(set(digests)) == 1 and cached[0]['namespace'] == cached[1]['namespace']
            fixture_results.append(dict(fixture=name, artifact_sha256=digests[0], native_matches=True,
                cold_skipped=cached[0]['skipped_functions'], warm_skipped=cached[1]['skipped_functions']))
            print(name, 'native/interpreter/JIT and reused bytecode match', flush=True)

        bad = work / 'invalid-strlen.rbc'
        selected = dict(env, RUST_INTERP_ENTRY='invalid_strlen', RUST_INTERP_OUTPUT=str(bad),
                        RUST_INTERP_TRAP_UNSUPPORTED_CALLS='1', RUST_INTERP_RUN_TRY_CALLBACKS='1')
        invoke('invalid-strlen-export', [tools / 'rust-interp-mir-export', ROOT / 'tests/environment_fixture.rs',
            '--crate-name', 'invalid_strlen', '--edition=2024', '--emit=metadata', '--sysroot', sysroot,
            '-o', work / 'invalid-strlen.rmeta'], selected)
        for engine in ['interpreter', 'jit']:
            flags = ['--jit-resumable-calls', '--jit-tree-bridge', '--jit-persistent-registers'] if engine == 'jit' else []
            for pointer in ['0', str(2**64 - 1)]:
                stdout, stderr = invoke('invalid-strlen-' + engine + '-' + pointer,
                    [tools / 'rust-interp-vm', '--engine', engine, *flags, bad, pointer], success=False)
                assert stdout == '' and ('invalid guest memory access' in stderr or 'JIT guest memory access failed' in stderr)
        for symbol in ['getenv', 'strlen']:
            source = work / ('bad-' + symbol + '.rs')
            source.write_text('unsafe extern "C" { fn ' + symbol + '(x: u128) -> u128; }\npub fn rust_interp_entry(x: u64) -> u64 { unsafe { ' + symbol + '(x as u128) as u64 } }\n')
            output = work / ('bad-' + symbol + '.rbc')
            selected = dict(env, RUST_INTERP_ENTRY='rust_interp_entry', RUST_INTERP_OUTPUT=str(output),
                            RUST_INTERP_TRAP_UNSUPPORTED_CALLS='1')
            _, stderr = invoke('reject-' + symbol + '-signature', [tools / 'rust-interp-mir-export', source,
                '--crate-name', 'bad_signature', '--crate-type', 'lib', '--edition=2024', '--emit=metadata',
                '--sysroot', sysroot, '-o', work / ('bad-' + symbol + '.rmeta')], selected, success=False)
            assert 'invalid ' + symbol + ' signature' in stderr and not output.exists()

        crate = work / 'crate'
        (crate / 'src').mkdir(parents=True)
        (crate / 'Cargo.toml').write_text('[package]\nname="composed-cache-fixture"\nversion="0.1.0"\nedition="2024"\n[workspace]\n')
        source = crate / 'src/lib.rs'
        original = (ROOT / 'tests/scalar_constant_fixture.rs').read_bytes()
        source.write_bytes(original)
        invoke('cargo-lockfile', ['cargo', '+' + TOOLCHAIN, 'generate-lockfile',
                                  '--manifest-path', crate / 'Cargo.toml', '--offline'])
        base = [sys.executable, ROOT / 'scripts/interpreter.py', '--manifest-path', crate / 'Cargo.toml',
                '--package', 'composed-cache-fixture', '--tool-key', key, '--cache-namespace', args.run_id,
                '--entry', 'rust_interp_entry', '--jobs', '2', '--std-mir', '--engine', 'jit',
                '--jit-resumable-calls', '--jit-tree-bridge', '--jit-persistent-registers', '--inline-leaves']
        launch_env = dict(env, RUST_INTERP_LAUNCH_STATS='1')
        states = [('original', original), ('helper-edit', original.replace(b'wrapping_add(29)', b'wrapping_add(31)')),
                  ('restored', original)]
        assert states[1][1] != original
        cargo_results = []
        with SourceEdit(source, original) as edit:
            for label, payload in states:
                edit.replace(payload)
                native = work / ('cargo-' + label + '-native')
                invoke('cargo-' + label + '-native-build', ['rustc', '+' + TOOLCHAIN, source,
                    '--edition=2024', '-o', native])
                expected = invoke('cargo-' + label + '-native-run', [native, '7'])[0]
                artifacts = []
                for index, mode in enumerate(['reuse', 'off', 'auto' if args.automatic_cache else 'reuse']):
                    stdout, stderr = invoke('cargo-' + label + '-' + str(index) + '-' + mode,
                        [*base, '--function-cache', mode, '--', '7'], launch_env)
                    assert stdout == expected
                    launched = report(stderr, 'rust-interp-launch: ')
                    assert launched['function_cache'] == mode and launched['jit_tree_bridge'] is True
                    artifact = Path(launched['artifact_path'])
                    assert sha(artifact) == launched['artifact_sha256']
                    artifacts.append(sha(artifact))
                    snapshot = work / ('cargo-' + label + '-' + str(index) + '.rbc')
                    snapshot.write_bytes(artifact.read_bytes())
                    if mode != 'off':
                        cached = cache_report(stderr)
                        cache_rows.append(dict(fixture='cargo-scalar', state=label, index=index, **cached))
                    else:
                        assert 'rust-interp-function-cache: ' not in stderr
                assert len(set(artifacts)) == 1
                cargo_results.append(dict(state=label, source_sha256=sha(source),
                    artifact_sha256=artifacts[0], native_stdout=expected))
                if label == 'helper-edit':
                    for error, bad, diagnostic in [
                        ('type', b'fn unused() { let _: u64 = "wrong"; }', 'mismatched types'),
                        ('borrow', b'fn unused() { let mut x=1; let a=&mut x; let b=&mut x; *a+=*b; }', 'cannot borrow')]:
                        edit.replace(payload + b'\n' + bad + b'\n')
                        stdout, stderr = invoke('cargo-reject-' + error,
                            [*base, '--function-cache', 'reuse', '--', '7'], launch_env, success=False)
                        assert diagnostic in stderr and 'rust-interp-launch: ' not in stderr
                        assert stdout == '' and not re.search(r'\binstructions=\d+', stderr)
                        # Cargo may retain prior successful metadata/sidecars on
                        # an error. Failure must stop the launcher before the VM;
                        # physical absence of historical artifacts is not needed.
                        # The restored-source command below must rebuild/check
                        # and agree with the native result for that source.
                        edit.replace(payload)
            assert cargo_results[0]['artifact_sha256'] == cargo_results[2]['artifact_sha256']
            assert cargo_results[0]['native_stdout'] == cargo_results[2]['native_stdout']
            assert cargo_results[0]['native_stdout'] != cargo_results[1]['native_stdout']
            if args.automatic_cache:
                manifest = crate / 'Cargo.toml'
                manifest.write_text(manifest.read_text() + '\n[profile.dev]\nincremental=false\n')
                for label, payload in states:
                    edit.replace(payload)
                    expected = next(r['native_stdout'] for r in cargo_results if r['state'] == label)
                    digests = []
                    for mode in ['off', 'auto']:
                        stdout, stderr = invoke('cargo-no-incremental-' + label + '-' + mode,
                            [*base, '--function-cache', mode, '--', '7'], launch_env)
                        assert stdout == expected
                        launch = report(stderr, 'rust-interp-launch: ')
                        assert launch['function_cache'] == mode and launch['jit_tree_bridge'] is True
                        artifact = Path(launch['artifact_path'])
                        assert sha(artifact) == launch['artifact_sha256']
                        digests.append(sha(artifact))
                        if mode == 'auto':
                            cached = report(stderr, 'rust-interp-function-cache: ')
                            assert cached['requested_mode'] == 'auto' and cached['mode'] == 'off'
                            assert cached['all_original_lowering_executed'] and cached['skipped_functions'] == 0
                            assert cached['lowered_functions'] > 0 and not cached['staged_in_incremental_session']
                            cache_rows.append(dict(fixture='cargo-without-incremental', state=label, **cached))
                    assert len(set(digests)) == 1
                _, stderr = invoke('cargo-forced-reuse-no-incremental',
                    [*base, '--function-cache', 'reuse', '--', '7'], launch_env, success=False)
                assert 'incremental dependency graph' in stderr and 'rust-interp-launch: ' not in stderr
                for error, bad, diagnostic in [
                    ('type', b'fn unused() { let _: u64 = "wrong"; }', 'mismatched types'),
                    ('borrow', b'fn unused() { let mut x=1; let a=&mut x; let b=&mut x; *a+=*b; }', 'cannot borrow')]:
                    edit.replace(original + b'\n' + bad + b'\n')
                    stdout, stderr = invoke('cargo-auto-no-incremental-reject-' + error,
                        [*base, '--function-cache', 'auto', '--', '7'], launch_env, success=False)
                    assert diagnostic in stderr and stdout == '' and 'rust-interp-launch: ' not in stderr
                edit.replace(original)
                stdout, _ = invoke('cargo-auto-no-incremental-restored-final',
                    [*base, '--function-cache', 'auto', '--', '7'], launch_env)
                assert stdout == cargo_results[0]['native_stdout']
        assert source.read_bytes() == original
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        assert len(rows) == 119, len(rows)
        write(work / 'cache-reports.json', cache_rows)
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', tool_key=key, commands=len(rows),
            fixtures=fixture_results, cargo_states=cargo_results, strict_rejections=['type', 'borrow'],
            source_restored=True, automatic_cache_qualified=args.automatic_cache,jit_tree_bridge=True,
            performance_measurement=False, raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'),
            cache_reports_sha256=sha(work / 'cache-reports.json')))
        print('PASS composed cache, native/reference agreement and strict Cargo edits', flush=True)


if __name__ == '__main__':
    main()
