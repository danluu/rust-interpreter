#!/usr/bin/env python3
"""Import a qualified Cargo build and select it without changing rustup defaults.

Installed bytes and provenance are hashed once, then frozen and checked by inode,
mode, size, mtime and ctime. This is local mutation detection, not authentication
of an untrusted installation. Loading does not execute or rehash a compiler.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from custom_compiler import digest, file_digest, read_json, require, tree_stamps, valid_key
from toolchain_lookup import _installation

ROOT = Path(__file__).resolve().parents[1]
POLICY = 'owned-qualified-cargo-v1'


def file_identity(path):
    return dict(path=str(path), bytes=path.stat().st_size, sha256=file_digest(path))


@dataclass(frozen=True)
class Cargo:
    key: str
    directory: Path
    identity: dict

    @property
    def executable(self):
        return self.directory / 'payload/cargo'

    def environment(self, environment, toolchain, custom=None):
        env = environment.copy()
        binding = self.identity['pinned_compiler']
        require(toolchain == binding['toolchain'], 'Cargo selection uses a different pinned toolchain')
        require(not any(k.startswith(('LD_', 'DYLD_')) for k in env),
                'custom Cargo does not permit dynamic-loader overrides')
        require('RUST_SYSROOT' not in env, 'custom Cargo conflicts with RUST_SYSROOT')
        expected_toolchain = toolchain + '-' + binding['host']
        if 'RUSTUP_TOOLCHAIN' in env:
            require(env['RUSTUP_TOOLCHAIN'] in [toolchain, expected_toolchain],
                    'custom Cargo conflicts with RUSTUP_TOOLCHAIN')
        if 'RUSTUP_HOME' in env:
            require(Path(env['RUSTUP_HOME']).resolve() == Path(binding['rustup_home']),
                    'custom Cargo conflicts with RUSTUP_HOME')
        if custom is not None:
            require(custom.host == binding['host'], 'custom Cargo and compiler hosts differ')
            env = custom.environment(env)
            rustc = custom.rustc
        else:
            rustc = Path(binding['sysroot']) / 'bin/rustc'
        for name in ['RUSTC', 'CARGO_BUILD_RUSTC']:
            if name in env:
                require(Path(env[name]).resolve() == rustc, 'custom Cargo conflicts with ' + name)
        if 'CARGO' in env:
            require(Path(env['CARGO']).resolve() == self.executable, 'custom Cargo conflicts with CARGO')
        env.update(RUSTC=str(rustc), CARGO=str(self.executable),
                   RUSTUP_HOME=binding['rustup_home'], RUSTUP_TOOLCHAIN=expected_toolchain)
        return env

    def receipt(self, custom=None):
        binding = self.identity['pinned_compiler']
        return dict(key=self.key, executable=str(self.executable),
                    sha256=self.identity['files']['cargo'],
                    provenance=self.identity['provenance'],
                    compiler_key=custom.key if custom else None,
                    rustc=str(custom.rustc if custom else Path(binding['sysroot']) / 'bin/rustc'),
                    toolchain=binding['toolchain'])


def compiler_stamps(binding):
    return _installation(dict(home=binding['rustup_home'], toolchain=binding['toolchain']),
                         binding['compiler'], Path(binding['sysroot']))


def load_cargo(root, key):
    require(valid_key(key), 'Cargo key must contain 64 lowercase hexadecimal characters')
    directory = root / '.work/cargos' / key
    try:
        require(directory.resolve(strict=True) == directory and not directory.is_symlink(),
                'Cargo installation path is not owned')
        ready = read_json(directory / 'ready.json')
        identity = ready['identity']
        require(ready['owner'] == str(root) and ready['key'] == key and digest(identity) == key
                and identity['policy'] == POLICY, 'Cargo ownership or identity mismatch')
        current = tree_stamps(directory / 'payload')
        require(current == ready['stamps'], 'Cargo installation changed')
        require(set(identity['files']) == {p for p in current if p != '.'},
                'Cargo file inventory differs')
        require(all(valid_key(h) for h in identity['files'].values()) and
                all(not (s[2] & 0o222) for s in current.values()), 'Cargo installation is writable or invalid')
        require(os.access(directory / 'payload/cargo', os.X_OK), 'custom Cargo is not executable')
        require(compiler_stamps(identity['pinned_compiler']) == ready['compiler_stamps'],
                'pinned compiler installation changed; reimport Cargo after requalification')
        return Cargo(key, directory, identity)
    except (OSError, KeyError, TypeError, ValueError, AttributeError) as error:
        raise RuntimeError('invalid custom Cargo installation: ' + str(error)) from error


def install_qualified_cargo(root, report_path, mode, toolchain):
    """Import exact binary/source/build receipts from a completed qualification.

    The report may live in another explicitly selected owned worktree. It is
    read-only; the import belongs to root and contains independent file copies.
    """
    require(mode in ['stock', 'candidate'], 'unknown qualification mode')
    require(re.fullmatch(r'nightly-\d{4}-\d{2}-\d{2}', toolchain), 'expected dated pinned toolchain')
    report = read_json(report_path)
    owner = Path(report['owner'])
    require(report_path.resolve(strict=True).is_relative_to(owner / '.work') and
            report['status'] == 'passed' and report['candidate_source_restored'] is True,
            'Cargo report is not a passed owned qualification')
    selected = [t for t in report['tools'] if t['mode'] == mode]
    require(len(selected) == 1, 'Cargo qualification has no unique selected tool')
    tool = selected[0]
    binary, manifest_path = Path(tool['binary']['path']), Path(tool['source_manifest']['path'])
    require(binary.resolve(strict=True).is_relative_to(owner / '.work') and
            manifest_path.resolve(strict=True).is_relative_to(owner / '.work') and
            not binary.is_symlink() and not manifest_path.is_symlink(), 'Cargo inputs escape their owner')
    require(file_identity(binary) == tool['binary'] and file_identity(manifest_path) == tool['source_manifest'],
            'qualified Cargo binary or source manifest changed')
    manifest = read_json(manifest_path)
    composition = manifest['composition']
    require(digest(composition) == tool['tool_key'] == manifest['tool_key'] and
            composition['mode'] == mode and composition['cargo_sha256'] == tool['binary']['sha256'] and
            composition['source_revision'] == report['source_revision'] and
            composition['compiler'] == report['compiler'] and
            composition['environment_overrides'] == report['environment_overrides'],
            'qualified Cargo composition differs')
    require(re.fullmatch(r'[0-9a-f]{40}', composition['source_revision']) and
            composition['source_inventory'] and
            all(valid_key(h) for h in composition['source_inventory'].values()),
            'Cargo source provenance is incomplete')
    inputs = dict(source=manifest_path, qualification=report_path)
    for label in [mode + '-build', mode + '-regression']:
        rows = [c for c in report['commands'] if c['label'] == label]
        require(len(rows) == 1, 'missing Cargo build/test command')
        row = rows[0]
        receipt_path = report_path.parent / 'logs' / (label + '-process.json')
        receipt = read_json(receipt_path)
        require(receipt['status'] == 'finished' and receipt['command'] == row['command'] and
                receipt['returncode'] == row['returncode'] == row['expected_returncode'] and
                receipt['pid'] == row['pid'] and receipt['parent_pid'] == report['supervisor_pid'] and
                receipt['cwd'] == report['source'], 'Cargo process receipt differs')
        # Qualification records use the ordinary sorted JSON encoding here.
        require(row['source_inventory_sha256'] == hashlib.sha256(
            json.dumps(composition['source_inventory'], sort_keys=True).encode()).hexdigest(),
            'Cargo build/test sources differ from installed tool')
        inputs[label] = receipt_path
        for stream in ['stdout', 'stderr']:
            path = report_path.parent / 'logs' / (label + '.' + stream)
            require(file_digest(path) == row[stream + '_sha256'], 'Cargo command log changed')
            inputs[label + '.' + stream] = path
    compiler = report['compiler']
    hosts = [line[6:] for line in compiler.splitlines() if line.startswith('host: ')]
    require(len(hosts) == 1, 'Cargo build compiler has no unique host')
    rustc = Path(report['environment_overrides']['RUSTC'])
    require(file_identity(rustc) == report['compiler_files']['rustc'] and
            composition['compiler_sha256'] == report['compiler_files']['rustc']['sha256'],
            'Cargo build compiler changed')
    require(file_identity(Path(report['compiler_files']['cargo']['path'])) == report['compiler_files']['cargo']
            and composition['builder_sha256'] == report['compiler_files']['cargo']['sha256'],
            'Cargo builder changed')
    binding = dict(toolchain=toolchain, host=hosts[0], compiler=compiler,
                   sysroot=str(rustc.parent.parent), rustup_home=report['environment_overrides']['RUSTUP_HOME'])
    stamps = compiler_stamps(binding)
    parent = root / '.work/cargos'
    parent.mkdir(parents=True, exist_ok=True)
    require(parent.resolve(strict=True) == parent, 'Cargo installation parent is not owned')
    temporary = Path(tempfile.mkdtemp(prefix='.import-', dir=parent))
    payload = temporary / 'payload'; payload.mkdir()
    shutil.copy2(binary, payload / 'cargo')
    for name, path in inputs.items():
        shutil.copyfile(path, payload / name)
    files = {p.name: file_digest(p) for p in payload.iterdir()}
    require(files['cargo'] == tool['binary']['sha256'], 'copied Cargo differs')
    identity = dict(policy=POLICY, files=files, pinned_compiler=binding,
                    provenance=dict(source_revision=composition['source_revision'],
                        qualified_tool_key=tool['tool_key'], mode=mode,
                        source_manifest_sha256=files['source'], qualification_sha256=files['qualification'],
                        profile=composition['profile'], features=composition['features']))
    key = digest(identity)
    destination = parent / key
    if destination.exists():
        shutil.rmtree(temporary)
        return load_cargo(root, key)
    temporary.rename(destination)
    payload = destination / 'payload'
    for p in payload.iterdir():
        p.chmod(0o555 if p.name == 'cargo' else 0o444)
    payload.chmod(0o555)
    require(compiler_stamps(binding) == stamps, 'compiler changed during Cargo import')
    ready = dict(owner=str(root), key=key, identity=identity,
                 stamps=tree_stamps(payload), compiler_stamps=stamps)
    path = destination / 'ready.json'
    path.write_text(json.dumps(ready, sort_keys=True) + '\n'); path.chmod(0o444)
    return load_cargo(root, key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qualified-report', type=Path, required=True)
    parser.add_argument('--mode', choices=['stock', 'candidate'], required=True)
    args = parser.parse_args()
    from interpreter import TOOLCHAIN
    # Import only copies and validates existing evidence; no compiler/Cargo runs.
    from compare_saved_runtime import acquire_lock
    (ROOT / '.work').mkdir(exist_ok=True)
    with (ROOT / '.work/cargos.lock').open('a') as lock:
        acquire_lock(lock, 45)
        cargo = install_qualified_cargo(ROOT, args.qualified_report.resolve(strict=True), args.mode, TOOLCHAIN)
    print(json.dumps(cargo.receipt()))


if __name__ == '__main__':
    main()
