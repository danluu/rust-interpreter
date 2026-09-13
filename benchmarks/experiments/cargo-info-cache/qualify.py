#!/usr/bin/env python3
"""Build matched Cargo binaries and qualify empty-wrapper info-cache behavior."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, lock_wait_seconds
from workflow_io import SourceEdit, capture, require_space, write_json

REVISION = '3c0b534756e166d12eb9fd2e1abfe5b42ac6101e'
TOOLCHAIN = 'nightly-2026-09-08'
IMPLEMENTATION = 'src/util/rustc.rs'
REGRESSION = 'tests/testsuite/rustc_info_cache.rs'
FOCUSED = 'tests/info_cache_focused.rs'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_identity(path):
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=digest(data))


def git(source, *args):
    return subprocess.check_output(['git', *args], cwd=source)


def inventory(source, names):
    result = {}
    for name in names:
        path = source / name
        if path.is_symlink():
            data = b'symlink\0' + os.fsencode(os.readlink(path))
        else:
            require(path.is_file(), 'source input missing: ' + name)
            data = b'file\0' + path.read_bytes()
        result[name] = digest(data)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--lock-wait-seconds', type=lock_wait_seconds, default=45)
    args = parser.parse_args()
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid run ID')
    source = args.source.resolve(strict=True)
    require(source == ROOT / '.work/sources/cargo', 'source must be the owned Cargo snapshot')
    owner = json.loads((source / '.rust-interp-owned.json').read_bytes())
    require(owner['owner'] == str(ROOT) and owner['revision'] == REVISION and
            git(source, 'rev-parse', 'HEAD').decode().strip() == REVISION,
            'source ownership or revision differs')
    require(not (source / '.git/objects/info/alternates').exists(), 'source uses shared Git objects')
    patch = Path(__file__).with_name('cargo-info-cache.patch')
    require(git(source, 'diff', '--', IMPLEMENTATION, REGRESSION) == patch.read_bytes(),
            'candidate patch differs from the reviewed experiment')
    require(set(git(source, 'diff', '--name-only').decode().splitlines()) == {IMPLEMENTATION, REGRESSION},
            'unrecognized tracked source edits')
    names = [n for n in git(source, 'ls-files', '-z').decode().split('\0') if n]
    tracked_names = list(names)
    focused = Path(__file__).with_name('focused.rs')
    focused_path = source / FOCUSED
    if focused_path.exists():
        require(not focused_path.is_symlink() and focused_path.read_bytes() == focused.read_bytes(),
                'unrecognized focused test entry')
    else:
        with focused_path.open('xb') as stream:
            stream.write(focused.read_bytes())
    names.append(FOCUSED)
    candidate = (source / IMPLEMENTATION).read_bytes()
    stock = git(source, 'show', 'HEAD:' + IMPLEMENTATION)
    require(candidate != stock, 'candidate has no production change')
    frozen = inventory(source, names)
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    (work / 'logs').mkdir()
    (work / 'fixtures').mkdir()
    target = ROOT / '.work/cargo-info-target'
    cargo_home = ROOT / '.work/cargo-info-home'
    compiler_dir = Path.home() / '.rustup/toolchains' / (TOOLCHAIN + '-aarch64-apple-darwin')
    rustc, builder, rustfmt = [compiler_dir / 'bin' / n for n in ['rustc', 'cargo', 'rustfmt']]
    require(all(p.is_file() for p in [rustc, builder, rustfmt]), 'pinned toolchain is incomplete')
    env = {k: v for k, v in os.environ.items() if not k.startswith(('CARGO_', 'RUST_INTERP_', 'RUSTDEV_'))
           and k not in {'RUSTC', 'RUSTDOC', 'RUSTFLAGS', 'RUSTDOCFLAGS', 'RUSTC_WRAPPER',
                        'RUSTC_WORKSPACE_WRAPPER', 'CFG_RELEASE_CHANNEL'}}
    require(not any(k.startswith(('LD_', 'DYLD_')) for k in env), 'unexpected dynamic loader override')
    overrides = dict(CARGO_HOME=str(cargo_home), CARGO_TERM_COLOR='never', CARGO_INCREMENTAL='0',
        CARGO_PROFILE_RELEASE_DEBUG='1', CARGO_BUILD_JOBS='2', CFG_RELEASE_CHANNEL='nightly',
        RUSTC=str(rustc), RUSTDOC=str(compiler_dir / 'bin/rustdoc'), RUSTFLAGS='',
        CARGO_ENCODED_RUSTFLAGS='', RUSTC_WRAPPER='', RUSTC_WORKSPACE_WRAPPER='',
        RUSTUP_TOOLCHAIN=TOOLCHAIN + '-aarch64-apple-darwin', RUSTUP_HOME=str(Path.home() / '.rustup'))
    env.update(overrides)
    summary = dict(schema_version=1, status='waiting', owner=str(ROOT), source=str(source),
        source_revision=REVISION, supervisor_pid=os.getpid(), started_at=time.time(),
        performance_measurement=False, source_patch=file_identity(patch), environment_overrides=overrides,
        environment_sha256=digest(json.dumps(env, sort_keys=True).encode()),
        target=str(target), cargo_home=str(cargo_home), commands=[], tools=[],
        source_inventory_algorithm='SHA256 of file\\0 + bytes or symlink\\0 + link target',
        original_candidate_inventory=frozen, compiler_files={p.name: file_identity(p) for p in [rustc, builder, rustfmt]},
        harness={str(p.relative_to(ROOT)): file_identity(p) for p in [Path(__file__),
            patch, focused, Path(__file__).with_name('PLAN.md'), ROOT / 'scripts/workflow_io.py',
            ROOT / 'scripts/compare_saved_runtime.py']})
    write_json(work / 'summary.json', summary)

    def verify(expected):
        require(inventory(source, names) == expected, 'Cargo source changed during qualification')
        require(git(source, 'ls-files', '-z').decode().split('\0') == tracked_names + [''], 'tracked inventory changed')
        for item in summary['harness'].values():
            require(file_identity(Path(item['path'])) == item, 'qualification harness changed')

    def run(label, command, expected, returncode=0):
        verify(expected)
        require_space(ROOT, 8)
        print('Starting', label, flush=True)
        child, stdout, stderr = capture(command, cwd=source, env=env,
            receipt_path=work / 'logs' / (label + '-process.json'), receipt=dict(label=label))
        (work / 'logs' / (label + '.stdout')).write_text(stdout)
        (work / 'logs' / (label + '.stderr')).write_text(stderr)
        record = dict(label=label, command=command, pid=child.pid, returncode=child.returncode,
            expected_returncode=returncode, source_inventory_sha256=digest(json.dumps(expected, sort_keys=True).encode()),
            stdout_sha256=digest(stdout.encode()), stderr_sha256=digest(stderr.encode()))
        summary['commands'].append(record)
        write_json(work / 'summary.json', summary)
        verify(expected)
        print('Finished', label, 'exit', child.returncode, flush=True)
        require(child.returncode == returncode, f'{label} returned {child.returncode}; see retained logs')
        return stdout, stderr

    def install(mode, expected):
        binary = file_identity(target / 'release/cargo')
        composition = dict(schema_version=1, kind='cargo-empty-wrapper-info-cache', mode=mode,
            source_revision=REVISION, source_inventory=expected, compiler=summary['compiler'],
            compiler_sha256=summary['compiler_files']['rustc']['sha256'],
            builder_sha256=summary['compiler_files']['cargo']['sha256'],
            environment_overrides=overrides, profile='release', features='Cargo default features',
            cargo_sha256=binary['sha256'])
        key = digest(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode())
        destination = ROOT / '.work/cargo-info-tools' / key
        destination.mkdir(parents=True, exist_ok=False)
        shutil.copy2(binary['path'], destination / 'cargo')
        require(file_identity(destination / 'cargo')['sha256'] == binary['sha256'], 'installed binary differs')
        write_json(destination / 'source.json', dict(tool_key=key, composition=composition))
        write_json(destination / 'ready.json', dict(cargo=binary['sha256']))
        record = dict(mode=mode, tool_key=key, directory=str(destination),
            binary=file_identity(destination / 'cargo'), source_manifest=file_identity(destination / 'source.json'))
        summary['tools'].append(record)
        write_json(work / 'summary.json', summary)

    def retain_fixtures(mode):
        old = target / 'tmp/cit'
        require(old.is_dir() and not old.is_symlink(), 'test fixture directory missing')
        destination = work / 'fixtures' / mode
        old.rename(destination)
        summary.setdefault('fixture_moves', []).append(dict(mode=mode, original=str(old), retained=str(destination)))
        write_json(work / 'summary.json', summary)

    tail = ['--release', '--locked', '--offline', '--jobs', '2', '--target-dir', str(target), '-p', 'cargo']
    build_command = [str(builder), 'build', *tail, '--bin', 'cargo']
    test_command = [str(builder), 'test', *tail, '--test', 'info_cache_focused', 'rustc_info_cache::',
                    '--', '--test-threads=1', '--nocapture']
    try:
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            acquire_lock(lock, args.lock_wait_seconds)
            summary.update(status='running', lock_acquired_at=time.time())
            write_json(work / 'summary.json', summary)
            version, _ = run('compiler-version', [str(rustc), '-vV'], frozen)
            summary['compiler'] = version
            run('format-check', [str(rustfmt), '--edition', '2024', '--check', IMPLEMENTATION, REGRESSION, FOCUSED], frozen)
            run('fetch-locked', [str(builder), 'fetch', '--locked', '--target', 'aarch64-apple-darwin'], frozen)
            with SourceEdit(source / IMPLEMENTATION, candidate) as edit:
                edit.replace(stock)
                stock_frozen = dict(frozen, **{IMPLEMENTATION: digest(b'file\0' + stock)})
                verify(stock_frozen)
                run('stock-build', build_command, stock_frozen)
                stdout, stderr = run('stock-regression', test_command, stock_frozen, returncode=101)
                require('2 passed; 1 failed;' in stdout and
                        re.search(r'failures:\n\s+rustc_info_cache::rustc_info_cache_with_empty_wrappers\s+\ntest result:', stdout),
                        'stock failed outside the intended new regression')
                install('stock', stock_frozen)
                retain_fixtures('stock')
            verify(frozen)
            run('candidate-build', build_command, frozen)
            stdout, stderr = run('candidate-regression', test_command, frozen)
            require('3 passed; 0 failed; 0 ignored;' in stdout, 'candidate did not pass all cache tests')
            install('candidate', frozen)
            retain_fixtures('candidate')
            for tool in summary['tools']:
                require(file_identity(Path(tool['binary']['path'])) == tool['binary'] and
                        file_identity(Path(tool['source_manifest']['path'])) == tool['source_manifest'],
                        'installed qualified tool changed')
            verify(frozen)
            summary.update(status='passed', candidate_source_restored=True,
                           stock_expected_regression_failures=1, stock_existing_tests_passed=2,
                           candidate_tests_passed=3, source_only_production_difference=IMPLEMENTATION)
    except BaseException as error:
        summary.update(status='failed', error_type=type(error).__name__, error=str(error),
                       candidate_source_restored=(source / IMPLEMENTATION).read_bytes() == candidate)
        raise
    finally:
        summary['finished_at'] = time.time()
        write_json(work / 'summary.json', summary)


if __name__ == '__main__':
    main()
