"""Synthetic runtime installation controls: no compiler, loader or Cargo execution."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import custom_compiler
import runtime_compiler as runtime

HOST = 'aarch64-apple-darwin'
DRIVER = 'lib/librustc_driver-fixture.dylib'


def thaw(root):
    for directory, dirs, files in os.walk(root):
        Path(directory).chmod(0o755)
        for name in files:
            path = Path(directory) / name
            if not path.is_symlink():
                path.chmod(0o644)


def component(root, role, destination, names):
    files = {}
    for name, executable in names.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = ('synthetic ' + name + '\n').encode()
        path.write_bytes(payload)
        path.chmod(0o755 if executable else 0o644)
        files[name] = dict(sha256=hashlib.sha256(payload).hexdigest(),
                           size=len(payload), mode=0o755 if executable else 0o644)
    result = dict(role=role, root=str(root), destination=destination, files=files, links={})
    if role == 'source':
        result['source_receipt_sha256'] = 'e' * 64
    return result


def specification(root):
    checkout = root / 'checkout'
    checkout.mkdir()
    names = {'bin/rustc': True, 'bin/rustdoc': True, DRIVER: True, 'lib/libLLVM.dylib': True}
    names.update({'lib/rustlib/' + HOST + '/lib/lib' + c + '-fixture.rlib': False
                  for c in runtime.CRATES})
    native = component(root / 'native', 'runtime', '', names)
    for index, name in enumerate(runtime.SOURCE_ROOTS):
        path = Path(native['root']) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(checkout, target_is_directory=True)
        native['links'][name] = dict(text=str(checkout), resolved_target=str(checkout),
            action='replace' if index == 0 else 'omit', reason='explicit synthetic source policy')
    sources = component(root / 'sources', 'source', runtime.SOURCE.rstrip('/'),
                        {name: False for name in runtime.REQUIRED_SOURCES})
    loader = {name: dict(rpaths=[], loads=[['LC_LOAD_DYLIB', '/usr/lib/libSystem.B.dylib']])
              for name in ('bin/rustc', 'bin/rustdoc', DRIVER, 'lib/libLLVM.dylib')}
    for name in ('bin/rustc', 'bin/rustdoc'):
        loader[name] = dict(rpaths=['@loader_path/../lib'],
                            loads=[['LC_LOAD_DYLIB', '@rpath/librustc_driver-fixture.dylib']])
    loader[DRIVER]['loads'].append(['LC_LOAD_DYLIB', '@rpath/libLLVM.dylib'])
    return dict(schema_version=1, loader_policy=runtime.LOADER_POLICY, host=HOST,
                compiler='rustc fixture\ncommit-hash: ' + 'a' * 40 + '\nhost: ' + HOST + '\n',
                unstable_options=runtime.option_proof('    -Z fixture-option=val -- fixture\n'),
                provenance=dict(source_checkout=str(checkout), source_commit='a' * 40,
                    build_receipt_sha256='b' * 64, qualification_receipt_sha256='c' * 64,
                    bootstrap_sha256='d' * 64), components=[native, sources], loader=loader)


def output_for(row):
    commands = [('LC_RPATH', name) for name in row['rpaths']] + row['loads']
    return 'synthetic:\n' + ''.join(
        f'Load command {index}\n cmd {kind}\n '
        f'{"path" if kind == "LC_RPATH" else "name"} {name} (offset 24)\n'
        for index, (kind, name) in enumerate(commands))


class RuntimeCompilerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.addCleanup(thaw, self.root)
        self.spec = specification(self.root)
        self.calls = []

    def run_probe(self, command, environment):
        self.calls.append((command, environment))
        sysroot = self.install_path() / 'sysroot'
        self.assertEqual(environment['RUSTC'], str(sysroot / 'bin/rustc'))
        if command[:2] == ['/usr/bin/otool', '-l']:
            name = str(Path(command[2]).relative_to(sysroot))
            output = output_for(self.spec['loader'][name])
        elif command[1:] == ['-vV']:
            output = self.spec['compiler']
        elif command[1:] == ['--print', 'sysroot']:
            output = str(sysroot) + '\n'
        elif command[1:] == ['-Zhelp']:
            output = self.spec['unstable_options']['output']
        else:
            raise AssertionError(command)
        return dict(returncode=0, stdout=output, stderr='retained synthetic stderr\n')

    def install_path(self):
        return self.root / '.work' / runtime.NAMESPACE / runtime.digest(runtime.identity_for(self.spec))

    def install(self, run=None, guard=None, validator=None):
        with patch.object(runtime.sys, 'platform', 'darwin'):
            return runtime.install_runtime_compiler(self.root, self.spec,
                run=run or self.run_probe, guard=guard or (lambda: None), environment={'PATH': '/bin'},
                validate_before_publication=validator)

    def qualification(self, compiler, **changes):
        record = dict(schema_version=1, status='passed',
            policy=compiler.identity['admission']['prepublication_qualification']['policy'],
            key=compiler.key, owner=str(self.root), sysroot=str(compiler.sysroot),
            source_commit=compiler.identity['provenance']['source_commit'])
        record.update(changes)
        path = self.root / ('qualification-' + compiler.key + '.json')
        path.write_text(json.dumps(record, sort_keys=True) + '\n')
        return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def test_declared_validator_binds_retained_receipt_without_warm_content_reads(self):
        self.spec['prepublication_qualification'] = dict(policy='fixture-source-v1')
        calls = []
        def validate(compiler, environment):
            self.assertFalse((compiler.sysroot.parent / 'ready.json').exists())
            self.assertEqual(self.calls[-1][0][1:], ['-Zhelp'])
            self.assertEqual(environment['RUSTC'], str(compiler.rustc))
            calls.append(self.qualification(compiler))
            return calls[-1]
        compiler = self.install(validator=validate)
        self.assertEqual(len(calls), 1)
        retained = compiler.sysroot.parent / 'qualification.json'
        self.assertEqual(retained.read_bytes(), Path(calls[0]['path']).read_bytes())
        ready = json.loads((compiler.sysroot.parent / 'ready.json').read_text())
        self.assertEqual(ready['prepublication_qualification']['sha256'], calls[0]['sha256'])
        self.assertEqual(ready['prepublication_qualification']['stamp'], runtime.stamp(retained.lstat()))
        self.assertFalse(ready['application_qualified'])
        self.assertNotIn('std_source_paths', compiler.identity['provenance'])
        Path(calls[0]['path']).unlink()  # Lookup uses the retained proof, not external evidence.
        original_open = Path.open
        def guarded_open(path, *args, **kwargs):
            if path == retained:
                raise AssertionError('warm qualification content read')
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', guarded_open), \
             patch.object(runtime, 'qualification_record', side_effect=AssertionError('proof reread')):
            self.assertEqual(runtime.load_runtime_compiler(self.root, compiler.key), compiler)

    def test_validator_declaration_is_keyed_and_required_before_input_work(self):
        original = runtime.digest(runtime.identity_for(self.spec))
        self.spec['prepublication_qualification'] = dict(policy='fixture-source-v1')
        self.assertNotEqual(runtime.digest(runtime.identity_for(self.spec)), original)
        with patch.object(runtime, 'inspect_component', side_effect=AssertionError('input read')):
            with self.assertRaisesRegex(RuntimeError, 'explicit validator'):
                self.install()
            del self.spec['prepublication_qualification']
            with self.assertRaisesRegex(RuntimeError, 'explicit validator'):
                self.install(validator=lambda *_: None)
        self.assertFalse(self.calls)
        self.assertFalse((self.root / '.work').exists())

    def test_validator_failure_and_wrong_runtime_receipt_prevent_ready(self):
        for kind in ('raises', 'key', 'source', 'status'):
            self.spec['prepublication_qualification'] = dict(policy='fixture-' + kind)
            def validate(compiler, environment):
                if kind == 'raises':
                    raise RuntimeError('actual qualification failed')
                changes = {'key': {'key': '0' * 64}, 'source': {'source_commit': 'f' * 40},
                           'status': {'status': 'failed'}}[kind]
                return self.qualification(compiler, **changes)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                self.install(validator=validate)
            self.assertFalse((self.install_path() / 'ready.json').exists())
            self.assertTrue((self.install_path() / 'failure.json').is_file())

    def test_validator_output_input_and_nested_identity_mutations_prevent_ready(self):
        source = self.root / 'native/bin/rustc'
        original = source.read_bytes()
        for kind in ('output', 'input', 'identity'):
            self.spec['prepublication_qualification'] = dict(policy='fixture-' + kind)
            def validate(compiler, environment):
                reference = self.qualification(compiler)
                if kind == 'identity':
                    compiler.identity['provenance']['source_commit'] = 'f' * 40
                elif kind == 'input':
                    source.write_bytes(b'changed input')
                else:
                    (compiler.sysroot / DRIVER).write_bytes(b'changed installed output')
                return reference
            try:
                with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                    self.install(validator=validate)
                self.assertFalse((self.install_path() / 'ready.json').exists())
                self.assertTrue((self.install_path() / 'failure.json').is_file())
            finally:
                source.write_bytes(original)

    def test_qualification_copy_corruption_is_rejected_before_ready(self):
        self.spec['prepublication_qualification'] = dict(policy='fixture-copy-readback')
        original_transfer = runtime.transfer
        def altered(path, row, expected_stamp, guard, destination=None):
            original_transfer(path, row, expected_stamp, guard, destination)
            if destination is not None and destination.name == 'qualification.json':
                destination.chmod(0o644)
                destination.write_bytes(b'corrupted receipt after transfer')
                destination.chmod(0o444)
        with patch.object(runtime, 'transfer', altered), self.assertRaisesRegex(RuntimeError, 'receipt bytes'):
            self.install(validator=lambda compiler, _: self.qualification(compiler))
        self.assertFalse((self.install_path() / 'ready.json').exists())
        self.assertTrue((self.install_path() / 'failure.json').is_file())

    def test_qualification_same_size_restored_mtime_mutation_invalidates_lookup(self):
        self.spec['prepublication_qualification'] = dict(policy='fixture-receipt-mutation')
        compiler = self.install(validator=lambda compiler, _: self.qualification(compiler))
        retained = compiler.sysroot.parent / 'qualification.json'
        original = retained.stat()
        payload = retained.read_bytes()
        changed = payload.replace(b'"passed"', b'"failed"')
        self.assertNotEqual(payload, changed)
        self.assertEqual(len(payload), len(changed))
        retained.chmod(0o644); retained.write_bytes(changed); retained.chmod(0o444)
        os.utime(retained, ns=(original.st_atime_ns, original.st_mtime_ns))
        self.assertEqual(retained.stat().st_size, original.st_size)
        self.assertEqual(retained.stat().st_mtime_ns, original.st_mtime_ns)
        with self.assertRaisesRegex(RuntimeError, 'qualification receipt changed'):
            runtime.load_runtime_compiler(self.root, compiler.key)

    def test_final_root_sources_no_private_metadata_and_no_lookup_workload(self):
        compiler = self.install()
        self.assertEqual(compiler.sysroot, self.install_path() / 'sysroot')
        self.assertFalse(any(p.is_symlink() for p in compiler.sysroot.rglob('*')))
        self.assertFalse((compiler.sysroot / runtime.SOURCE_ROOTS[1]).exists())
        self.assertEqual((compiler.sysroot / runtime.SOURCE / 'core/src/lib.rs').read_bytes(),
                         (self.root / 'sources/core/src/lib.rs').read_bytes())
        with self.assertRaisesRegex(RuntimeError, 'missing .*rust-objcopy'):
            custom_compiler.require_complete(compiler.identity['files'], HOST)
        for name in compiler.identity['files']:
            self.assertEqual((compiler.sysroot / name).stat().st_nlink, 1)
        with patch.object(runtime, 'transfer', side_effect=AssertionError('content read')), \
             patch.object(runtime, 'inspect_component', side_effect=AssertionError('origin inspection')):
            self.assertEqual(runtime.load_runtime_compiler(self.root, compiler.key), compiler)
            self.assertIs(compiler.revalidate(self.root), compiler)
        compiler.require_option('fixture-option')
        with self.assertRaisesRegex(RuntimeError, 'no recorded'):
            compiler.require_option('unrecorded-option')
        self.assertTrue(all('/.install-' not in str(argv) for argv, _ in self.calls))
        self.assertFalse(json.loads((compiler.sysroot.parent / 'ready.json').read_text())['application_qualified'])

    def test_source_links_wrong_target_unlisted_link_and_omission_contents_rejected(self):
        native = self.root / 'native'
        link = native / runtime.SOURCE_ROOTS[0]
        other = self.root / 'other'; other.mkdir()
        link.unlink(); link.symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'source-link identity'):
            self.install()
        self.assertFalse(self.calls)
        self.assertFalse(self.install_path().exists())
        link.unlink(); link.symlink_to(self.root / 'checkout', target_is_directory=True)
        (native / 'unlisted').symlink_to(other)
        with self.assertRaisesRegex(RuntimeError, 'unexpected component entry'):
            self.install()
        changed = copy.deepcopy(self.spec)
        changed['components'][0]['links'][runtime.SOURCE_ROOTS[0]]['action'] = 'omit'
        with self.assertRaisesRegex(RuntimeError, 'action and provider'):
            runtime.identity_for(changed)

    def test_source_extra_files_and_bad_hash_fail_before_installation(self):
        extra = self.root / 'sources/extra.rs'; extra.write_text('not admitted')
        with self.assertRaisesRegex(RuntimeError, 'inventory differs'):
            self.install()
        extra.unlink()
        self.spec['components'][1]['files']['Cargo.toml']['sha256'] = '0' * 64
        with self.assertRaisesRegex(RuntimeError, 'digest differs'):
            self.install()
        self.assertFalse(self.calls)
        self.assertFalse(self.install_path().exists())

    def test_executable_source_script_is_preserved_and_never_probed_as_native(self):
        path = self.root / 'sources/check.sh'
        payload = b'#!/bin/sh\nexit 0\n'
        path.write_bytes(payload); path.chmod(0o751)
        self.spec['components'][1]['files']['check.sh'] = dict(
            sha256=hashlib.sha256(payload).hexdigest(), size=len(payload), mode=0o751)
        compiler = self.install()
        copied = compiler.sysroot / runtime.SOURCE / 'check.sh'
        self.assertEqual(copied.read_bytes(), payload)
        self.assertEqual(copied.stat().st_mode & 0o777, 0o551)
        self.assertFalse(any(str(copied) in command for command, _ in self.calls))

    def test_component_collision_native_ambiguity_and_stage_claim_rejected(self):
        changed = copy.deepcopy(self.spec)
        changed['components'].append(copy.deepcopy(changed['components'][1]))
        with self.assertRaisesRegex(RuntimeError, 'collision'):
            runtime.identity_for(changed)
        changed = copy.deepcopy(self.spec)
        files = changed['components'][0]['files']
        name = 'lib/rustlib/' + HOST + '/lib/libstd-fixture.rlib'
        files[name.replace('-fixture', '-other')] = copy.deepcopy(files[name])
        with self.assertRaisesRegex(RuntimeError, 'ambiguous native std'):
            runtime.identity_for(changed)
        changed = copy.deepcopy(self.spec)
        changed['provenance']['stage'] = 2
        with self.assertRaisesRegex(RuntimeError, 'must not claim'):
            runtime.identity_for(changed)

    def test_auxiliary_tool_has_its_own_executable_rpath_context(self):
        name = 'lib/rustlib/' + HOST + '/bin/rust-objcopy'
        row = self.spec['components'][0]['files']['bin/rustc'].copy()
        self.spec['components'][0]['files'][name] = row
        self.spec['loader'][name] = dict(rpaths=['@executable_path/../lib'],
                                       loads=[['LC_LOAD_DYLIB', '@rpath/libLLVM.dylib']])
        with self.assertRaisesRegex(RuntimeError, 'rpath dependency'):
            runtime.identity_for(self.spec)
        self.spec['loader'][name]['rpaths'] = ['@executable_path/../../../']
        runtime.identity_for(self.spec)  # resolves to sysroot/lib, containing the exact LLVM image

    def test_loader_rejects_external_missing_ambiguous_and_unknown_edges(self):
        for dependency in ('/old/runtime/libLLVM.dylib', '@loader_path/../../escape.dylib',
                           '@rpath/libMissing.dylib'):
            changed = copy.deepcopy(self.spec)
            changed['loader'][DRIVER]['loads'] = [['LC_LOAD_DYLIB', dependency]]
            with self.subTest(dependency=dependency), self.assertRaises(RuntimeError):
                runtime.identity_for(changed)
        changed = copy.deepcopy(self.spec)
        changed['components'][0]['files']['other/libLLVM.dylib'] = changed['components'][0]['files']['lib/libLLVM.dylib']
        changed['loader']['other/libLLVM.dylib'] = copy.deepcopy(changed['loader']['lib/libLLVM.dylib'])
        changed['loader']['bin/rustc']['rpaths'].append('@loader_path/../other')
        with self.assertRaisesRegex(RuntimeError, 'ambiguous runtime rpath'):
            runtime.identity_for(changed)
        with self.assertRaisesRegex(RuntimeError, 'unknown Mach-O'):
            runtime.macho_commands('Load command 0\n cmd LC_UNKNOWN_DYLIB\n')
        self.assertEqual(runtime.macho_commands('Load command 0\n cmd LC_ID_DYLIB\n'
            ' name /original/self-identity.dylib (offset 24)\n'), dict(rpaths=[], loads=[]))

    def test_actual_loader_mismatch_preserves_incomplete_attempt(self):
        def probe(command, env):
            result = self.run_probe(command, env)
            if command[:2] == ['/usr/bin/otool', '-l']:
                result['stdout'] = output_for(dict(rpaths=[], loads=[['LC_LOAD_DYLIB', '/foreign/image']]))
            return result
        with self.assertRaisesRegex(RuntimeError, 'actual runtime loader'):
            self.install(run=probe)
        directory = self.install_path()
        self.assertTrue((directory / 'failure.json').is_file())
        self.assertFalse((directory / 'ready.json').exists())
        self.assertTrue((directory / 'sysroot/bin/rustc').is_file())
        with self.assertRaisesRegex(RuntimeError, 'already exists'):
            self.install()

    def test_probe_wrong_final_root_cannot_publish(self):
        def wrong(command, env):
            result = self.run_probe(command, env)
            if command[1:] == ['--print', 'sysroot']:
                result['stdout'] = str(self.root / 'native') + '\n'
            return result
        with self.assertRaisesRegex(RuntimeError, 'final-root compiler'):
            self.install(run=wrong)
        self.assertFalse((self.install_path() / 'ready.json').exists())

    def test_output_mutation_during_probe_cannot_publish(self):
        def changed(command, env):
            result = self.run_probe(command, env)
            if command[1:] == ['-Zhelp']:
                (self.install_path() / 'sysroot' / DRIVER).write_bytes(b'changed after loader audit')
            return result
        with self.assertRaisesRegex(RuntimeError, 'files changed during probes'):
            self.install(run=changed)
        self.assertFalse((self.install_path() / 'ready.json').exists())

    def test_destination_corrupted_before_first_stamp_is_rejected_before_probes(self):
        original_stamps = runtime.tree_stamps
        changed = []
        def corrupt_before_first_snapshot(directory):
            if not changed:
                destination = directory / DRIVER
                data = destination.read_bytes()
                destination.write_bytes(bytes([data[0] ^ 1]) + data[1:])
                changed.append(destination)
            return original_stamps(directory)
        with patch.object(runtime, 'tree_stamps', side_effect=corrupt_before_first_snapshot):
            with self.assertRaisesRegex(RuntimeError, 'file digest differs'):
                self.install()
        self.assertEqual(changed, [self.install_path() / 'sysroot' / DRIVER])
        self.assertFalse(self.calls)
        self.assertTrue((self.install_path() / 'failure.json').is_file())
        self.assertFalse((self.install_path() / 'ready.json').exists())

    def test_capacity_failure_during_copy_retains_bytes_and_starts_no_probe(self):
        def guard():
            path = self.install_path() / 'sysroot/bin/rustc'
            if path.exists() and path.stat().st_size:
                raise RuntimeError('synthetic capacity floor')
        with self.assertRaisesRegex(RuntimeError, 'capacity floor'):
            self.install(guard=guard)
        self.assertFalse(self.calls)
        self.assertTrue((self.install_path() / 'failure.json').is_file())
        self.assertFalse((self.install_path() / 'ready.json').exists())

    def test_changed_runtime_bytes_even_with_restored_size_mtime_are_rejected(self):
        compiler = self.install()
        path = compiler.sysroot / DRIVER
        before = path.stat()
        path.chmod(0o644)
        path.write_bytes(b'x' * before.st_size)
        path.chmod(0o555)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.assertRaisesRegex(RuntimeError, 'installation changed'):
            runtime.load_runtime_compiler(self.root, compiler.key)
        with self.assertRaisesRegex(RuntimeError, 'installation changed'):
            compiler.revalidate(self.root)

    def test_forged_probe_options_wrong_owner_and_live_overrides_rejected(self):
        compiler = self.install()
        for env in ({'DYLD_LIBRARY_PATH': '/old'}, {'RUSTC': '/other/rustc'},
                    {'FORCE_RUSTC_VERSION': ''}, {'RUSTC_OVERRIDE_VERSION_STRING': 'anything'},
                    {'RUSTDOC': '/other/rustdoc'}):
            with self.subTest(env=env), self.assertRaises(RuntimeError):
                compiler.environment(env)
        ready = compiler.sysroot.parent / 'ready.json'
        value = json.loads(ready.read_text())
        value['probes']['options'] = runtime.option_proof(' -Z invented=val\n')
        ready.chmod(0o644); ready.write_text(json.dumps(value)); ready.chmod(0o444)
        with self.assertRaisesRegex(RuntimeError, 'probe proof differs'):
            runtime.load_runtime_compiler(self.root, compiler.key)
        value['owner'] = '/another/owner'
        ready.chmod(0o644); ready.write_text(json.dumps(value)); ready.chmod(0o444)
        with self.assertRaisesRegex(RuntimeError, 'ownership or identity'):
            runtime.load_runtime_compiler(self.root, compiler.key)


if __name__ == '__main__':
    unittest.main()
