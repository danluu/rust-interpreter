"""Explicit native controls and exporter timing fields for edit benchmarks."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import tomllib


def native_toolchain(value):
    """Accept a single rustup toolchain name, never a path or extra argument."""
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', value):
        raise ValueError('native toolchain must be a rustup toolchain name')
    return value


ROUTE_ENVIRONMENT = ('RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                     'CARGO_BUILD_RUSTC', 'CARGO_BUILD_RUSTC_WRAPPER', 'CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER')


def native_identity_environment(base):
    names = {'HOME', 'PATH', 'CARGO_HOME', 'RUSTUP_HOME', 'RUSTUP_TOOLCHAIN',
        'TMPDIR', 'LANG', 'LC_ALL', 'TZ', 'SYSTEMROOT', 'RUSTC_BOOTSTRAP',
        '__CARGO_TEST_CHANNEL_OVERRIDE_DO_NOT_USE_THIS'}
    return {name: value for name, value in base.items() if name in names or
            name.startswith(('LD_', 'DYLD_', 'RUSTC_OVERRIDE_'))}


def file_identity(path):
    path = Path(path)
    resolved = path.resolve(strict=True)
    def stamp(p):
        s = p.lstat()
        return [s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns]
    before, target = stamp(path), stamp(resolved)
    if not path.is_absolute() or not resolved.is_file() or resolved.stat().st_size > 512 * 1024**2:
        raise RuntimeError('invalid native tool identity path')
    digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    if before != stamp(path) or target != stamp(resolved) or path.resolve(strict=True) != resolved:
        raise RuntimeError('native tool changed while reading identity')
    return dict(path=str(path), resolved=str(resolved), stamp=before, target_stamp=target, sha256=digest)


def native_route_configuration(source, environment):
    """Reject routing policy that explicit compiler binding would override."""
    for name in ROUTE_ENVIRONMENT:
        if environment.get(name):
            raise RuntimeError('explicit native toolchain conflicts with inherited ' + name)
    source = Path(source).resolve(strict=True)
    cargo_home = Path(environment.get('CARGO_HOME', str(Path(environment['HOME']) / '.cargo')))
    if not cargo_home.is_absolute():
        raise RuntimeError('explicit native toolchain requires an absolute Cargo home')
    directories = [p / '.cargo' for p in [source, *source.parents]] + [cargo_home]
    result = {}
    for directory in directories:
        for name in ['config', 'config.toml']:
            path = directory / name
            if str(path) in result:
                continue
            if path.is_symlink():
                raise RuntimeError('native route configuration follows a symlink: ' + str(path))
            if not path.exists():
                result[str(path)] = None
                continue
            if not path.is_file() or path.stat().st_size > 1024**2:
                raise RuntimeError('invalid native route configuration: ' + str(path))
            payload = path.read_bytes()
            config = tomllib.loads(payload.decode())
            build, exports = config.get('build', {}), config.get('env', {})
            if ('include' in config or any(build.get(key) for key in
                    ['rustc', 'rustc-wrapper', 'rustc-workspace-wrapper']) or
                    any(key in exports for key in ROUTE_ENVIRONMENT)):
                raise RuntimeError('explicit native toolchain conflicts with Cargo configuration: ' + str(path))
            result[str(path)] = hashlib.sha256(payload).hexdigest()
    return result


def inspect_native_toolchain(toolchain, run, *, environment=None, source=None):
    """Resolve installed tools without rustup's implicit-install Cargo proxy.

    The caller retains each command, output and process receipt as setup. This
    identifies the native control separately from the custom engine's compiler.
    """
    environment = os.environ if environment is None else environment
    configurations = native_route_configuration(Path.cwd() if source is None else source, environment)
    rustup = shutil.which('rustup', path=environment.get('PATH'))
    if rustup is None:
        raise RuntimeError('rustup is not installed')
    result = dict(toolchain=native_toolchain(toolchain), tools={}, rustup=file_identity(rustup),
                  configuration=configurations, identity_environment=native_identity_environment(environment))
    for name in ['rustc', 'cargo']:
        lookup = run([rustup, 'which', '--toolchain', toolchain, name])
        if lookup['returncode'] != 0:
            raise RuntimeError('native toolchain is not installed: ' + toolchain)
        reported = lookup['stdout'].strip()
        identity = file_identity(reported)
        path = Path(identity['resolved'])
        version = run([str(path), '-vV'])
        if version['returncode'] != 0 or not version['stdout'].startswith(name + ' '):
            raise RuntimeError('native tool identity probe failed: ' + name)
        if file_identity(reported) != identity:
            raise RuntimeError('native tool changed during identity probe: ' + name)
        result['tools'][name] = dict(identity, rustup_path=reported,
            version_stdout=version['stdout'], version_stderr=version['stderr'])
    if file_identity(rustup) != result['rustup']:
        raise RuntimeError('rustup changed during native identity probes')
    return result


def revalidate_native_toolchain(identity, run, *, environment=None, source=None):
    current = inspect_native_toolchain(identity['toolchain'], run, environment=environment, source=source)
    if current != identity:
        raise RuntimeError('native compiler or route changed during workflow')
    return current


def native_environment(base, profile, rustflags, *, compiler=None):
    env = base.copy()
    if compiler is not None:
        for name in ROUTE_ENVIRONMENT:
            if env.get(name):
                raise RuntimeError('explicit native toolchain conflicts with inherited ' + name)
        env.update(RUSTC=compiler['tools']['rustc']['resolved'], RUSTC_WRAPPER='', RUSTC_WORKSPACE_WRAPPER='')
    if profile == 'o0-incremental':
        for name in ['DEV', 'TEST']:
            env[f'CARGO_PROFILE_{name}_OPT_LEVEL'] = '0'
            env[f'CARGO_PROFILE_{name}_INCREMENTAL'] = 'true'
    elif profile != 'repository':
        raise ValueError('unknown native profile')
    if rustflags:
        # Preserve each Rust argument exactly, including paths containing spaces.
        env.pop('RUSTFLAGS', None)
        env['CARGO_ENCODED_RUSTFLAGS'] = '\x1f'.join(rustflags)
    return env


def native_command(toolchain, manifest, package, target, jobs, test_threads,
                   selected, *, check=False, timings=False, cargo=None):
    native_toolchain(toolchain)
    command = (['cargo', '+' + toolchain] if cargo is None else [str(cargo)]) + ['check' if check else 'test',
               '--manifest-path', str(manifest), '--package', package, '--lib',
               '--locked', '--offline', '--jobs', str(jobs), '--target-dir', str(target)]
    if check:
        # Match the launcher's library-test target selection on the pinned Cargo.
        command += ['--profile', 'test']
    if timings:
        command += ['--timings']
    if not check:
        command += ['--', '--exact']
        if test_threads != 'default':
            command += ['--test-threads=' + test_threads]
        command += selected
    return command


def exporter_seconds(stderr):
    """Record nested stage scopes separately; never sum them into a total."""
    result = {}
    for phase in ['scalar-frames', 'scalar-promotion', 'inline', 'cfg']:
        values = re.findall(r'^rust-interp-' + phase + r': .*?\bseconds=([0-9.]+)\b', stderr, re.M)
        if values:
            result[phase] = sum(map(float, values))
    for field in ['frontend_ms', 'lowering_ms']:
        values = re.findall(r'^rust-interp-export: .*?\b' + field + r'=([0-9.]+)\b', stderr, re.M)
        if values:
            result[field.removesuffix('_ms')] = sum(map(float, values)) / 1000
    return result
