"""Pure archived provenance validation, with separately requested live guards.

No compiler, Cargo, library inspector or fixture is executed by this module.
The byte reader is the only input to validate_public_tool; archived callers do
not need the build checkout, installed binaries or external dependency files.
"""
import hashlib
import json
import os
from pathlib import Path
import re

from custom_compiler import digest, file_digest, require, valid_key
from custom_cargo_libraries import platform_identity, system_path
from toolchain_lookup import _stamp
from std_mir import POLICY as STD_POLICY, FLAGS as STD_FLAGS

KIND = 'qualified-public-toolset-v1'
GUARD_POLICY = 'qualified-public-input-guard-v1'
BINARIES = ('rust-interp-vm', 'rust-interp-mir-export', 'rust-interp-rustc-wrapper')
SOURCE_REVISION = '01e36c0426afbd61bbfe540af6673a5e7db2f87c'
COMPILER_REVISION = 'cea272fa356e94bd2ee2cadf376630aa0683867a'
TOOLCHAIN = 'nightly-2026-09-08-aarch64-apple-darwin'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def relative(name):
    require(isinstance(name, str) and name and not name.startswith('/')
            and all(p not in ('', '.', '..') for p in name.split('/')),
            'invalid relative provenance path')
    return name


def absolute(name):
    require(isinstance(name, str) and name.startswith('/') and os.path.normpath(name) == name,
            'invalid absolute input path')
    return name


def hashes(value):
    require(isinstance(value, dict) and value and all(valid_key(v) for v in value.values()),
            'invalid hash inventory')


def record_file(record):
    """Validate an archived identity; _stamp layout is shared with live guards."""
    absolute(record['path']); absolute(record['resolved'])
    require(valid_key(record['sha256']) and type(record['bytes']) is int and record['bytes'] >= 0,
            'invalid file identity')
    state = record['stamp']
    require(isinstance(state, list) and len(state) == 10 and state[0] == record['resolved']
            and all(type(v) is int and v >= 0 for v in state[1:]) and state[4] == record['bytes'],
            'invalid file stat identity')


def check_closure(closure):
    """Reconcile retained loader edges without filesystem or dyld access."""
    identity, root = closure['identity'], closure['executable']
    record_file(root)
    require(identity['policy'] == 'macos-dyld-closure-v1', 'unsupported library policy')
    aliases, searches = closure['aliases'], identity['searches']
    require(all(type(v) is bool for v in searches.values()), 'invalid library search proof')
    for name, resolved in aliases.items():
        absolute(name); absolute(resolved)
    require(aliases.get(root['path']) == root['resolved'], 'missing executable resolution')
    libraries = {entry['logical']: entry for entry in identity['libraries']}
    require(len(libraries) == len(identity['libraries']), 'duplicate library identity')
    for name, item in libraries.items():
        absolute(name); absolute(item['resolved'])
        require(valid_key(item['sha256']) and type(item['bytes']) is int and item['bytes'] >= 0
                and aliases.get(name) == item['resolved'], 'invalid library identity')
    visited, used, systems, contexts = set(), set(), set(), set()

    def expanded(token, loader):
        if token.startswith('@loader_path/'):
            return os.path.normpath(str(Path(loader).parent / token[len('@loader_path/'):]))
        if token.startswith('@executable_path/'):
            return os.path.normpath(str(Path(root['resolved']).parent / token[len('@executable_path/'):]))
        return absolute(token)

    def visit(logical, inherited=(), ancestors=()):
        resolved = aliases[logical]
        context = (logical, inherited)
        if context in contexts or resolved in ancestors:
            return
        contexts.add(context)
        require(len(contexts) <= 256, 'excessive library closure')
        name = '$CARGO' if resolved == root['resolved'] else logical
        node = identity['nodes'][name]; visited.add(name)
        rpaths = tuple(expanded(p, resolved) for p in node['rpaths']) + inherited
        for token in node['dependencies']:
            if system_path(token):
                systems.add(token); continue
            if token.startswith('@rpath/'):
                candidates = [os.path.normpath(str(Path(p) / token[len('@rpath/'):])) for p in rpaths]
                require(candidates and not any(system_path(p) for p in candidates), 'unproved runpath')
                available = [p for p in candidates if searches[p]]
                require(available and len({aliases[p] for p in available}) == 1,
                        'ambiguous or unresolved library search')
                target = available[0]
            else:
                target = expanded(token, resolved)
            if system_path(target):
                systems.add(target); continue
            resolved_target = aliases.get(target, target)
            if resolved_target in (root['resolved'], resolved):
                continue
            require(target in libraries and libraries[target]['resolved'] == resolved_target,
                    'unbound non-system library edge')
            used.add(target)
            visit(target, rpaths, (*ancestors, resolved))

    visit(root['path'])
    require(used == set(libraries) and visited == set(identity['nodes'])
            and systems == set(identity['system_libraries']), 'library closure inventory differs')
    require(set(closure['state']['libraries']) == set(libraries)
            and closure['state']['searches'] == searches, 'library closure state differs')
    for name, library in libraries.items():
        record_file(dict(path=name, resolved=library['resolved'], sha256=library['sha256'],
                         bytes=library['bytes'], stamp=closure['state']['libraries'][name]))


def suite_result(label, stdout, stderr):
    """Parse actual test runner output; never infer success from exit zero alone."""
    if label == 'rust-workspace-tests':
        rows = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', stdout)
        require(rows and sum(int(p) for p, _, _ in rows) > 0 and all(int(f) == 0 for _, f, _ in rows),
                'missing successful Rust test suites')
        return dict(suites=[dict(passed=int(p), failed=int(f), ignored=int(i)) for p, f, i in rows],
                    passed=sum(int(p) for p, _, _ in rows), failed=0)
    expected = {'launcher-contracts': 3, 'screen-contracts': 24, 'real-histories': 3}[label]
    matches = re.findall(r'^Ran (\d+) tests? in [\d.]+s$', stderr, re.M)
    require(matches == [str(expected)] and re.search(r'^OK$', stderr, re.M)
            and not re.search(r'\b(skipped|FAILED|ERROR|FAIL:)\b', stderr), 'Python qualification differs')
    return dict(passed=expected, failed=0, skipped=0)


def planned_commands(plan, compiler, cargo):
    """A rekeyed plan cannot replace qualification with a successful no-op."""
    labels = ['public-rustc-identity', 'public-cargo-identity', 'rust-workspace-tests', 'release-tools',
              'launcher-contracts', 'screen-contracts', 'capabilities', 'real-histories']
    require([c['label'] for c in plan['commands']] == labels, 'required qualification commands differ')
    owner = absolute(plan['owner'])
    work = Path(absolute(plan['commands'][0]['receipt'])).parent
    require(work.parent == Path(owner) / '.work', 'qualification work escapes its owner')
    target = work / 'target'
    common = ['--release', '--locked', '--offline', '--jobs', '2', '--target-dir', str(target)]
    expected = [[compiler['rustc_path'], '-vV'], [cargo['path'], '-vV'],
        [cargo['path'], 'test', *common, '--workspace'],
        [cargo['path'], 'build', *common, '-p', 'rust-interp-bytecode', '-p', 'rust-interp-mir-export', '--bins']]
    for index, pattern in [(4, 'test_host_proc_macro_launcher.py'), (5, 'test_strict_warm*screen.py'),
                           (7, 'test_host_proc_macro_native.py')]:
        command = plan['commands'][index]
        absolute(command['argv'][0])
        require(command['argv'][1:] == ['-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern, '-v'],
                'required Python qualification differs')
    expected += [plan['commands'][4]['argv'], plan['commands'][5]['argv'],
                 [str(target / 'release/rust-interp-mir-export'), '--rust-interp-capabilities'],
                 plan['commands'][7]['argv']]
    for command, argv in zip(plan['commands'], expected):
        require(command['argv'] == argv and command['cwd'] == owner, 'required qualification argv differs')
    fixture = plan['commands'][7]['environment_overrides']
    require(fixture['RUST_INTERP_TEST_RUSTC'] == compiler['rustc_path']
            and fixture['RUST_INTERP_TEST_VM'] == str(target / 'release/rust-interp-vm')
            and fixture['RUST_INTERP_TEST_WRAPPER'] == str(target / 'release/rust-interp-rustc-wrapper')
            and fixture['RUST_INTERP_TEST_EXPORTER'] == str(target / 'release/rust-interp-mir-export')
            and fixture['RUST_INTERP_TEST_STD_SYSROOT'] == str(Path(plan['shared_std']['path']).parent / 'sysroot'),
            'real qualification uses different tools or skips VM/std execution')


def validate_public_tool(tool, key, read_bytes):
    """Return reconciled identities using ONLY callback bytes, never live inputs."""
    tool = Path(tool)
    require(tool.is_absolute() and valid_key(key) and tool.name == key, 'invalid public tool location/key')
    try:
        source = json.loads(read_bytes(tool / 'source.json'))
        composition = source['composition']
        require(source['tool_key'] == key == digest(composition) and composition['schema_version'] == 1
                and composition['kind'] == KIND, 'public tool composition differs')
        manifest = composition['payloads']; hashes(manifest)
        require(len(manifest) <= 10000, 'excessive public provenance inventory')
        payload = {}
        for name, expected in manifest.items():
            relative(name)
            require(name.startswith('provenance/'), 'payload escapes provenance directory')
            data = read_bytes(tool / name)
            require(isinstance(data, bytes) and len(data) <= 64 * 1024**2 and sha(data) == expected,
                    'public provenance payload changed: ' + name)
            data.decode('utf-8')  # Saved assessor retains these exact textual bytes.
            payload[name] = data

        def load(name, expected=None):
            if expected is not None:require(manifest[name] == expected, 'bound payload hash differs: ' + name)
            return json.loads(payload[name])

        plan = load('provenance/build-plan.json', composition['build']['plan_sha256'])
        require(plan['schema_version'] == 2 and plan['status'] == 'not-executed'
                and plan['tool_key'] is None and plan['screen_command'] is None, 'wrong qualified build plan')
        inputs = composition['source']
        require(inputs['revision'] == plan['production_source_revision'] == SOURCE_REVISION
                and inputs['files'] == plan['workspace_sources']
                and inputs['ordered_paths'] == plan['source_input_paths']
                and inputs['source_input_key'] == plan['source_input_key'], 'source identity differs')
        hashes(inputs['files'])
        source_hash = hashlib.sha256()
        for name, expected in inputs['files'].items():
            relative(name)
            require(manifest['provenance/source/' + name] == expected, 'source bytes differ')
        require(len(set(inputs['ordered_paths'])) == len(inputs['ordered_paths'])
                and set(inputs['ordered_paths']) == set(plan['tool_sources']), 'source ordering differs')
        for name in inputs['ordered_paths']:
            require(inputs['files'][name] == plan['tool_sources'][name], 'source subset differs')
            source_hash.update(name.encode() + b'\0' + payload['provenance/source/' + name])
        require(source_hash.hexdigest() == inputs['source_input_key'], 'source input key differs')
        harness = load('provenance/harness.json', composition['build']['harness_inventory_sha256'])
        require(all(harness['files'].get(p) == h for p, h in plan['harness'].items()), 'planned harness changed')
        for name, expected in harness['files'].items():
            relative(name)
            require(manifest['provenance/harness/' + name] == expected, 'harness bytes differ')
        contract = plan['publication']['contract']
        require(harness['files'][contract] == plan['publication']['contract_sha256'], 'contract differs')
        binaries = composition['binaries']; hashes(binaries)
        require(set(binaries) == set(BINARIES) and json.loads(read_bytes(tool / 'ready.json')) == binaries,
                'published binaries differ')
        compiler, cargo = composition['public_compiler'], composition['public_cargo']
        require(compiler['toolchain'] == TOOLCHAIN and compiler['target'] == 'aarch64-apple-darwin'
                and compiler['source_revision'] == COMPILER_REVISION == plan['public_compiler_source_revision'],
                'wrong public compiler')
        sysroot = Path(absolute(compiler['sysroot']))
        require(sysroot.name == TOOLCHAIN and compiler['rustc_path'] == str(sysroot / 'bin/rustc')
                and cargo['path'] == str(sysroot / 'bin/cargo'), 'public rustup paths differ')
        planned_commands(plan, compiler, cargo)
        build = composition['build']
        require(build['profile'] == 'release' and build['environment_overrides'] == plan['clean_environment']['overrides']
                and build['environment_overrides']['CARGO_PROFILE_RELEASE_DEBUG'] == '1'
                and build['environment_overrides']['CARGO_INCREMENTAL'] == '0'
                and build['environment_overrides']['RUSTC'] == compiler['rustc_path']
                and build['environment_overrides']['RUSTUP_TOOLCHAIN'] == TOOLCHAIN, 'build settings differ')
        commands = load('provenance/commands.json', build['command_records_sha256'])
        require([r['label'] for r in commands] == [r['label'] for r in plan['commands']], 'qualification command set differs')
        results, outputs = {}, {}
        for expected, actual in zip(plan['commands'], commands):
            require(actual['argv'] == expected['argv'] and actual['cwd'] == expected['cwd'], 'qualification argv differs')
            receipt = load(actual['receipt'])
            env = {**build['environment_overrides'], **expected.get('environment_overrides', {})}
            require(actual['environment_overrides'] == env and receipt['command'] == expected['argv']
                    and receipt['cwd'] == expected['cwd'] and receipt['status'] == 'finished'
                    and receipt['returncode'] == 0 and type(receipt['pid']) is int and receipt['pid'] > 0,
                    'qualification command did not complete successfully')
            stdout, stderr = payload[actual['stdout']], payload[actual['stderr']]
            outputs[actual['label']] = (stdout, stderr)
            if actual['label'] in ('rust-workspace-tests', 'launcher-contracts', 'screen-contracts', 'real-histories'):
                results[actual['label']] = suite_result(actual['label'], stdout.decode(), stderr.decode())
        rust_version = outputs['public-rustc-identity'][0]
        require(sha(rust_version) == compiler['version_stdout_sha256']
                and ('commit-hash: ' + COMPILER_REVISION + '\n').encode() in rust_version
                and b'host: aarch64-apple-darwin\n' in rust_version
                and sha(outputs['public-cargo-identity'][0]) == cargo['version_stdout_sha256'], 'public version output differs')
        raw_capability = outputs['capabilities'][0]
        require(sha(raw_capability) == composition['capability_stdout_sha256'], 'raw capability differs')
        capability = json.loads(raw_capability)
        require(not {'tool_key', 'exporter_sha256'} & capability.keys() and capability['schema_version'] == 1
                and capability['bytecode_version'] == 5 and capability['compiler_sysroot'] == str(sysroot)
                and 'host-proc-macro-opt-v1' in capability['export_options'], 'required capability is missing')
        capability.update(tool_key=key, exporter_sha256=binaries['rust-interp-mir-export'])
        require(json.loads(read_bytes(tool / 'capabilities.json')) == capability, 'capability envelope differs')
        correctness = load('provenance/correctness.json', composition['correctness_receipt_sha256'])
        require(correctness['schema_version'] == 1 and correctness['status'] == 'passed'
                and correctness['source_input_key'] == inputs['source_input_key']
                and correctness['plan_sha256'] == build['plan_sha256'] and correctness['binaries'] == binaries
                and correctness['results'] == results and correctness['commands'] == commands
                and correctness['compiler_identity_sha256'] == digest(compiler)
                and correctness['cargo_identity_sha256'] == digest(cargo)
                and correctness['library_identity_sha256'] == digest(composition['libraries'])
                and correctness['capability_stdout_sha256'] == composition['capability_stdout_sha256']
                and 'tool_key' not in correctness, 'correctness receipt is not bound to this build')
        shared = correctness['shared_std']
        std = load(shared['ready_payload'], shared['ready_sha256'])
        ready_path = Path(absolute(plan['shared_std']['path']))
        std_owner = Path(absolute(std['owner']))
        require(shared['ready_payload'] == 'provenance/std-ready.json' and shared['identity'] == std['identity']
                and shared['key'] == sha(json.dumps(std['identity'], sort_keys=True).encode())
                and shared['key'] == plan['shared_std']['key'] and shared['identity'] == plan['shared_std']['identity']
                and shared['ready_sha256'] == plan['shared_std']['sha256']
                and shared['sysroot'] == str(Path(plan['shared_std']['path']).parent / 'sysroot')
                and std['identity']['compiler'].encode() == rust_version and std['identity']['target'] == compiler['target']
                and not {'compiler_key', 'cargo', 'namespace', 'source_sha256'} & std['identity'].keys()
                and std['identity']['policy'] == STD_POLICY and std['identity']['flags'] == STD_FLAGS
                and valid_key(std['identity']['lock_sha256'])
                and ready_path == std_owner / '.work/std-mir' / shared['key'] / 'ready.json'
                and str(std_owner) == plan['screen_owner'] and std['artifacts'],
                'qualified shared standard library differs')
        std_lib = 'sysroot/lib/rustlib/' + compiler['target'] + '/lib/'
        for crate in ('core', 'alloc', 'std', 'test', 'proc_macro'):
            require(len([name for name in std['artifacts'] if name.startswith(std_lib + 'lib' + crate + '-')
                         and '/' not in name[len(std_lib):] and name.endswith('.rmeta')]) == 1,
                    'qualified std lacks unique metadata for ' + crate)
        compiler_inputs = load('provenance/compiler-inputs.json', compiler['input_inventory_sha256'])
        dependencies = load('provenance/dependencies.json', build['dependency_inventory_sha256'])
        require(dependencies['lock_sha256'] == inputs['files']['Cargo.lock'] and dependencies['packages']
                and dependencies['configuration']['environment_overrides'] == build['environment_overrides'],
                'dependency/configuration inventory differs')
        libraries = load('provenance/libraries.json', composition['libraries']['manifest_sha256'])
        platform = load('provenance/platform.json', composition['libraries']['platform_sha256'])
        require(libraries['schema_version'] == 1 and set(libraries['subjects']) == {'rustc', 'cargo', *BINARIES},
                'library subject set differs')
        records, searches = {}, {}

        def add(record):
            record_file(record)
            require(records.setdefault(record['path'], record) == record, 'conflicting input identity')

        require(compiler_inputs['files'], 'empty compiler input inventory')
        for record in compiler_inputs['files']:add(record)
        for package in dependencies['packages']:
            require(package['files'] and package['name'] and package['version'], 'empty dependency source inventory')
            for record in package['files']:add(record)
        for subject, closure in libraries['subjects'].items():
            check_closure(closure)
            require(closure['identity']['platform'] == platform, 'library platform differs')
            executable = closure['executable']; add(executable)
            expected_hash = compiler['rustc_sha256'] if subject == 'rustc' else cargo['binary_sha256'] if subject == 'cargo' else binaries[subject]
            require(executable['sha256'] == expected_hash, 'library subject binary differs')
            if subject in ('rustc', 'cargo'):
                require(executable['path'] == (compiler['rustc_path'] if subject == 'rustc' else cargo['path']),
                        'library subject path differs')
            for item in closure['identity']['libraries']:
                add(dict(path=item['logical'], resolved=item['resolved'], sha256=item['sha256'], bytes=item['bytes'],
                         stamp=closure['state']['libraries'][item['logical']]))
            for path, exists in closure['identity']['searches'].items():
                require(searches.setdefault(path, exists) == exists, 'conflicting library search identity')
        require(set(shared['files']) == set(std['artifacts']), 'qualified std input set differs')
        for name, proof in std['artifacts'].items():
            relative(name)
            path = str(Path(plan['shared_std']['path']).parent / name)
            record = shared['files'][name]; record_file(record)
            s = record['stamp']
            require(record['path'] == path and record['resolved'] == path
                    and record['sha256'] == proof['sha256']
                    and [s[1], s[2], s[4], s[5]] == proof['stamp'], 'qualified std input differs')
            add(record)
        publication = json.loads(read_bytes(tool / 'publication.json'))
        require(publication['schema_version'] == 1 and publication['tool_key'] == key
                and publication['directory'] == str(tool) and publication['status'] == 'published'
                and publication['owner'] == str(tool.parents[2])
                and set(publication['binaries']) == set(BINARIES), 'publication receipt differs')
        for name, record in publication['binaries'].items():
            require(record['path'] == str(tool / name) and record['resolved'] == record['path']
                    and record['sha256'] == binaries[name], 'published binary identity differs')
            add(record)
        require(records[compiler['rustc_path']]['sha256'] == compiler['rustc_sha256']
                and records[cargo['path']]['sha256'] == cargo['binary_sha256'], 'compiler/Cargo input hash differs')
        return dict(composition=composition, capability=capability, correctness=correctness, libraries=libraries,
                    platform=platform, plan=plan, commands=commands, payload_paths=[tool / n for n in manifest],
                    input_records=records, searches=searches, tool_key=key, tool=str(tool), publication=publication)
    except (KeyError, TypeError, ValueError, AttributeError, UnicodeError) as error:
        raise RuntimeError('invalid qualified public tool provenance: ' + str(error)) from error


def validate_input_guard(validated, guard):
    """Validate saved guard bytes against provenance, without live file access."""
    expected = {path: record['stamp'] for path, record in validated['input_records'].items()}
    require(guard['schema_version'] == 1 and guard['policy'] == GUARD_POLICY
            and guard['tool_key'] == validated['tool_key'] and guard['validation'] in ('sha256', 'stat')
            and guard['platform'] == validated['platform'] and guard['files'] == expected
            and guard['searches'] == validated['searches'], 'public input guard differs from publication')
    return guard


def validate_live_inputs(validated, *, rehash):
    """Explicit live check; no subprocesses. Never called by the saved assessor."""
    require(not any(k.startswith(('LD_', 'DYLD_')) for k in os.environ), 'loader override is unsupported')
    require(platform_identity() == validated['platform'], 'public input platform changed')
    files = {}
    for name, record in validated['input_records'].items():
        path = Path(name); before = _stamp(path)
        require(before == record['stamp'], 'public input identity changed: ' + name)
        if rehash:
            require(file_digest(path) == record['sha256'] and _stamp(path) == before,
                    'public input content changed: ' + name)
        files[name] = before
    searches = {name: Path(name).exists() or Path(name).is_symlink() for name in validated['searches']}
    return validate_input_guard(validated, dict(schema_version=1, policy=GUARD_POLICY,
        tool_key=validated['tool_key'], validation='sha256' if rehash else 'stat',
        platform=validated['platform'], files=files, searches=searches))
