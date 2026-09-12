"""Restoration must invalidate builds and preserve recoverable source on errors."""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from workflow_io import SourceEdit


class SourceRestorationTests(unittest.TestCase):
    def test_original_bytes_are_restored_with_a_fresh_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.rs'
            source.write_bytes(b'original')
            with SourceEdit(source, b'original') as edit:
                os.utime(edit.backup, ns=(1, 1))
                edit.replace(b'changed')
                after_build = time.time_ns()
            self.assertEqual(source.read_bytes(), b'original')
            self.assertGreaterEqual(source.stat().st_mtime_ns, after_build)

    def test_timestamp_failure_preserves_original_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.rs'
            source.write_bytes(b'original')
            edit = SourceEdit(source, b'original').__enter__()
            edit.replace(b'changed')
            with patch('workflow_io.os.utime', side_effect=OSError('metadata write failed')):
                with self.assertRaisesRegex(RuntimeError, 'source restoration failed'):
                    edit.__exit__(None, None, None)
            self.assertEqual(edit.backup.read_bytes(), b'original')
            self.assertEqual(source.read_bytes(), b'changed')

    def test_external_edit_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.rs'
            source.write_bytes(b'original')
            edit = SourceEdit(source, b'original').__enter__()
            edit.replace(b'changed')
            source.write_bytes(b'external change')
            with self.assertRaisesRegex(RuntimeError, 'source changed outside benchmark'):
                edit.__exit__(None, None, None)
            self.assertEqual(source.read_bytes(), b'external change')
            self.assertEqual(edit.backup.read_bytes(), b'original')


if __name__ == '__main__':
    unittest.main()
