#!/usr/bin/env python3
"""Freeze one local-only acquisition proposal. Does not create its namespace."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import acquire as a

HERE, OWNER = a.HERE, a.OWNER
OLD = Path('/Users/danluu/dev/rustc-hir-capture-check-20260913')
BASE = '7efc0d9484da82cd327deb3b48616f8ec81eaf8d'
BACKTRACE = 'd902726a1dcdc1e1c66f73d1162181b5423c645b'
GIT = '/usr/bin/git'


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def git(root, *args):
    return subprocess.check_output([GIT, '--no-optional-locks', '-C', str(root), *args])


def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize
    assert not a.NAMESPACE.exists() and not a.WORK.exists()
    files, symlinks = {}, {}
    def add(path):
        path = Path(path)
        assert path.resolve(strict=True) == path and stat.S_ISREG(path.lstat().st_mode)
        first = a.stamp(path)
        result = dict(sha256=a.owned.sha(path), stamp=first)
        assert a.stamp(path) == first
        assert str(path) not in files or files[str(path)] == result
        files[str(path)] = result
        return result
    def tree(root, revision):
        assert git(root, 'rev-parse', 'HEAD').decode().strip() == revision
        assert not git(root, 'diff', 'HEAD', '--')
        result = {}
        for entry in git(root, 'ls-tree', '-r', '-z', revision).split(b'\0'):
            if not entry:
                continue
            metadata, raw_name = entry.split(b'\t', 1)
            mode, kind, blob = metadata.decode().split()
            name = raw_name.decode()
            path = root / name
            record = dict(mode=mode, blob=blob)
            if mode == '160000':
                assert kind == 'commit'
            elif mode == '120000':
                assert path.is_symlink()
                target = os.readlink(path)
                data = os.fsencode(target)
                record['target'] = target
                symlinks[str(path)] = dict(target=target, stamp=a.stamp(path))
                assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == blob
            else:
                assert mode in ['100644', '100755'] and kind == 'blob'
                record['sha256'] = add(path)['sha256']
                data = path.read_bytes()
                assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == blob
            result[name] = record
        return result
    source_tree = tree(OLD, BASE)
    backtrace_tree = tree(OLD / 'library/backtrace', BACKTRACE)
    source_manifest = a.read(HERE / 'source-01/manifest.json')
    assert source_manifest['base_commit'] == BASE
    for name, digest in source_manifest['before_hashes'].items():
        assert source_tree[name]['sha256'] == digest
    provider = a.read(HERE / 'provider-proposal-01.json')
    assert provider['base_commit'] == BASE
    assert not provider['historical_required_archives_missing'] and not provider['historical_packages_outside_current_locks']
    copies = []
    def copy(source, destination, digest):
        assert add(source)['sha256'] == digest
        assert destination.is_relative_to(a.NAMESPACE)
        copies.append(dict(source=str(source), destination=str(destination), sha256=digest,
            bytes=Path(source).stat().st_size))
    copy(OLD / 'bootstrap.toml', a.SOURCE / 'bootstrap.toml',
        '71b495da8fc35ca1321322f56065eb149ecd82fa3c8ff7ef4d4c10ec53f0df9b')
    seed_config = json.loads(git(OWNER, 'show', 'HEAD:experiments/hir-arena-identity-upgrade/planned-upgrade-01.json'))['previous']['old_plan']['copied_archives']
    assert len(seed_config) == 6
    for source, row in sorted(seed_config.items()):
        relative = Path(source).relative_to(OLD)
        copy(Path(source), a.SOURCE / relative, row['sha256'])
    registry = Path('/Users/danluu/.cargo/registry')
    for row in [provider['sparse_index_config'], *provider['sparse_index'].values(), *provider['archives'].values()]:
        source = Path(row['path'])
        assert add(source)['sha256'] == row['sha256'] and a.stamp(source) == row['stamp']
        copy(source, a.CARGO / 'registry' / source.relative_to(registry), row['sha256'])
    for row in provider['historical_depinfo'].values():
        assert add(Path(row['path']))['sha256'] == row['sha256']
    assert len({r['destination'] for r in copies}) == len(copies)
    environment = dict(PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin', HOME='/Users/danluu',
        USER='danluu', LOGNAME='danluu', LANG='C', LC_ALL='C', TZ='UTC', PYTHONDONTWRITEBYTECODE='1',
        PYTHONNOUSERSITE='1', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
        GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0', CARGO_NET_OFFLINE='true',
        CARGO_HOME=str(a.CARGO), RUSTUP_DIST_SERVER='file:///dev/null',
        GIT_AUTHOR_DATE='2026-09-18T23:59:00+00:00', GIT_COMMITTER_DATE='2026-09-18T23:59:00+00:00')
    prefix = [GIT, '-c', 'core.hooksPath=/dev/null', '-c', 'core.autocrlf=false', '-c', 'core.fsmonitor=false',
        '-c', 'commit.gpgsign=false', '-c', 'protocol.allow=never', '-c', 'protocol.file.allow=always']
    before, after = [], []
    def command(output, cwd, *args, expected_stdout=None):
        output.append(dict(argv=[*prefix, *map(str,args)], cwd=str(cwd), environment=environment,
            expected_stdout=expected_stdout))
    command(before, OLD, 'rev-parse', 'HEAD', expected_stdout=BASE + '\n')
    command(before, OLD, 'diff', 'HEAD', '--', expected_stdout='')
    command(before, OLD / 'library/backtrace', 'rev-parse', 'HEAD', expected_stdout=BACKTRACE + '\n')
    command(before, OWNER, 'clone', '--no-hardlinks', '--no-checkout', OLD, a.SOURCE)
    command(before, a.SOURCE, 'checkout', '--detach', BASE)
    command(before, a.SOURCE, 'clone', '--no-hardlinks', '--no-checkout', OLD / 'library/backtrace', a.SOURCE / 'library/backtrace')
    command(before, a.SOURCE / 'library/backtrace', 'checkout', '--detach', BACKTRACE)
    command(before, a.SOURCE, 'apply', '--check', HERE / 'source-01/candidate.patch')
    command(before, a.SOURCE, 'apply', HERE / 'source-01/candidate.patch')
    command(after, a.SOURCE, 'add', '--', *source_manifest['changed_files'])
    command(after, a.SOURCE, '-c', 'user.name=Rust interpreter experiment', '-c', 'user.email=experiment@localhost',
        'commit', '--no-gpg-sign', '--no-verify', '-m', 'Cache immutable per-context incremental options hash')
    revision_child = len(before) + len(after)
    command(after, a.SOURCE, 'rev-parse', 'HEAD')
    command(after, a.SOURCE, 'diff', 'HEAD', '--', expected_stdout='')
    command(after, a.SOURCE, 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD', expected_stdout=''.join(n+'\n' for n in source_manifest['changed_files']))
    command(after, OLD, 'rev-parse', 'HEAD', expected_stdout=BASE+'\n')
    command(after, OLD, 'diff', 'HEAD', '--', expected_stdout='')
    command(after, OLD / 'library/backtrace', 'rev-parse', 'HEAD', expected_stdout=BACKTRACE+'\n')
    configurations = {}
    for directory in [OWNER, OLD, a.SOURCE, a.SOURCE / 'compiler/rustc', a.SOURCE / 'src/bootstrap', a.CARGO]:
        for ancestor in [directory, *directory.parents]:
            for name in ['.cargo/config', '.cargo/config.toml']:
                path = ancestor / name
                assert not path.is_symlink()
                configurations[str(path)] = a.owned.sha(path) if path.is_file() else None
                if path.is_file():
                    add(path)
    for path in [Path('/Users/danluu/.cargo/config'), Path('/Users/danluu/.cargo/config.toml')]:
        assert not path.is_symlink()
        configurations[str(path)] = a.owned.sha(path) if path.is_file() else None
    for path in [a.CARGO/'config', a.CARGO/'config.toml']:
        assert not path.exists() and not path.is_symlink()
        configurations[str(path)] = None
    plan = dict(schema_version=1, owner=str(OWNER), namespace=str(a.NAMESPACE), status='prepared-unexecuted',
        base_commit=BASE, backtrace_commit=BACKTRACE, source_tree=source_tree, backtrace_tree=backtrace_tree,
        children_before_copy=before, children_after_copy=after, candidate_revision_child=revision_child,
        copies=copies, capacity=dict(initial_free_gib=24, capacity_stop_gib=9, running_floor_gib=8,
            aggregate_allocated_gib=14, acquisition_allocated_gib=2),
        canonical_lock=str(a.owned.CANONICAL_LOCK), wait_seconds=600, compiler_builds=0, cargo_commands=0,
        network_fallback=False, provider_proposal_sha256=a.owned.sha(HERE / 'provider-proposal-01.json'),
        source_manifest_sha256=a.owned.sha(HERE / 'source-01/manifest.json'))
    write(HERE / 'acquisition-plan.json', plan)
    for path in sorted(HERE.rglob('*')):
        if path.is_file():
            add(path)
            if path.suffix == '.py':
                ast.parse(path.read_text())
    python = Path(sys.executable).resolve(strict=True)
    for path in [python, Path(GIT), OWNER/'scripts/supervise_experiment.py', OWNER/'experiments/stable-cgu/owned_stage.py']:
        add(path)
    frozen = dict(schema_version=1, files=files, symlinks=symlinks, configurations=configurations,
        plan_sha256=a.owned.sha(HERE/'acquisition-plan.json'), python=str(python))
    write(HERE/'acquisition-inputs.json', frozen)
    launch = dict(status='prepared-unexecuted-awaiting-review', owner=str(OWNER), environment=environment,
        command=[str(python), '-B', str(OWNER/'scripts/supervise_experiment.py'), '--run-id', 'hir-options-hash-acquisition-supervisor-01', '--',
            str(python), '-B', str(HERE/'acquire.py'), '--inputs-sha256', a.owned.sha(HERE/'acquisition-inputs.json')],
        helper_sha256=a.owned.sha(HERE/'acquire.py'), inputs_sha256=a.owned.sha(HERE/'acquisition-inputs.json'),
        plan_sha256=a.owned.sha(HERE/'acquisition-plan.json'), expected_children=len(before)+len(after),
        capacity=plan['capacity'], compiler_builds=0, cargo_commands=0)
    write(HERE/'acquisition-launch.json', launch)
    print(json.dumps(dict(launch_sha256=a.owned.sha(HERE/'acquisition-launch.json'),
        inputs_sha256=launch['inputs_sha256'], plan_sha256=launch['plan_sha256'],
        inputs=len(files), source_files=len(source_tree), copies=len(copies), children=launch['expected_children']), indent=2))


if __name__ == '__main__':
    main()
