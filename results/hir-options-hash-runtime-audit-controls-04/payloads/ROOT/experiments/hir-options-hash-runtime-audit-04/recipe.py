"""Independent pure reconstruction of the exact admitted runtime recipes.

This module does not construct a compiler, resolve a path, inspect a provider,
or execute a command. The enclosing reader authenticates runtime/q definitions,
the full source and executable routes, and the original inherited environment.
The absence of compiler overrides is checked on every reconstruction, including
final installation. It is a restriction on this exact task's recorded context.
"""
import os
from pathlib import Path

POLICY = 'saved-runtime-recipe-v1'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def canonical_root(value):
    require(type(value) is str and value and '\\' not in value and '\x00' not in value,
            'exact canonical runtime root required')
    path = Path(value)
    require(path.is_absolute() and str(path) == value and '..' not in path.parts,
            'runtime root spelling differs')
    return path


def environment(runtime, identity, sysroot, original):
    require(type(original) is dict and all(type(k) is str and type(v) is str
            and k and '\x00' not in k+v for k, v in original.items()),
            'complete string environment required')
    require(not any(k.startswith(('LD_', 'DYLD_')) for k in original),
            'dynamic loader override is outside admitted environment')
    require(not any(k in original for k in (*runtime.OVERRIDES, 'RUSTC', 'RUSTDOC')),
            'actual inherited environment must have no compiler overrides')
    require('PATH' in original, 'exact inherited PATH required')
    result = dict(original)
    result['RUSTC'] = str(sysroot/'bin/rustc')
    result['PATH'] = str(sysroot/'bin') + os.pathsep + original['PATH']
    if 'bin/rustdoc' in identity['files']:
        result['RUSTDOC'] = str(sysroot/'bin/rustdoc')
    return result


def preflight_commands(q, candidate, owner, work, original_environment):
    identity = q.runtime.identity_for(candidate)
    components = [row for row in candidate['components'] if row['role'] == 'runtime']
    require(len(components) == 1, 'one exact admitted runtime component required')
    sysroot = canonical_root(components[0]['root'])
    owner, work = canonical_root(str(owner)), canonical_root(str(work))
    require(work.is_relative_to(owner/'.work') and work != owner/'.work', 'owned preflight work required')
    env = environment(q.runtime, identity, sysroot, original_environment)
    commands = q.probe_commands(sysroot/'bin/rustc', sysroot, work)
    require(type(commands) is list and len(commands) == 2, 'exact local and virtual probe pair required')
    return [dict(argv=argv, cwd=str(work), environment=dict(env), expected=[1],
                 output=str(work/'commands'/str(index))) for index, argv in enumerate(commands)]


def installation_commands(q, spec, owner, work, original_environment):
    runtime = q.runtime
    identity = runtime.identity_for(spec)
    key = runtime.digest(identity)
    require(type(key) is str and len(key) == 64 and all(c in '0123456789abcdef' for c in key),
            'exact content-derived runtime key required')
    owner, work = canonical_root(str(owner)), canonical_root(str(work))
    require(work.is_relative_to(owner/'.work') and work != owner/'.work', 'owned installation work required')
    sysroot = owner/'.work'/runtime.NAMESPACE/key/'sysroot'
    env = environment(runtime, identity, sysroot, original_environment)
    require(type(spec['loader']) is dict, 'complete admitted loader map required')
    names = sorted(spec['loader'])
    require(all(type(name) is str and runtime.relative(name) == name for name in names),
            'exact admitted relative loader paths required')
    commands = [['/usr/bin/otool', '-l', str(sysroot/name)] for name in names]
    commands += [[str(sysroot/'bin/rustc'), '-vV'],
                 [str(sysroot/'bin/rustc'), '--print', 'sysroot'],
                 [str(sysroot/'bin/rustc'), '-Zhelp']]
    rows = [dict(argv=argv, cwd=str(owner), environment=dict(env), expected=[0],
                 output=str(work/'commands'/f'{index:03}')) for index, argv in enumerate(commands)]
    source_work = work/'source-probe'
    probes = q.probe_commands(sysroot/'bin/rustc', sysroot, source_work)
    require(type(probes) is list and len(probes) == 2, 'exact final local and virtual probe pair required')
    rows += [dict(argv=argv, cwd=str(source_work), environment=dict(env), expected=[1],
                  output=str(source_work/'commands'/str(index))) for index, argv in enumerate(probes)]
    require(len(rows) == len(spec['loader'])+5, 'derived complete actual recipe count differs')
    return key, sysroot, rows
