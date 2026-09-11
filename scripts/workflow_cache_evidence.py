"""Derive completed public check/custom Cargo targets from recorded commands.

The shared-entries-v1 namespace formula is deliberately checked against every
recorded executed artifact. This module never builds, executes or removes files.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
from pathlib import Path
import re
import stat

from verify_repeated_workflow import require


def option(command, flag):
    require(command.count(flag) == 1, 'missing or duplicate cache identity option: ' + flag)
    position = command.index(flag) + 1
    require(position < len(command) and not command[position].startswith('--'), 'missing cache identity value')
    return command[position]


def digest(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'invalid recorded digest')
    return value


def canonical(path):
    require(path.is_absolute() and path.resolve() == path, 'noncanonical cache evidence path')
    return path


def derive(root, run_id, report, rows, checks, mode):
    require(mode in ['check', 'baseline', 'candidate'], 'unsupported completed cache mode')
    require(report['project'] in ['pgrust', 'nushell', 'ruff', 'fre'], 'public cache evidence required')
    raw = root / '.work/runs' / run_id
    require(report['raw'] == str(raw.relative_to(root)), 'cache workflow root differs')
    manifest = root / '.work/sources' / report['project'] / 'Cargo.toml'
    require(rows and report['batch'] and 'comparison' in report, 'batched comparison evidence required')
    targets = {'native': raw / 'native', 'check': raw / 'check'}
    identities, snapshots, packages = {}, [], set()
    for row in rows:
        selected = row['mode']
        require(selected in ['native', 'baseline', 'candidate'] and len(row['calls']) == 1,
                'unexpected cache mode or command count')
        call = row['calls'][0]
        command = call['command']
        require(option(command, '--manifest-path') == str(manifest), 'cache source manifest differs')
        packages.add(option(command, '--package'))
        if selected == 'native':
            require(option(command, '--target-dir') == str(targets['native']), 'native cache target differs')
            continue
        require(Path(command[1]) == root / 'scripts/interpreter.py', 'unexpected custom launcher')
        settings = report['tool_builds'][selected]
        key = digest(settings['tool_key'])
        namespace = run_id + ':' + selected
        require(option(command, '--tool-key') == key == row['tool_key'], 'custom cache tool differs')
        require(option(command, '--cache-namespace') == namespace, 'custom cache namespace differs')
        require(command.count('--test-body') == 1, 'custom cache is not a library-test target')
        std = report.get('std_mir')
        require(command.count('--std-mir') == int(bool(std)), 'standard MIR selection differs')
        identity_input = 'shared-entries-v1\0' + str(manifest) + '\0' + option(command, '--package') + '\0True'
        if std:
            identity_input += '\0std-mir:' + digest(std['key'])
        identity_input += '\0' + namespace
        identity = hashlib.sha256(identity_input.encode()).hexdigest()[:24]
        target = root / '.work/interpreter-workspaces' / key / identity / 'target'
        require(selected not in targets or targets[selected] == target, 'custom target changes within workflow')
        targets[selected] = target
        identities[selected] = dict(tool_key=key, namespace=namespace, workspace_identity=identity)
        launch = call['launch']
        lines = [json.loads(line[len('rust-interp-launch: '):]) for line in call['stderr'].splitlines()
                 if line.startswith('rust-interp-launch: ')]
        require(lines == [launch], 'executed cache trace differs from recorded stderr')
        require(launch['tool_key'] == key and launch['engine'] == settings['engine'] == row['engine'],
                'executed tool or engine differs')
        artifact = canonical(Path(launch['artifact_path']))
        require(artifact.is_relative_to(target) and artifact != target, 'executed artifact belongs to another cache')
        require(len(row['artifacts']) == 1, 'executed artifact snapshot is missing or ambiguous')
        snapshot = row['artifacts'][0]
        path = canonical(root / snapshot['path'])
        require(path.is_relative_to(raw / 'artifacts' / selected) and path.is_file(),
                'executed snapshot is outside the preserved workflow directory')
        require(snapshot['sha256'] == digest(launch['artifact_sha256']) and
                snapshot['bytes'] == launch['artifact_bytes'] == path.stat().st_size,
                'executed artifact snapshot identity differs')
        snapshots.append(path)
    require(set(targets) == {'native', 'check', 'baseline', 'candidate'} and
            len(set(targets.values())) == 4 and len(packages) == 1, 'missing or shared cache identities')
    require(report.get('check_floor') and checks, 'independent check evidence required')
    for check in checks:
        command = check['command']
        require(command[2] == 'check' and option(command, '--profile') == 'test' and
                option(command, '--manifest-path') == str(manifest) and
                option(command, '--package') in packages and
                option(command, '--target-dir') == str(targets['check']), 'independent check cache differs')
    target = canonical(targets[mode])
    require(target.is_dir(), 'completed cache target is absent')
    return target, dict(mode=mode, **identities.get(mode, {})), snapshots


def workflow_cache(root, run_id, corpus, mode, workflow, sha):
    native, proofs, verified = workflow(run_id, corpus)
    if mode == 'native':
        return native, proofs, verified
    raw = root / '.work/runs' / run_id
    read = lambda path: json.loads(path.read_text())
    target, selection, snapshots = derive(root, run_id,
        read(root / 'results' / run_id / 'summary.json'), read(raw / 'records.json'),
        read(raw / 'check-records.json'), mode)
    # The ordinary workflow verifier already hashes the exact snapshots. Bind
    # those preserved copies individually in the archive inventory as well.
    proofs.update({str(p.relative_to(root)): sha(p) for p in snapshots})
    return target, proofs, dict(verified, cache_selection=selection)


@contextmanager
def cache_guard(target, mode):
    if mode in ['native', 'check']:
        yield
        return
    require(mode in ['baseline', 'candidate'], 'unknown cache lock mode')
    path = canonical(target.parent / 'invocation.lock')
    require(stat.S_ISREG(path.lstat().st_mode), 'custom invocation lock is not a regular file')
    with path.open('r') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
