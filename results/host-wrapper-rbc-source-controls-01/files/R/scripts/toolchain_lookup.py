"""Optional, conservatively invalidated identity cache for dated rustup tools.

This caches discovery, never checking or compilation. Unknown installations use
the original two rustc commands. File stamps include ctime as well as mtime;
this is a local installation cache, not authentication of an untrusted compiler.
Callers serialize publication with their standard-library setup lock.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _stamp(path):
    resolved = path.resolve(strict=True)
    s = resolved.stat()
    link = path.lstat()
    return [str(resolved), s.st_dev, s.st_ino, s.st_mode, s.st_size,
            s.st_mtime_ns, s.st_ctime_ns, link.st_ino, link.st_mtime_ns,
            link.st_ctime_ns]


def _optional_stamp(path):
    return _stamp(path) if path.exists() or path.is_symlink() else None


def _context(toolchain):
    if not re.fullmatch(r'nightly-\d{4}-\d{2}-\d{2}', toolchain):
        return None
    if any(name.startswith(('LD_', 'DYLD_')) for name in os.environ):
        return None
    rustc = shutil.which('rustc')
    rustup = shutil.which('rustup')
    if not rustc or not rustup or not os.path.samefile(rustc, rustup):
        return None
    home = Path(os.environ.get('RUSTUP_HOME', str(Path.home()/'.rustup'))).resolve(strict=True)
    # Hash environment values rather than persisting paths/URLs that may carry
    # credentials. Explicit +toolchain takes precedence over directory overrides.
    env = {k: v for k, v in os.environ.items()
           if k.startswith('RUST') or k in ['PATH', 'HOME', 'CARGO_HOME']}
    return dict(schema_version=1, toolchain=toolchain, cwd=str(Path.cwd().resolve()),
                environment_sha256=_digest(env), home=str(home),
                rustc=[str(Path(rustc).absolute()), _stamp(Path(rustc))],
                rustup=[str(Path(rustup).absolute()), _stamp(Path(rustup))],
                settings=_optional_stamp(home/'settings.toml'),
                system_settings=_optional_stamp(Path('/etc/rustup/settings.toml')),
                toolchains=_stamp(home/'toolchains'))


def _installation(context, compiler, original):
    hosts = [line[6:] for line in compiler.splitlines() if line.startswith('host: ')]
    if len(hosts) != 1 or not re.fullmatch(r'[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)+', hosts[0]):
        raise ValueError('unrecognized compiler host')
    expected = Path(context['home'])/'toolchains'/(context['toolchain']+'-'+hosts[0])
    if original != expected or original.is_symlink():
        raise ValueError('not a standard dated rustup installation')
    paths = [original, original/'bin', original/'bin/rustc', original/'lib',
             original/'lib/rustlib', original/'lib/rustlib'/hosts[0],
             original/'lib/rustlib'/hosts[0]/'lib']
    # Include loaded compiler libraries and install manifests, but do not read
    # hundreds of megabytes of compiler/LLVM data just to discover its identity.
    for directory in [original/'lib', original/'lib/rustlib',
                      original/'lib/rustlib'/hosts[0]/'lib']:
        for path in sorted(directory.iterdir()):
            if path.is_file() and (directory.name == 'rustlib' or
                                  directory == original/'lib' or
                                  path.suffix in ['.dylib', '.so', '.dll']):
                paths.append(path)
    return {str(p.relative_to(original)): _stamp(p) for p in paths}


def _discover(toolchain):
    compiler = subprocess.check_output(['rustc', '+'+toolchain, '-vV'], text=True)
    original = Path(subprocess.check_output(
        ['rustc', '+'+toolchain, '--print', 'sysroot'], text=True).strip())
    return compiler, original


def compiler_identity(toolchain, cache_directory=None):
    """Return (verbose version, original sysroot, lookup outcome)."""
    if cache_directory is None:
        return (*_discover(toolchain), 'fresh')
    try:
        context = _context(toolchain)
    except (OSError, ValueError):
        context = None
    if context is None:
        return (*_discover(toolchain), 'unsupported')
    path = cache_directory/(_digest(context)+'.json')
    try:
        if path.is_symlink() or path.stat().st_size > 128*1024:
            raise ValueError('invalid lookup cache file')
        cached = json.loads(path.read_text())
        payload = cached['payload']
        if cached['sha256'] != _digest(payload) or payload['context'] != context:
            raise ValueError('lookup cache context changed')
        compiler, original = payload['compiler'], Path(payload['sysroot'])
        if payload['installation'] != _installation(context, compiler, original):
            raise ValueError('compiler installation changed')
        return compiler, original, 'hit'
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    compiler, original = _discover(toolchain)
    try:
        installation = _installation(context, compiler, original)
        # Establish a stable observation around discovery before publishing a
        # new record. A cache miss pays for verification; edited hits do not.
        if (_discover(toolchain) != (compiler, original) or
                _context(toolchain) != context or
                _installation(context, compiler, original) != installation):
            return compiler, original, 'unstable'
        payload = dict(context=context, compiler=compiler, sysroot=str(original),
                       installation=installation)
        cache_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', dir=cache_directory,
                                         prefix='.lookup-', delete=False) as output:
            temporary = Path(output.name)
            try:
                json.dump(dict(payload=payload, sha256=_digest(payload)), output)
                output.write('\n')
                output.close()
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
    except (OSError, ValueError):
        return compiler, original, 'uncached'
    return compiler, original, 'miss'
