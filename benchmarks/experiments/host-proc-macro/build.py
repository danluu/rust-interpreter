#!/usr/bin/env python3
"""Execute a reviewed public-tool build/qualification/publication plan, never a screen."""
import argparse
import json
import os
from pathlib import Path
import sys
import tarfile
import tomllib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from custom_compiler import file_digest, require
from public_tool_publication import (build_admission, capture_library_closure, command_environment,
    compose_qualified_tools, file_identity, immutable_publish, materialize_screen_command,
    retained_command, run_plan_commands)
from qualified_public_tools import BINARIES, COMPILER_REVISION, TOOLCHAIN, WORKER_BUILD_POLICY, planned_commands, sha
from workflow_io import write_json


def put(root, name, payload):
    path = root / name
    require(not path.exists() and not path.is_symlink(), 'payload already exists: ' + name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:stream.write(payload)


def put_json(root, name, value):
    put(root, name, (json.dumps(value, indent=2) + '\n').encode())


def retain_command(root, directory, label, *, prefix='metadata'):
    for suffix, kind in [('-process.json', 'receipts'), ('.stdout', 'logs'), ('.stderr', 'logs')]:
        put(root, f'provenance/{kind}/{prefix}-{label}{suffix}', (directory / (label + suffix)).read_bytes())


def frozen_sources(plan_path, plan, root):
    put(root, 'provenance/build-plan.json', plan_path.read_bytes())
    for section, prefix in [('workspace_sources', 'source'), ('harness', 'harness')]:
        for name, expected in plan[section].items():
            source = ROOT / name
            require(source.resolve(strict=True) == source and source.is_file()
                    and file_digest(source) == expected, 'frozen input differs: ' + name)
            put(root, f'provenance/{prefix}/{name}', source.read_bytes())
    put_json(root, 'provenance/harness.json', dict(files=plan['harness']))
    for name, expected in plan.get('prior_attempt', {}).get('records', {}).items():
        source = ROOT / name
        require(file_digest(source) == expected, 'prior attempt evidence changed: ' + name)
        put(root, 'provenance/prior-attempt/' + name, source.read_bytes())
    ready_path = Path(plan['shared_std']['path'])
    require(file_digest(ready_path) == plan['shared_std']['sha256'], 'shared std readiness differs')
    put(root, 'provenance/std-ready.json', ready_path.read_bytes())


def configuration(env):
    """Record every ancestor/home Cargo configuration consulted by this build."""
    cargo_home = Path(env.get('CARGO_HOME', str(Path.home() / '.cargo'))).resolve(strict=True)
    directories = [cargo_home, *[path / '.cargo' for path in [ROOT, *ROOT.parents]]]
    searches = {str(path / name): (path / name).exists() or (path / name).is_symlink()
                for path in directories for name in ('config', 'config.toml')}
    records = []
    for name, exists in searches.items():
        if not exists:continue
        path = Path(name)
        require(path.is_file(), 'Cargo config is not a regular file')
        value = tomllib.loads(path.read_text())
        build = value.get('build', {})
        # These selectors could replace the recorded compiler or inject a
        # wrapper before any meaningful qualification. Do not silently disable
        # configured behavior; require a separately reviewed plan if present.
        require(not any(k in build for k in ('rustc', 'rustc-wrapper', 'rustc-workspace-wrapper', 'rustflags'))
                and not value.get('env')
                and not any('rustflags' in table for table in value.get('target', {}).values() if isinstance(table, dict)),
                'Cargo config injects an unreviewed compiler/wrapper/Rustflags override')
        records.append(file_identity(path))
    allowed = {'PATH', 'HOME', 'USER', 'LOGNAME', 'SHELL', 'TMPDIR', 'LANG', 'LC_ALL', 'TERM',
               'CARGO_HOME', 'RUSTUP_HOME', 'SDKROOT', 'MACOSX_DEPLOYMENT_TARGET',
               'RUSTC', 'RUSTDOC', 'RUSTUP_TOOLCHAIN', 'CARGO_TERM_COLOR', 'CARGO_TERM_VERBOSE',
               'CARGO_INCREMENTAL', 'CARGO_BUILD_TARGET', 'CARGO_TARGET_DIR', 'CARGO_BUILD_JOBS'}
    compiler_env = {k: v for k, v in env.items() if k in allowed or k.startswith('CARGO_PROFILE_')}
    require(not any(k in env for k in ('CARGO_BUILD_RUSTC_WRAPPER', 'CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER',
                                     'RUST_SYSROOT', 'RUSTC_BOOTSTRAP')),
            'unreviewed compiler selection/environment override')
    require(not any((k.endswith('RUSTFLAGS') or k == 'CARGO_ENCODED_RUSTFLAGS') and v for k, v in env.items()),
            'unreviewed effective Rustflags')
    # Keep possible credentials out of publication; their presence cannot change
    # an offline build's downloaded dependency set. Store only a digest for any
    # other inherited environment, alongside the selected compiler settings.
    compiler_env = {k: v for k, v in compiler_env.items()
                    if not any(word in k for word in ('TOKEN', 'PASSWORD', 'SECRET', 'CREDENTIAL'))}
    return dict(files=records, searches=searches, compiler_environment=compiler_env,
                inherited_environment_sha256=sha(json.dumps(env, sort_keys=True).encode()))


def compiler_inventory(sysroot):
    paths = {sysroot / 'bin/rustc', sysroot / 'bin/rustdoc', sysroot / 'bin/cargo',
             sysroot / 'lib/rustlib/src/rust/library/Cargo.lock'}
    paths.update(p for p in (sysroot / 'lib').rglob('*') if p.is_file()
                 and p.suffix in ('.rlib', '.rmeta', '.dylib', '.so', '.dll'))
    require(any(p.name.startswith('librustc_driver-') for p in paths), 'public compiler driver is missing')
    return dict(files=[file_identity(p) for p in sorted(paths)])


def registry_files(base, locked_package):
    """Reconcile the installed tree with its locked archive, without extracting it."""
    require(base.parent.parent.name == 'src', 'unreviewed registry source layout')
    archive = base.parents[2] / 'cache' / base.parent.name / (base.name + '.crate')
    require(file_digest(archive) == locked_package['checksum'], 'registry archive differs from lockfile')
    expected = {}
    with tarfile.open(archive, 'r:gz') as bundle:
        for member in bundle:
            parts = Path(member.name).parts
            require(parts and parts[0] == base.name and not Path(member.name).is_absolute()
                    and all(p not in ('.', '..') for p in parts), 'unsafe registry archive member')
            if member.isdir():continue
            require(member.isfile() and len(parts) > 1, 'non-file registry archive member')
            name = str(Path(*parts[1:]))
            require(name not in expected and name not in ('.cargo-ok', '.cargo-checksum.json'),
                    'duplicate or reserved registry archive member')
            source = bundle.extractfile(member)
            require(source is not None, 'missing registry archive member bytes')
            with source:expected[name] = sha(source.read())
    entries = list(base.rglob('*'))
    require(not any(p.is_symlink() for p in entries), 'registry source contains a symlink')
    actual = {str(p.relative_to(base)): p for p in entries if p.is_file()}
    extras = set(actual) - set(expected)
    require(expected and set(expected) <= actual.keys()
            and extras <= {'.cargo-ok', '.cargo-checksum.json'}, 'registry source file inventory differs')
    for name, checksum in expected.items():
        require(file_digest(actual[name]) == checksum, 'registry source differs from archive')
    if '.cargo-checksum.json' in actual:
        checksum = json.loads(actual['.cargo-checksum.json'].read_bytes())
        require(checksum['package'] == locked_package['checksum'] and checksum['files'] == expected,
                'registry checksum inventory differs from archive')
    return [*actual.values(), archive]


def dependency_inventory(metadata, env, config):
    lock = tomllib.loads((ROOT / 'Cargo.lock').read_text())
    locked = {(row['name'], row['version'], row.get('source')): row for row in lock['package']}
    features = {row['id']: row['features'] for row in metadata['resolve']['nodes']}
    packages = []
    for package in metadata['packages']:
        manifest = Path(package['manifest_path']).resolve(strict=True)
        base = manifest.parent
        locked_package = locked[(package['name'], package['version'], package.get('source'))]
        if package.get('source'):
            require(package['source'].startswith('registry+'), 'unreviewed non-registry external dependency')
            paths = registry_files(base, locked_package)
        else:
            require(base.is_relative_to(ROOT / 'crates'), 'path dependency escapes frozen workspace crates')
            paths = [p for p in base.rglob('*') if p.is_file()]
        require(manifest in paths and paths, 'dependency inventory lacks its manifest')
        packages.append(dict(id=package['id'], name=package['name'], version=package['version'],
            source=package.get('source'), manifest_path=str(manifest), features=features[package['id']],
            lock=locked_package, files=[file_identity(p) for p in sorted(paths)]))
    require({p['id'] for p in packages} == set(features), 'dependency resolver/inventory differs')
    config['environment_overrides'] = env
    return dict(lock_sha256=file_digest(ROOT / 'Cargo.lock'), metadata_payload='provenance/cargo-metadata.json',
                packages=packages, configuration=config)


def unchanged(records):
    for record in records:
        require(file_identity(Path(record['path'])) == record, 'qualified input changed: ' + record['path'])


def fixture_payloads(work, payload):
    fixtures = work / 'fixtures'
    roots = list(fixtures.glob('test_*-*'))
    require(len(roots) == 3 and all(root.is_dir() for root in roots), 'real fixture histories were not retained')
    for root in roots:
        require((root / 'commands.jsonl').is_file() and (root / 'macro-invocations.jsonl').is_file(),
                'real history lacks exact command records')
        # Retain inputs and textual receipts, without recursively copying Cargo
        # targets or compiled native/VM artifacts into versioned provenance.
        for directory, subdirs, names in os.walk(root):
            subdirs[:] = [name for name in subdirs if not name.startswith('target')
                          and name not in ('debug', 'release', 'incremental', '.fingerprint')]
            for name in names:
                path = Path(directory) / name
                if path.suffix not in ('.json', '.jsonl', '.rs', '.toml', '.py', '.txt') and name != 'Cargo.lock':continue
                require(not path.is_symlink(), 'fixture provenance follows a symlink')
                put(payload, 'provenance/fixtures/' + str(path.relative_to(fixtures)), path.read_bytes())


def execute(plan_path):
    plan = json.loads(plan_path.read_bytes())
    policy = plan.get('qualification_policy')
    require(plan['owner'] == str(ROOT), 'public build plan belongs to another owner')
    if policy != WORKER_BUILD_POLICY:
        require(policy is None and plan['source_input_key'] ==
            'f77229fac75b617de4cc760a8e509015e48e7442462f4276c250c7d4e382e23a', 'wrong macro production source plan')
    require(plan['publication']['composition_kind'] == 'qualified-public-toolset-v1', 'wrong publication contract')
    rustc_path = plan['clean_environment']['overrides']['RUSTC']
    planned_commands(plan, dict(rustc_path=rustc_path), dict(path=str(Path(rustc_path).with_name('cargo'))), policy)
    with build_admission(plan) as work:
        payload = work / 'payload'; payload.mkdir()
        metadata_work = work / 'metadata'; metadata_work.mkdir()
        frozen_sources(plan_path, plan, payload)
        environment = command_environment(plan, {}, os.environ)
        config = configuration(environment)
        source_check = ['git', 'diff', '--exit-code', plan['production_source_revision'], '--',
                        'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', 'crates']
        retained_command(source_check, cwd=ROOT, env=environment, directory=metadata_work, label='production-source')
        retain_command(payload, metadata_work, 'production-source')
        retained_command(['git', 'rev-parse', 'HEAD'], cwd=ROOT, env=environment,
                         directory=metadata_work, label='harness-revision')
        retain_command(payload, metadata_work, 'harness-revision')
        sysroot = Path(environment['RUSTC']).parent.parent
        require(sysroot.name == TOOLCHAIN, 'tool build does not select the pinned public compiler')
        compiler_inputs = compiler_inventory(sysroot)
        put_json(payload, 'provenance/compiler-inputs.json', compiler_inputs)
        cargo = sysroot / 'bin/cargo'
        metadata_argv = [str(cargo), 'metadata', '--locked', '--offline', '--format-version=1',
                         '--manifest-path', str(ROOT / 'Cargo.toml')]
        metadata_stdout, _ = retained_command(metadata_argv, cwd=ROOT, env=environment,
                                               directory=metadata_work, label='cargo-metadata')
        retain_command(payload, metadata_work, 'cargo-metadata')
        metadata = json.loads(metadata_stdout)
        put(payload, 'provenance/cargo-metadata.json', metadata_stdout.encode())
        dependencies = dependency_inventory(metadata, plan['clean_environment']['overrides'], config)
        put_json(payload, 'provenance/dependencies.json', dependencies)
        subjects = {name: capture_library_closure(sysroot / 'bin' / name, 'aarch64-apple-darwin',
            receipt_directory=metadata_work, env=environment, label='closure-' + name) for name in ('rustc', 'cargo')}
        qualified_binaries = None

        def after(command, stdout, stderr):
            nonlocal qualified_binaries
            if command['label'] == 'public-rustc-identity':
                require('commit-hash: ' + COMPILER_REVISION + '\n' in stdout
                        and stdout == plan['shared_std']['identity']['compiler'],
                        'compiler identity differs before any tool build')
            if command['label'] == 'release-tools':
                qualified_binaries = {name: file_digest(Path(path)) for name, path in plan['publication']['source_binaries'].items()}
            for suffix, kind in [('-process.json', 'receipts'), ('.stdout', 'logs'), ('.stderr', 'logs')]:
                put(payload, f"provenance/{kind}/{command['label']}{suffix}",
                    (work / (command['label'] + suffix)).read_bytes())

        commands = run_plan_commands(plan, inherited=os.environ, after_command=after)
        put_json(payload, 'provenance/commands.json', commands)
        require(qualified_binaries is not None, 'release tools were not captured')
        unchanged(compiler_inputs['files'])
        unchanged([r for package in dependencies['packages'] for r in package['files']])
        unchanged(config['files'])
        require({**configuration(environment), 'environment_overrides': plan['clean_environment']['overrides']} == config,
                'effective Cargo configuration changed during qualification')
        for name, path in plan['publication']['source_binaries'].items():
            subjects[name] = capture_library_closure(Path(path), 'aarch64-apple-darwin',
                receipt_directory=metadata_work, env=environment, label='closure-' + name)
        for name in ('rustc', 'cargo'):
            require(file_identity(sysroot / 'bin' / name) == subjects[name]['executable'], 'compiler/Cargo changed')
        # Every inspector receipt is retained exactly; metadata was already copied.
        for receipt in sorted(metadata_work.glob('closure-*-process.json')):
            retain_command(payload, metadata_work, receipt.name.removesuffix('-process.json'))
        put_json(payload, 'provenance/libraries.json', dict(schema_version=1, subjects=subjects))
        put_json(payload, 'provenance/platform.json', subjects['rustc']['identity']['platform'])
        if policy is None:fixture_payloads(work, payload)
        rust_version = (work / 'public-rustc-identity.stdout').read_bytes()
        require(('commit-hash: ' + COMPILER_REVISION + '\n').encode() in rust_version, 'public compiler commit differs')
        compiler = dict(toolchain=TOOLCHAIN, target='aarch64-apple-darwin', source_revision=COMPILER_REVISION,
            sysroot=str(sysroot), rustc_path=str(sysroot / 'bin/rustc'), rustc_sha256=file_digest(sysroot / 'bin/rustc'),
            version_stdout_sha256=sha(rust_version), input_inventory_sha256=file_digest(payload / 'provenance/compiler-inputs.json'))
        cargo_identity = dict(path=str(cargo), binary_sha256=file_digest(cargo),
                             version_stdout_sha256=file_digest(work / 'public-cargo-identity.stdout'))
        composition = compose_qualified_tools(payload, public_compiler=compiler, public_cargo=cargo_identity,
                                               qualified_binaries=qualified_binaries)
        write_json(work / 'composition.json', composition)
        publication = immutable_publish(composition, payload, plan['publication']['source_binaries'],
                                        [ROOT, Path(plan['screen_owner'])])
        write_json(work / 'published.json', publication)
        status = 'public-build-published-worker-qualification-pending' if policy == WORKER_BUILD_POLICY else 'qualified-and-published'
        entry = ROOT / 'experiments/frontend-workers/build.py' if policy == WORKER_BUILD_POLICY else Path(__file__).resolve()
        write_json(work / 'result.json', dict(status=status, source_input_key=plan['source_input_key'],
            tool_key=publication['tool_key'], commands=len(commands), publication=publication,
            materialize_argv=[sys.executable, str(entry), '--plan', str(plan_path),
                              '--materialize', str(work / 'published.json')],
            performance_claim=False, screen_executed=False,
            qualification_argv=([sys.executable, str(entry), '--plan', str(plan_path), '--qualify', str(work / 'published.json')]
                if policy == WORKER_BUILD_POLICY else None),
            pending='integrate exact source/harness; worker build additionally requires external30 qualification before screen'
                if policy == WORKER_BUILD_POLICY else 'integrate exact screen harness and prepare owned source, then materialize'))
        print(json.dumps(dict(status=status, tool_key=publication['tool_key'],
                              publication=str(work / 'published.json'), screen_executed=False)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--materialize', type=Path, metavar='PUBLISHED_JSON',
                        help='only validate published tools and write the planned screen command; never execute it')
    args = parser.parse_args()
    plan_path = args.plan.resolve(strict=True)
    if args.materialize:
        plan = json.loads(plan_path.read_bytes())
        publication = json.loads(args.materialize.read_bytes())
        # Hashing the installed input set is setup work; share the canonical
        # lock even though this mode launches no compiler or benchmark.
        from compare_saved_runtime import acquire_lock
        with Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock').open('a') as lock:
            acquire_lock(lock, 45)
            result = materialize_screen_command(plan, publication, output=plan['screen_request']['materialize_to'])
        print(json.dumps(result))
    else:
        execute(plan_path)


if __name__ == '__main__':
    main()
