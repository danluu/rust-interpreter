#!/usr/bin/env python3
"""Write exact source-only build/qualification/screen commands; execute none."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from interpreter import TOOLCHAIN, CURRENT_TOOL_BINARIES
from workflow_io import write_json


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen-root', type=Path, required=True)
    parser.add_argument('--std-mir-ready', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    screen_root = args.screen_root.resolve(strict=True)
    ready_path = args.std_mir_ready.resolve(strict=True)
    ready = json.loads(ready_path.read_bytes())
    identity = ready['identity']
    if (ready['owner'] != str(screen_root) or ready_path.parent.parent != screen_root / '.work/std-mir'
            or 'cargo' in identity or 'compiler_key' in identity):
        raise RuntimeError('plan requires one existing public std identity owned by the eventual screen root')
    if hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest() != ready_path.parent.name:
        raise RuntimeError('prepared std identity does not match its directory')
    host = identity['target']
    sysroot = Path.home() / '.rustup/toolchains' / (TOOLCHAIN + '-' + host)
    if not (sysroot / 'bin/rustc').is_file() or not (sysroot / 'bin/cargo').is_file():
        raise RuntimeError('public dated compiler/Cargo are not installed at the planned paths')
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        raise RuntimeError('output must be a new path in an existing directory')
    inputs = [ROOT / 'Cargo.toml', ROOT / 'Cargo.lock']
    for crate in ['bytecode', 'mir-export']:
        inputs += sorted((ROOT / 'crates' / crate).rglob('*.rs'))
        inputs.append(ROOT / 'crates' / crate / 'Cargo.toml')
    key_hash = hashlib.sha256()
    for path in inputs:
        key_hash.update(str(path.relative_to(ROOT)).encode() + b'\0' + path.read_bytes())
    key = key_hash.hexdigest()
    work = ROOT / '.work/host-proc-macro-build-01'
    target = work / 'target'
    tools = ROOT / '.work/interpreter-tools' / key
    screen_work = screen_root / '.work/strict-warm-proc-macro-screen-01'
    source = screen_root / '.work/sources/nushell-proc-macro-opt'
    installed_screen_tools = screen_root / '.work/interpreter-tools' / key
    env = dict(CARGO_TERM_COLOR='never', CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0',
               CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='1',
               RUSTC=str(sysroot / 'bin/rustc'), RUSTUP_TOOLCHAIN=TOOLCHAIN + '-' + host)
    common = ['--release', '--locked', '--offline', '--jobs', '2', '--target-dir', str(target)]
    commands = [
        dict(label='public-rustc-identity', argv=[str(sysroot / 'bin/rustc'), '-vV']),
        dict(label='public-cargo-identity', argv=[str(sysroot / 'bin/cargo'), '-vV']),
        dict(label='rust-workspace-tests', argv=[str(sysroot / 'bin/cargo'), 'test', *common, '--workspace']),
        dict(label='release-tools', argv=[str(sysroot / 'bin/cargo'), 'build', *common,
             '-p', 'rust-interp-bytecode', '-p', 'rust-interp-mir-export', '--bins']),
        dict(label='launcher-contracts', argv=[sys.executable, '-m', 'unittest', 'discover',
             '-s', 'tests', '-p', 'test_host_proc_macro_launcher.py', '-v'], expected_tests=3),
        dict(label='screen-contracts', argv=[sys.executable, '-m', 'unittest', 'discover',
             '-s', 'tests', '-p', 'test_strict_warm*screen.py', '-v'], expected_tests=24),
        dict(label='capabilities', argv=[str(target / 'release/rust-interp-mir-export'), '--rust-interp-capabilities']),
        dict(label='real-histories', argv=[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
             '-p', 'test_host_proc_macro_native.py', '-v'], expected_tests=3, required_skips=0,
             environment_overrides=dict(RUST_INTERP_TEST_RUSTC=str(sysroot / 'bin/rustc'),
                 RUST_INTERP_TEST_EXPORTER=str(target / 'release/rust-interp-mir-export'),
                 RUST_INTERP_TEST_WRAPPER=str(target / 'release/rust-interp-rustc-wrapper'),
                 RUST_INTERP_TEST_VM=str(target / 'release/rust-interp-vm'),
                 RUST_INTERP_TEST_STD_SYSROOT=str(ready_path.parent / 'sysroot'),
                 RUST_INTERP_TEST_ARTIFACT_DIR=str(work / 'fixtures'))),
    ]
    for command in commands:
        command.update(cwd=str(ROOT), receipt=str(work / (command['label'] + '-process.json')),
                       stdout=str(work / (command['label'] + '.stdout')),
                       stderr=str(work / (command['label'] + '.stderr')))
    screen_command = [sys.executable, str(screen_root / 'benchmarks/experiments/strict-warm-build/screen.py'),
        '--run-id', screen_work.name, '--source', str(source), '--candidate-policy', 'host-proc-macro-opt',
        '--baseline-tool-key', key, '--candidate-tool-key', key,
        '--std-mir-ready', str(ready_path), '--lock-wait-seconds', '45']
    paths = [Path(__file__), ROOT / 'rust-toolchain.toml', ROOT / 'benchmarks/corpus.json',
        *sorted((ROOT / 'scripts').glob('*.py')),
        *[ROOT / 'tests' / name for name in ['test_host_proc_macro_launcher.py', 'test_host_proc_macro_native.py',
            'test_strict_warm_screen.py', 'test_strict_warm_cargo_screen.py', 'test_strict_warm_proc_macro_screen.py',
            'test_custom_cargo.py', 'test_custom_compiler.py', 'test_borrowck_cache.py']],
        *[ROOT / 'benchmarks/experiments/strict-warm-build' / name for name in
            ['screen.py', 'PROTOCOL.md', 'HOST_PROC_MACRO_OPT.md', 'HOST_PROC_MACRO_SCREEN.md']]]
    plan = dict(schema_version=1, kind='source-only-build-qualification-plan', status='not-executed',
        owner=str(ROOT), screen_owner=str(screen_root), production_source_revision='01e36c0426afbd61bbfe540af6673a5e7db2f87c',
        public_compiler_source_revision='cea272fa356e94bd2ee2cadf376630aa0683867a',
        tool_key=key, key_algorithm='interpreter.py ordered source-content fingerprint',
        tool_sources={str(p.relative_to(ROOT)): sha(p) for p in inputs},
        harness={str(p.relative_to(ROOT)): sha(p) for p in paths},
        shared_std=dict(path=str(ready_path), sha256=sha(ready_path), key=ready_path.parent.name,
            compiler=identity['compiler'], target=host, identity=identity),
        workload_admission=dict(lock='/Users/danluu/dev/rust-interp/.work/benchmark.lock',
            wait_seconds=45, after=['custom compiler integration and stable-CGU screen', 'Cargo-info-cache setup and screen'],
            supervisor_must_wait_children_on_receipt_failure=True, tool_build_minimum_free_gib=12,
            screen_initial_minimum_free_gib=16, per_command_minimum_free_gib=8),
        clean_environment=dict(remove_prefixes=['RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'],
            remove=['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'CARGO_BUILD_RUSTC', 'RUSTC_WRAPPER',
                    'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET',
                    'RUST_TEST_THREADS', 'CARGO', 'RUSTUP_TOOLCHAIN'],
            reject_prefixes=['LD_', 'DYLD_'], overrides=env),
        commands=commands,
        publication=dict(status='pending-qualification', tools=str(tools), screen_tools=str(installed_screen_tools),
            source_binaries={name: str(target / 'release' / name) for name in CURRENT_TOOL_BINARIES},
            require_new_destinations=True, same_all_arm_binaries=True,
            retain=['source inventory', 'public compiler/Cargo/driver hashes', 'exact command receipts and logs',
                    'test counts and zero real-fixture skips', 'capability output', 'all binary hashes',
                    'source.json', 'capabilities.json', 'ready.json'],
            qualify_before_install=True, preserve_all_prior_tools=True),
        project_preparation=dict(status='pending', destination=str(source),
            revision='9d3157963241cf89447119d34d6e887859f5e7e8',
            clone_argv=['git', 'clone', '--no-local', '--no-hardlinks', '--no-checkout',
                        str(screen_root / '.work/sources/nushell'), str(source)],
            checkout_argv=['git', '-C', str(source), 'checkout', '--detach',
                           '9d3157963241cf89447119d34d6e887859f5e7e8'],
            owner_marker={'owner': str(screen_root), 'revision': '9d3157963241cf89447119d34d6e887859f5e7e8'},
            forbid_alternates=True, initially_empty_project_targets=True),
        screen_command=screen_command, screen_ready=False, build_qualified=False,
        final_qualification=False, performance_claim=False,
        pending=['coordinate shared lock', 'run build and correctness commands with exact receipts',
                 'publish immutable qualified toolset', 'integrate reviewed screen harness in screen root',
                 'prepare owned source snapshot', 'run separate 27-command screen after releasing build lock'])
    write_json(args.output, plan)
    print(json.dumps(dict(plan=str(args.output.absolute()), sha256=sha(args.output),
        tool_key=key, screen_ready=False, workloads_executed=0)))


if __name__ == '__main__':
    main()
