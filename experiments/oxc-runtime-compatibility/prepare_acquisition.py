#!/usr/bin/env python3
"""Read existing qualified inputs and freeze one additive transfer, without running it."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tomllib

import acquire_runtime_source as a


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as output:
        json.dump(value, output, sort_keys=True, indent=2)
        output.write('\n')


def main():
    a.require(sys.dont_write_bytecode and Path.cwd() == a.OWNER, 'Python -B and fixed owner required')
    for path in [a.PLAN, a.FROZEN, a.WORK, a.SOURCE]:
        a.absent(path)
    registry = a.load('oxc_prepare_registry', a.OWNER / 'experiments/oxc-plugin-normalization/registry_cache.py')
    qualified = a.read(a.QUALIFIED)['archives']
    a.require(len(qualified) == 323, 'qualified package count changed')
    native = a.read(a.OWNER / '.work/oxc-native-compatibility-02/receipt.json')
    a.require(native['status'] == 'passed' and native['clean_native_performance_qualified']
              and native['source_restored'], 'qualified restored native history required')
    lock = tomllib.loads((a.ORIGINAL / 'Cargo.lock').read_text())
    locked = {p['name'] + '-' + p['version']: p for p in lock['package'] if p.get('source')}
    packages, indexes = {}, {}
    for label, item in qualified.items():
        package = locked[label]
        a.require(package['source'] == 'registry+https://github.com/rust-lang/crates.io-index' and
                  package['checksum'] == item['checksum'], 'qualified package differs from Cargo.lock')
        archive = a.CARGO_HOME / 'registry/cache' / a.REGISTRY / (label + '.crate')
        source = a.CARGO_HOME / 'registry/src' / a.REGISTRY / label
        a.require(archive.exists() == source.exists() and not archive.is_symlink() and not source.is_symlink(),
                  'partial or indirect shared package')
        present = archive.exists()
        existing = registry.verify(archive, source, item['checksum']) if present else None
        if present:
            # Only extraction permissions can legitimately differ across umasks.
            def bytes_only(proof):
                return dict(checksum=proof['checksum'], directories=proof['directories'],
                    unpacked_bytes=proof['unpacked_bytes'], cargo_marker=proof['cargo_marker'],
                    members={n: {k: v for k, v in row.items() if k != 'extracted_mode'}
                             for n, row in proof['members'].items()})
            a.require(bytes_only(existing) == bytes_only(item), 'shared cache differs from qualified bytes')
            a.require(all(bool(row['extracted_mode'] & 0o111) == bool(item['members'][name]['extracted_mode'] & 0o111)
                          for name, row in existing['members'].items()), 'shared executable permissions differ')
        packages[label] = dict(label=label, name=package['name'], version=package['version'],
                               checksum=item['checksum'], present=present, existing=existing)
        relative = a.index_path(package['name'])
        private, shared = a.PRIVATE / relative, a.CARGO_HOME / relative
        if relative not in indexes:
            a.require(not shared.is_symlink(), 'shared index is a symlink')
            indexes[relative] = dict(private=a.file_record(private), present=shared.exists(),
                                     existing=a.file_record(shared) if shared.exists() else None, records=[])
        record = a.index_record(private, package['name'], package['version'], item['checksum'])
        if shared.exists():
            a.require(a.index_record(shared, package['name'], package['version'], item['checksum']) == record,
                      'preexisting required index record differs or is absent')
        indexes[relative]['records'].append(dict(name=package['name'], version=package['version'],
                                                checksum=item['checksum'], record=record))
    for name in ['registry/cache/' + a.REGISTRY, 'registry/src/' + a.REGISTRY,
                 'registry/index/' + a.REGISTRY + '/.cache']:
        a.ordinary(a.CARGO_HOME / name, directory=True)
    source_inventory = a.inventory(a.ORIGINAL)
    a.require('.git/objects/info/alternates' not in source_inventory and
              all(not n.endswith('/index.lock') for n in source_inventory), 'source Git database is shared or busy')
    original_config = (a.ORIGINAL / '.git/config').read_text()
    a.require(original_config == '[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n\tbare = false\n'
              '\tlogallrefupdates = true\n\tignorecase = true\n\tprecomposeunicode = true\n',
              'unexpected original Git policy')
    a.require((a.ORIGINAL / '.git/HEAD').read_text() == a.REVISION + '\n', 'original HEAD differs')
    runtime_gitdir = Path((a.RROOT / '.git').read_text().removeprefix('gitdir: ').strip())
    head_text = (runtime_gitdir / 'HEAD').read_text()
    a.require(head_text.startswith('ref: refs/heads/') and head_text.endswith('\n'), 'runtime HEAD route differs')
    reference = head_text.removeprefix('ref: ').strip()
    a.safe_relative(reference)
    common = (runtime_gitdir / (runtime_gitdir / 'commondir').read_text().strip()).resolve(strict=True)
    reference_path = common / reference
    a.require(reference_path.read_text() == a.RHEAD + '\n', 'runtime owner HEAD differs')
    runtime_files = {str(path): a.sha(path) for path in sorted((a.RROOT / 'scripts').rglob('*.py'))}
    runtime_files.update({str(a.RROOT / '.git'): a.sha(a.RROOT / '.git'),
                         str(runtime_gitdir / 'HEAD'): a.sha(runtime_gitdir / 'HEAD'),
                         str(runtime_gitdir / 'commondir'): a.sha(runtime_gitdir / 'commondir'),
                         str(reference_path): a.sha(reference_path)})
    environment = dict(HOME='/Users/danluu', PATH='/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin',
        LANG='C.UTF-8', LC_ALL='C.UTF-8', TZ='UTC', TMPDIR=str(a.WORK / 'tmp'),
        PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', GIT_OPTIONAL_LOCKS='0',
        GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_ATTR_NOSYSTEM='1',
        __CF_USER_TEXT_ENCODING='0x1F5:0x0:0x0')
    python = '/opt/homebrew/bin/python3'
    tools = [python, '/usr/bin/git', '/bin/ps', '/usr/sbin/lsof']
    executors = {name: dict(resolved=str(Path(name).resolve(strict=True)), stamp=a.stamp(name), sha256=a.sha(name))
                 for name in tools}
    a.require(shutil.which('ps', path=environment['PATH']) == '/bin/ps' and
              shutil.which('lsof', path=environment['PATH']) == '/usr/sbin/lsof', 'unexpected supervisor PATH route')
    git_version = subprocess.check_output(['/usr/bin/git', '--version'], env=environment, text=True)
    commands = [dict(label='controls', argv=[python, '-B', str(a.HERE / 'test_acquire_runtime_source.py')], cwd=str(a.OWNER)),
                dict(label='git-version-before', argv=['/usr/bin/git', '--version'], cwd=str(a.OWNER))]
    for phase, source in [('original-before', a.ORIGINAL), ('acquired', a.SOURCE), ('original-after', a.ORIGINAL)]:
        commands.extend([dict(label=phase + '-head', argv=['/usr/bin/git', 'rev-parse', 'HEAD'], cwd=str(source)),
                         dict(label=phase + '-status', argv=['/usr/bin/git', 'status', '--porcelain', '--untracked-files=all'],
                              cwd=str(source))])
    commands.append(dict(label='git-version-after', argv=['/usr/bin/git', '--version'], cwd=str(a.OWNER)))
    lock_stat = a.ordinary(a.CARGO_HOME / '.package-cache')
    config_paths = [a.CARGO_HOME / 'config', a.CARGO_HOME / 'config.toml',
                    a.CARGO_HOME / 'registry/index' / a.REGISTRY / 'config.json',
                    a.PRIVATE / 'registry/index' / a.REGISTRY / 'config.json']
    configuration = {}
    for path in config_paths:
        a.require(not path.is_symlink(), 'configuration symlink')
        configuration[str(path)] = dict(exists=path.exists(), record=a.file_record(path) if path.exists() else None)
    a.require((config_paths[2]).read_bytes() == (config_paths[3]).read_bytes(), 'private/shared registry endpoints differ')
    plan = dict(schema_version=1, owner=str(a.OWNER), runtime_owner=str(a.RROOT), runtime_head=a.RHEAD,
        original=str(a.ORIGINAL), source=str(a.SOURCE), cargo_home=str(a.CARGO_HOME), revision=a.REVISION,
        canonical_lock='/Users/danluu/dev/rust-interp/.work/benchmark.lock', wait_seconds=600,
        entry_gib=16, stop_gib=9, floor_gib=8, total_allocation_limit_bytes=640*2**20,
        evidence_limit_bytes=128*2**20, environment=environment, commands=commands,
        executors=executors, configuration=configuration, platform=list(os.uname()), git_version=git_version,
        source_inventory=source_inventory, source_root_mode=stat.S_IMODE(a.ORIGINAL.stat().st_mode),
        packages=packages, indexes=indexes, runtime_files=runtime_files,
        cargo_lock_identity=dict(dev=lock_stat.st_dev, ino=lock_stat.st_ino),
        ownership_marker=dict(owner=str(a.RROOT), revision=a.REVISION, source='https://github.com/oxc-project/oxc.git',
                              acquired_from=str(a.ORIGINAL), acquisition_owner=str(a.OWNER)),
        expected_children=9, expected_controls=17, network=False, compiler=False, benchmark=False)
    write(a.PLAN, plan)
    inputs = [a.PLAN, a.HERE / 'acquire_runtime_source.py', a.HERE / 'prepare_acquisition.py',
        a.HERE / 'test_acquire_runtime_source.py', a.HERE / 'PREPARATION.md',
        a.OWNER / 'experiments/stable-cgu/owned_stage.py', a.OWNER / 'scripts/supervise_experiment.py',
        a.OWNER / 'experiments/oxc-plugin-normalization/registry_cache.py',
        a.OWNER / 'experiments/oxc-plugin-normalization/case.json', a.QUALIFIED,
        a.OWNER / '.work/oxc-acquisition-continuation-01/receipt.json',
        a.OWNER / '.work/oxc-native-setup-01/source-inventory.json',
        a.OWNER / '.work/oxc-native-compatibility-02/receipt.json',
        Path('/Users/danluu/dev/rust-interp/.work/sources/cargo/src/util/cache_lock.rs'),
        Path('/Users/danluu/dev/rust-interp/.work/sources/cargo/src/util/flock.rs'),
        Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin/lib/rustlib/src/rust/library/std/src/sys/fs/unix.rs'),
        *[Path(name) for name in runtime_files], *[Path(item['resolved']) for item in executors.values()]]
    frozen = dict(schema_version=1, owner=str(a.OWNER), files={str(path): a.sha(path) for path in sorted(set(inputs))},
                  python=dict(resolved=str(Path(sys.executable).resolve()), sha256=a.sha(sys.executable)))
    write(a.FROZEN, frozen)
    launch = dict(owner=str(a.OWNER), cwd=str(a.OWNER), environment=environment,
        command=[python, '-B', str(a.OWNER / 'scripts/supervise_experiment.py'), '--run-id',
                 'oxc-runtime-source-acquisition-supervisor-01', '--', python, '-B',
                 str(a.HERE / 'acquire_runtime_source.py'), '--frozen-sha256', a.sha(a.FROZEN)],
        frozen=str(a.FROZEN), frozen_sha256=a.sha(a.FROZEN))
    launch_path = a.OWNER / '.work/oxc-runtime-source-acquisition-launch-01.json'
    write(launch_path, launch)
    print(json.dumps(dict(plan_sha256=a.sha(a.PLAN), frozen_sha256=a.sha(a.FROZEN), launch=str(launch_path),
        launch_sha256=a.sha(launch_path), frozen_inputs=len(frozen['files']),
        frozen_bytes=sum(Path(name).stat().st_size for name in frozen['files']),
        existing_packages=sum(p['present'] for p in packages.values()),
        new_packages=sum(not p['present'] for p in packages.values()),
        new_indexes=sum(not p['present'] for p in indexes.values())), indent=2))


if __name__ == '__main__':
    main()
