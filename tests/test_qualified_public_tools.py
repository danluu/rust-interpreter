"""Mocked archived-provenance and owned temporary-file guard boundaries."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import qualified_public_tools as q


def archive(change=None, std_change=None):
    """A complete tiny publication, independent of any installed compiler."""
    data = {}
    def put(name, value):
        data[name] = value if isinstance(value, bytes) else (json.dumps(value, sort_keys=True) + '\n').encode()
        return q.sha(data[name])
    def file(path, value=b'fixture'):
        return dict(path=path, resolved=path, bytes=len(value), sha256=q.sha(value),
                    stamp=[path, 1, 2, 0o100555, len(value), 3, 4, 2, 3, 4])
    owner = '/owned/build'; sysroot = '/public/' + q.TOOLCHAIN
    compiler_version = f'rustc fixture\ncommit-hash: {q.COMPILER_REVISION}\nhost: aarch64-apple-darwin\n'
    std_identity = dict(compiler=compiler_version, target='aarch64-apple-darwin',
                       policy=q.STD_POLICY, flags=q.STD_FLAGS, lock_sha256='1' * 64)
    std_key = q.sha(json.dumps(std_identity, sort_keys=True).encode())
    std_path = '/owned/screen/.work/std-mir/' + std_key
    env = dict(RUSTC=sysroot + '/bin/rustc', RUSTUP_TOOLCHAIN=q.TOOLCHAIN,
               CARGO_PROFILE_RELEASE_DEBUG='1', CARGO_INCREMENTAL='0')
    source_bytes = {'Cargo.toml': b'[workspace]\n', 'Cargo.lock': b'version = 4\n'}
    files = {p: put('provenance/source/' + p, b) for p, b in source_bytes.items()}
    source_key = hashlib.sha256(b''.join(p.encode() + b'\0' + b for p, b in source_bytes.items())).hexdigest()
    contract = 'contract.md'; harness = {contract: put('provenance/harness/' + contract, b'fixture contract\n')}
    binaries = {name: q.sha(name.encode()) for name in q.BINARIES}
    platform = dict(system='Darwin', release='fixture', version='fixture', machine='arm64')
    capability = dict(schema_version=1, bytecode_version=5, compiler_sysroot=sysroot,
                      export_options=['host-proc-macro-opt-v1'])
    labels = ['public-rustc-identity', 'public-cargo-identity', 'rust-workspace-tests', 'release-tools',
              'launcher-contracts', 'screen-contracts', 'capabilities', 'real-histories']
    commands, planned, results = [], [], {}
    work = owner + '/.work/build'; target = work + '/target'
    common = ['--release', '--locked', '--offline', '--jobs', '2', '--target-dir', target]
    for label in labels:
        args = [sysroot + '/bin/rustc', '-vV'] if label == labels[0] else [sysroot + '/bin/cargo', '-vV']
        if label == 'rust-workspace-tests':args = [sysroot + '/bin/cargo', 'test', *common, '--workspace']
        if label == 'release-tools':args = [sysroot + '/bin/cargo', 'build', *common,
            '-p', 'rust-interp-bytecode', '-p', 'rust-interp-mir-export', '--bins']
        if label == 'capabilities':args = [target + '/release/rust-interp-mir-export', '--rust-interp-capabilities']
        patterns = {'launcher-contracts': 'test_host_proc_macro_launcher.py',
                    'screen-contracts': 'test_strict_warm*screen.py', 'real-histories': 'test_host_proc_macro_native.py'}
        if label in patterns:args = ['/python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', patterns[label], '-v']
        expected = dict(label=label, argv=args, cwd=owner, receipt=work + '/' + label + '-process.json')
        if label == 'real-histories':
            expected['environment_overrides'] = dict(RUST_INTERP_TEST_RUSTC=env['RUSTC'],
                RUST_INTERP_TEST_EXPORTER=target + '/release/rust-interp-mir-export',
                RUST_INTERP_TEST_WRAPPER=target + '/release/rust-interp-rustc-wrapper',
                RUST_INTERP_TEST_VM=target + '/release/rust-interp-vm', RUST_INTERP_TEST_STD_SYSROOT=std_path + '/sysroot')
        planned.append(expected)
        receipt = dict(command=args, cwd=owner, pid=10, status='finished', returncode=0)
        stdout, stderr = b'', b''
        if label == 'public-rustc-identity':stdout = compiler_version.encode()
        elif label == 'public-cargo-identity':stdout = b'cargo fixture\n'
        elif label == 'capabilities':stdout = json.dumps(capability).encode() + b'\n'
        elif label == 'rust-workspace-tests':stdout = b'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured;\n'
        elif label in ('launcher-contracts', 'screen-contracts', 'real-histories'):
            count = 24 if label == 'screen-contracts' else 3
            stderr = f'Ran {count} tests in 0.001s\n\nOK\n'.encode()
        if label in ('rust-workspace-tests', 'launcher-contracts', 'screen-contracts', 'real-histories'):
            results[label] = q.suite_result(label, stdout.decode(), stderr.decode())
        names = dict(receipt='provenance/receipts/' + label + '.json',
                     stdout='provenance/logs/' + label + '.stdout', stderr='provenance/logs/' + label + '.stderr')
        put(names['receipt'], receipt); put(names['stdout'], stdout); put(names['stderr'], stderr)
        commands.append(dict(label=label, argv=args, cwd=owner,
            environment_overrides={**env, **expected.get('environment_overrides', {})}, **names))
    std_files = {'sysroot/lib/rustlib/aarch64-apple-darwin/lib/lib' + name + '-fixture.rmeta': None
                 for name in ('core', 'alloc', 'std', 'test', 'proc_macro')}
    std_files = {name: file(std_path + '/' + name) for name in std_files}
    std = dict(owner='/owned/screen', identity=std_identity, artifacts={name:
        dict(sha256=record['sha256'], stamp=[1, 2, record['bytes'], 3]) for name, record in std_files.items()})
    if std_change:std_change(std)
    ready_sha = put('provenance/std-ready.json', std)
    plan = dict(schema_version=2, status='not-executed', owner=owner, screen_owner='/owned/screen', tool_key=None, screen_command=None,
        production_source_revision=q.SOURCE_REVISION, public_compiler_source_revision=q.COMPILER_REVISION,
        workspace_sources=files, tool_sources=files, source_input_paths=list(files), source_input_key=source_key,
        harness=harness, publication=dict(contract=contract, contract_sha256=harness[contract]),
        clean_environment=dict(overrides=env), commands=planned,
        shared_std=dict(path=std_path + '/ready.json', key=std_key, identity=std_identity, sha256=ready_sha))
    compiler = dict(toolchain=q.TOOLCHAIN, target=std_identity['target'], source_revision=q.COMPILER_REVISION,
        sysroot=sysroot, rustc_path=env['RUSTC'], rustc_sha256=q.sha(b'fixture'),
        version_stdout_sha256=q.sha(compiler_version.encode()), input_inventory_sha256=
        put('provenance/compiler-inputs.json', dict(files=[file(env['RUSTC'])])))
    cargo = dict(path=sysroot + '/bin/cargo', binary_sha256=q.sha(b'fixture'),
                 version_stdout_sha256=q.sha(b'cargo fixture\n'))
    closures = {}
    for name in ['rustc', 'cargo', *q.BINARIES]:
        path = sysroot + '/bin/' + name if name in ('rustc', 'cargo') else owner + '/target/release/' + name
        root = file(path, b'fixture' if name in ('rustc', 'cargo') else name.encode())
        closures[name] = dict(executable=root, aliases={path: path},
            identity=dict(policy='macos-dyld-closure-v1', platform=platform, libraries=[], searches={},
                system_libraries=['/usr/lib/libSystem.B.dylib'],
                nodes={'$CARGO': dict(dependencies=['/usr/lib/libSystem.B.dylib'], rpaths=[])}),
            state=dict(libraries={}, searches={}))
    library_binding = dict(manifest_sha256=put('provenance/libraries.json', dict(schema_version=1, subjects=closures)),
                           platform_sha256=put('provenance/platform.json', platform))
    build = dict(profile='release', environment_overrides=env, plan_sha256=put('provenance/build-plan.json', plan),
        command_records_sha256=put('provenance/commands.json', commands),
        harness_inventory_sha256=put('provenance/harness.json', dict(files=harness)),
        dependency_inventory_sha256=put('provenance/dependencies.json', dict(lock_sha256=files['Cargo.lock'],
            packages=[dict(name='fixture', version='1', files=[file('/registry/fixture/src/lib.rs')])],
            configuration=dict(environment_overrides=env))))
    raw_capability_sha = q.sha(data[next(c['stdout'] for c in commands if c['label'] == 'capabilities')])
    correctness = dict(schema_version=1, status='passed', source_input_key=source_key, plan_sha256=build['plan_sha256'],
        binaries=binaries, results=results, commands=commands, compiler_identity_sha256=q.digest(compiler),
        cargo_identity_sha256=q.digest(cargo), library_identity_sha256=q.digest(library_binding),
        capability_stdout_sha256=raw_capability_sha, shared_std=dict(key=std_key, identity=std_identity,
            ready_payload='provenance/std-ready.json', ready_sha256=ready_sha, sysroot=std_path + '/sysroot',
            files=std_files))
    composition = dict(schema_version=1, kind=q.KIND, source=dict(revision=q.SOURCE_REVISION,
        files=files, ordered_paths=list(files), source_input_key=source_key), public_compiler=compiler,
        public_cargo=cargo, build=build, libraries=library_binding, binaries=binaries,
        capability_stdout_sha256=raw_capability_sha,
        correctness_receipt_sha256=put('provenance/correctness.json', correctness))
    if change:change(composition, data)
    composition['payloads'] = {p: q.sha(b) for p, b in data.items()}
    key = q.digest(composition); tool = Path('/owned/screen/.work/interpreter-tools') / key
    put('source.json', dict(tool_key=key, composition=composition))
    put('ready.json', binaries)
    put('capabilities.json', dict(capability, tool_key=key, exporter_sha256=binaries['rust-interp-mir-export']))
    put('publication.json', dict(schema_version=1, status='published', owner='/owned/screen', directory=str(tool),
        tool_key=key, binaries={name: file(str(tool / name), name.encode()) for name in q.BINARIES}))
    return tool, key, data


class PublicToolProvenanceTests(unittest.TestCase):
    def validate(self, fixture):
        tool, key, data = fixture
        return q.validate_public_tool(tool, key, lambda p: data[str(p.relative_to(tool))])

    def test_archive_only_validation_and_guard_completeness(self):
        fixture = archive()
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('live filesystem read')):
            validated = self.validate(fixture)
            guard = dict(schema_version=1, policy=q.GUARD_POLICY, tool_key=fixture[1], validation='stat',
                platform=validated['platform'], files={p: r['stamp'] for p, r in validated['input_records'].items()},
                searches=validated['searches'])
            q.validate_input_guard(validated, guard)
            del guard['files'][next(iter(guard['files']))]
            with self.assertRaises(RuntimeError):q.validate_input_guard(validated, guard)

    def test_rekeyed_wrong_profile_and_failed_qualification_are_rejected(self):
        def wrong_profile(composition, _):composition['build']['profile'] = 'dev'
        with self.assertRaisesRegex(RuntimeError, 'build settings'):
            self.validate(archive(wrong_profile))
        def failed(_, data):
            name = 'provenance/receipts/real-histories.json'
            receipt = json.loads(data[name]); receipt['returncode'] = 1
            data[name] = json.dumps(receipt).encode()
        with self.assertRaisesRegex(RuntimeError, 'did not complete'):
            self.validate(archive(failed))

    def test_missing_payload_and_capability_swap_are_rejected(self):
        fixture = archive(); fixture[2].pop('provenance/source/Cargo.lock')
        with self.assertRaises(RuntimeError):self.validate(fixture)
        fixture = archive(); capability = json.loads(fixture[2]['capabilities.json'])
        capability['exporter_sha256'] = '0' * 64
        fixture[2]['capabilities.json'] = json.dumps(capability).encode()
        with self.assertRaisesRegex(RuntimeError, 'capability envelope'):
            self.validate(fixture)

    def test_rekeyed_incomplete_or_differently_owned_std_is_rejected(self):
        def missing_std(std):
            del std['artifacts'][next(name for name in std['artifacts'] if '/libstd-' in name)]
        with self.assertRaisesRegex(RuntimeError, 'unique metadata for std'):
            self.validate(archive(std_change=missing_std))
        def wrong_owner(std):std['owner'] = '/another/owner'
        with self.assertRaisesRegex(RuntimeError, 'shared standard library'):
            self.validate(archive(std_change=wrong_owner))

    def test_live_library_content_and_symlink_changes_fail_closed(self):
        def file_identity(path):
            state = q._stamp(path)
            return dict(path=str(path), resolved=state[0], bytes=state[4], sha256=q.file_digest(path), stamp=state)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary); first = directory / 'first'; second = directory / 'second'
            first.write_bytes(b'library'); second.write_bytes(b'library')
            link = directory / 'current'; link.symlink_to(first)
            record = file_identity(link)
            validated = dict(tool_key='1' * 64, platform=q.platform_identity(),
                             input_records={str(link): record}, searches={})
            q.validate_live_inputs(validated, rehash=True)
            link.unlink(); link.symlink_to(second)
            with self.assertRaisesRegex(RuntimeError, 'identity changed'):
                q.validate_live_inputs(validated, rehash=False)
            record = file_identity(link); validated['input_records'][str(link)] = record
            second.write_bytes(b'changed')
            with self.assertRaisesRegex(RuntimeError, 'identity changed'):
                q.validate_live_inputs(validated, rehash=True)


if __name__ == '__main__':
    unittest.main()
