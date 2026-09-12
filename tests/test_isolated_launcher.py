import contextlib
import io
import json
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

    def test_worker_counts_require_a_bounded_isolated_suite(self):
        self.rejected(['--entry', 'first', '--suite-workers', '2'])
        with tempfile.TemporaryDirectory() as directory:
            base = ['--entry', 'first', '--entry', 'second', '--test-body', '--engine', 'jit',
                    '--jit-resumable-calls', '--isolated-batch', 'prepared',
                    '--suite-report', str(Path(directory) / 'report.json')]
            for count in ['0', '-1', '65', '1.5']:
                with self.subTest(count=count): self.rejected(base + ['--suite-workers', count])

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

    def test_entry_catalog_cannot_silently_select_different_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact=Path(directory)/'program.rbc';artifact.write_bytes(b'VM checks the exact artifact digest')
            path=Path(str(artifact)+'.entries.json')
            valid=dict(schema_version=1,bytecode_version=5,entries=[dict(name='one'),dict(name='two')])
            path.write_text(json.dumps(valid))
            self.assertEqual(interpreter.selected_entry_catalog(artifact,['one','two']),path)
            for bad in [dict(valid,entries=[dict(name='two'),dict(name='one')]),dict(valid,entries=[]),
                        dict(valid,entries=['one','two']),dict(valid,schema_version=2),[],None]:
                path.write_text(json.dumps(bad))
                with self.subTest(bad=bad),self.assertRaises(RuntimeError):
                    interpreter.selected_entry_catalog(artifact,['one','two'])
            path.write_text('{')
            with self.assertRaises(RuntimeError):interpreter.selected_entry_catalog(artifact,['one','two'])

    def test_catalog_capability_is_bound_to_its_exporter_and_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);key='a'*64;exporter='b'*64
            self.assertFalse(interpreter.entry_catalog_supported(root,key))
            (root/'ready.json').write_text(json.dumps({'rust-interp-mir-export':exporter}))
            caps=dict(schema_version=1,tool_key=key,exporter_sha256=exporter,bytecode_version=5,export_options=['entry-catalog'])
            (root/'capabilities.json').write_text(json.dumps(caps))
            self.assertTrue(interpreter.entry_catalog_supported(root,key))
            (root/'capabilities.json').write_text(json.dumps(dict(caps,exporter_sha256='c'*64)))
            with self.assertRaises(RuntimeError):interpreter.entry_catalog_supported(root,key)


if __name__ == '__main__':
    unittest.main()
