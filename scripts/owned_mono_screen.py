"""Pure saved-byte checks for the per-MonoItem screen and std source policy.

These checks authenticate retained evidence; they do not replace live installation
guards or prepare/load a compiler, Cargo, metadata, or source tree.
"""
import json
from pathlib import Path, PurePosixPath
import stat

from custom_compiler import digest, require, valid_key
from std_mir_source_paths import (FLAGS, POLICY, SOURCE, command_for, compiler_sources,
                                  expected_sysroot_files, make_identity, selection_for_identity, namespace_for)
from verified_std_diagnostics import source_span_text


def relative_name(name):
    path = PurePosixPath(name)
    require(isinstance(name, str) and name == str(path) and not path.is_absolute()
            and name != '.' and '..' not in path.parts, 'noncanonical saved evidence path')
    return name


def inventory(files, stamps):
    require(files and isinstance(stamps, dict) and '.' in stamps, 'empty saved std tree inventory')
    for name, value in files.items():
        relative_name(name)
        require(valid_key(value), 'invalid saved std file digest')
    regular = set()
    for name, value in stamps.items():
        if name != '.':
            relative_name(name)
        require(isinstance(value, list) and len(value) == 6
                and all(type(v) is int and v >= 0 for v in value), 'invalid saved std tree stamp')
        require((stat.S_ISREG(value[2]) or stat.S_ISDIR(value[2])) and not value[2] & 0o222,
                'saved std tree is writable, linked or unsupported')
        if stat.S_ISREG(value[2]):
            regular.add(name)
        parent = str(PurePosixPath(name).parent)
        require(name == '.' or parent in stamps and stat.S_ISDIR(stamps[parent][2]),
                'saved std tree parent is missing')
    require(stat.S_ISDIR(stamps['.'][2]) and regular == set(files), 'saved std tree file set differs')


def validate_probe(row, source, sources, read_bytes):
    records = [json.loads(line) for line in row['stderr'].splitlines() if line.strip()]
    require(any(d.get('level') == 'error' and (d.get('code') or {}).get('code') == 'E0080'
                for d in records), 'saved std probe lacks E0080')
    seen = set()
    def visit(value):
        if isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, dict):
            if 'file_name' in value:
                name = value['file_name']
                require(isinstance(name, str), 'invalid saved std probe filename')
                path = Path(name)
                if path.is_absolute() and path.is_relative_to(source):
                    relative = relative_name(str(path.relative_to(source)))
                    require(relative in sources, 'unknown saved std probe source')
                    payload = read_bytes(path)
                    from hashlib import sha256
                    require(sha256(payload).hexdigest() == sources[relative], 'saved std probe source changed')
                    require(value.get('text') and value['text'] == source_span_text(value, payload),
                            'saved std probe snippet is missing or differs')
                    seen.add(relative)
                else:
                    require(not name.startswith(('/rustc/', 'library/', 'core/', 'std/')),
                            'saved std probe retains an unresolved source alias')
            for child in value.values():
                visit(child)
    visit(records)
    require({'core/src/panic.rs', 'std/src/macros.rs'} <= seen, 'saved std probe lacks core/std source spans')
    return sorted(seen)


def validate_std(std, owner, compiler, mode, read_bytes):
    """Reconcile a v2 screen row with its immutable identity and saved setup."""
    from hashlib import sha256
    key = std['key']
    require(valid_key(key), 'invalid saved std key')
    work = Path(owner) / '.work/std-mir' / key
    path = work / 'ready.json'
    payload = read_bytes(path)
    ready = json.loads(payload)
    identity = ready['identity']
    selection = selection_for_identity(identity)
    require(std['path'] == str(path) and std['sha256'] == sha256(payload).hexdigest()
            and std['sysroot'] == str(work / 'sysroot') and ready['owner'] == str(owner)
            and ready['key'] == key == digest(identity) and std['policy'] == identity['policy']
            and std['identity'] == identity and std['readiness'] == ready,
            'saved v2 std manifest or physical identity differs')
    compiler_sources(compiler)
    require(identity == make_identity(compiler, identity['cargo'], namespace_for(selection, 'stable-mono-cgu:' + mode),
                identity['configuration'], identity['build_environment_sha256'])
            and valid_key(identity['build_environment_sha256'])
            and std['compiler'] == compiler.identity['compiler'] and std['target'] == compiler.host
            and std['rustc'] == str(compiler.rustc)
            and std['rustc_sha256'] == compiler.identity['files']['bin/rustc'],
            'saved v2 compiler, source, namespace or recipe differs')
    require(json.loads(read_bytes(work / 'owner.json')) == dict(owner=str(owner), identity=identity,
                run_id=ready['run_id']), 'saved v2 owner marker differs')
    require(ready['command'] == command_for(identity, work)
            and ready['environment'] == dict(RUSTC=str(compiler.rustc), RUSTFLAGS=FLAGS,
                RUSTC_WRAPPER='', RUSTC_WORKSPACE_WRAPPER='', CARGO_TERM_COLOR='never',
                __CARGO_RUSTC_BOOTSTRAP_WS_REMAP=identity['virtual_prefix']),
            'saved v2 actual setup command/environment differs')
    cargo = identity['cargo']
    require(Path(cargo['executable']).is_absolute()
            and [line[6:] for line in cargo['version'].splitlines() if line.startswith('host: ')] == [compiler.host]
            and ready['cargo_state']['route'] == cargo['route'], 'saved v2 Cargo identity/route differs')
    require(ready['sysroot_files'] == expected_sysroot_files(identity, ready['metadata'])
            and ready['source_sha256'] == compiler.identity['source_sha256'],
            'saved v2 source/metadata publication differs')
    inventory(ready['sysroot_files'], ready['sysroot_stamps'])
    inventory(identity['source_files'], ready['snapshot_stamps'])
    inventory(ready['evidence_files'], ready['evidence_stamps'])
    artifacts = {str(work / 'sysroot' / p): dict(sha256=h,
        stamp=[s[0], s[1], s[3], s[4]]) for p, h in ready['metadata'].items()
        for s in [ready['sysroot_stamps'][p]]}
    require(artifacts == std['artifacts'] and all(p['stamp'][2] > 0 for p in artifacts.values()),
            'saved v2 metadata artifact proof differs')
    require(ready['probes'] == ['native', 'prepared'] and ready['full_presentation_qualified'] is False,
            'saved v2 setup must not claim full diagnostic qualification')
    evidence = {}
    for name, expected in ready['evidence_files'].items():
        payload = read_bytes(work / 'evidence' / relative_name(name))
        require(sha256(payload).hexdigest() == expected, 'saved v2 setup evidence hash differs: ' + name)
        evidence[name] = payload
    required = {'plan.json', 'commands.json', 'metadata.json', 'metadata-process.json',
        'probe-native.json', 'probe-native-process.json', 'probe-native/source.rs',
        'probe-prepared.json', 'probe-prepared-process.json', 'probe-prepared/source.rs', 'probe-summary.json'}
    require(required <= evidence.keys(), 'saved v2 setup evidence is incomplete')
    plan = json.loads(evidence['plan.json'])
    require(plan['identity'] == identity and plan['command'] == ready['command']
            and plan['environment'] == ready['environment']
            and plan['environment_sha256'] == identity['build_environment_sha256'],
            'saved v2 setup plan differs')
    commands = json.loads(evidence['commands.json'])
    require(isinstance(commands, list), 'invalid saved v2 command history')
    labels = [row.get('label') for row in commands]
    require(all(labels.count(label) == 1 for label in ['probe-native', 'metadata', 'probe-prepared'])
            and labels.index('probe-native') < labels.index('metadata') < labels.index('probe-prepared'),
            'saved v2 native preflight/build/prepared probe order differs')
    seen = {}
    for label, code in [('metadata', 0), ('probe-native', 1), ('probe-prepared', 1)]:
        row, process = [json.loads(evidence[label + suffix]) for suffix in ['.json', '-process.json']]
        require(row in commands and sum(r.get('label') == label for r in commands) == 1
                and row['returncode'] == process['returncode'] == code
                and process['status'] == 'finished' and process['command'] == row['command']
                and process['finished_at'] >= process['started_at'], 'saved v2 child completion differs')
        if label == 'metadata':
            require(row['command'] == ready['command'] and process['cwd'] == str(work),
                    'saved v2 metadata command differs')
        else:
            route = 'native' if label == 'probe-native' else 'prepared'
            sysroot = compiler.sysroot if route == 'native' else work / 'sysroot'
            directory = Path(owner) / '.work' / ready['run_id'] / label
            require(row['command'] == [str(compiler.rustc), str(directory / 'source.rs'),
                    '--crate-type=lib', '--edition=2024', '--emit=metadata', '--error-format=json',
                    '--sysroot', str(sysroot), '-o', str(directory / 'probe.rmeta')]
                    and process['cwd'] == str(directory), 'saved v2 probe command is mapped or uses another compiler')
            seen[route] = validate_probe(row, sysroot / SOURCE, identity['source_files'], read_bytes)
    require(json.loads(evidence['probe-summary.json']) == dict(**seen,
                full_presentation_qualified=False, strict_integration_required=True),
            'saved v2 probe summary differs')
    return ready


def qualification(plan, custom, read_bytes, *, source_observables_validator=None):
    from stable_mono_qualification import validate_qualification
    require(plan['candidate_policy'] == 'stable-mono-cgu', 'not a MonoItem screen')
    stds = dict(off=plan['std_mir_by_mode']['baseline'], on=plan['std_mir_by_mode']['candidate'])
    expected = plan.get('compiler_qualification')
    require(isinstance(expected, dict) and 'path' in expected, 'missing strict MonoItem qualification')
    checked = validate_qualification(expected['path'], plan['owner'], custom.key,
        plan['tools']['baseline'], stds, compiler_sysroot=custom.sysroot, read_bytes=read_bytes)
    require(checked == expected, 'saved MonoItem qualification differs from admission')
    # The 36-command integration does not establish the independent source/file
    # observable controls. Until its typed validator exists, assessment fails.
    require(source_observables_validator is not None and isinstance(plan.get('source_observables'), dict),
            'MonoItem source-observable prerequisite and typed validator are required')
    observable = plan['source_observables']
    checked_observable = source_observables_validator(observable['path'], plan['owner'], custom.key,
        plan['tools']['baseline'], stds, compiler_sysroot=custom.sysroot, read_bytes=read_bytes)
    require(checked_observable == observable and checked_observable.get('evidence_files'),
            'saved source-observable qualification differs from admission')
    return dict(integration=checked, source_observables=checked_observable)
