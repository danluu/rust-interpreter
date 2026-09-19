"""Standalone std CLI routes select only their requested installers before setup."""
import builtins
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import std_mir as std


class StdMirSelectionTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        (self.root / 'benchmarks').mkdir()
        (self.root / 'benchmarks/corpus.json').write_text(
            json.dumps({'toolchain': 'nightly-2026-09-08'}))
        self.stack.enter_context(patch.object(std, 'ROOT', self.root))
        self.events = []
        self.compiler_error = self.cargo_error = self.setup_error = None
        self.compiler = SimpleNamespace(key='a' * 64)
        self.cargo = SimpleNamespace(key='b' * 64)
        self.prepared = (self.root / 'prepared/sysroot', 'aarch64-apple-darwin', 'c' * 64,
                         {'setup_seconds': 3, 'build_seconds': 2, 'metadata_bytes': 640})

        def load_compiler(root, key):
            self.events.append('load:compiler')
            if self.compiler_error is not None:
                raise self.compiler_error
            return self.compiler

        def load_cargo(root, key):
            self.events.append('load:cargo')
            if self.cargo_error is not None:
                raise self.cargo_error
            return self.cargo

        def checked(*args, **kwargs):
            self.events.append('checked_std_mir')
            if self.setup_error is not None:
                raise self.setup_error
            return self.prepared

        compiler_module = ModuleType('custom_compiler')
        cargo_module = ModuleType('custom_cargo')
        self.load_compiler = compiler_module.load_compiler = Mock(side_effect=load_compiler)
        self.load_cargo = cargo_module.load_cargo = Mock(side_effect=load_cargo)
        self.stack.enter_context(patch.dict(sys.modules, custom_compiler=compiler_module,
                                           custom_cargo=cargo_module))
        self.checked = self.stack.enter_context(patch.object(std, 'checked_std_mir', side_effect=checked))
        # Every setup/installer boundary above is fake; accidental real children fail.
        self.stack.enter_context(patch.object(std.subprocess, 'Popen',
            side_effect=AssertionError('std selection tests must not start a child')))
        self.stack.enter_context(patch.object(std.subprocess, 'run',
            side_effect=AssertionError('std selection tests must not run a child')))

    def launch(self, *selection, allowed=()):
        original_import = builtins.__import__
        output = io.StringIO()

        def importing(name, globals=None, locals=None, fromlist=(), level=0):
            if name in ('custom_compiler', 'custom_cargo'):
                self.events.append('import:' + name)
                if name not in allowed:
                    raise AssertionError('unselected installer imported: ' + name)
            return original_import(name, globals, locals, fromlist, level)

        with patch.object(sys, 'argv', ['std_mir.py', *selection]), \
             patch.object(builtins, '__import__', side_effect=importing), \
             redirect_stdout(output), redirect_stderr(io.StringIO()):
            std.main()
        return json.loads(output.getvalue())

    def assert_report(self, report):
        self.assertEqual(report, dict(sysroot=str(self.prepared[0]), target=self.prepared[1],
            key=self.prepared[2], setup_seconds=3, build_seconds=2, metadata_bytes=640))
        self.assertFalse((self.root / '.work').exists())

    def test_stock_cli_skips_unselected_installers_and_preserves_setup_and_report(self):
        report = self.launch()
        self.load_compiler.assert_not_called()
        self.load_cargo.assert_not_called()
        self.checked.assert_called_once_with('nightly-2026-09-08', fetch=False)
        self.assertEqual(self.events, ['checked_std_mir'])
        self.assert_report(report)

    def test_compiler_only_preserves_namespace_and_does_not_import_cargo_installer(self):
        report = self.launch('--compiler-key', self.compiler.key, '--stable-cgu-partitioning', 'on',
            '--std-mir-policy', 'source-paths-v2', '--std-mir-key', 'd' * 64,
            allowed=('custom_compiler',))
        self.load_compiler.assert_called_once_with(self.root, self.compiler.key)
        self.load_cargo.assert_not_called()
        self.checked.assert_called_once_with('nightly-2026-09-08', fetch=False,
            custom=self.compiler, namespace='stable-cgu:on', policy='source-paths-v2',
            prepared_key='d' * 64)
        self.assertEqual(self.events, ['import:custom_compiler', 'load:compiler', 'checked_std_mir'])
        self.assert_report(report)

    def test_cargo_only_preserves_selection_without_calling_compiler_loader(self):
        report = self.launch('--cargo-key', self.cargo.key, '--fetch', allowed=('custom_cargo',))
        self.load_compiler.assert_not_called()
        self.load_cargo.assert_called_once_with(self.root, self.cargo.key)
        self.checked.assert_called_once_with('nightly-2026-09-08', fetch=True, cargo=self.cargo)
        self.assertEqual(self.events, ['import:custom_cargo', 'load:cargo', 'checked_std_mir'])
        self.assert_report(report)

    def test_both_selected_preserve_import_load_order_and_selected_tools(self):
        report = self.launch('--compiler-key', self.compiler.key, '--cargo-key', self.cargo.key,
                             allowed=('custom_compiler', 'custom_cargo'))
        self.load_compiler.assert_called_once_with(self.root, self.compiler.key)
        self.load_cargo.assert_called_once_with(self.root, self.cargo.key)
        self.checked.assert_called_once_with('nightly-2026-09-08', fetch=False,
            custom=self.compiler, namespace='stable-cgu:off', cargo=self.cargo)
        self.assertEqual(self.events, ['import:custom_compiler', 'import:custom_cargo',
                                      'load:compiler', 'load:cargo', 'checked_std_mir'])
        self.assert_report(report)

    def test_invalid_partition_selection_fails_before_import_loading_or_setup(self):
        with self.assertRaises(SystemExit) as error:
            self.launch('--stable-cgu-partitioning', 'on')
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(self.events, [])
        self.load_compiler.assert_not_called()
        self.load_cargo.assert_not_called()
        self.checked.assert_not_called()

    def test_selected_compiler_failure_preserves_both_imports_and_stops_before_cargo_load(self):
        self.compiler_error = RuntimeError('invalid owned compiler')
        with self.assertRaisesRegex(RuntimeError, '^invalid owned compiler$'):
            self.launch('--compiler-key', '', '--cargo-key', self.cargo.key,
                        allowed=('custom_compiler', 'custom_cargo'))
        self.load_compiler.assert_called_once_with(self.root, '')
        self.load_cargo.assert_not_called()
        self.checked.assert_not_called()
        self.assertEqual(self.events, ['import:custom_compiler', 'import:custom_cargo', 'load:compiler'])

    def test_selected_cargo_failure_does_not_fall_back_or_start_setup(self):
        self.cargo_error = RuntimeError('invalid owned Cargo')
        with self.assertRaisesRegex(RuntimeError, '^invalid owned Cargo$'):
            self.launch('--cargo-key', '', allowed=('custom_cargo',))
        self.load_compiler.assert_not_called()
        self.load_cargo.assert_called_once_with(self.root, '')
        self.checked.assert_not_called()
        self.assertEqual(self.events, ['import:custom_cargo', 'load:cargo'])

    def test_setup_rejection_of_unselected_source_path_policy_propagates_without_fallback(self):
        self.setup_error = RuntimeError('std source-paths-v2 requires an explicit custom compiler')
        with self.assertRaisesRegex(RuntimeError, 'requires an explicit custom compiler'):
            self.launch('--std-mir-policy', 'source-paths-v2', '--std-mir-key', 'd' * 64)
        self.checked.assert_called_once_with('nightly-2026-09-08', fetch=False,
                                             policy='source-paths-v2', prepared_key='d' * 64)
        self.load_compiler.assert_not_called()
        self.load_cargo.assert_not_called()
        self.assertEqual(self.events, ['checked_std_mir'])


if __name__ == '__main__':
    unittest.main()
