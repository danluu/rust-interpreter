"""Actual compiler-call evidence for the explicit per-item integration policy."""
import json
from pathlib import Path

from custom_compiler import file_digest, require
from workflow_io import write_json

POLICY = 'stable-mono-cgu-integration-v1'


def mode_arguments(mono, mode):
    return (['--stable-cgu-partitioning', 'off', '--stable-mono-cgu-partitioning', mode]
            if mono else ['--stable-cgu-partitioning', mode])


def namespace(mono, mode):
    return ('stable-mono-cgu:' if mono else 'stable-cgu:') + mode


def option(args, name):
    values = []
    for i, arg in enumerate(args):
        if arg == name:
            require(i + 1 < len(args), 'missing compiler option value')
            values.append(args[i + 1])
        elif arg.startswith(name + '='):
            values.append(arg[len(name) + 1:])
    require(len(values) <= 1, 'duplicate compiler option: ' + name)
    return values[0] if values else None


def validate_flags(args, mode):
    unstable = []
    for i, arg in enumerate(args):
        require(not arg.startswith('@'), 'response file in actual compiler argv')
        if arg == '-Z':
            require(i + 1 < len(args), 'missing unstable compiler option')
            unstable.append(args[i + 1].replace('_', '-'))
        elif arg.startswith('-Z'):
            unstable.append(arg[2:].replace('_', '-'))
        require(not (arg.startswith('-j') or arg == '--jobs' or arg.startswith('--jobs=')
                     or arg.startswith('--jobs-frontend')), 'mixed frontend worker policy')
    for name, expected in [('stable-cgu-partitioning', 'no'),
                           ('stable-mono-cgu-partitioning', 'yes' if mode == 'on' else 'no')]:
        require([v for v in unstable if v.split('=', 1)[0] == name] == [name + '=' + expected],
                'actual compiler partitioning flags differ')
    require(not any(v.split('=', 1)[0] in ['threads', 'proc-macro-execution-strategy',
                    'cache-proc-macros'] for v in unstable), 'mixed compiler experiment')


def decode_record(path):
    payload = path.read_bytes()
    require(payload.endswith(b'\0'), 'incomplete compiler argv record')
    fields = [p.decode('utf-8') for p in payload[:-1].split(b'\0')]
    require(len(fields) >= 5 and fields[0] == 'rust-interp-compiler-argv-v1'
            and fields[1] in ['native', 'native-driver', 'exported'], 'invalid compiler argv envelope')
    return dict(schema_version=1, role=fields[1], compiler_sysroot=fields[2], cwd=fields[3], argv=fields[4:])


def retain_records(work, directory, mode, compiler):
    require(directory.resolve(strict=True) == directory, 'indirect compiler argv directory')
    result = []
    for path in sorted(directory.iterdir()):
        require(path.is_file() and not path.is_symlink() and path.suffix == '.argv',
                'unexpected compiler argv record')
        record = decode_record(path)
        require(record['compiler_sysroot'] == str(compiler.sysroot)
                and record['argv'][0] == str(compiler.rustc), 'actual compiler identity differs')
        validate_flags(record['argv'], mode)
        record['raw'] = dict(path=str(path.relative_to(work)), sha256=file_digest(path))
        destination = path.with_suffix('.json')
        write_json(destination, record)
        target, crate = option(record['argv'], '--target'), option(record['argv'], '--crate-name')
        role = ('native-host' if record['role'] in ['native', 'native-driver'] and crate and target is None
                else 'selected-guest' if record['role'] == 'exported' and crate == 'custom_compiler_fixture'
                and target == compiler.host else None)
        if role:
            result.append(dict(mode=mode, role=role, path=str(destination.relative_to(work)),
                               sha256=file_digest(destination)))
    return result


def publish_proof(work, records):
    require({(r['mode'], r['role']) for r in records} == {
        (m, r) for m in ['off', 'on'] for r in ['native-host', 'selected-guest']},
        'missing actual host or selected guest compiler calls')
    path = work / 'compiler-flag-proof.json'
    write_json(path, dict(schema_version=1, policy=POLICY, records=records))
    return dict(path=path.name, sha256=file_digest(path))


def evidence_files(work):
    # Only qualification evidence, never its generated caches or live std/tool
    # installations. Capture exact producer sources for later archived review.
    paths = list(work.glob('*.json')) + list(work.glob('*.rbc'))
    for name in ['compiler-argv', 'source-snapshots', 'fixture']:
        root = work / name
        if root.exists():
            paths.extend(p for p in root.rglob('*') if p.is_file())
    return {str(p.relative_to(work)): file_digest(p) for p in sorted(set(paths))
            if p.name != 'result.json'}
