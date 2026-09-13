#!/usr/bin/env python3
"""Compose a local stage2 prefix from provenanced bootstrap components."""
import argparse
import atexit
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
import tomllib

from owned_stage import CANONICAL_LOCK, workload_lock


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
parser.add_argument('--llvm-objcopy', type=Path, required=True)
parser.add_argument('--llvm-source-proof', type=Path, required=True)
parser.add_argument('--previous-package-receipt', type=Path)
parser.add_argument('--first-production', action='store_true')
parser.add_argument('--source-capability', type=Path)
parser.add_argument('--prefix', type=Path, required=True)
parser.add_argument('--receipt', type=Path, required=True)
parser.add_argument('--host', default='aarch64-apple-darwin')
parser.add_argument('--lock-wait-seconds', type=int, default=45)
parser.add_argument('--lock-fd', type=int, help='canonical lock descriptor inherited from the owned stage supervisor')
args = parser.parse_args()
require(0 < args.lock_wait_seconds <= 1800, 'invalid lock admission bound')
require((args.first_production and args.previous_package_receipt is None and args.source_capability is not None)
        or (not args.first_production and args.previous_package_receipt is not None and args.source_capability is None),
        'choose legacy additive packaging with a predecessor or explicit first-production with a source capability')
for name, value in vars(args).items():
    if isinstance(value, Path):
        setattr(args, name, value.resolve())
require(not args.prefix.exists(), 'package prefix already exists')
require(not any(name.startswith(('LD_', 'DYLD_')) for name in os.environ),
        'package probes require an ordinary dynamic loader environment')
require('RUST_SYSROOT' not in os.environ, 'package probes reject a sysroot override')
args.receipt.mkdir(parents=True, exist_ok=False)
started = time.time()
lock_path = CANONICAL_LOCK
admission = {'supervisor_pid': os.getpid(), 'started_at': started,
             'lock_path': str(lock_path), 'lock_wait_limit_seconds': args.lock_wait_seconds,
             'status': 'waiting', 'runner_sha256': sha256(Path(__file__)),
             'inputs': {name: str(value) if isinstance(value, Path) else value
                        for name, value in vars(args).items()}}
def save_admission():
    (args.receipt / 'admission.json').write_text(json.dumps(admission, indent=2) + '\n')
save_admission()
lock_scope = ExitStack()
atexit.register(lock_scope.close)
print('Owned package supervisor', os.getpid(), 'waiting for shared slot', flush=True)
try:
    lock_scope.enter_context(workload_lock(lock_path, args.lock_wait_seconds, args.lock_fd))
except TimeoutError:
    admission.update(status='lock admission timed out; no package started', finished_at=time.time())
    save_admission()
    raise SystemExit('shared lock unavailable; no package started')
admission.update(status='lock acquired', lock_acquired_at=time.time())
save_admission()

revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.source, text=True).strip()
require(not subprocess.check_output(['git', 'diff', 'HEAD', '--'], cwd=args.source),
        'compiler tracked source differs from frozen commit')
config_hash = sha256(args.source / 'bootstrap.toml')
build = json.loads(args.build_receipt.read_text())
original_build = json.loads(args.original_build_receipt.read_text())
dist = json.loads(args.dist_receipt.read_text())
llvm_proof = json.loads(args.llvm_source_proof.read_text())
require(llvm_proof['archive_sha256'] ==
        '0035445cb01c652999862c240d3c8ce663247abdc410482dde10f9e9c264bf8f',
        'objcopy archive is not the pinned CI LLVM archive')
require(sha256(Path(llvm_proof['archive'])) == llvm_proof['archive_sha256'],
        'CI LLVM archive changed')
with tarfile.open(llvm_proof['archive'], 'r:xz') as archive:
    member = archive.getmember(llvm_proof['member'])
    member_hash = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
require(member_hash == llvm_proof['member_sha256'] == sha256(args.llvm_objcopy),
        'objcopy does not match its pinned archive member')
require(str(args.llvm_objcopy) in llvm_proof['files'] and
        os.access(args.llvm_objcopy, os.X_OK), 'configured LLVM objcopy is unavailable')
previous_package = (json.loads(args.previous_package_receipt.read_text())
                    if args.previous_package_receipt is not None else None)
source_capability = None
if args.first_production:
    # This import comes from the same reviewed repository snapshot as the
    # production driver. No external validator path or derived snippets.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
    from std_mir_source_paths import source_capability as expected_source_capability, validate_probe
    source_capability = json.loads(args.source_capability.read_text())
    require(source_capability == expected_source_capability(revision),
            'production source capability differs from the truthful compiler revision')
    config = tomllib.loads((args.source / 'bootstrap.toml').read_text())
    reviewed_config = tomllib.loads((Path(__file__).with_name(
        'bootstrap-production-source-paths.toml')).read_text())
    require(config == reviewed_config, 'production bootstrap TOML differs from the full reviewed configuration')
    expected_rust = {'download-rustc': False, 'optimize': True, 'incremental': False,
        'debug-assertions': False, 'debug-assertions-tools': False, 'overflow-checks': False,
        'debug-assertions-std': False, 'overflow-checks-std': False, 'debug-logging': False,
        'debuginfo-level': 1, 'codegen-units': 16, 'lto': 'thin-local', 'channel': 'dev',
        'omit-git-hash': False, 'lld': False, 'llvm-tools': False, 'remap-debuginfo': True}
    require(all(config.get('rust', {}).get(k) == v for k, v in expected_rust.items())
            and config.get('build', {}).get('jobs') == 2
            and config.get('llvm', {}).get('download-ci-llvm') is True
            and config.get('llvm', {}).get('link-shared') is True,
            'first-production bootstrap profile differs from the reviewed assertions-off/remapped policy')
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
record['llvm_source_proof'] = llvm_proof
record['llvm_source_proof_sha256'] = sha256(args.llvm_source_proof)
record['package_mode'] = 'first-production' if args.first_production else 'additive-support-tool'
if previous_package is not None:
    record['previous_package_receipt_sha256'] = sha256(args.previous_package_receipt)
if source_capability is not None:
    record['std_source_paths'] = source_capability
    record['source_capability_sha256'] = sha256(args.source_capability)


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


def command(argv, expected_returncode=0):
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
    require(item['returncode'] == expected_returncode, 'package probe failed: ' + str(argv))
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
support_tool = args.prefix / 'lib/rustlib' / args.host / 'bin/rust-objcopy'
support_tool.parent.mkdir(parents=True, exist_ok=True)
require(not support_tool.exists(), 'unexpected preexisting objcopy support tool')
shutil.copy2(args.llvm_objcopy, support_tool)
require(sha256(support_tool) == member_hash and os.access(support_tool, os.X_OK),
        'packaged objcopy is not the verified executable')
record['support_tool'] = {'path': str(support_tool.relative_to(args.prefix)),
                          'sha256': member_hash, 'size': support_tool.stat().st_size}
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
option_help = command([str(args.prefix / 'bin/rustc'), '-Zhelp'])
require('stable-cgu-partitioning' in option_help,
        'packaged compiler lacks experimental option')
if args.first_production:
    require('stable-mono-cgu-partitioning' in option_help,
            'production compiler lacks the per-MonoItem policy option')
    probe = args.receipt / 'native-source-probe.rs'
    probe.write_text('const UNCALLED: u32 = panic!("native production source lookup probe");\n')
    diagnostics = command([str(args.prefix / 'bin/rustc'), str(probe), '--crate-type=lib',
        '--edition=2024', '--emit=metadata', '--error-format=json', '--sysroot', str(args.prefix),
        '-Zstable-cgu-partitioning=no', '-Zstable-mono-cgu-partitioning=no',
        '-o', str(args.receipt / 'native-source-probe.rmeta')], expected_returncode=1)
    library = args.prefix / 'lib/rustlib/src/rust/library'
    files = {str(p.relative_to(library)): sha256(p) for p in sorted(library.rglob('*')) if p.is_file()}
    record['native_source_probe'] = {'sources': validate_probe(
        [json.loads(line) for line in diagnostics.splitlines() if line.strip()], library, files),
        'source_files': files, 'diagnostics_rewritten': False,
        'raw_log': f'probe-{len(record["commands"]) - 1:02d}.log',
        'full_presentation_qualified': False, 'strict_integration_required': True}
    save()
command([str(support_tool), '--version'])
for path in [args.prefix / 'bin/rustc', support_tool,
             *sorted((args.prefix / 'lib').rglob('*.dylib'))]:
    command(['otool', '-L', str(path)])
    command(['otool', '-l', str(path)])

record['files'] = {str(path.relative_to(args.prefix)): sha256(path)
                   for path in sorted(args.prefix.rglob('*')) if path.is_file()}
if previous_package is not None:
    require(all(record['files'].get(name) == value
                for name, value in previous_package['files'].items()),
            'previously qualified package file changed')
    require(record['files'].keys() - previous_package['files'].keys() ==
            {str(support_tool.relative_to(args.prefix))}, 'unexpected package additions')
    record['previous_package_files_preserved'] = len(previous_package['files'])
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
              'llvm_source_proof_sha256': sha256(args.llvm_source_proof),
              'llvm_archive_sha256': llvm_proof['archive_sha256'],
              'objcopy_sha256': member_hash,
              'packaging': 'assembled stage2 runtime plus bootstrap rustc-dev/std images and matching pinned rust-src'}
if previous_package is not None:
    provenance['previous_package_receipt_sha256'] = sha256(args.previous_package_receipt)
if source_capability is not None:
    provenance.update(std_source_paths=source_capability, package_mode='first-production',
        source_capability_sha256=sha256(args.source_capability),
        native_std_profile='assertions-off; overflow-checks-off; bootstrap source remapping enabled',
        native_source_probe='passed raw E0080 source/snippet preflight; strict integration still required')
(args.receipt / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
print(json.dumps({'prefix': str(args.prefix), 'provenance': str(args.receipt / 'provenance.json')}))
