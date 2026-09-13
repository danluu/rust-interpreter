#!/usr/bin/env python3
"""Compose a local stage2 prefix from provenanced bootstrap components."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--stage2', type=Path, required=True)
parser.add_argument('--std-image', type=Path, required=True)
parser.add_argument('--dev-image', type=Path, required=True)
parser.add_argument('--rust-src', type=Path, required=True)
parser.add_argument('--source-comparison', type=Path, required=True)
parser.add_argument('--build-receipt', type=Path, required=True)
parser.add_argument('--original-build-receipt', type=Path, required=True)
parser.add_argument('--dist-receipt', type=Path, required=True)
parser.add_argument('--patch', type=Path, required=True)
parser.add_argument('--prefix', type=Path, required=True)
parser.add_argument('--receipt', type=Path, required=True)
parser.add_argument('--host', default='aarch64-apple-darwin')
parser.add_argument('--lock-wait-seconds', type=int, default=45)
args = parser.parse_args()
require(0 < args.lock_wait_seconds <= 1800, 'invalid lock admission bound')
for name, value in vars(args).items():
    if isinstance(value, Path):
        setattr(args, name, value.resolve())
require(not args.prefix.exists(), 'package prefix already exists')
require(not any(name.startswith(('LD_', 'DYLD_')) for name in os.environ),
        'package probes require an ordinary dynamic loader environment')
require('RUST_SYSROOT' not in os.environ, 'package probes reject a sysroot override')
args.receipt.mkdir(parents=True, exist_ok=False)
started = time.time()
lock_path = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
admission = {'supervisor_pid': os.getpid(), 'started_at': started,
             'lock_path': str(lock_path), 'lock_wait_limit_seconds': args.lock_wait_seconds,
             'status': 'waiting', 'runner_sha256': sha256(Path(__file__)),
             'inputs': {name: str(value) if isinstance(value, Path) else value
                        for name, value in vars(args).items()}}
def save_admission():
    (args.receipt / 'admission.json').write_text(json.dumps(admission, indent=2) + '\n')
save_admission()
lock = lock_path.open('a+')
def admission_timeout(signum, frame):
    raise TimeoutError('shared resource admission deadline')
previous_alarm = signal.signal(signal.SIGALRM, admission_timeout)
signal.alarm(args.lock_wait_seconds)
print('Owned package supervisor', os.getpid(), 'waiting for shared slot', flush=True)
try:
    fcntl.flock(lock, fcntl.LOCK_EX)
except TimeoutError:
    admission.update(status='lock admission timed out; no package started', finished_at=time.time())
    save_admission()
    raise SystemExit('shared lock unavailable; no package started')
finally:
    signal.alarm(0)
    signal.signal(signal.SIGALRM, previous_alarm)
admission.update(status='lock acquired', lock_acquired_at=time.time())
save_admission()

revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.source, text=True).strip()
require(not subprocess.check_output(['git', 'diff', 'HEAD', '--'], cwd=args.source),
        'compiler tracked source differs from frozen commit')
config_hash = sha256(args.source / 'bootstrap.toml')
build = json.loads(args.build_receipt.read_text())
original_build = json.loads(args.original_build_receipt.read_text())
dist = json.loads(args.dist_receipt.read_text())
for receipt in [build, original_build, dist]:
    require(receipt['returncode'] == 0, 'input bootstrap command did not pass')
    require(receipt['source_revision'] == revision, 'source revision differs from build')
    require(receipt['config_sha256'] == config_hash, 'configuration differs from build')
    require('--stage' in receipt['command'] and
            receipt['command'][receipt['command'].index('--stage') + 1] == '2',
            'component was not requested at stage2')
comparison = json.loads(args.source_comparison.read_text())
require(comparison['source_commit'] == revision and not comparison['mismatched'],
        'rust-src does not match the compiler library source')
for name, expected in comparison['checked'].items():
    require(sha256(args.rust_src / name) == expected, 'rust-src changed since comparison')
    require(sha256(args.source / name) == expected, 'compiler library source changed')
require(all(Path(name).name in ['.gitignore', '.gitmodules', '.gitattributes']
            for name in comparison['missing']), 'required library source missing')
backtrace = comparison['backtrace']
require(not backtrace['mismatched'], 'backtrace source differs')
for name, expected in backtrace['checked'].items():
    require(sha256(args.rust_src / 'library/backtrace' / name) == expected and
            sha256(args.source / 'library/backtrace' / name) == expected,
            'backtrace source changed since comparison')
require(all(name == '.gitignore' or name.startswith('crates/') for name in backtrace['missing']),
        'required backtrace source missing from component')

inputs = {}
for name in ['stage2', 'std_image', 'dev_image', 'rust_src']:
    root = getattr(args, name)
    inputs[name] = {'path': str(root), 'files': {}}
    for path in sorted(root.rglob('*')):
        if path.is_file():
            inputs[name]['files'][str(path.relative_to(root))] = {
                'size': path.stat().st_size, 'sha256': sha256(path)}
for name, receipt in [('stage2', build), ('std_image', dist), ('dev_image', dist)]:
    root = str(getattr(args, name))
    require(receipt.get('artifact_inventories', {}).get(root) == inputs[name]['files'],
            'component path/content does not match recorded bootstrap output: ' + root)
original_runtime = original_build.get('artifact_inventories', {}).get(str(args.stage2))
require(original_runtime is not None, 'original build did not record this stage2 runtime')
current_runtime = inputs['stage2']['files']
require(all(current_runtime.get(name) == value for name, value in original_runtime.items()),
        'runtime bytes changed after the original stage2 build')
runtime_additions = sorted(current_runtime.keys() - original_runtime.keys())
require(set(runtime_additions) <= {'bin/rustdoc'}, 'unexpected runtime additions after compiler tests')
estimated_bytes = sum(value['size'] for tree in inputs.values() for value in tree['files'].values())
require(shutil.disk_usage(args.source).free >= 8 * 2**30 + estimated_bytes,
        'insufficient space for complete package plus 8GiB floor')
record = {'schema_version': 1, 'supervisor_pid': os.getpid(), 'started_at': started,
          'lock_path': str(lock_path), 'lock_wait_seconds': time.time() - started,
          'prefix': str(args.prefix), 'source_revision': revision, 'config_sha256': config_hash,
          'free_bytes_before': shutil.disk_usage(args.source).free,
          'inputs': inputs, 'commands': [], 'copied_files': {}, 'materialized_file_symlinks': {}}


def save():
    (args.receipt / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')


def copy_tree(root, destination, skip=()):
    for path in sorted(root.iterdir()):
        relative = path.relative_to(root)
        if str(relative) in skip:
            continue
        target = destination / relative
        if path.is_dir():
            require(not path.is_symlink(), 'unexpected live directory symlink: ' + str(path))
            target.mkdir(parents=True, exist_ok=True)
            copy_tree(path, target)
        elif path.is_file():
            expected = sha256(path)
            if target.exists():
                require(target.is_file() and sha256(target) == expected,
                        'conflicting component file: ' + str(target))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target, follow_symlinks=True)
            require(sha256(target) == expected, 'copy digest mismatch')
            record['copied_files'][str(target.relative_to(args.prefix))] = expected
            if path.is_symlink():
                record['materialized_file_symlinks'][str(path)] = str(path.resolve())
        else:
            raise RuntimeError('unsupported package entry: ' + str(path))


def command(argv):
    index = len(record['commands'])
    log_path = args.receipt / f'probe-{index:02d}.log'
    with log_path.open('w') as log:
        child = subprocess.Popen(argv, cwd=args.prefix, stdout=log, stderr=subprocess.STDOUT)
        try:
            identity = subprocess.run(['ps', '-p', str(child.pid), '-o', 'pid,ppid,lstart,command'],
                                      text=True, capture_output=True)
            item = {'argv': argv, 'pid': child.pid, 'started_at': time.time(),
                    'identity': identity.stdout.strip(), 'identity_status': identity.returncode}
            record['commands'].append(item)
            save()
        finally:
            returncode = child.wait()
        item['returncode'] = returncode
    item.update(finished_at=time.time(), log_sha256=sha256(log_path))
    save()
    require(item['returncode'] == 0, 'package probe failed: ' + str(argv))
    return log_path.read_text()


save()
args.prefix.mkdir(parents=True)
# Preserve every qualified runtime file, including native LLVM link aliases.
# Bootstrap's std/private distribution images may overlay only identical bytes.
copy_tree(args.stage2 / 'bin', args.prefix / 'bin')
copy_tree(args.stage2 / 'lib', args.prefix / 'lib', skip=('rustlib',))
for path in sorted((args.stage2 / 'lib/rustlib').iterdir()):
    if path.name == 'src':
        continue
    if path.name == 'rustc-src':
        # Bootstrap exposes its live checkout here for development. Ship only
        # the materialized compiler sources in the provenanced rustc-dev image.
        require(sorted(child.name for child in path.iterdir()) == ['rust'] and
                (path / 'rust').is_symlink() and
                (path / 'rust').resolve() == args.source,
                'unexpected stage2 rustc-src layout')
        record['omitted_live_source_link'] = str(path / 'rust')
        continue
    if path.name == args.host:
        copy_tree(path, args.prefix / 'lib/rustlib' / args.host)
    elif path.is_dir():
        copy_tree(path, args.prefix / 'lib/rustlib' / path.name)
copy_tree(args.std_image, args.prefix)
copy_tree(args.dev_image, args.prefix)
copy_tree(args.rust_src, args.prefix / 'lib/rustlib/src/rust')
copy_tree(args.source / 'LICENSES', args.prefix / 'share/doc/rust/licenses')
for name in ['COPYRIGHT', 'LICENSE-APACHE', 'LICENSE-MIT', 'README.md']:
    destination = args.prefix / 'share/doc/rust' / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.source / name, destination)

for name, expected in current_runtime.items():
    require((args.prefix / name).is_file() and
            sha256(args.prefix / name) == expected['sha256'],
            'qualified runtime file missing or changed in package: ' + name)
record['qualified_runtime_files_preserved'] = len(current_runtime)

version = command([str(args.prefix / 'bin/rustc'), '-vV'])
require('commit-hash: ' + revision in version, 'packaged compiler source identity differs')
require(command([str(args.prefix / 'bin/rustc'), '--print', 'sysroot']).strip() == str(args.prefix),
        'packaged compiler does not resolve its own sysroot')
require('stable-cgu-partitioning' in command([str(args.prefix / 'bin/rustc'), '-Zhelp']),
        'packaged compiler lacks experimental option')
for path in [args.prefix / 'bin/rustc', *sorted((args.prefix / 'lib').rglob('*.dylib'))]:
    command(['otool', '-L', str(path)])
    command(['otool', '-l', str(path)])

record['files'] = {str(path.relative_to(args.prefix)): sha256(path)
                   for path in sorted(args.prefix.rglob('*')) if path.is_file()}
record.update(finished_at=time.time(), free_bytes_after=shutil.disk_usage(args.source).free,
              status='composed; loader closure and installer qualification still required')
save()
provenance = {'stage': 2, 'source_commit': revision,
              'base_source_commit': 'cea272fa356e94bd2ee2cadf376630aa0683867a',
              'patch_sha256': sha256(args.patch), 'bootstrap_sha256': config_hash,
              'build_receipt_sha256': sha256(args.build_receipt),
              'original_build_receipt_sha256': sha256(args.original_build_receipt),
              'qualified_runtime_additions': runtime_additions,
              'dist_receipt_sha256': sha256(args.dist_receipt),
              'package_receipt_sha256': sha256(args.receipt / 'receipt.json'),
              'rust_src_comparison_sha256': sha256(args.source_comparison),
              'rust_src_source': str(args.rust_src), 'rustc_vv': version,
              'packaging': 'assembled stage2 runtime plus bootstrap rustc-dev/std images and matching pinned rust-src'}
(args.receipt / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
print(json.dumps({'prefix': str(args.prefix), 'provenance': str(args.receipt / 'provenance.json')}))
