#!/usr/bin/env python3
"""Install and validate an owned, complete stage2 compiler without rustup changes."""
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
POLICY = 'owned-stage2-compiler-v1'
TOOL_POLICY = 'owned-compiler-tools-v1'
PRIVATE_CRATES = ('rustc_abi', 'rustc_ast', 'rustc_borrowck', 'rustc_data_structures',
                  'rustc_driver', 'rustc_hir', 'rustc_incremental', 'rustc_interface',
                  'rustc_middle', 'rustc_session', 'rustc_span')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_digest(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def valid_key(key):
    return isinstance(key, str) and re.fullmatch(r'[0-9a-f]{64}', key) is not None


def tree_stamps(directory):
    require(directory.resolve(strict=True) == directory and directory.is_dir(),
            'compiler installation must be an ordinary directory')
    result = {}
    for path in [directory, *sorted(directory.rglob('*'))]:
        require(not path.is_symlink(), 'compiler installation contains a symlink: ' + str(path))
        stat = path.stat()
        require(path.is_file() or path.is_dir(), 'unsupported compiler installation entry')
        result[str(path.relative_to(directory))] = [stat.st_dev, stat.st_ino, stat.st_mode,
            stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]
    return result


def compiler_programs(host):
    programs = ['bin/rustc']
    if host.endswith('-apple-darwin'):
        programs.append('lib/rustlib/' + host + '/bin/rust-objcopy')
    return programs


def require_executable_programs(sysroot, host):
    for name in compiler_programs(host):
        require(os.access(sysroot / name, os.X_OK), 'custom compiler program is not executable: ' + name)


def require_complete(files, host):
    require(re.fullmatch(r'[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)+', host) is not None,
            'invalid custom compiler host')
    for name in compiler_programs(host):
        require(name in files, 'custom compiler is missing ' + name)
    require('bin/cargo' not in files, 'compiler installation must not shadow the separately selected Cargo')
    lib = 'lib/rustlib/' + host + '/lib/'
    names = [p[len(lib):] for p in files if p.startswith(lib) and '/' not in p[len(lib):]]
    def crate_files(crate, suffixes):
        return [name for name in names if name.startswith('lib' + crate + '-')
                and any(name.endswith(suffix) for suffix in suffixes)]
    for crate in ['core', 'alloc', 'std', 'test', 'proc_macro']:
        require(len(crate_files(crate, ['.rlib'])) == 1,
                'custom compiler has missing or ambiguous native ' + crate)
    for crate in PRIVATE_CRATES:
        require(len({p.rsplit('.', 1)[0] for p in crate_files(crate, ['.rlib', '.rmeta'])}) == 1,
                'custom compiler has missing or ambiguous rustc-dev ' + crate)
    require(len([p for p in files if p.startswith('lib/librustc_driver-')
                 and p.endswith(('.dylib', '.so', '.dll'))]) == 1,
            'custom compiler has missing or ambiguous driver library')
    source = 'lib/rustlib/src/rust/library/'
    for name in ['Cargo.toml', 'Cargo.lock', 'core/src/lib.rs', 'std/src/lib.rs', 'proc_macro/src/lib.rs']:
        require(source + name in files, 'custom compiler is missing rust-src ' + name)


def read_json(path):
    require(not path.is_symlink() and path.is_file() and path.stat().st_size <= 32 * 1024 * 1024,
            'missing or invalid compiler manifest: ' + str(path))
    return json.loads(path.read_bytes())


@dataclass(frozen=True)
class Compiler:
    key: str
    sysroot: Path
    identity: dict

    @property
    def rustc(self):
        return self.sysroot / 'bin/rustc'

    @property
    def host(self):
        return self.identity['host']

    def environment(self, environment):
        env = environment.copy()
        require(not any(k.startswith(('LD_', 'DYLD_')) for k in env),
                'custom compiler does not permit dynamic-loader overrides')
        require('RUST_SYSROOT' not in env, 'custom compiler conflicts with RUST_SYSROOT')
        if 'RUSTC' in env:
            require(Path(env['RUSTC']).resolve() == self.rustc,
                    'custom compiler conflicts with RUSTC')
        env['RUSTC'] = str(self.rustc)
        env['PATH'] = str(self.sysroot / 'bin') + os.pathsep + env.get('PATH', os.defpath)
        return env


def load_compiler(root, key):
    require(valid_key(key), 'compiler key must contain 64 lowercase hexadecimal characters')
    directory = root / '.work/compilers' / key
    try:
        ready = read_json(directory / 'ready.json')
        identity = ready['identity']
        require(ready['owner'] == str(root) and ready['key'] == key and digest(identity) == key,
                'custom compiler ownership or identity mismatch')
        require(identity['policy'] == POLICY and identity['provenance']['stage'] == 2,
                'custom compiler must be a complete stage2 installation')
        require(all(valid_key(value) for value in identity['files'].values()),
                'invalid compiler file digest')
        require_complete(identity['files'], identity['host'])
        sysroot = directory / 'sysroot'
        current = tree_stamps(sysroot)
        require(current == ready['stamps'], 'custom compiler installation changed')
        require(set(identity['files']) == {p for p, s in current.items() if stat.S_ISREG(s[2])},
                'custom compiler file inventory differs')
        require(all(not (entry[2] & 0o222) for entry in current.values()),
                'custom compiler installation is writable')
        require_executable_programs(sysroot, identity['host'])
        return Compiler(key, sysroot, identity)
    except (OSError, KeyError, TypeError, ValueError, AttributeError) as error:
        raise RuntimeError('invalid custom compiler installation: ' + str(error)) from error


def validate_tool_compiler(directory, key, compiler):
    path = directory / 'compiler.json'
    if compiler is None:
        require(not path.exists() and not path.is_symlink(),
                'custom compiler tools require --compiler-key')
        return
    try:
        composition = read_json(path)
        require(digest(composition) == key and composition['kind'] == TOOL_POLICY,
                'custom tool composition identity mismatch')
        require(composition['compiler_key'] == compiler.key
                and composition['compiler_sysroot'] == str(compiler.sysroot),
                'tool was built with a different compiler')
        require(composition['binaries'] == read_json(directory / 'ready.json'),
                'custom tool composition binary mismatch')
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError('invalid custom tool compiler association: ' + str(error)) from error


def audit_macos_libraries(sysroot):
    if sys.platform != 'darwin':
        return
    executables = [sysroot / 'bin/rustc', *sorted(sysroot.glob('lib/rustlib/*/bin/rust-objcopy'))]
    files = [*executables, *sorted(p for p in (sysroot / 'lib').rglob('*')
             if p.is_file() and p.suffix in ['.dylib', '.so'])]
    def system(path):
        return path.startswith(('/usr/lib/', '/System/Library/'))
    def local(path, binary, executable):
        if path.startswith('@loader_path/'):
            return binary.parent / path.removeprefix('@loader_path/')
        if path.startswith('@executable_path/'):
            return executable.parent / path.removeprefix('@executable_path/')
        return None
    load_commands = {'LC_LOAD_DYLIB', 'LC_LOAD_WEAK_DYLIB', 'LC_REEXPORT_DYLIB',
                     'LC_LOAD_UPWARD_DYLIB', 'LC_LAZY_LOAD_DYLIB'}
    for binary in files:
        executable = binary if binary in executables else sysroot / 'bin/rustc'
        commands = subprocess.check_output(['/usr/bin/otool', '-l', str(binary)], text=True)
        blocks = re.split(r'(?m)^Load command \d+\s*$', commands)[1:]
        require(blocks, 'compiler binary has no readable Mach-O load commands: ' + str(binary))
        for block in blocks:
            match = re.search(r'(?m)^\s*cmd (LC_\w+)\s*$', block)
            require(match is not None, 'malformed compiler Mach-O load command')
            kind = match[1]
            # `otool -L` includes LC_ID_DYLIB, which names this library rather
            # than loading anything. Only actual load edges affect closure.
            if kind == 'LC_ID_DYLIB':
                continue
            require(not kind.endswith('_DYLIB') or kind in load_commands,
                    'unrecognized compiler library load command: ' + kind)
            if kind == 'LC_RPATH':
                match = re.search(r'(?m)^\s*path (.+) \(offset \d+\)\s*$', block)
                require(match is not None, 'malformed compiler loader search path')
                path = match[1]
                resolved = local(path, binary, executable)
                require(system(path) or (resolved is not None
                        and resolved.resolve(strict=True).is_relative_to(sysroot)),
                        'compiler loader search path escapes installation: ' + path)
                continue
            if kind not in load_commands:
                continue
            match = re.search(r'(?m)^\s*name (.+) \(offset \d+\)\s*$', block)
            require(match is not None, 'malformed compiler library dependency')
            path = match[1]
            if system(path):
                continue
            if path.startswith('@rpath/'):
                suffix = path.removeprefix('@rpath/')
                require(any(str(p.relative_to(sysroot)).endswith('/' + suffix) for p in files),
                        'compiler library is absent from installation: ' + path)
                continue
            resolved = local(path, binary, executable)
            require(resolved is not None and resolved.resolve(strict=True).is_relative_to(sysroot),
                    'compiler library refers outside its installation: ' + path)


def install_compiler(root, source, provenance):
    """Copy packaged stage2 components, probe them, then freeze their identity."""
    require(provenance.get('stage') == 2, 'only complete stage2 installations are supported')
    require(re.fullmatch(r'[0-9a-f]{40}', provenance.get('source_commit', '')) is not None,
            'missing compiler source commit')
    for name in ['patch_sha256', 'bootstrap_sha256', 'build_receipt_sha256']:
        require(valid_key(provenance.get(name)), 'missing compiler provenance: ' + name)
    require(source.resolve(strict=True) == source and source.is_dir(), 'invalid compiler package prefix')
    require(not any(p.is_symlink() and p.is_dir() for p in source.rglob('*')),
            'install packaged rust-src; live source-directory symlinks are unsupported')
    parent = root / '.work/compilers'
    parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.install-', dir=parent))
    sysroot = temporary / 'sysroot'
    shutil.copytree(source, sysroot, symlinks=False)
    audit_macos_libraries(sysroot)
    env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'LD_', 'DYLD_'))
           and k not in ['RUST_SYSROOT', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER']}
    compiler = subprocess.check_output([str(sysroot / 'bin/rustc'), '-vV'], env=env, text=True)
    reported = subprocess.check_output([str(sysroot / 'bin/rustc'), '--print', 'sysroot'], env=env, text=True).strip()
    require(Path(reported).resolve() == sysroot, 'installed compiler reports another sysroot')
    hosts = [line[6:] for line in compiler.splitlines() if line.startswith('host: ')]
    require(len(hosts) == 1, 'installed compiler has no unique host')
    commits = [line.removeprefix('commit-hash: ') for line in compiler.splitlines()
               if line.startswith('commit-hash: ')]
    require(commits == [provenance['source_commit']], 'compiler version does not match its source commit')
    help_text = subprocess.check_output([str(sysroot / 'bin/rustc'), '-Zhelp'], env=env, text=True)
    require(re.search(r'\bstable-cgu-partitioning\b', help_text) is not None,
            'custom compiler lacks stable-CGU support')
    files = {str(p.relative_to(sysroot)): file_digest(p) for p in sorted(sysroot.rglob('*')) if p.is_file()}
    require_complete(files, hosts[0])
    require_executable_programs(sysroot, hosts[0])
    identity = dict(policy=POLICY, provenance=provenance, compiler=compiler, host=hosts[0], files=files,
                    source_sha256=digest({p: h for p, h in files.items()
                        if p.startswith('lib/rustlib/src/rust/library/')}))
    key = digest(identity)
    directory = parent / key
    require(not directory.exists(), 'compiler identity is already installed')
    temporary.rename(directory)
    sysroot = directory / 'sysroot'
    for path in [*sysroot.rglob('*'), sysroot]:
        path.chmod(0o555 if path.is_dir() or os.access(path, os.X_OK) else 0o444)
    ready = dict(owner=str(root), key=key, identity=identity, stamps=tree_stamps(sysroot))
    (directory / 'ready.json').write_text(json.dumps(ready, sort_keys=True) + '\n')
    (directory / 'ready.json').chmod(0o444)
    return load_compiler(root, key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-from', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    args = parser.parse_args()
    from compare_saved_runtime import acquire_lock
    from workflow_io import require_space
    (ROOT / '.work').mkdir(exist_ok=True)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        installed = install_compiler(ROOT, args.install_from.absolute(), read_json(args.provenance))
    print(json.dumps(dict(compiler_key=installed.key, sysroot=str(installed.sysroot))))


if __name__ == '__main__':
    main()
