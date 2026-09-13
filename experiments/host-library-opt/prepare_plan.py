#!/usr/bin/env python3
"""Freeze the host-library build inputs under admission; no compiler/Cargo probes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, lock_wait_seconds
from custom_compiler import require
from qualified_public_tools import (BINARIES, COMPILER_REVISION, HOST_LIBRARY_BUILD_POLICY,
                                    STD_FLAGS, STD_POLICY, TOOLCHAIN, planned_commands)
from workflow_io import write_json

LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(args):
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid run ID')
    owner = args.screen_root.resolve(strict=True)
    require(owner != ROOT, 'publication requires distinct build and future screen owners')
    ready_path = args.std_mir_ready.resolve(strict=True)
    ready = json.loads(ready_path.read_bytes()); identity = ready['identity']
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    require(ready['owner'] == str(owner) and ready_path == owner / '.work/std-mir' / key / 'ready.json'
            and not {'compiler_key', 'cargo', 'namespace', 'source_sha256'} & identity.keys()
            and identity['policy'] == STD_POLICY and identity['flags'] == STD_FLAGS
            and identity['target'] == 'aarch64-apple-darwin'
            and 'commit-hash: ' + COMPILER_REVISION + '\n' in identity['compiler'],
            'host-library plan requires the existing pinned public standard library')
    require(not args.output.exists() and not args.output.is_symlink() and args.output.parent.is_dir(),
            'plan output must be new')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    work = ROOT / '.work' / args.run_id
    require(not work.exists() and not work.is_symlink(), 'build destination already exists')
    target = work / 'target'; public = Path.home() / '.rustup/toolchains' / TOOLCHAIN
    tool_paths = [ROOT / 'Cargo.toml', ROOT / 'Cargo.lock']
    for crate in ['bytecode', 'mir-export']:
        tool_paths += sorted((ROOT / 'crates' / crate).rglob('*.rs'))
        tool_paths.append(ROOT / 'crates' / crate / 'Cargo.toml')
    workspace = [ROOT / 'Cargo.toml', ROOT / 'Cargo.lock', ROOT / 'rust-toolchain.toml',
                 *sorted(p for p in (ROOT / 'crates').rglob('*') if p.is_file())]
    contract = Path(__file__).with_name('PUBLICATION.md')
    harness = [*sorted((ROOT / 'scripts').glob('*.py')),
        *sorted(p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py', '.md']),
        ROOT / 'benchmarks/experiments/host-proc-macro/build.py',
        ROOT / 'docs/HOST-LIBRARY-OPT.md',
        *[ROOT / 'tests' / name for name in ['test_host_library_launcher.py', 'test_host_library_publication.py',
            'test_host_library_native.py', 'test_host_proc_macro_launcher.py', 'test_host_proc_macro_native.py',
            'test_borrowck_cache.py', 'test_qualified_public_tools.py', 'test_public_tool_publication.py',
            'test_frontend_worker_publication.py']]]
    all_paths = sorted(set([*workspace, *tool_paths, *harness]))
    require(all(p.resolve(strict=True) == p and p.is_file() for p in all_paths),
            'source inventory contains a symlink or non-file')
    names = [str(p.relative_to(ROOT)) for p in all_paths]
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z', '--', *names], cwd=ROOT).decode().split('\0'))
    require(set(names) <= tracked, 'all build and qualification sources must be committed before freezing')
    subprocess.check_call(['git', 'diff', '--exit-code', revision, '--', *names], cwd=ROOT)
    relative = lambda paths: {str(p.relative_to(ROOT)): sha(p) for p in paths}
    source_key = hashlib.sha256(b''.join(str(p.relative_to(ROOT)).encode() + b'\0' + p.read_bytes()
                                        for p in tool_paths)).hexdigest()
    env = dict(CARGO_TERM_COLOR='never', CARGO_TERM_VERBOSE='true', CARGO_INCREMENTAL='0',
        CARGO_PROFILE_DEV_DEBUG='0', CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='1',
        RUSTC=str(public / 'bin/rustc'), RUSTDOC=str(public / 'bin/rustdoc'), RUSTUP_TOOLCHAIN=TOOLCHAIN)
    common = ['--release', '--locked', '--offline', '--jobs', '2', '--target-dir', str(target)]
    python_test = lambda pattern: [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern, '-v']
    commands = [
        ('public-rustc-identity', [str(public / 'bin/rustc'), '-vV']),
        ('public-cargo-identity', [str(public / 'bin/cargo'), '-vV']),
        ('rust-workspace-tests', [str(public / 'bin/cargo'), 'test', *common, '--workspace']),
        ('release-tools', [str(public / 'bin/cargo'), 'build', *common, '-p', 'rust-interp-bytecode', '-p', 'rust-interp-mir-export', '--bins']),
        ('launcher-contracts', python_test('test_host_library_launcher.py')),
        ('publication-contracts', python_test('test_host_library_publication.py')),
        ('capabilities', [str(target / 'release/rust-interp-mir-export'), '--rust-interp-capabilities']),
        ('wrapper-capabilities', [str(target / 'release/rust-interp-rustc-wrapper'), '--rust-interp-host-library-capability']),
        ('real-histories', python_test('test_host_library_native.py'))]
    records = [dict(label=label, argv=argv, cwd=str(ROOT), receipt=str(work / (label + '-process.json')),
                    stdout=str(work / (label + '.stdout')), stderr=str(work / (label + '.stderr')))
               for label, argv in commands]
    records[-1]['environment_overrides'] = dict(RUST_INTERP_TEST_RUSTC=env['RUSTC'],
        RUST_INTERP_TEST_VM=str(target / 'release/rust-interp-vm'),
        RUST_INTERP_TEST_WRAPPER=str(target / 'release/rust-interp-rustc-wrapper'),
        RUST_INTERP_TEST_EXPORTER=str(target / 'release/rust-interp-mir-export'),
        RUST_INTERP_TEST_STD_SYSROOT=str(ready_path.parent / 'sysroot'),
        RUST_INTERP_TEST_ARTIFACT_DIR=str(work / 'fixtures'))
    plan = dict(schema_version=2, kind='source-only-build-qualification-plan', status='not-executed',
        qualification_policy=HOST_LIBRARY_BUILD_POLICY, owner=str(ROOT), screen_owner=str(owner),
        production_source_revision=revision, public_compiler_source_revision=COMPILER_REVISION,
        source_input_key=source_key, source_input_paths=[str(p.relative_to(ROOT)) for p in tool_paths],
        tool_sources=relative(tool_paths), workspace_sources=relative(workspace), harness=relative(harness),
        tool_key=None, screen_command=None, shared_std=dict(path=str(ready_path), sha256=sha(ready_path),
            key=key, identity=identity, compiler=identity['compiler'], target=identity['target']),
        clean_environment=dict(remove_prefixes=['RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'],
            remove=['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'CARGO_BUILD_RUSTC', 'RUSTC_WRAPPER',
                'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET',
                'RUST_TEST_THREADS', 'RUSTDOC', 'CARGO', 'RUSTUP_TOOLCHAIN'],
            reject_prefixes=['LD_', 'DYLD_'], overrides=env), commands=records,
        workload_admission=dict(lock=str(LOCK), wait_seconds=args.lock_wait_seconds,
            tool_build_minimum_free_gib=12, per_command_minimum_free_gib=8),
        publication=dict(composition_kind='qualified-public-toolset-v1', contract=str(contract.relative_to(ROOT)),
            contract_sha256=sha(contract), source_binaries={name: str(target / 'release' / name) for name in BINARIES}),
        implementation_contract_tests=dict(status='not-executed', patterns=['test_qualified_public_tools.py',
            'test_public_tool_publication.py', 'test_frontend_worker_publication.py', 'test_host_library_publication.py'],
            expected_tests=[5, 5, 2, 5], canonical_lock_required=True),
        final_qualification=False, performance_claim=False, screen_ready=False, workloads_executed=0)
    planned_commands(plan, {'rustc_path': env['RUSTC']}, {'path': str(public / 'bin/cargo')}, HOST_LIBRARY_BUILD_POLICY)
    write_json(args.output, plan)
    print(json.dumps(dict(path=str(args.output), sha256=sha(args.output), source_input_key=source_key,
                         tool_key=None, workloads_executed=0)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen-root', type=Path, required=True)
    parser.add_argument('--std-mir-ready', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--lock-wait-seconds', type=lock_wait_seconds, default=600)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(LOCK.is_file() and LOCK.resolve(strict=True) == LOCK, 'canonical workload lock is required')
    receipt_path = args.output.with_suffix('.process.json')
    require(not receipt_path.exists() and not receipt_path.is_symlink(), 'metadata receipt already exists')
    receipt = dict(schema_version=1, kind='source-metadata-only', status='waiting', pid=os.getpid(),
        parent_pid=os.getppid(), cwd=os.getcwd(), command=sys.argv, lock=str(LOCK),
        waiting_at=time.time(), workloads_executed=0)
    write_json(receipt_path, receipt)
    try:
        with LOCK.open('a') as lock:
            acquire_lock(lock, args.lock_wait_seconds)
            receipt.update(status='running', started_at=time.time()); write_json(receipt_path, receipt)
            freeze(args)
            receipt.update(status='passed', plan_sha256=sha(args.output))
    except BaseException as error:
        receipt.update(status='failed', error=str(error)); raise
    finally:
        receipt['finished_at'] = time.time(); write_json(receipt_path, receipt)


if __name__ == '__main__':
    main()
