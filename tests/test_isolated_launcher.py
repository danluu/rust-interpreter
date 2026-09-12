import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import interpreter


class IsolatedLauncherValidation(unittest.TestCase):
    def rejected(self, arguments):
        with patch.object(sys, 'argv', ['interpreter.py', '--package', 'fixture', *arguments]), \
                patch.object(interpreter, 'checked_tools') as tools, \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            interpreter.main()
        self.assertEqual(error.exception.code, 2)
        tools.assert_not_called()

    def test_incompatible_suite_selection_is_rejected_before_tools_or_cargo(self):
        base = ['--entry', 'first', '--entry', 'second', '--test-body', '--engine', 'jit', '--jit-resumable-calls']
        with tempfile.TemporaryDirectory() as directory:
            report = str(Path(directory) / 'report.json')
            pair = ['--isolated-batch', 'prepared', '--suite-report', report]
            cases = [base + pair[:-2], base + pair[2:], base + pair + ['--engine', 'interpreter'],
                     base + pair + ['--jit-native-calls'],
                     ['--entry', 'first', '--test-body', '--engine', 'jit', '--jit-resumable-calls', *pair],
                     base + pair + ['--', '7']]
            for arguments in cases:
                with self.subTest(arguments=arguments): self.rejected(arguments)
            self.assertFalse(Path(report).exists())

    def test_existing_or_dangling_report_paths_are_preserved_before_building(self):
        base = ['--entry', 'first', '--entry', 'second', '--test-body', '--engine', 'jit', '--jit-resumable-calls',
                '--isolated-batch', 'prepared', '--suite-report']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / 'existing.json'; existing.write_bytes(b'prior evidence')
            dangling = root / 'dangling.json'; destination = root / 'not-created.json'; dangling.symlink_to(destination)
            for path in [existing, dangling, root / 'missing-directory/report.json']:
                with self.subTest(path=path): self.rejected(base + [str(path)])
            self.assertEqual(existing.read_bytes(), b'prior evidence')
            self.assertTrue(dangling.is_symlink()); self.assertFalse(destination.exists())


if __name__ == '__main__':
    unittest.main()
