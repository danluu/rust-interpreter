#!/usr/bin/env python3
"""Explicit, immutable source-containing std MIR preparation; v1 is unchanged.

Preparation is a workload. Loading only checks an already published key. Neither
publication nor its two smoke probes constitute full diagnostic qualification.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import time
import tomllib

from compare_saved_runtime import acquire_lock, lock_wait_seconds
from custom_compiler import digest, file_digest, load_compiler, read_json, require, tree_stamps, valid_key
from std_mir import FLAGS
from toolchain_lookup import _stamp
from workflow_io import capture, require_space, write_json

ROOT = Path(__file__).resolve().parents[1]
POLICY = 'metadata-sysroot-v2-source-paths-release-backtrace'
SELECTION = 'source-paths-v2'
TOOLCHAIN = 'nightly-2026-09-08'
CARGO_COMMIT = '3c0b534756e166d12eb9fd2e1abfe5b42ac6101e'
SOURCE = 'lib/rustlib/src/rust/library/'
REQUIRED_SOURCES = ('Cargo.toml', 'Cargo.lock', 'core/src/lib.rs', 'alloc/src/lib.rs',
                    'std/src/lib.rs', 'test/src/lib.rs', 'proc_macro/src/lib.rs',
                    'core/src/panic.rs', 'std/src/macros.rs')
CRATES = ('core', 'alloc', 'std', 'test', 'proc_macro')


def source_capability(commit):
    return dict(schema_version=1, policy='bootstrap-remap-source-paths-v1',
        remap_debuginfo=True, virtual_rust_source_base_dir='/rustc/' + commit,
        virtual_rustc_dev_source_base_dir='/rustc-dev/' + commit, cargo_source_commit=CARGO_COMMIT)


def compiler_sources(compiler):
    identity = compiler.identity
    commit = identity['provenance']['source_commit']
    require(re.fullmatch('[0-9a-f]{40}', commit) is not None, 'unknown compiler source commit')
    require([line[13:] for line in identity['compiler'].splitlines()
             if line.startswith('commit-hash: ')] == [commit], 'compiler/source commit mismatch')
    require(identity['provenance'].get('std_source_paths') == source_capability(commit),
            'compiler lacks the qualified bootstrap source-path policy; v1 cannot be relabeled')
    files = {p[len(SOURCE):]: h for p, h in identity['files'].items() if p.startswith(SOURCE)}
    require(all(p in files for p in REQUIRED_SOURCES), 'incomplete compiler standard sources')
    require(digest({SOURCE + p: h for p, h in files.items()}) == identity['source_sha256'],
            'compiler standard source inventory differs')
    return commit, files


def recipe():
    # Typed placeholders are keyed BEFORE W exists. No key includes its own path.
    def work(suffix):
        return dict(std_work=suffix)
    return ['check', '--manifest-path', work('library/Cargo.toml'), '-p', 'sysroot', '--release',
        '--target', dict(compiler_host=True), '--features', 'backtrace', '--locked', '--offline',
        '--jobs', '2', '--target-dir', work('target'), dict(std_root=True), '-Ztrim-paths',
        '--config', 'profile.release.trim-paths="all"', '--config', 'profile.dev.trim-paths="all"']


def command_for(identity, work):
    result = [identity['cargo']['executable']]
    require(identity['recipe'] == recipe(), 'std v2 command recipe differs')
    for item in identity['recipe']:
        if isinstance(item, str):
            result.append(item)
        elif item == dict(compiler_host=True):
            result.append(identity['target'])
        elif item == dict(std_root=True):
            result.append('-Zroot-dir=' + str(work))
        else:
            require(set(item) == {'std_work'} and item['std_work'] in ['library/Cargo.toml', 'target'],
                    'unknown std v2 path placeholder')
            result.append(str(work / item['std_work']))
    return result


def validate_environment(environment):
    forbidden = {'CARGO_ENCODED_RUSTFLAGS', 'RUSTFLAGS', 'CARGO_BUILD_RUSTFLAGS',
        'CARGO_BUILD_RUSTC', 'CARGO_BUILD_RUSTC_WRAPPER', 'CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER',
        'CARGO_BUILD_TARGET', 'CARGO_TARGET_DIR', 'CARGO_INCREMENTAL', 'RUST_SYSROOT',
        '__CARGO_RUSTC_BOOTSTRAP_WS_REMAP', 'CFG_VIRTUAL_RUST_SOURCE_BASE_DIR',
        'CFG_VIRTUAL_RUSTC_DEV_SOURCE_BASE_DIR', 'CARGO', 'CARGO_BUILD_DEP_INFO_BASEDIR'}
    for name, value in environment.items():
        # Presence matters: Cargo treats an empty CARGO_ENCODED_RUSTFLAGS as
        # an explicit empty flag list, overriding even our nonempty RUSTFLAGS.
        require(not (name in forbidden or name.startswith(('LD_', 'DYLD_', 'CARGO_PROFILE_'))
            or (name.startswith('CARGO_') and any(token in name for token in
                ['RUSTFLAGS', 'ROOT_DIR', 'TRIM_PATHS', 'HOST_CONFIG', 'TARGET_APPLIES_TO_HOST']))),
            'std v2 conflicts with environment setting ' + name)
    for name in ['CARGO_HOME', 'RUSTUP_HOME', 'HOME']:
        if name in environment:
            require(bool(environment[name]) and Path(environment[name]).is_absolute(),
                    'std v2 requires an absolute nonempty ' + name)
    for name in ['RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER']:
        require(not environment.get(name), 'std v2 conflicts with ' + name)
    require(environment.get('RUSTUP_TOOLCHAIN', TOOLCHAIN) == TOOLCHAIN or
            environment.get('RUSTUP_TOOLCHAIN', '').startswith(TOOLCHAIN + '-'),
            'std v2 requires the pinned Cargo toolchain')


def configuration(root, environment):
    # Cargo reads cwd ancestors, not the manifest's source directory. W has no
    # local config, and all possible ancestor/home files are guarded, including
    # absent files so a new overriding config invalidates reuse.
    paths = set()
    for directory in [root / '.work/std-mir', root / '.work', root, *root.parents]:
        paths.update(directory / '.cargo' / name for name in ['config', 'config.toml'])
    home = Path(environment.get('CARGO_HOME', str(Path.home() / '.cargo'))).absolute()
    paths.update(home / name for name in ['config', 'config.toml'])
    result = {}
    def check(value, route=()):
        if not isinstance(value, dict):
            return
        for key, child in value.items():
            # Pinned Cargo recursively loads top-level includes, including
            # optional/table forms. Their contents are not in this inventory.
            require(route or key != 'include', 'std v2 conflicts with Cargo configuration: include')
            require(key not in ['rustflags', 'rustc', 'rustc-wrapper', 'rustc-workspace-wrapper',
                               'root-dir', 'trim-paths', 'host-config', 'target-applies-to-host']
                    and not (route == ('build',) and key in ['target', 'target-dir', 'incremental']),
                    'std v2 conflicts with Cargo configuration: ' + '.'.join((*route, key)))
            check(child, (*route, key))
    for path in sorted(paths):
        require(not path.is_symlink(), 'indirect Cargo configuration is unsupported')
        if path.exists():
            require(path.is_file(), 'Cargo configuration is not a file')
            payload = path.read_bytes()
            check(tomllib.loads(payload.decode()))
            result[str(path)] = dict(sha256=file_digest(path), stamp=_stamp(path))
        else:
            result[str(path)] = None
    return result


def cargo_identity(root, host, run, environment):
    from custom_cargo_libraries import library_closure
    # The exact executable/version/hash, not just the toolchain label, is keyed.
    path = Path(run('cargo-location', ['rustup', 'which', '--toolchain', TOOLCHAIN, 'cargo'],
                    environment)['stdout'].strip()).resolve(strict=True)
    version = run('cargo-version', [str(path), '-Vv'], environment)['stdout']
    require([s[13:] for s in version.splitlines() if s.startswith('commit-hash: ')] == [CARGO_COMMIT]
            and [s[6:] for s in version.splitlines() if s.startswith('host: ')] == [host],
            'Cargo does not implement the reviewed source-path recipe pin')
    probes = 0
    def probe(command, *, text):
        require(text is True, 'std v2 library inspector requires text output')
        nonlocal probes
        probes += 1
        return run('cargo-library-' + str(probes), command, environment)['stdout']
    libraries, guard = library_closure(path, host, inspect=probe)
    identity = dict(executable=str(path), sha256=file_digest(path), version=version,
                    toolchain=TOOLCHAIN, host=host, libraries=libraries, route=cargo_route(host))
    require(identity['route']['executable'] == str(path), 'pinned Cargo installation route differs')
    return identity, dict(executable=_stamp(path), libraries=guard, route=identity['route'])


def cargo_route(host):
    cargo, rustup = shutil.which('cargo'), shutil.which('rustup')
    require(cargo and rustup and os.path.samefile(cargo, rustup), 'std v2 requires the ordinary rustup Cargo proxy')
    home = Path(os.environ.get('RUSTUP_HOME', str(Path.home() / '.rustup'))).resolve(strict=True)
    executable = home / 'toolchains' / (TOOLCHAIN + '-' + host) / 'bin/cargo'
    require(executable.resolve(strict=True) == executable, 'pinned Cargo path is indirect')
    return dict(executable=str(executable), rustup_home=str(home),
        cargo_proxy=dict(path=cargo, stamp=_stamp(Path(cargo))),
        rustup=dict(path=rustup, stamp=_stamp(Path(rustup))))


def cargo_state(identity):
    from custom_cargo_libraries import library_state
    return dict(executable=_stamp(Path(identity['executable'])),
                libraries=library_state(identity['libraries']), route=cargo_route(identity['host']))


def make_identity(compiler, cargo, namespace, configs, build_environment_sha256=None):
    commit, sources = compiler_sources(compiler)
    require(re.fullmatch(r'[a-z0-9][a-z0-9:._-]{0,127}', namespace) is not None,
            'std v2 requires an explicit compiler-policy namespace')
    require(cargo['toolchain'] == TOOLCHAIN and cargo['host'] == compiler.host and valid_key(cargo['sha256']) and
            [s[13:] for s in cargo['version'].splitlines() if s.startswith('commit-hash: ')] == [CARGO_COMMIT],
            'std v2 Cargo identity differs')
    return dict(policy=POLICY, compiler_key=compiler.key, compiler=compiler.identity['compiler'],
        compiler_sysroot=str(compiler.sysroot), compiler_source_commit=commit, target=compiler.host,
        source_sha256=compiler.identity['source_sha256'], source_files=sources, namespace=namespace,
        flags=FLAGS, cargo=cargo, recipe=recipe(), setup_jobs=2, configuration=configs,
        virtual_prefix='/rustc/' + commit,
        build_environment_sha256=build_environment_sha256 if build_environment_sha256 is not None else digest({}))


def freeze_tree(directory):
    for path in [*directory.rglob('*'), directory]:
        require(not path.is_symlink(), 'std v2 cannot publish links')
        path.chmod(0o555 if path.is_dir() else 0o444)


def tree_files(directory):
    stamps = tree_stamps(directory)
    return {p: file_digest(directory / p) for p, s in stamps.items() if stat.S_ISREG(s[2])}


def verify_tree(directory, files, stamps, *, rehash=False):
    require(files and all(valid_key(h) for h in files.values()), 'empty or invalid std v2 inventory')
    current = tree_stamps(directory)
    require(current == stamps, 'std v2 tree changed: ' + str(directory))
    require(set(files) == {p for p, s in current.items() if stat.S_ISREG(s[2])},
            'std v2 file inventory differs')
    require(all(not (s[2] & 0o222) for s in current.values()), 'std v2 tree is writable')
    if rehash:
        require(tree_files(directory) == files, 'std v2 file bytes differ')


def expected_sysroot_files(identity, metadata):
    prefix = 'lib/rustlib/' + identity['target'] + '/lib/'
    require(metadata and all(p.startswith(prefix) and '/' not in p[len(prefix):]
                            and p.endswith('.rmeta') and valid_key(h) for p, h in metadata.items()),
            'invalid or empty std v2 metadata inventory')
    for crate in CRATES:
        require(len([p for p in metadata if p.startswith(prefix + 'lib' + crate + '-')]) == 1,
                'missing or ambiguous std metadata: ' + crate)
    return metadata | {SOURCE + p: h for p, h in identity['source_files'].items()}


def validate_probe(records, source, files):
    # Verification only: preserve raw JSON and require its existing text to
    # match. Never fill, rewrite, normalize or return a derived diagnostic.
    from verified_std_diagnostics import source_span_text
    seen = set()
    require(any(d.get('code', {}) and d['code'].get('code') == 'E0080'
                and d.get('level') == 'error' for d in records), 'probe did not report E0080')
    def visit(value):
        if isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, dict):
            if 'file_name' in value:
                path = Path(value['file_name'])
                relative = str(path.relative_to(source)) if path.is_absolute() and path.is_relative_to(source) else None
                if relative is not None:
                    require(relative in files and path.resolve(strict=True) == path,
                            'probe has unrecognized standard source')
                    require(file_digest(path) == files[relative], 'probe standard source changed')
                    require(value.get('text') and value['text'] == source_span_text(value, path.read_bytes()),
                            'probe standard source snippet is missing or differs')
                    seen.add(relative)
                else:
                    require(not str(path).startswith(('/rustc/', 'library/', 'core/', 'std/')),
                            'probe has an unresolved standard source path')
            for child in value.values():
                visit(child)
    visit(records)
    require({'core/src/panic.rs', 'std/src/macros.rs'} <= seen,
            'probe did not expose both core and std expansion sources')
    return sorted(seen)


def load(root, key, compiler, namespace, *, rehash=False):
    require(valid_key(key), 'std v2 requires a preinstalled 64-hex key')
    compiler_sources(compiler)
    validate_environment(os.environ)
    work = root / '.work/std-mir' / key
    require(work.resolve(strict=True) == work and work.is_dir(), 'std v2 work path is indirect')
    ready = read_json(work / 'ready.json')
    require(not (work / 'ready.json').stat().st_mode & 0o222, 'std v2 readiness is writable')
    validate_ready(root, work, key, compiler, namespace, ready, rehash=rehash)
    return work / 'sysroot', compiler.host, key, ready


def validate_ready(root, work, key, compiler, namespace, ready, *, rehash=False):
    identity = ready['identity']
    require(ready['owner'] == str(root) and ready['key'] == key and digest(identity) == key,
            'std v2 owner or key differs')
    require(read_json(work / 'owner.json') == dict(owner=str(root), identity=identity, run_id=ready['run_id']),
            'std v2 owner marker differs')
    configs = configuration(root, os.environ)
    require(valid_key(identity['build_environment_sha256']) and identity == make_identity(
            compiler, identity['cargo'], namespace, configs, identity['build_environment_sha256']),
            'std v2 compiler, source, namespace or configuration differs')
    require(cargo_state(identity['cargo']) == ready['cargo_state'], 'std v2 Cargo changed')
    require(ready['command'] == command_for(identity, work), 'std v2 expanded command differs')
    require(ready['environment'] == dict(RUSTC=str(compiler.rustc), RUSTFLAGS=FLAGS,
        RUSTC_WRAPPER='', RUSTC_WORKSPACE_WRAPPER='', CARGO_TERM_COLOR='never',
        __CARGO_RUSTC_BOOTSTRAP_WS_REMAP=identity['virtual_prefix']), 'std v2 setup environment differs')
    require(ready['sysroot_files'] == expected_sysroot_files(identity, ready['metadata']),
            'std v2 source or metadata publication differs')
    verify_tree(work / 'sysroot', ready['sysroot_files'], ready['sysroot_stamps'], rehash=rehash)
    verify_tree(work / 'library', identity['source_files'], ready['snapshot_stamps'], rehash=rehash)
    for name in ['config', 'config.toml']:
        require(not (work / '.cargo' / name).exists() and not (work / '.cargo' / name).is_symlink(),
                'std v2 work acquired a local Cargo configuration')
    require(ready['probes'] == ['native', 'prepared'] and ready['full_presentation_qualified'] is False,
            'std v2 preparation is not full presentation qualification')
    verify_tree(work / 'evidence', ready['evidence_files'], ready['evidence_stamps'], rehash=rehash)
    require({'plan.json', 'commands.json', 'metadata.json', 'metadata-process.json',
             'probe-native.json', 'probe-native-process.json', 'probe-native/source.rs',
             'probe-prepared.json', 'probe-prepared-process.json', 'probe-prepared/source.rs',
             'probe-summary.json'} <= set(ready['evidence_files']), 'std v2 completion evidence is incomplete')
    plan = read_json(work / 'evidence/plan.json')
    require(plan['identity'] == identity and plan['command'] == ready['command']
            and plan['environment'] == ready['environment']
            and plan['environment_sha256'] == identity['build_environment_sha256'], 'std v2 retained plan differs')
    for label, code in [('metadata', 0), ('probe-native', 1), ('probe-prepared', 1)]:
        row = read_json(work / 'evidence' / (label + '.json'))
        process = read_json(work / 'evidence' / (label + '-process.json'))
        require(row['returncode'] == code and process['returncode'] == code
                and process['status'] == 'finished' and process['command'] == row['command']
                and process['finished_at'] >= process['started_at'], 'std v2 child completion differs')
        if label == 'metadata':
            require(row['command'] == ready['command'] and process['cwd'] == str(work),
                    'std v2 actual metadata command differs')
        elif rehash:
            source = compiler.sysroot / SOURCE if label == 'probe-native' else work / 'sysroot' / SOURCE
            validate_probe([json.loads(line) for line in row['stderr'].splitlines() if line.strip()],
                           source, identity['source_files'])


def prepare(root, compiler, namespace, run_id, lock_path, wait_seconds):
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', run_id) is not None, 'invalid std v2 run ID')
    run_work = root / '.work' / run_id
    run_work.mkdir(parents=True, exist_ok=False)
    rows, work = [], None
    write_json(run_work / 'result.json', dict(status='waiting', commands=rows, lock=str(lock_path)))
    try:
        require(lock_path.is_absolute() and lock_path.is_file(), 'supply an existing canonical workload lock')
        require(lock_path.resolve() == lock_path, 'supply the canonical lock path, not a worktree alias')
        with lock_path.open('r+') as lock:
            acquire_lock(lock, wait_seconds)
            with (root / '.work/std-mir.lock').open('a') as setup_lock:
                acquire_lock(setup_lock, wait_seconds)
                started = time.perf_counter()
                compiler_sources(compiler)
                validate_environment(os.environ)
                compiler.environment(os.environ)
                configs = configuration(root, os.environ)
                env = {k: v for k, v in os.environ.items() if not k.startswith('RUST_INTERP_')}
                env.update(RUSTC_WRAPPER='', RUSTC_WORKSPACE_WRAPPER='', CARGO_TERM_COLOR='never')
                def run(label, command, actual_env, cwd=run_work, expected=0):
                    require_space(root, 8)
                    record = dict(label=label, environment_sha256=digest(actual_env))
                    child, stdout, stderr = capture(list(map(str, command)), cwd=cwd, env=actual_env,
                        receipt_path=run_work / (label + '-process.json'), receipt=record)
                    row = dict(record, command=list(map(str, command)), returncode=child.returncode,
                               stdout=stdout, stderr=stderr)
                    rows.append(row)
                    write_json(run_work / (label + '.json'), row)
                    write_json(run_work / 'commands.json', rows)
                    require(child.returncode == expected, 'std v2 child failed: ' + label)
                    return row
                cargo, guard = cargo_identity(root, compiler.host, run, env)
                selected_env = dict(RUSTC=str(compiler.rustc), RUSTFLAGS=FLAGS, RUSTC_WRAPPER='',
                    RUSTC_WORKSPACE_WRAPPER='', CARGO_TERM_COLOR='never',
                    __CARGO_RUSTC_BOOTSTRAP_WS_REMAP='/rustc/' + compiler.identity['provenance']['source_commit'])
                env = compiler.environment(env)
                env.update(selected_env)
                identity = make_identity(compiler, cargo, namespace, configs, digest(env))
                key = digest(identity)
                work = root / '.work/std-mir' / key
                # Never overwrite a ready installation or a failed attempt.
                work.mkdir(parents=True, exist_ok=False)
                write_json(work / 'owner.json', dict(owner=str(root), identity=identity, run_id=run_id))
                command = command_for(identity, work)
                write_json(run_work / 'plan.json', dict(owner=str(root), key=key, identity=identity,
                    command=command, environment=selected_env, environment_sha256=digest(env),
                    lock=str(lock_path), setup_jobs=2, full_presentation_qualified=False))
                source = compiler.sysroot / SOURCE
                require(tree_files(source) == identity['source_files'], 'installed standard source differs')
                require_space(root, 8)
                shutil.copytree(source, work / 'library', symlinks=False)
                # Cargo reads W/library with W as its actual compilation root.
                require(tree_files(work / 'library') == identity['source_files'], 'snapshot copy differs')
                def probe(label, sysroot):
                    directory = run_work / ('probe-' + label)
                    directory.mkdir()
                    path = directory / 'source.rs'
                    path.write_text('const UNCALLED: u32 = panic!("std source lookup probe");\n')
                    probe_env = {k: v for k, v in env.items() if k not in
                                 ['RUSTFLAGS', '__CARGO_RUSTC_BOOTSTRAP_WS_REMAP']}
                    row = run('probe-' + label, [compiler.rustc, path, '--crate-type=lib',
                        '--edition=2024', '--emit=metadata', '--error-format=json', '--sysroot', sysroot,
                        '-o', directory / 'probe.rmeta'], probe_env, cwd=directory, expected=1)
                    diagnostics = [json.loads(line) for line in row['stderr'].splitlines() if line.strip()]
                    return validate_probe(diagnostics, sysroot / SOURCE, identity['source_files'])
                native = probe('native', compiler.sysroot)
                before = time.perf_counter()
                run('metadata', command, env, cwd=work)
                build_seconds = time.perf_counter() - before
                require(tree_files(work / 'library') == identity['source_files'], 'std sources changed during check')
                lib = work / 'sysroot/lib/rustlib' / compiler.host / 'lib'
                lib.mkdir(parents=True)
                metadata = {}
                for path in sorted((work / 'target' / compiler.host / 'release').rglob('*.rmeta')):
                    require(not path.is_symlink() and path.is_file() and path.stat().st_size > 0,
                            'invalid std metadata output')
                    destination = lib / path.name
                    require(not destination.exists(), 'duplicate std metadata output: ' + path.name)
                    shutil.copy2(path, destination)
                    metadata[str(destination.relative_to(work / 'sysroot'))] = file_digest(destination)
                expected = expected_sysroot_files(identity, metadata)
                shutil.copytree(work / 'library', work / 'sysroot' / SOURCE, symlinks=False)
                require(tree_files(work / 'sysroot') == expected, 'published std files differ')
                prepared = probe('prepared', work / 'sysroot')
                require(load_compiler(root, compiler.key) == compiler, 'compiler changed during std preparation')
                require(configuration(root, os.environ) == configs and cargo_state(cargo) == guard,
                        'Cargo inputs changed during std preparation')
                require(tree_files(source) == identity['source_files'] and
                        tree_files(work / 'library') == identity['source_files'], 'standard sources changed')
                write_json(run_work / 'probe-summary.json', dict(native=native, prepared=prepared,
                    full_presentation_qualified=False, strict_integration_required=True))
                evidence = work / 'evidence'
                evidence.mkdir()
                for path in sorted(run_work.glob('*.json')):
                    if path.name != 'result.json':
                        shutil.copy2(path, evidence / path.name)
                for directory in ['probe-native', 'probe-prepared']:
                    shutil.copytree(run_work / directory, evidence / directory)
                freeze_tree(work / 'library')
                freeze_tree(work / 'sysroot')
                freeze_tree(evidence)
                ready = dict(owner=str(root), key=key, identity=identity, run_id=run_id, command=command,
                    environment=selected_env, cargo_state=guard, metadata=metadata, sysroot_files=expected,
                    snapshot_stamps=tree_stamps(work / 'library'), sysroot_stamps=tree_stamps(work / 'sysroot'),
                    evidence_files=tree_files(evidence), evidence_stamps=tree_stamps(evidence),
                    probes=['native', 'prepared'], full_presentation_qualified=False,
                    source_sha256=compiler.identity['source_sha256'], build_seconds=build_seconds,
                    setup_seconds=time.perf_counter() - started, fetch_seconds=0,
                    metadata_bytes=sum((work / 'sysroot' / p).stat().st_size for p in metadata))
                # All outputs, ordinary checks, source probes and complete
                # inventories exist before readiness becomes visible.
                validate_ready(root, work, key, compiler, namespace, ready, rehash=True)
                write_json(work / 'ready.json', ready)
                (work / 'ready.json').chmod(0o444)
                write_json(run_work / 'result.json', dict(status='passed', key=key, work=str(work),
                    commands=len(rows), full_presentation_qualified=False, strict_integration_required=True))
                return work / 'sysroot', compiler.host, key, ready
    except BaseException as error:
        write_json(run_work / 'result.json', dict(status='failed', error=repr(error), commands=len(rows),
            work=str(work) if work else None, lock=str(lock_path), retained_children=rows))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler-key', required=True)
    parser.add_argument('--namespace', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--workload-lock', type=Path, required=True)
    parser.add_argument('--lock-wait-seconds', type=lock_wait_seconds, default=600)
    args = parser.parse_args()
    compiler = load_compiler(ROOT, args.compiler_key)
    sysroot, target, key, _ = prepare(ROOT, compiler, args.namespace, args.run_id,
                                    args.workload_lock, args.lock_wait_seconds)
    print(json.dumps(dict(sysroot=str(sysroot), target=target, key=key, policy=POLICY,
                         full_presentation_qualified=False)))


if __name__ == '__main__':
    main()
