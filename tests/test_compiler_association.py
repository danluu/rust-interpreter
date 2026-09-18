"""Real temporary-manifest association checks; no compiler or Cargo processes."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import compiler_association as association


class CompilerAssociationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.tools = self.root / 'tools'
        self.tools.mkdir()
        self.compiler = SimpleNamespace(key='a' * 64, sysroot=self.root / 'sysroot')
        self.binaries = {'rust-interp-vm': 'e' * 64, 'rust-interp-mir-export': 'f' * 64}
        self.composition = dict(kind=association.TOOL_POLICY, compiler_key=self.compiler.key,
                               compiler_sysroot=str(self.compiler.sysroot), binaries=self.binaries)
        self.key = association.digest(self.composition)

    def publish_manifests(self):
        (self.tools / 'compiler.json').write_text(json.dumps(self.composition))
        (self.tools / 'ready.json').write_text(json.dumps(self.binaries))

    def test_stock_tools_accept_absence_and_reject_a_dangling_association_link(self):
        association.validate_tool_compiler(self.tools, self.key, None)
        (self.tools / 'compiler.json').symlink_to(self.root / 'missing')
        with self.assertRaises(RuntimeError) as caught:
            association.validate_tool_compiler(self.tools, self.key, None)
        self.assertEqual(str(caught.exception), 'custom compiler tools require --compiler-key')

    def test_custom_composition_compiler_and_ready_mismatches_keep_error_order(self):
        self.publish_manifests()
        association.validate_tool_compiler(self.tools, self.key, self.compiler)
        wrong = SimpleNamespace(key='b' * 64, sysroot=self.compiler.sysroot)
        (self.tools / 'ready.json').write_text('{}')
        for key, compiler, message in [
            ('0' * 64, wrong, 'custom tool composition identity mismatch'),
            (self.key, wrong, 'tool was built with a different compiler'),
            (self.key, self.compiler, 'custom tool composition binary mismatch'),
        ]:
            with self.subTest(message=message), self.assertRaises(RuntimeError) as caught:
                association.validate_tool_compiler(self.tools, key, compiler)
            self.assertEqual(str(caught.exception), message)
        self.publish_manifests()
        wrong = SimpleNamespace(key=self.compiler.key, sysroot=self.root / 'other-sysroot')
        with self.assertRaisesRegex(RuntimeError, '^tool was built with a different compiler$'):
            association.validate_tool_compiler(self.tools, self.key, wrong)

    def test_association_manifest_guards_and_parse_read_failures_are_preserved(self):
        path = self.tools / 'compiler.json'
        expected = 'missing or invalid compiler manifest: ' + str(path)
        for form in ('absent', 'directory', 'dangling-link', 'oversized'):
            with self.subTest(form=form):
                if form == 'directory':
                    path.mkdir()
                elif form == 'dangling-link':
                    path.symlink_to(self.root / 'missing')
                elif form == 'oversized':
                    # Sparse size only; the reader must reject before reading.
                    with path.open('wb') as stream:
                        stream.truncate(32 * 1024 * 1024 + 1)
                try:
                    with self.assertRaises(RuntimeError) as caught:
                        association.validate_tool_compiler(self.tools, self.key, self.compiler)
                    self.assertEqual(str(caught.exception), expected)
                finally:
                    if form == 'directory': path.rmdir()
                    elif form != 'absent': path.unlink()
        path.write_text('{')
        with self.assertRaises(RuntimeError) as caught:
            association.validate_tool_compiler(self.tools, self.key, self.compiler)
        self.assertTrue(str(caught.exception).startswith('invalid custom tool compiler association: '))
        self.assertIsInstance(caught.exception.__cause__, json.JSONDecodeError)
        self.publish_manifests()
        with patch.object(Path, 'read_bytes', side_effect=OSError('fixture read failure')):
            with self.assertRaises(RuntimeError) as caught:
                association.validate_tool_compiler(self.tools, self.key, self.compiler)
        self.assertEqual(str(caught.exception),
                         'invalid custom tool compiler association: fixture read failure')


if __name__ == '__main__':
    unittest.main()
