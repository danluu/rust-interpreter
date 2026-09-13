"""Prepared compiler-free contracts; actual compiler presentation remains a separate gate."""
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from custom_compiler import Compiler, digest, file_digest
import standard_diagnostic_mapping as mapping
from std_mir_source_paths import REQUIRED_SOURCES, SOURCE, source_capability
from verified_std_diagnostics import source_span_text

HOST = 'aarch64-apple-darwin'
PUBLIC_COMMIT = 'a' * 40
CUSTOM_COMMIT = 'b' * 40


class StandardDiagnosticMappingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.environment = {'PATH': '/bin', 'CARGO_HOME': str(self.root / 'cargo-home')}
        environment_patch = patch.dict(os.environ, self.environment, clear=True)
        environment_patch.start(); self.addCleanup(environment_patch.stop)
        self.fixture = self.root / 'fixture'; self.fixture.mkdir()
        installed = self.root / 'installed'
        for relative in REQUIRED_SOURCES:
            path = installed / SOURCE / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('éxample source\nsecond line\n')
        self.public_library = self.root / 'public' / SOURCE
        self.prepared = {mode: self.root / ('prepared-' + mode) for mode in ['off', 'on']}
        for destination in [self.public_library, *[p / SOURCE for p in self.prepared.values()]]:
            shutil.copytree(installed / SOURCE, destination)
        files = {SOURCE + name: file_digest(installed / SOURCE / name) for name in REQUIRED_SOURCES}
        for name in ['public', 'installed']:
            path = self.root / name / 'bin/rustc'
            path.parent.mkdir(); path.write_bytes((name + ' compiler bytes').encode())
        identity = dict(compiler=self.version(CUSTOM_COMMIT), host=HOST,
            files=files | {'bin/rustc': file_digest(installed / 'bin/rustc')},
            source_sha256=digest(files),
            provenance=dict(source_commit=CUSTOM_COMMIT, std_source_paths=source_capability(CUSTOM_COMMIT)))
        self.compiler = Compiler(digest(identity), installed, identity)
        self.public_compiler = dict(rustc=str(self.root / 'public/bin/rustc'),
            sha256=file_digest(self.root / 'public/bin/rustc'), compiler=self.version(PUBLIC_COMMIT))

    @staticmethod
    def version(commit):
        return 'rustc fixture\ncommit-hash: ' + commit + '\nhost: ' + HOST + '\n'

    def prepare(self):
        return mapping.prepare_standard_diagnostic_mapping(self.fixture, self.compiler,
            self.public_library, self.prepared, self.environment, public_compiler=self.public_compiler)

    def diagnostics(self, configured):
        spans = []
        for relative in ['core/src/panic.rs', 'std/src/macros.rs']:
            span = dict(file_name=configured.namespace + '/' + relative, byte_start=2, byte_end=3,
                line_start=1, line_end=1, column_start=2, column_end=3)
            span['text'] = source_span_text(span, (self.public_library / relative).read_bytes())
            spans.append(span)
        return [dict(level='error', code=dict(code='E0080'), spans=spans[:1],
                     children=[dict(spans=spans[1:])])]

    def test_equal_ordered_diagnostics_only_flags_reach_explicit_host_and_target(self):
        configured = self.prepare()
        config = tomllib.loads(configured.config_path.read_text())
        self.assertFalse(config['target-applies-to-host'])
        self.assertEqual(config['unstable'], {'host-config': True, 'target-applies-to-host': True})
        self.assertEqual(config['host']['rustflags'], configured.rustc_flags)
        self.assertEqual(config['host'][HOST]['rustflags'], configured.rustc_flags)
        self.assertEqual(config['target'][HOST]['rustflags'], configured.rustc_flags)
        self.assertEqual(configured.rustc_flags[0], '--remap-path-scope=diagnostics')
        self.assertEqual(len(configured.rustc_flags), 7)
        for commit in [PUBLIC_COMMIT, CUSTOM_COMMIT]:
            self.assertIn('--remap-path-prefix=/rustc/' + commit + '/library=' + configured.namespace,
                          configured.rustc_flags)
        evidence = configured.evidence()
        self.assertTrue(evidence['actual_compiler_argv_required'])
        self.assertTrue(evidence['correctness_qualification_only'])
        self.assertFalse(evidence['diagnostic_records_rewritten'])

    def test_actual_unicode_nested_spans_pass_unchanged_and_empty_or_wrong_text_fails(self):
        configured = self.prepare()
        original = self.diagnostics(configured)
        saved = copy.deepcopy(original)
        configured.validate_diagnostics(original, require_std=True)
        self.assertEqual(original, saved)
        for update in [{'text': []}, {'byte_start': 1}, {'column_start': 1},
                       {'text': [{'text': 'invented', 'highlight_start': 2, 'highlight_end': 3}]}]:
            broken = copy.deepcopy(original)
            broken[0]['spans'][0].update(update)
            before = copy.deepcopy(broken)
            with self.subTest(update=update), self.assertRaises(RuntimeError):
                configured.validate_diagnostics(broken, require_std=True)
            self.assertEqual(broken, before)
        with self.assertRaisesRegex(RuntimeError, 'complete mapped core and std'):
            configured.validate_diagnostics([], require_std=True)

    def test_unmapped_roots_and_relative_alias_fail_but_application_filename_is_not_remapped(self):
        configured = self.prepare()
        original = self.diagnostics(configured)
        for prefix in [str(self.public_library), str(self.prepared['off'] / SOURCE),
                       '/rustc/' + CUSTOM_COMMIT + '/library', 'library']:
            broken = copy.deepcopy(original)
            broken[0]['spans'][0]['file_name'] = prefix + '/core/src/panic.rs'
            with self.subTest(prefix=prefix), self.assertRaises(RuntimeError):
                configured.validate_diagnostics(broken, require_std=True)
        app = self.fixture / 'core/src/panic.rs'
        app.parent.mkdir(parents=True); app.write_text('application file\n')
        records = [dict(spans=[dict(file_name=str(app), text=[])])]
        before = copy.deepcopy(records)
        configured.validate_diagnostics(records, require_std=False)
        self.assertEqual(records, before)

    def test_full_inventory_equality_includes_unused_files_and_public_identity(self):
        extra = self.prepared['on'] / SOURCE / 'extra.rs'
        extra.write_text('extra file')
        with self.assertRaisesRegex(RuntimeError, 'full standard source inventories differ'):
            self.prepare()
        extra.unlink()
        unused = self.prepared['on'] / SOURCE / 'alloc/src/lib.rs'
        original = unused.read_bytes(); unused.write_bytes(b'x' * len(original))
        with self.assertRaisesRegex(RuntimeError, 'full standard source inventories differ'):
            self.prepare()
        unused.write_bytes(original)
        self.public_compiler['sha256'] = 'c' * 64
        with self.assertRaisesRegex(RuntimeError, 'public compiler bytes'):
            self.prepare()

    def test_competing_empty_flags_configured_loader_and_host_config_fail_before_write(self):
        self.environment['CARGO_ENCODED_RUSTFLAGS'] = ''
        with self.assertRaises(RuntimeError):
            self.prepare()
        del self.environment['CARGO_ENCODED_RUSTFLAGS']
        home = Path(self.environment['CARGO_HOME']); home.mkdir()
        path = home / 'config.toml'
        for content in ['include="other.toml"\n', '[host.' + HOST + ']\nrustflags=[]\n',
                        '[env]\nDYLD_LIBRARY_PATH={value="/foreign",force=true}\n']:
            path.write_text(content)
            with self.subTest(content=content), self.assertRaises(RuntimeError):
                self.prepare()
        self.assertFalse((self.fixture / '.cargo/config.toml').exists())

    def test_existing_fixture_config_is_never_overwritten(self):
        directory = self.fixture / '.cargo'; directory.mkdir()
        path = directory / 'config.toml'; path.write_text('[env]\nBUILD_INPUT="benign"\n')
        before = path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'will not replace'):
            self.prepare()
        self.assertEqual(path.read_bytes(), before)

    def test_config_source_flags_and_environment_mutation_invalidate_mapping(self):
        configured = self.prepare()
        path = self.public_library / 'alloc/src/lib.rs'
        before = path.stat(); original = path.read_bytes()
        path.write_bytes(b'x' * len(original))
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.assertRaisesRegex(RuntimeError, 'source tree changed'):
            configured.recheck()
        # Separate controls do not try to restore an already invalidated object.

    def test_new_inherited_config_and_changed_flag_or_environment_are_rejected(self):
        configured = self.prepare()
        configured.rustc_flags.append('-Zthreads=2')
        with self.assertRaisesRegex(RuntimeError, 'compiler flags changed'):
            configured.recheck()
        configured.rustc_flags.pop()
        self.environment['BUILD_INPUT'] = 'changed'
        with self.assertRaisesRegex(RuntimeError, 'base environment changed'):
            configured.recheck()
        del self.environment['BUILD_INPUT']
        home = Path(self.environment['CARGO_HOME']); home.mkdir()
        (home / 'config.toml').write_text('[env]\nBUILD_INPUT="new"\n')
        with self.assertRaisesRegex(RuntimeError, 'configuration changed'):
            configured.recheck()


if __name__ == '__main__':
    unittest.main()
