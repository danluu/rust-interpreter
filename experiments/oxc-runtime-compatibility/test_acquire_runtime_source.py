"""Small local controls for exclusive copying and Cargo-compatible locking."""
import fcntl
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import acquire_runtime_source as transfer


class TransferControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='oxc-transfer-control-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / 'source'
        self.source.write_bytes(b'qualified source bytes\n')
        self.target = self.root / 'target'
        self.proof = transfer.file_record(self.source)

    def test_independent_copy_preserves_bytes_and_mode(self):
        transfer.copy_file(self.source, self.target, self.proof)
        self.assertEqual(transfer.file_record(self.target), self.proof)
        self.assertNotEqual(self.source.stat().st_ino, self.target.stat().st_ino)

    def test_existing_destination_is_never_overwritten(self):
        self.target.write_bytes(b'peer-owned data')
        with self.assertRaisesRegex(RuntimeError, 'already exists'):
            transfer.copy_file(self.source, self.target, self.proof)
        self.assertEqual(self.target.read_bytes(), b'peer-owned data')

    def test_destination_link_is_never_followed(self):
        self.target.symlink_to(self.source)
        with self.assertRaisesRegex(RuntimeError, 'already exists'):
            transfer.copy_file(self.source, self.target, self.proof)
        self.assertEqual(self.source.read_bytes(), b'qualified source bytes\n')
        self.assertTrue(self.target.is_symlink())

    def test_source_hardlink_is_rejected(self):
        os.link(self.source, self.root / 'other-name')
        with self.assertRaisesRegex(RuntimeError, 'ordinary path'):
            transfer.copy_file(self.source, self.target, self.proof)
        self.assertFalse(self.target.exists())

    def test_recorded_executor_may_have_unchanged_hardlinks(self):
        os.link(self.source, self.root / 'system-alias')
        executors = {str(self.source): dict(resolved=str(self.source), stamp=transfer.stamp(self.source),
                                           sha256=transfer.sha(self.source))}
        self.assertEqual(transfer.frozen_input_file(self.source, executors).st_nlink, 2)
        with self.assertRaisesRegex(RuntimeError, 'ordinary path'):
            transfer.frozen_input_file(self.source, {})

    def test_recorded_executor_link_change_is_rejected(self):
        os.link(self.source, self.root / 'system-alias')
        executors = {str(self.source): dict(resolved=str(self.source), stamp=transfer.stamp(self.source),
                                           sha256=transfer.sha(self.source))}
        os.link(self.source, self.root / 'new-alias')
        with self.assertRaisesRegex(RuntimeError, 'links, or bytes changed'):
            transfer.frozen_input_file(self.source, executors)

    def test_symlink_route_cannot_exempt_unrecorded_target_hardlinks(self):
        os.link(self.source, self.root / 'system-alias')
        route = self.root / 'symlink-route'
        route.symlink_to(self.source)
        executors = {str(route): dict(resolved=str(self.source), stamp=transfer.stamp(route),
                                      sha256=transfer.sha(route))}
        with self.assertRaisesRegex(RuntimeError, 'requires direct recorded identity'):
            transfer.frozen_input_file(self.source, executors)

    def test_file_appearing_at_exclusive_create_is_preserved(self):
        checked_absent = transfer.absent
        def race(path):
            checked_absent(path)
            path.write_bytes(b'concurrent peer data')
        with patch.object(transfer, 'absent', race), self.assertRaises(FileExistsError):
            transfer.copy_file(self.source, self.target, self.proof)
        self.assertEqual(self.target.read_bytes(), b'concurrent peer data')

    def test_symlink_appearing_at_exclusive_create_is_preserved(self):
        checked_absent = transfer.absent
        def race(path):
            checked_absent(path)
            path.symlink_to(self.source)
        with patch.object(transfer, 'absent', race), self.assertRaises(FileExistsError):
            transfer.copy_file(self.source, self.target, self.proof)
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(self.source.read_bytes(), b'qualified source bytes\n')

    def test_changed_source_during_copy_is_rejected_and_retained(self):
        original_open = Path.open
        def race(path, mode='r', *args, **kwargs):
            if path == self.target and mode == 'xb':
                with original_open(self.source, 'wb') as changed:
                    changed.write(b'changed during copy\n')
            return original_open(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', race), self.assertRaisesRegex(RuntimeError, 'source/readback changed'):
            transfer.copy_file(self.source, self.target, self.proof)
        self.assertTrue(self.target.exists())

    def lock_identity(self):
        self.target.touch()
        row = self.target.stat()
        return dict(dev=row.st_dev, ino=row.st_ino)

    def test_cargo_lock_contention_is_bounded(self):
        identity = self.lock_identity()
        notes = []
        with self.target.open('r+') as other:
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(RuntimeError, 'admission timed out'):
                with transfer.download_lock(self.target, identity, wait_seconds=.01, note=notes.append):
                    self.fail('a competing download lock was admitted')
        self.assertIsNone(notes[-1]['acquired_at'])
        self.assertIn('released_at', notes[-1])

    def test_cargo_lock_releases_on_failure(self):
        identity = self.lock_identity()
        with self.assertRaisesRegex(ValueError, 'retained failure'):
            with transfer.download_lock(self.target, identity):
                raise ValueError('retained failure')
        with self.target.open('r+') as next_owner:
            fcntl.flock(next_owner, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_cargo_lock_inode_replacement_is_rejected(self):
        identity = self.lock_identity()
        with self.assertRaisesRegex(RuntimeError, 'replaced while held'):
            with transfer.download_lock(self.target, identity):
                self.target.rename(self.root / 'old-lock')
                self.target.touch()
        self.assertTrue((self.root / 'old-lock').exists())
        self.assertNotEqual(self.target.stat().st_ino, identity['ino'])

    def test_empty_relative_path_is_rejected(self):
        for name in ['', '.', '/absolute', '../escape']:
            with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, 'unsafe relative path'):
                transfer.safe_relative(name)

    def test_duplicate_required_index_version_is_rejected(self):
        row = b'{"name":"test","vers":"1.0.0","cksum":"abc"}'
        self.target.write_bytes(b'\x03\x02\x00\x00\x00etag: "test"\x001.0.0\x00' + row +
                                b'\x001.0.0\x00' + row + b'\x00')
        with self.assertRaisesRegex(RuntimeError, 'missing or duplicated'):
            transfer.index_record(self.target, 'test', '1.0.0', 'abc')

    def test_source_symlink_cannot_escape_copy_root(self):
        self.target.mkdir()
        (self.target / 'escape').symlink_to('../source')
        with self.assertRaisesRegex(RuntimeError, 'escapes its checkout'):
            transfer.inventory(self.target)

    def test_contained_directory_link_is_recorded_without_traversal(self):
        self.target.mkdir()
        (self.target / 'ordinary').mkdir()
        (self.target / 'ordinary/input').write_bytes(b'fixture')
        (self.target / 'alias').symlink_to('ordinary')
        records = transfer.inventory(self.target)
        self.assertEqual(records['alias'], dict(kind='symlink', target='ordinary'))
        self.assertEqual(set(records), {'alias', 'ordinary', 'ordinary/input'})


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TransferControls)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
