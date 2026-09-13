"""Compose an honestly identified stage2 package from the existing HIRC checkout.

The caller owns canonical admission, full source/history guards, every child
receipt and the preceding stage2/dist inventories. Native15 and strip6 remain
separate caller stages; this adapter never mutates the original production driver.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import tarfile
import tomllib

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'experiments/stable-cgu'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'scripts'))
from owned_stage import inventory, require, sha, write
from std_mir_source_paths import source_capability


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


engine = load('hir_stage2_package_engine', ROOT / 'experiments/hir-capture-upgrade/upgrade.py')
legacy = load('hir_stage2_package_legacy', HERE / 'production-driver.py')
SOURCE = engine.SOURCE
HOST = engine.old.HOST


def ordinary_files(records):
    """Convert the full guarded HIRC inventory without reinterpreting other kinds."""
    result = {}
    for name, row in records.items():
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts and path.parts,
                'invalid source inventory path')
        if row['kind'] == 'file':
            require(set(row) == {'kind', 'sha256'} and re.fullmatch('[0-9a-f]{64}', row['sha256']),
                    'invalid ordinary source digest')
            result[name] = row['sha256']
        elif row['kind'] == 'symlink':
            require(set(row) == {'kind', 'target'} and isinstance(row['target'], str),
                    'invalid tracked source symlink')
        else:
            require(row['kind'] == 'gitlink' and set(row) == {'kind', 'object'}
                    and re.fullmatch('[0-9a-f]{40}', row['object']), 'invalid source Git submodule')
    return result


def compose(command, work, records, source_state, component, lock_fd):
    """Package fresh stage2 products; return exact receipt and provenance references."""
    work = Path(work)
    require(work.is_absolute() and work.resolve(strict=True) == work and work.is_dir(),
            'package work root must be an existing ordinary owned directory')
    require(isinstance(lock_fd, int) and lock_fd >= 0, 'inherited canonical descriptor required')
    revision = source_state['revision']
    require(re.fullmatch('[0-9a-f]{40}', revision), 'truthful compiler source commit required')
    source_files = ordinary_files(source_state['files'])
    backtrace_files = ordinary_files(source_state['backtrace_files'])
    require(sha(SOURCE / 'bootstrap.toml') == source_state['config_sha256'], 'bootstrap profile changed')
    for name in ['stage2', 'stage2-hir', 'dist']:
        ref = records[name]
        path = Path(ref['path'])
        require(path.is_file() and not path.is_symlink() and path.resolve(strict=True) == path
                and sha(path) == ref['sha256'], 'stage2 component receipt changed')
        row = json.loads(path.read_bytes())
        require(row['returncode'] == 0 and row['source_revision'] == revision
                and row['config_sha256'] == source_state['config_sha256']
                and '--stage' in row['command']
                and row['command'][row['command'].index('--stage') + 1] == '2',
                'package requires actual new-source stage2 products')
        if name == 'stage2-hir':
            direct = row['direct_recipe']; direct_path = Path(direct['path'])
            require(direct_path.is_relative_to(work/'stage2-hir-direct') and direct_path.is_file()
                    and not direct_path.is_symlink() and direct_path.resolve(strict=True) == direct_path
                    and sha(direct_path) == direct['sha256'],
                    'stage2 complete direct-recipe evidence changed')
            evidence = json.loads(direct_path.read_bytes())
            require(evidence['status'] == 'passed' and evidence['returncode'] == 0
                    and evidence['source_revision'] == revision and evidence['actual_complete_recipe'] is True
                    and evidence['observations']['actual_verified_hits'] > 0
                    and all(sha(p) == h for p,h in evidence['evidence'].items()),
                    'stage2 package requires actual unabridged complete recipe proof')

    capability = work / 'source-capability.json'
    rust_src = work / 'rust-src'
    comparison = work / 'source-comparison.json'
    proof = work / 'llvm-source-proof.json'
    prefix = work / 'packaged-stage2-01'
    package_dir = work / 'package-01'
    for path in [capability, rust_src, comparison, proof, prefix, package_dir]:
        require(not path.exists() and not path.is_symlink(), 'first package destination already exists: ' + str(path))
    require((work / 'combined-upstream.patch').is_file()
            and not (work / 'combined-upstream.patch').is_symlink(), 'complete upstream-to-current patch required')
    write(capability, source_capability(revision))
    require(legacy.public_component() == component, 'pinned public rust-src component changed')
    shutil.copytree(legacy.PUBLIC_LIBRARY, rust_src / 'library', symlinks=False)
    copied = inventory(rust_src)
    require({name.removeprefix('library/'): item['sha256'] for name, item in copied.items()}
            == component['files'], 'distributed library source copy differs')
    checked, missing = {}, []
    for name, digest in source_files.items():
        if name.startswith('library/'):
            if name in copied:
                require(copied[name]['sha256'] == digest == sha(SOURCE / name),
                        'current compiler library differs from the public source component')
                checked[name] = digest
            else:
                missing.append(name)
    backtrace, backtrace_missing = {}, []
    for name, digest in backtrace_files.items():
        if 'library/backtrace/' + name in copied:
            require(copied['library/backtrace/' + name]['sha256'] == digest
                    == sha(SOURCE / 'library/backtrace' / name), 'current backtrace differs from distribution')
            backtrace[name] = digest
        else:
            backtrace_missing.append(name)
    old = json.loads(legacy.OLD_COMPARISON.read_text())
    require(sorted(missing) == sorted(old['missing'])
            and sorted(backtrace_missing) == sorted(old['backtrace']['missing']),
            'distribution source omissions differ')
    extras = {name: item['sha256'] for name, item in copied.items()
              if name not in checked and name.removeprefix('library/backtrace/') not in backtrace}
    require(all(name.startswith('library/vendor/') or name == 'library/.cargo/config.toml' for name in extras),
            'unrecognized distribution-only source file')
    lock = tomllib.loads((rust_src / 'library/Cargo.lock').read_text())
    packages = {(p['name'], p['version']): p.get('checksum') for p in lock['package']}
    vendors = {}
    for directory in sorted((rust_src / 'library/vendor').iterdir()):
        require(directory.is_dir() and not directory.is_symlink(), 'invalid distributed vendor directory')
        checksum = json.loads((directory / '.cargo-checksum.json').read_text())
        manifest = tomllib.loads((directory / 'Cargo.toml').read_text())['package']
        require(checksum['package'] == packages[(manifest['name'], manifest['version'])],
                'distributed vendor package differs from library lockfile')
        actual = {name: item['sha256'] for name, item in inventory(directory).items()}
        require(actual == checksum['files'] | {'.cargo-checksum.json': sha(directory / '.cargo-checksum.json')},
                'distributed vendor file differs from Cargo checksum')
        vendors[directory.name] = dict(package=manifest['name'], version=manifest['version'],
            checksum=checksum['package'], checksum_file=sha(directory / '.cargo-checksum.json'))
    write(comparison, dict(source_commit=revision, checked=checked, missing=missing, mismatched=[],
        backtrace=dict(checked=backtrace, missing=backtrace_missing, mismatched=[]),
        distributed_component=component, distribution_only=extras, vendor_packages=vendors,
        distribution_only_configuration={name: (rust_src / name).read_text() for name in extras
                                          if name == 'library/.cargo/config.toml'},
        source_state_plan_sha256=source_state['plan_sha256'],
        vendor_provenance='pinned installed public rust-src component; full files and Cargo checksum/lock binding; no crate archive assertion'))
    archive = SOURCE / ('build/cache/llvm-' + HOST + '-' + legacy.UPSTREAM + '-false') / legacy.LLVM.name
    objcopy = SOURCE / 'build' / HOST / 'ci-llvm/bin/llvm-objcopy'
    member_name = 'rust-dev-nightly-' + HOST + '/rust-dev/bin/llvm-objcopy'
    with tarfile.open(archive, 'r:xz') as reader:
        member = reader.getmember(member_name)
        require(member.isfile(), 'configured LLVM helper archive member is not ordinary')
        digest = hashlib.sha256(reader.extractfile(member).read()).hexdigest()
    require(sha(archive) == legacy.LLVM_SHA and sha(objcopy) == digest,
            'native support tool differs from exact configured CI archive')
    write(proof, dict(schema_version=1, archive=str(archive), archive_sha256=legacy.LLVM_SHA,
        member=member_name, member_sha256=digest,
        files={str(objcopy): dict(size=objcopy.stat().st_size, sha256=digest)}))
    command([sys.executable, HERE / 'package-owned.py', '--first-production', '--source-capability', capability,
        '--source', SOURCE, '--stage2', SOURCE / 'build' / HOST / 'stage2',
        '--std-image', SOURCE / 'build/tmp/tarball/rust-std' / HOST / 'image',
        '--dev-image', SOURCE / 'build/tmp/tarball/rustc-dev' / HOST / 'image',
        '--rust-src', rust_src, '--source-comparison', comparison,
        '--build-receipt', records['stage2-hir']['path'], '--original-build-receipt', records['stage2']['path'],
        '--dist-receipt', records['dist']['path'], '--patch', work / 'combined-upstream.patch',
        '--llvm-objcopy', objcopy, '--llvm-source-proof', proof, '--prefix', prefix,
        '--receipt', package_dir, '--host', HOST, '--lock-fd', str(lock_fd),
        '--lock-wait-seconds', '600'], cwd=ROOT, fds=(lock_fd,))
    receipt_path = package_dir / 'receipt.json'
    provenance_path = package_dir / 'provenance.json'
    receipt = json.loads(receipt_path.read_bytes())
    provenance = json.loads(provenance_path.read_bytes())
    require(provenance['source_commit'] == revision and provenance['stage'] == 2
            and provenance['package_mode'] == 'first-production'
            and provenance['package_receipt_sha256'] == sha(receipt_path)
            and provenance['std_source_paths'] == source_capability(revision)
            and receipt['source_revision'] == revision and receipt['prefix'] == str(prefix),
            'new stage2 package provenance differs from its current source')
    return dict(package_receipt=dict(path=str(receipt_path), sha256=sha(receipt_path)),
                provenance=dict(path=str(provenance_path), sha256=sha(provenance_path)))
