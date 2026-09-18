"""Explicit compiler selections for ordinary edited-build comparisons."""
from custom_compiler import require, valid_key


def arguments(runtime_key, std_key):
    if runtime_key is None:
        require(std_key is None, 'prepared std requires an explicit runtime compiler')
        return []
    require(valid_key(runtime_key), 'invalid workflow runtime compiler key')
    result = ['--runtime-compiler-key', runtime_key]
    if std_key is not None:
        require(valid_key(std_key), 'invalid workflow prepared std key')
        result += ['--std-mir-policy', 'source-paths-v2-shared', '--std-mir-key', std_key]
    return result


def runtime_receipt(compiler):
    return dict(key=compiler.key, policy=compiler.identity['policy'], rustc=str(compiler.rustc),
        rustc_sha256=compiler.identity['files']['bin/rustc'], compiler=compiler.identity['compiler'])


def verify_runtime_call(call, runtime, std):
    """Reject silently selected stock tools or a different prepared sysroot."""
    command, launch = call['command'], call['launch']
    expected = arguments(runtime['key'], None if std is None else std['key'])
    for index in range(0, len(expected), 2):
        flag, value = expected[index:index + 2]
        require(command.count(flag) == 1 and command[command.index(flag) + 1:command.index(flag) + 2] == [value],
                'workflow compiler selection differs from its command')
    require('--compiler-key' not in command, 'workflow selected both compiler policies')
    actual = launch['custom_compiler']
    require(all(actual.get(k) == v for k, v in runtime.items())
            and actual.get('stable_cgu_partitioning') == 'off', 'launched runtime compiler differs')
    if std is not None:
        require(command.count('--std-mir') == 1 and launch['std_mir'] == std,
                'launched prepared standard library differs')
        require(launch['std_mir_policy'] == 'metadata-sysroot-v2-shared-source-paths-release-backtrace',
                'launched standard library policy differs')
    else:
        require('--std-mir' not in command and 'std_mir' not in launch,
                'workflow unexpectedly selected standard MIR')


def rustflags(flags):
    require(isinstance(flags, list) and all(isinstance(flag, str) and flag and
            '\x00' not in flag and '\x1f' not in flag for flag in flags), 'invalid guest rustflag')
    return '\x1f'.join(flags)


def flag_environment(base, flags, encoded=False):
    env = base.copy()
    if encoded:
        env.pop('RUSTFLAGS', None)
        env['CARGO_ENCODED_RUSTFLAGS'] = rustflags(flags)
    elif flags:
        env['RUSTFLAGS'] = ' '.join(flags)
    return env


def verify_flags(call, flags, encoded=False, launcher=False):
    if launcher:
        actual=[arg.removeprefix('--rustflag=') for arg in call['command'] if arg.startswith('--rustflag=')]
        require(actual == flags and '--rustflag' not in call['command']
                and call['launch'].get('application_rustflags', []) == flags
                and call.get('rustflags') is None and call.get('encoded_rustflags') is None,
                'application compiler arguments differ')
    elif encoded:
        require(call.get('rustflags') is None and call.get('encoded_rustflags') == rustflags(flags),
                'encoded guest compiler flags differ')
    else:
        require(call.get('rustflags') == (' '.join(flags) if flags else None)
                and call.get('encoded_rustflags') is None, 'guest compiler flags differ')
