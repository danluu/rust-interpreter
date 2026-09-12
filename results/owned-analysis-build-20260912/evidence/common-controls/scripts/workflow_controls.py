"""Explicit native controls and exporter timing fields for edit benchmarks."""
import re


def native_environment(base, profile, rustflags):
    env = base.copy()
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
                   selected, *, check=False, timings=False):
    command = ['cargo', '+' + toolchain, 'check' if check else 'test',
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
