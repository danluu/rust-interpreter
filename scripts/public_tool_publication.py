"""Supervisor primitives for reviewed public-tool builds and immutable publication.

The caller admits its entire operation under the canonical workload lock. No
work starts on import. These functions never start a screen, replace an existing
installation, or infer qualification from the presence of built executables.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import sys
import time

from custom_compiler import digest, file_digest, require
from custom_cargo_libraries import library_closure, platform_identity
from qualified_public_tools import (BINARIES, check_closure, record_file, sha,
    relative, suite_result, validate_live_inputs, validate_public_tool, WORKER_BUILD_POLICY, worker_capability)
from toolchain_lookup import _stamp
from workflow_io import atomic_bytes, capture, require_space, write_json


@contextmanager
def build_admission(plan):
    """Bounded canonical lock and fresh owned work directory for a supervisor."""
    from compare_saved_runtime import acquire_lock
    owner = Path(plan['owner'])
    require(owner.resolve(strict=True) == owner, 'build owner is not an ordinary directory')
    work = Path(plan['commands'][0]['receipt']).parent
    require(work.parent == owner / '.work' and not work.exists() and not work.is_symlink(),
            'build work directory must be new and owned')
    admission = plan['workload_admission']
    require(admission['lock'] == '/Users/danluu/dev/rust-interp/.work/benchmark.lock'
            and 0 < admission['wait_seconds'] <= 1800, 'unexpected workload lock/admission bound')
    with Path(admission['lock']).open('a') as lock:
        acquire_lock(lock, admission['wait_seconds'])
        require_space(owner, admission['tool_build_minimum_free_gib'])
        work.parent.mkdir(exist_ok=True)
        require(work.parent.resolve(strict=True) == work.parent, 'build work parent is a symlink')
        work.mkdir()
        receipt = dict(schema_version=1, status='running', pid=os.getpid(), parent_pid=os.getppid(),
                       cwd=os.getcwd(), command=sys.argv, owner=str(owner), started_at=time.time())
        write_json(work / 'supervisor.json', receipt)
        try:
            yield work
        except BaseException as error:
            receipt.update(status='failed', error_type=type(error).__name__, error=str(error))
            raise
        else:
            receipt['status'] = 'supervisor-exited'
        finally:
            receipt['finished_at'] = time.time()
            write_json(work / 'supervisor.json', receipt)


def file_identity(path):
    path = Path(path).absolute()
    before = _stamp(path)
    record = dict(path=str(path), resolved=before[0], bytes=before[4],
                  sha256=file_digest(path), stamp=before)
    require(_stamp(path) == before, 'input changed while capturing identity')
    record_file(record)
    return record


def retained_command(command, *, cwd, env, directory, label):
    """Drain/wait through receipt failures; retain both output streams and exit."""
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink(), 'missing owned receipt directory')
    require(label and all(c.isalnum() or c in '-_' for c in label), 'invalid receipt label')
    for suffix in ('-process.json', '.stdout', '.stderr'):
        path = directory / (label + suffix)
        require(not path.exists() and not path.is_symlink(), 'receipt already exists')
    require_space(directory, 8)
    child, stdout, stderr = capture(list(map(str, command)), cwd=str(cwd), env=env,
        receipt_path=directory / (label + '-process.json'), receipt=dict(label=label))
    # capture has already drained/waited, including on an initial receipt error.
    (directory / (label + '.stdout')).write_text(stdout)
    (directory / (label + '.stderr')).write_text(stderr)
    require(child.returncode == 0, 'qualification command failed: ' + label)
    return stdout, stderr


def command_environment(plan, command, inherited):
    cleaning = plan['clean_environment']
    require(not any(k.startswith(tuple(cleaning['reject_prefixes'])) for k in inherited),
            'unreviewed loader environment')
    env = {k: v for k, v in inherited.items() if k not in cleaning['remove']
           and not k.startswith(tuple(cleaning['remove_prefixes']))}
    env.update(cleaning['overrides']); env.update(command.get('environment_overrides', {}))
    return env


def run_plan_commands(plan, *, inherited, before_command=None, after_command=None):
    """Run the frozen eight commands, under a lock already held by the caller.

    Hooks capture source/tool/dependency identities at the required boundaries.
    They cannot replace or filter the command list. A hook failure stops the
    supervisor; started children have already been waited before after_command.
    """
    require(plan['status'] == 'not-executed' and plan['tool_key'] is None,
            'only an unpublished reviewed plan can execute')
    for label in ('tool_sources', 'workspace_sources', 'harness'):
        for name, expected in plan[label].items():
            path = Path(plan['owner']) / name
            require(not path.is_symlink() and file_digest(path) == expected,
                    'frozen build input differs: ' + str(path))
    records = []
    for command in plan['commands']:
        if before_command:before_command(command)
        directory = Path(command['receipt']).parent
        require(directory == Path(command['stdout']).parent == Path(command['stderr']).parent,
                'command output directory differs')
        stdout, stderr = retained_command(command['argv'], cwd=command['cwd'],
            env=command_environment(plan, command, inherited), directory=directory, label=command['label'])
        records.append(dict(label=command['label'], argv=command['argv'], cwd=command['cwd'],
            environment_overrides={**plan['clean_environment']['overrides'], **command.get('environment_overrides', {})},
            receipt='provenance/receipts/' + command['label'] + '-process.json',
            stdout='provenance/logs/' + command['label'] + '.stdout',
            stderr='provenance/logs/' + command['label'] + '.stderr'))
        if after_command:after_command(command, stdout, stderr)
    return records


def capture_library_closure(executable, host, *, receipt_directory, env, label):
    """Reuse the existing conservative resolver, retaining every otool command."""
    ordinal = 0

    def inspect(command, *, text):
        nonlocal ordinal
        require(text is True and command[0] == '/usr/bin/otool', 'unexpected library inspector')
        current = f'{label}-{ordinal:03}'; ordinal += 1
        stdout, _ = retained_command(command, cwd=str(receipt_directory), env=env,
                                      directory=receipt_directory, label=current)
        return stdout

    before = file_identity(executable)
    identity, state = library_closure(Path(executable), host, inspect=inspect)
    aliases = {before['path']: before['resolved'], before['resolved']: before['resolved']}
    for item in identity['libraries']:
        aliases[item['logical']] = item['resolved']
        aliases[item['resolved']] = item['resolved']
    for path, exists in identity['searches'].items():
        if exists:aliases[path] = str(Path(path).resolve(strict=True))
    require(file_identity(executable) == before, 'executable changed during dependency inspection')
    result = dict(executable=before, identity=identity, state=state, aliases=aliases)
    check_closure(result)
    return result


def compose_qualified_tools(payload_root, *, public_compiler, public_cargo, qualified_binaries):
    """Assemble the acyclic receipt/key inputs from already retained evidence.

    The supervisor supplies compiler/Cargo identities and the binary hashes
    captured before real histories. This function rehashes those binaries after
    histories, parses actual test outputs, and binds every retained payload.
    immutable_publish runs the same pure validator before writing readiness.
    """
    root = Path(payload_root).resolve(strict=True)
    def read(name):return json.loads((root / name).read_bytes())
    def hashed(name):return file_digest(root / name)
    plan = read('provenance/build-plan.json')
    commands = read('provenance/commands.json')
    policy = plan.get('qualification_policy')
    results = {}
    for command in commands:
        if command['label'] in ('rust-workspace-tests', 'launcher-contracts', 'screen-contracts', 'real-histories'):
            results[command['label']] = suite_result(command['label'], (root / command['stdout']).read_text(),
                                                    (root / command['stderr']).read_text(), policy)
    require(set(qualified_binaries) == set(BINARIES), 'missing pre-history binary identities')
    binaries = {name: file_digest(Path(path)) for name, path in plan['publication']['source_binaries'].items()}
    require(binaries == qualified_binaries, 'tool binary changed during real histories')
    for section in ('workspace_sources', 'harness'):
        for name, expected in plan[section].items():
            require(file_digest(Path(plan['owner']) / name) == expected, 'build input changed during qualification')
    libraries = dict(manifest_sha256=hashed('provenance/libraries.json'),
                     platform_sha256=hashed('provenance/platform.json'))
    build = dict(plan_sha256=hashed('provenance/build-plan.json'), profile='release',
        environment_overrides=plan['clean_environment']['overrides'],
        command_records_sha256=hashed('provenance/commands.json'),
        dependency_inventory_sha256=hashed('provenance/dependencies.json'),
        harness_inventory_sha256=hashed('provenance/harness.json'))
    capability_command = next(c for c in commands if c['label'] == 'capabilities')
    capability_sha = hashed(capability_command['stdout'])
    ready_path = Path(plan['shared_std']['path'])
    ready = read('provenance/std-ready.json')
    require(file_digest(ready_path) == hashed('provenance/std-ready.json') == plan['shared_std']['sha256'],
            'qualified shared std changed')
    shared_std = dict(key=plan['shared_std']['key'], identity=ready['identity'],
        ready_payload='provenance/std-ready.json', ready_sha256=plan['shared_std']['sha256'],
        sysroot=str(ready_path.parent / 'sysroot'),
        files={name: file_identity(ready_path.parent / name) for name in ready['artifacts']})
    correctness = dict(schema_version=1, status='passed', source_input_key=plan['source_input_key'],
        plan_sha256=build['plan_sha256'], binaries=binaries, compiler_identity_sha256=digest(public_compiler),
        cargo_identity_sha256=digest(public_cargo), library_identity_sha256=digest(libraries),
        capability_stdout_sha256=capability_sha, shared_std=shared_std, results=results, commands=commands)
    if policy == WORKER_BUILD_POLICY:
        correctness.update(qualification_policy=policy, qualification_scope='public-build-only')
    output = root / 'provenance/correctness.json'
    require(not output.exists() and not output.is_symlink(), 'correctness receipt already exists')
    write_json(output, correctness)
    paths = list((root / 'provenance').rglob('*'))
    require(not any(p.is_symlink() for p in paths), 'provenance contains symlinks')
    payloads = {str(p.relative_to(root)): file_digest(p) for p in sorted(paths) if p.is_file()}
    composition = dict(schema_version=1, kind='qualified-public-toolset-v1',
        source=dict(revision=plan['production_source_revision'], source_input_key=plan['source_input_key'],
                    ordered_paths=plan['source_input_paths'], files=plan['workspace_sources']),
        public_compiler=public_compiler, public_cargo=public_cargo, build=build, libraries=libraries,
        binaries=binaries, capability_stdout_sha256=capability_sha,
        correctness_receipt_sha256=payloads['provenance/correctness.json'], payloads=payloads)
    if policy == WORKER_BUILD_POLICY:composition['qualification_policy'] = policy
    return composition


def immutable_publish(composition, payload_root, source_binaries, owners):
    """Publish proved bytes to new destinations; retain failures, never replace.

    The supplied composition and payloads must already contain the complete
    correctness receipt and frozen command/source/input evidence. Readiness is
    synthesized for preflight callback validation and written physically last.
    """
    key = digest(composition)
    payload_root = Path(payload_root).resolve(strict=True)
    owners = [Path(p).resolve(strict=True) for p in owners]
    require(len(set(owners)) == len(owners) and owners, 'publication owners must be distinct')
    require(set(source_binaries) == set(BINARIES), 'publication requires all three binaries')
    for name in composition['payloads']:
        relative(name)
        require(name.startswith('provenance/'), 'publication payload escapes provenance')
    require(composition['libraries']['platform_sha256'] == sha(
        (payload_root / 'provenance/platform.json').read_bytes()), 'platform payload differs')
    require(json.loads((payload_root / 'provenance/platform.json').read_bytes()) == platform_identity(),
            'publication platform differs')
    # The build-path executable closure must remain valid after copying. This
    # initial publisher refuses executable-relative lookups instead of guessing
    # how a new content-keyed installation would resolve them.
    libraries = json.loads((payload_root / 'provenance/libraries.json').read_bytes())
    for name in BINARIES:
        nodes = libraries['subjects'][name]['identity']['nodes']
        require(not any(token.startswith('@executable_path/') for node in nodes.values()
                        for token in [*node['rpaths'], *node['dependencies']])
                and not any(token.startswith('@loader_path/') for token in
                            [*nodes['$CARGO']['rpaths'], *nodes['$CARGO']['dependencies']]),
                'tool copying requires a separately proved relative loader closure')
    destinations = [owner / '.work/interpreter-tools' / key for owner in owners]
    require(all(not p.exists() and not p.is_symlink() for p in destinations), 'publication would replace tools')
    for name, path in source_binaries.items():
        require(file_digest(Path(path)) == composition['binaries'][name], 'source binary differs')
    published = []
    for owner, destination in zip(owners, destinations):
        require_space(owner, 8)
        destination.parent.mkdir(parents=True, exist_ok=True)
        require(destination.parent.resolve(strict=True) == destination.parent, 'installation parent is linked')
        destination.mkdir()
        for name, expected in composition['payloads'].items():
            source = payload_root / name
            require(source.resolve(strict=True).is_relative_to(payload_root) and not source.is_symlink()
                    and source.is_file() and sha(source.read_bytes()) == expected, 'publication payload differs')
            target = destination / name; target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:stream.write(source.read_bytes())
            target.chmod(0o444)
        binary_records = {}
        for name, source in source_binaries.items():
            target = destination / name
            shutil.copyfile(source, target); target.chmod(0o555)
            binary_records[name] = file_identity(target)
        write_json(destination / 'source.json', dict(tool_key=key, composition=composition))
        commands = json.loads((destination / 'provenance/commands.json').read_bytes())
        capability_command = next(c for c in commands if c['label'] == 'capabilities')
        capability = json.loads((destination / capability_command['stdout']).read_bytes())
        if composition.get('qualification_policy') == WORKER_BUILD_POLICY:
            wrapper = next(c for c in commands if c['label'] == 'wrapper-capabilities')
            worker_capability(capability, (destination / wrapper['stdout']).read_bytes(), composition['binaries'])
        capability.update(tool_key=key, exporter_sha256=composition['binaries']['rust-interp-mir-export'])
        write_json(destination / 'capabilities.json', capability)
        publication = dict(schema_version=1, status='published', owner=str(owner), directory=str(destination),
                           tool_key=key, binaries=binary_records)
        write_json(destination / 'publication.json', publication)
        ready = (json.dumps(composition['binaries'], indent=2) + '\n').encode()
        validated = validate_public_tool(destination, key,
            lambda p: ready if p == destination / 'ready.json' else p.read_bytes(),
            qualification_policy=composition.get('qualification_policy'))
        guard = validate_live_inputs(validated, rehash=True)
        write_json(destination / 'publication-guard.json', guard)
        for path in destination.iterdir():
            if path.is_file() and path.name not in BINARIES:path.chmod(0o444)
        require(not (destination / 'ready.json').exists(), 'readiness unexpectedly appeared')
        atomic_bytes(destination / 'ready.json', ready, mode=0o444)
        published.append(dict(owner=str(owner), directory=str(destination), tool_key=key,
                              publication_sha256=sha((destination / 'publication.json').read_bytes())))
    return dict(schema_version=1, status='published', tool_key=key, installations=published)


def materialize_screen_command(plan, publication, *, output):
    """Produce argv only after actual publication; never execute the screen."""
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), 'screen handoff already exists')
    owner = Path(plan['screen_owner']); key = publication['tool_key']
    require(publication['status'] == 'published' and {p['owner'] for p in publication['installations']} ==
            {plan['owner'], plan['screen_owner']}, 'both owned installations are required')
    tool = owner / '.work/interpreter-tools' / key
    validated = validate_public_tool(tool, key, Path.read_bytes, qualification_policy=plan.get('qualification_policy'))
    validate_live_inputs(validated, rehash=True)
    require(validated['plan'] == plan, 'publication belongs to another build plan')
    request = plan['screen_request']
    worker = plan.get('qualification_policy') == WORKER_BUILD_POLICY
    names = ('benchmarks/experiments/strict-warm-build/screen.py',
             'benchmarks/experiments/strict-warm-build/FRONTEND_WORKERS_SCREEN.md' if worker else
             'benchmarks/experiments/strict-warm-build/HOST_PROC_MACRO_OPT.md')
    for name in names:
        require(file_digest(owner / name) == plan['harness'][name], 'screen harness is not integrated')
    require(file_digest(Path(request['std_mir_ready'])) == plan['shared_std']['sha256'], 'shared std changed')
    source = Path(request['source'])
    marker = json.loads((source / '.rust-interp-owned.json').read_bytes())
    require(source.resolve(strict=True) == source and marker == plan['project_preparation']['owner_marker'],
            'source clone is not prepared for this owner')
    argv = [request['python'], request['driver'], '--run-id', request['run_id'], '--source', request['source'],
        '--candidate-policy', request['candidate_policy'], '--baseline-tool-key', key, '--candidate-tool-key', key,
        '--std-mir-ready', request['std_mir_ready'], '--lock-wait-seconds', str(request['lock_wait_seconds'])]
    qualification = None
    if worker:
        from frontend_worker_screen import validate_qualification
        public = validated['composition']['public_compiler']
        shared = plan['shared_std']
        std = dict(shared, rustc=public['rustc_path'], rustc_sha256=public['rustc_sha256'],
                   sysroot=str(Path(shared['path']).parent / 'sysroot'))
        qualification = validate_qualification(plan['worker_qualification']['result'], key, validated, std, Path.read_bytes)
        require(qualification['workload_lock'] == plan['workload_admission']['lock'], 'worker qualification used another lock')
        argv += ['--frontend-worker-qualification', plan['worker_qualification']['result'],
                 '--workload-lock', plan['workload_admission']['lock']]
    result = dict(schema_version=1, status='ready-for-separate-screen-admission', tool_key=key,
                  plan_sha256=validated['composition']['build']['plan_sha256'], publication=publication,
                  argv=argv, workloads_executed=0, performance_claim=False)
    if qualification is not None:result['worker_qualification'] = qualification
    write_json(output, result)
    return result
