"""Freeze a proved macOS Cargo dynamic-library closure without copying libraries."""
import os
from pathlib import Path
import re
import subprocess
import sys

from custom_compiler import file_digest, require
from toolchain_lookup import _stamp


def platform_identity():
    value = os.uname()
    return dict(system=value.sysname, release=value.release, version=value.version, machine=value.machine)


def system_path(path):
    return path.startswith(('/usr/lib/', '/System/Library/'))


def library_state(identity):
    """No subprocesses or content reads on warm validation."""
    require(platform_identity() == identity['platform'], 'Cargo system platform changed')
    libraries = {}
    for item in identity['libraries']:
        path = Path(item['logical'])
        require(str(path.resolve(strict=True)) == item['resolved'], 'Cargo dynamic library link target changed')
        libraries[item['logical']] = _stamp(path)
    searches = {name: Path(name).exists() or Path(name).is_symlink() for name in identity['searches']}
    require(searches == identity['searches'], 'Cargo dynamic library search results changed')
    return dict(libraries=libraries, searches=searches)


def library_closure(executable, host):
    """Resolve all non-system dependencies, failing on ambiguous/unproved paths.

    System dyld-cache libraries are bound to uname's kernel/platform build
    identity. This is an explicit platform assumption, not a hash of the cache.
    Absolute, loader-relative and executable-relative paths are supported.
    Runpath lookup must resolve to exactly one library; all candidate existence
    results are retained so a later library cannot silently shadow that choice.
    """
    require(sys.platform == 'darwin', 'Cargo library import currently requires macOS closure validation')
    arch = {'aarch64': 'arm64', 'x86_64': 'x86_64'}.get(host.split('-')[0])
    require(arch is not None, 'unsupported Cargo Mach-O architecture')
    executable = executable.resolve(strict=True)
    nodes, libraries, searches, systems = {}, {}, {}, set()
    contexts = set()

    def relative(token, loader):
        if token.startswith('@loader_path/'):
            return loader.parent / token.removeprefix('@loader_path/')
        if token.startswith('@executable_path/'):
            return executable.parent / token.removeprefix('@executable_path/')
        if token.startswith('/'):
            return Path(token)
        raise RuntimeError('unproved Cargo dynamic-library path: ' + token)

    def visit(logical, inherited=(), ancestors=()):
        resolved = logical.resolve(strict=True)
        context = (str(logical), inherited)
        if context in contexts or str(resolved) in ancestors:
            return
        contexts.add(context)
        require(len(contexts) <= 256, 'Cargo library closure is unexpectedly large')
        name = '$CARGO' if resolved == executable else str(logical)
        if name not in nodes:
            links = subprocess.check_output(['/usr/bin/otool', '-arch', arch, '-L', str(logical)], text=True)
            tokens = [line.strip().split(' (compatibility version ', 1)[0]
                      for line in links.splitlines() if line.startswith('\t')]
            commands = subprocess.check_output(['/usr/bin/otool', '-arch', arch, '-l', str(logical)], text=True)
            rpaths, active = [], False
            for line in commands.splitlines():
                if line.strip().startswith('cmd '):
                    active = line.strip() == 'cmd LC_RPATH'
                elif active and (match := re.match(r'\s*path (.+) \(offset \d+\)', line)):
                    rpaths.append(match[1])
            require(tokens, 'Cargo Mach-O dependency list is empty: ' + str(logical))
            nodes[name] = dict(dependencies=tokens, rpaths=rpaths)
        node = nodes[name]
        # Canonical loader paths avoid ambiguity when Homebrew aliases point at
        # a cellar directory; dyld resolves @loader_path from the loaded image.
        rpaths = tuple(str(relative(token, resolved)) for token in node['rpaths']) + inherited
        for token in node['dependencies']:
            if system_path(token):
                systems.add(token)
                continue
            if token.startswith('@rpath/'):
                candidates = [Path(base) / token.removeprefix('@rpath/') for base in rpaths]
                require(candidates and not any(system_path(str(p)) for p in candidates),
                        'unproved system or empty Cargo runpath: ' + token)
                available = []
                for path in candidates:
                    exists = path.exists() or path.is_symlink()
                    searches[str(path)] = exists
                    if exists:
                        require(path.is_file(), 'Cargo runpath candidate is not a file')
                        available.append(path)
                require(len({str(p.resolve(strict=True)) for p in available}) == 1,
                        'unresolved or ambiguous Cargo runpath: ' + token)
                path = available[0]
            else:
                path = relative(token, resolved)
                if system_path(str(path)):
                    systems.add(str(path))
                    continue
            require(path.is_file(), 'Cargo dynamic library is missing: ' + str(path))
            target = path.resolve(strict=True)
            if target == executable or target == resolved:
                continue  # LC_ID_DYLIB may repeat the current image itself.
            if str(path) not in libraries:
                before = _stamp(path)
                libraries[str(path)] = dict(logical=str(path), resolved=str(target),
                                            bytes=path.stat().st_size, sha256=file_digest(path))
                require(_stamp(path) == before, 'Cargo dynamic library changed while hashing')
            visit(path, rpaths, (*ancestors, str(resolved)))

    visit(executable)
    identity = dict(policy='macos-dyld-closure-v1', platform=platform_identity(),
                    system_libraries=sorted(systems),
                    system_assumption='system dyld cache bound to uname platform/kernel build',
                    libraries=[libraries[k] for k in sorted(libraries)],
                    nodes=nodes, searches=searches)
    return identity, library_state(identity)
