"""Explicit CLI namespace selection; compiler installation is tested separately."""
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import runtime_compiler
import std_mir_source_paths as std


class StdRuntimeSelectionTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.compiler = SimpleNamespace(key='a' * 64)
        self.stage2 = self.stack.enter_context(patch.object(std, 'load_compiler', return_value=self.compiler))
        self.runtime = self.stack.enter_context(patch.object(runtime_compiler, 'load_runtime_compiler', return_value=self.compiler))
        self.prepare = self.stack.enter_context(patch.object(std, 'prepare', return_value=(
            Path('/prepared/sysroot'), 'aarch64-apple-darwin', 'b' * 64,
            {'identity': {'policy': std.POLICY}})))

    def launch(self, *selection):
        argv = ['std_mir_source_paths.py', *selection, '--namespace', 'native-runtime',
                '--run-id', 'fixture', '--workload-lock', '/owned/benchmark.lock']
        output = io.StringIO()
        with patch.object(sys, 'argv', argv), redirect_stdout(output), redirect_stderr(io.StringIO()):
            std.main()
        return json.loads(output.getvalue())

    def check_preparation(self):
        self.prepare.assert_called_once_with(std.ROOT, self.compiler, 'native-runtime',
            'fixture', Path('/owned/benchmark.lock'), 600)

    def test_existing_stage2_selection_preserves_loader_and_preparation(self):
        result = self.launch('--compiler-key', self.compiler.key)
        self.stage2.assert_called_once_with(std.ROOT, self.compiler.key)
        self.runtime.assert_not_called()
        self.check_preparation()
        self.assertEqual(result['key'], 'b' * 64)
        self.assertFalse(result['full_presentation_qualified'])

    def test_runtime_selection_uses_only_runtime_namespace_and_same_preparation(self):
        result = self.launch('--runtime-compiler-key', self.compiler.key)
        self.runtime.assert_called_once_with(std.ROOT, self.compiler.key)
        self.stage2.assert_not_called()
        self.check_preparation()
        self.assertEqual(result['policy'], std.POLICY)
        self.assertFalse(result['full_presentation_qualified'])

    def test_missing_or_ambiguous_selection_fails_before_loading_or_preparation(self):
        for selection in [(), ('--compiler-key', 'a' * 64, '--runtime-compiler-key', 'a' * 64)]:
            with self.subTest(selection=selection), self.assertRaises(SystemExit) as error:
                self.launch(*selection)
            self.assertEqual(error.exception.code, 2)
        self.runtime.assert_not_called()
        self.stage2.assert_not_called()
        self.prepare.assert_not_called()

    def test_invalid_runtime_installation_does_not_fall_back_to_stage2(self):
        self.runtime.side_effect = RuntimeError('runtime installation changed')
        with self.assertRaisesRegex(RuntimeError, 'runtime installation changed'):
            self.launch('--runtime-compiler-key', self.compiler.key)
        self.stage2.assert_not_called()
        self.prepare.assert_not_called()

    def test_preparation_failure_is_not_retried_with_another_compiler(self):
        self.prepare.side_effect = RuntimeError('source-path capability missing')
        with self.assertRaisesRegex(RuntimeError, 'source-path capability missing'):
            self.launch('--runtime-compiler-key', self.compiler.key)
        self.runtime.assert_called_once_with(std.ROOT, self.compiler.key)
        self.stage2.assert_not_called()
        self.check_preparation()


if __name__ == '__main__':
    unittest.main()
