"""Synthetic v2 preparation/rejection contracts; no Cargo or compiler processes."""
from contextlib import ExitStack
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import custom_compiler as custom
import std_mir
import std_mir_source_paths as v2
from verified_std_diagnostics import source_span_text
from workflow_io import write_json

HOST = 'aarch64-apple-darwin'
COMMIT = 'a' * 40
CONFIGURATION = v2.configuration


def thaw(root):
    for path in [root, *root.rglob('*')]:
        if not path.is_symlink():
            path.chmod(0o755 if path.is_dir() else 0o644)


class StdSourcePathsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.addCleanup(thaw, self.root)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(os.environ, {'PATH': '/bin'}, clear=True))
        sysroot = self.root / 'compiler/sysroot'
        for name in v2.REQUIRED_SOURCES:
            path = sysroot / v2.SOURCE / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('éxample source\n')
        sources = v2.tree_files(sysroot / v2.SOURCE)
        files = {v2.SOURCE + p: h for p, h in sources.items()}
        identity = dict(compiler='rustc test\ncommit-hash: ' + COMMIT + '\nhost: ' + HOST + '\n',
            host=HOST, files=files, source_sha256=custom.digest(files),
            provenance=dict(source_commit=COMMIT, std_source_paths=v2.source_capability(COMMIT)))
        self.compiler = custom.Compiler(custom.digest(identity), sysroot, identity)
        self.cargo = dict(executable='/owned/cargo', sha256='b' * 64, toolchain=v2.TOOLCHAIN,
            version='commit-hash: ' + v2.CARGO_COMMIT + '\nhost: ' + HOST + '\n', host=HOST,
            libraries={}, route={})
        self.guard = dict(executable=['unchanged'], libraries={}, route={})
        self.stack.enter_context(patch.object(v2, 'configuration', return_value={}))
        self.stack.enter_context(patch.object(v2, 'cargo_identity', return_value=(self.cargo, self.guard)))
        self.stack.enter_context(patch.object(v2, 'cargo_state', return_value=self.guard))
        self.stack.enter_context(patch.object(v2, 'load_compiler', return_value=self.compiler))
        self.stack.enter_context(patch.object(v2, 'require_space'))
        self.stack.enter_context(patch.object(v2, 'acquire_lock'))
        self.commands = []
        self.bad_probe = False
        self.failed_build = False
        self.stack.enter_context(patch.object(v2, 'capture', side_effect=self.capture))
        self.lock = self.root / 'canonical.lock'
        self.lock.touch()

    def diagnostic(self, sysroot):
        spans = []
        for name in ['core/src/panic.rs', 'std/src/macros.rs']:
            path = sysroot / v2.SOURCE / name
            span = dict(file_name=str(path), byte_start=2, byte_end=3, line_start=1, line_end=1,
                        column_start=2, column_end=3)
            span['text'] = source_span_text(span, path.read_bytes())
            spans.append(span)
        return [dict(level='error', code=dict(code='E0080'), spans=spans)]

    def capture(self, command, *, cwd, env, receipt_path, receipt):
        self.commands.append(command)
        label = receipt['label']
        if label == 'metadata':
            target = Path(command[command.index('--target-dir') + 1]) / HOST / 'release/deps'
            target.mkdir(parents=True)
            for crate in v2.CRATES:
                (target / ('lib' + crate + '-fixture.rmeta')).write_bytes(b'metadata ' + crate.encode())
            code, stderr = (101 if self.failed_build else 0), ''
        else:
            self.assertTrue(label.startswith('probe-'))
            sysroot = Path(command[command.index('--sysroot') + 1])
            diagnostics = self.diagnostic(sysroot)
            if self.bad_probe:
                diagnostics[0]['spans'][0]['text'] = []
            code, stderr = 1, '\n'.join(json.dumps(d) for d in diagnostics)
        write_json(receipt_path, dict(receipt, command=command, cwd=str(cwd), pid=123,
            parent_pid=456, started_at=1.0, finished_at=2.0, status='finished', returncode=code))
        return SimpleNamespace(returncode=code), '', stderr

    def prepare(self, run_id='attempt-one'):
        return v2.prepare(self.root, self.compiler, 'stable-cgu:off', run_id, self.lock, 0)

    def test_typed_prekey_recipe_preserves_flags_root_profile_features_and_two_jobs(self):
        identity = v2.make_identity(self.compiler, self.cargo, 'stable-cgu:off', {})
        serialized = json.dumps(identity)
        self.assertNotIn('std-mir/', serialized)
        work = self.root / '.work/std-mir' / custom.digest(identity)
        command = v2.command_for(identity, work)
        self.assertIn('-Zroot-dir=' + str(work), command)
        self.assertNotIn('-Zroot-dir=' + str(work / 'library'), command)
        self.assertEqual(command[command.index('--jobs') + 1], '2')
        self.assertEqual(command[command.index('--features') + 1], 'backtrace')
        self.assertEqual(identity['flags'], std_mir.FLAGS)
        for flag in ['--release', '--locked', '--offline', '-Ztrim-paths']:
            self.assertIn(flag, command)
        self.assertEqual(identity['virtual_prefix'], '/rustc/' + COMMIT)
        other = v2.make_identity(self.compiler, self.cargo, 'stable-cgu:on', {})
        self.assertNotEqual(custom.digest(identity), custom.digest(other))

    def test_old_unmapped_compiler_and_unreviewed_cargo_are_rejected(self):
        identity = copy.deepcopy(self.compiler.identity)
        del identity['provenance']['std_source_paths']
        with self.assertRaisesRegex(RuntimeError, 'cannot be relabeled'):
            v2.compiler_sources(custom.Compiler(self.compiler.key, self.compiler.sysroot, identity))
        identity['provenance']['std_source_paths'] = v2.source_capability('c' * 40)
        with self.assertRaisesRegex(RuntimeError, 'source-path policy'):
            v2.compiler_sources(custom.Compiler(self.compiler.key, self.compiler.sysroot, identity))
        with self.assertRaisesRegex(RuntimeError, 'Cargo identity'):
            v2.make_identity(self.compiler, self.cargo | {'version': 'unknown'}, 'stable-cgu:off', {})

    def test_conflicting_environment_is_rejected_instead_of_silently_cleared(self):
        for name in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', '__CARGO_RUSTC_BOOTSTRAP_WS_REMAP',
                     'CARGO_PROFILE_RELEASE_TRIM_PATHS', 'CARGO_BUILD_RUSTFLAGS', 'DYLD_LIBRARY_PATH']:
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                v2.validate_environment({name: 'conflicting value'})

    def test_empty_override_presence_cannot_suppress_required_mir_flags(self):
        for name in ['CARGO_ENCODED_RUSTFLAGS', 'RUSTFLAGS', 'CARGO_PROFILE_RELEASE_TRIM_PATHS',
                     'CARGO_BUILD_RUSTFLAGS', '__CARGO_RUSTC_BOOTSTRAP_WS_REMAP', 'DYLD_LIBRARY_PATH']:
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                v2.validate_environment({name: ''})
        for name in ['CARGO_HOME', 'RUSTUP_HOME', 'HOME']:
            for value in ['', 'relative-home']:
                with self.subTest(name=name, value=value), self.assertRaises(RuntimeError):
                    v2.validate_environment({name: value})
        v2.validate_environment({'RUSTC_WRAPPER': '', 'RUSTC_WORKSPACE_WRAPPER': ''})

    def test_inherited_trim_or_rustflags_configuration_is_rejected(self):
        cargo_home = self.root / 'cargo-home'; cargo_home.mkdir()
        config = cargo_home / 'config.toml'
        for payload in ['[profile.release]\ntrim-paths="none"\n',
                        '[build]\nrustflags=["-Zroot-dir=/wrong"]\n']:
            config.write_text(payload)
            with self.assertRaisesRegex(RuntimeError, 'Cargo configuration'):
                CONFIGURATION(self.root, {'CARGO_HOME': str(cargo_home)})

    def test_included_cargo_configuration_is_rejected_before_any_child(self):
        cargo_home = self.root / 'cargo-home'; cargo_home.mkdir()
        included = cargo_home / 'host.toml'
        included.write_text('[host.aarch64-apple-darwin]\nrustflags=["--remap-path-prefix=a=b"]\n')
        config = cargo_home / 'config.toml'
        for payload in ['include="host.toml"\n', 'include=["host.toml"]\n',
                        'include=[{path="host.toml",optional=true}]\n']:
            config.write_text(payload)
            with self.subTest(payload=payload), self.assertRaisesRegex(RuntimeError, 'configuration: include'):
                CONFIGURATION(self.root, {'CARGO_HOME': str(cargo_home)})
        self.assertEqual(self.commands, [])

    def test_missing_published_source_or_extra_sysroot_file_is_rejected(self):
        sysroot, _, key, _ = self.prepare()
        sysroot.chmod(0o755)
        (sysroot / 'unexpected').write_text('extra')
        with self.assertRaisesRegex(RuntimeError, 'tree changed'):
            v2.load(self.root, key, self.compiler, 'stable-cgu:off')
        (sysroot / 'unexpected').unlink()
        source = sysroot / v2.SOURCE / 'core/src/lib.rs'
        source.parent.chmod(0o755)
        source.unlink()
        with self.assertRaisesRegex(RuntimeError, 'tree changed'):
            v2.load(self.root, key, self.compiler, 'stable-cgu:off')

    def test_source_snippets_are_verified_without_rewriting_raw_diagnostics(self):
        records = self.diagnostic(self.compiler.sysroot)
        original = copy.deepcopy(records)
        files = v2.compiler_sources(self.compiler)[1]
        v2.validate_probe(records, self.compiler.sysroot / v2.SOURCE, files)
        self.assertEqual(records, original)
        for change in [{'text': []}, {'byte_start': 1}, {'file_name': 'library/core/src/panic.rs'}]:
            broken = copy.deepcopy(original)
            broken[0]['spans'][0].update(change)
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                v2.validate_probe(broken, self.compiler.sysroot / v2.SOURCE, files)

    def test_preparation_publishes_complete_readonly_sources_and_retains_actual_receipts(self):
        sysroot, _, key, ready = self.prepare()
        self.assertEqual(len(self.commands), 3)
        self.assertFalse(ready['full_presentation_qualified'])
        self.assertEqual(v2.tree_files(sysroot), ready['sysroot_files'])
        loaded = v2.load(self.root, key, self.compiler, 'stable-cgu:off', rehash=True)
        self.assertEqual(loaded[2], key)
        self.assertIn('probe-native.json', ready['evidence_files'])
        with self.assertRaisesRegex(RuntimeError, 'namespace'):
            v2.load(self.root, key, self.compiler, 'stable-cgu:on')
        with patch.object(v2, 'cargo_state', return_value={'changed': True}), \
             self.assertRaisesRegex(RuntimeError, 'Cargo changed'):
            v2.load(self.root, key, self.compiler, 'stable-cgu:off')

    def test_changed_source_same_size_mtime_and_restored_permissions_is_rejected(self):
        sysroot, _, key, _ = self.prepare()
        path = sysroot / v2.SOURCE / 'core/src/lib.rs'
        before = path.stat()
        path.chmod(0o644)
        path.write_bytes(b'X' * before.st_size)
        path.chmod(0o444)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.assertRaisesRegex(RuntimeError, 'tree changed'):
            v2.load(self.root, key, self.compiler, 'stable-cgu:off')

    def test_empty_duplicate_missing_and_escaping_inventories_fail(self):
        identity = v2.make_identity(self.compiler, self.cargo, 'stable-cgu:off', {})
        prefix = 'lib/rustlib/' + HOST + '/lib/'
        metadata = {prefix + 'lib' + crate + '-one.rmeta': 'b' * 64 for crate in v2.CRATES}
        for broken in [{}, metadata | {prefix + 'libcore-two.rmeta': 'b' * 64},
                       {p: h for p, h in metadata.items() if 'libstd-' not in p}]:
            with self.assertRaises(RuntimeError):
                v2.expected_sysroot_files(identity, broken)
        directory = self.root / 'escape'; directory.mkdir()
        (directory / 'link').symlink_to(self.compiler.sysroot)
        with self.assertRaisesRegex(RuntimeError, 'symlink'):
            v2.tree_files(directory)

    def test_failed_native_preflight_and_build_keep_receipts_but_never_publish_ready(self):
        for bad_probe, failed_build, name in [(True, False, 'bad-probe'), (False, True, 'bad-build')]:
            self.bad_probe, self.failed_build = bad_probe, failed_build
            with self.assertRaises(RuntimeError):
                v2.prepare(self.root, self.compiler, 'attempt:' + name, name, self.lock, 0)
            result = json.loads((self.root / '.work' / name / 'result.json').read_text())
            self.assertEqual(result['status'], 'failed')
            self.assertFalse((Path(result['work']) / 'ready.json').exists())
            self.assertGreater(result['commands'], 0)
            self.assertTrue((self.root / '.work' / name / 'probe-native-process.json').exists())

    def test_v1_default_dispatch_is_unchanged_and_v2_requires_explicit_selection(self):
        with patch.object(std_mir, 'ROOT', self.root), \
             patch.object(std_mir, '_checked_std_mir_locked', return_value='legacy') as old:
            self.assertEqual(std_mir.checked_std_mir('anything'), 'legacy')
            old.assert_called_once_with('anything', False, 'fresh', None, None, '', None)
        with patch.object(v2, 'load', return_value='v2') as load:
            stats = {}
            self.assertEqual(std_mir.checked_std_mir(v2.TOOLCHAIN, custom=self.compiler,
                policy=v2.SELECTION, prepared_key='d' * 64, namespace='stable-cgu:on', lookup_stats=stats), 'v2')
            self.assertEqual(stats['outcome'], 'owned-manifest')
            load.assert_called_once()
            for settings in [dict(policy='v1', prepared_key='d' * 64),
                             dict(policy=v2.SELECTION), dict(policy=v2.SELECTION, prepared_key='d' * 64, fetch=True)]:
                with self.assertRaises(RuntimeError):
                    std_mir.checked_std_mir(v2.TOOLCHAIN, custom=self.compiler, **settings)


if __name__ == '__main__':
    unittest.main()
