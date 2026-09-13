#!/usr/bin/env python3
"""Build and install tools associated with one immutable owned stage2 compiler."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from compare_saved_runtime import acquire_lock, lock_wait_seconds
from custom_compiler import TOOL_POLICY, digest, file_digest, load_compiler, require
from interpreter import CURRENT_TOOL_BINARIES, ROOT, TOOLCHAIN, installed_tools, require_export_option
from workflow_io import capture, require_space, write_json


def source_identity():
    files = [ROOT / 'Cargo.toml', ROOT / 'Cargo.lock', ROOT / 'rust-toolchain.toml']
    for crate in ['bytecode', 'mir-export']:
        files += sorted((ROOT / 'crates' / crate).rglob('*.rs'))
        files.append(ROOT / 'crates' / crate / 'Cargo.toml')
    return {str(path.relative_to(ROOT)): file_digest(path) for path in files}


def cargo_identity():
    executable = Path(subprocess.check_output(
        ['rustup', 'which', '--toolchain', TOOLCHAIN, 'cargo'], text=True).strip()).resolve(strict=True)
    return dict(executable=str(executable), sha256=file_digest(executable), toolchain=TOOLCHAIN,
                version=subprocess.check_output([str(executable), '-Vv'], text=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler-key', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--lock-wait-seconds', type=lock_wait_seconds, default=45)
    args = parser.parse_args()
    require(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid run ID')
    (ROOT / '.work').mkdir(exist_ok=True)
    with (ROOT / '.work/benchmark.lock').open('a') as benchmark_lock:
        acquire_lock(benchmark_lock, args.lock_wait_seconds)
        compiler = load_compiler(ROOT, args.compiler_key)
        compiler.environment(os.environ)
        source = source_identity()
        cargo = cargo_identity()
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('RUST_INTERP_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET',
                             'CARGO_INCREMENTAL']}
        env.update(CARGO_TERM_COLOR='never', RUSTC_WRAPPER='', RUSTC_WORKSPACE_WRAPPER='')
        env = compiler.environment(env)
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        target = ROOT / '.work/custom-interpreter-build' / compiler.key
        command = [cargo['executable'], 'build', '--release', '--locked', '--offline',
                   '--jobs', '2', '-p', 'rust-interp-bytecode', '-p', 'rust-interp-mir-export',
                   '--bins', '--target-dir', str(target)]
        settings = dict(profile='release', jobs=2, locked=True, offline=True, extra_features=[],
                        profile_overrides={}, rustflags=None,
                        compiler_environment={k: env[k] for k in
                            ['RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_TERM_COLOR', 'PATH']})
        plan = dict(compiler_key=compiler.key, compiler_sysroot=str(compiler.sysroot),
                    source_files=source, command=command, cargo=cargo, settings=settings,
                    environment_sha256=digest(env))
        write_json(work / 'plan.json', plan)
        require_space(work, 8)
        child, stdout, stderr = capture(command, cwd=ROOT, env=env, receipt_path=work / 'build.json',
                                       receipt=dict(compiler_key=compiler.key, phase='build-tools'))
        (work / 'stdout').write_text(stdout)
        (work / 'stderr').write_text(stderr)
        require(child.returncode == 0, 'custom tool build failed; retained logs: ' + str(work))
        require(source_identity() == source, 'tool sources changed during compilation')
        require(cargo_identity() == cargo, 'Cargo changed during tool compilation')
        load_compiler(ROOT, compiler.key)
        binaries = {name: file_digest(target / 'release' / name) for name in CURRENT_TOOL_BINARIES}
        composition = dict(kind=TOOL_POLICY, compiler_key=compiler.key,
            compiler_sysroot=str(compiler.sysroot), source_files=source, binaries=binaries,
            cargo=cargo, settings=settings, build_environment_sha256=digest(env))
        key = digest(composition)
        with (ROOT / '.work/interpreter-tools.lock').open('a') as tool_lock:
            acquire_lock(tool_lock, args.lock_wait_seconds)
            directory = ROOT / '.work/interpreter-tools' / key
            require(not directory.exists(), 'custom tool identity is already installed')
            directory.mkdir(parents=True)
            for name in CURRENT_TOOL_BINARIES:
                shutil.copy2(target / 'release' / name, directory / name)
                (directory / name).chmod(0o555)
                require(file_digest(directory / name) == binaries[name], 'tool changed during publication')
            probe = subprocess.run([str(directory / 'rust-interp-mir-export'), '--rust-interp-capabilities'],
                                   env=env, capture_output=True, text=True, timeout=10, check=True)
            capabilities = json.loads(probe.stdout)
            require(capabilities.get('schema_version') == 1 and capabilities.get('bytecode_version') == 5
                    and capabilities.get('compiler_sysroot') == str(compiler.sysroot)
                    and 'stable-cgu-partitioning' in capabilities.get('export_options', []),
                    'exporter was not built against the selected compiler')
            capabilities.update(tool_key=key, exporter_sha256=binaries['rust-interp-mir-export'])
            write_json(directory / 'compiler.json', composition)
            write_json(directory / 'capabilities.json', capabilities)
            write_json(directory / 'ready.json', binaries)
            for name in ['compiler.json', 'capabilities.json', 'ready.json']:
                (directory / name).chmod(0o444)
            installed_tools(key)
            require_export_option(directory, key, 'stable-cgu-partitioning')
        write_json(work / 'result.json', dict(tool_key=key, compiler_key=compiler.key, binaries=binaries))
        print(json.dumps(dict(tool_key=key, compiler_key=compiler.key)))


if __name__ == '__main__':
    main()
