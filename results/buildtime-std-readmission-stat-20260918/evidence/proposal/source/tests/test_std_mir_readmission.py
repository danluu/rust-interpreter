import errno
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import std_mir_readmission as recovery


class Readmission(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.ready = self.work / 'ready.json'
        self.result = dict(owner=str(self.work), artifacts={})
        for name in ['core.rmeta', 'std.rmeta']:
            path = self.work / name
            path.write_bytes(name.encode())
            old = recovery.stamp(path.stat())
            old[0] += 2
            self.result['artifacts'][name] = dict(stamp=old,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        self.ready.write_text(json.dumps(self.result))
        self.original_ready = self.ready.read_bytes()

    def validate(self):
        recovery.validate(self.work, self.ready, self.result)

    def test_complete_hash_readmission_preserves_manifest_and_reuses_exact_receipt(self):
        self.validate()
        receipts = list(self.work.glob('readmission-*.json'))
        self.assertEqual(len(receipts), 1)
        receipt = json.loads(receipts[0].read_text())
        self.assertEqual(set(receipt['artifacts']), set(self.result['artifacts']))
        self.assertEqual(self.ready.read_bytes(), self.original_ready)
        with patch.object(recovery, 'file_digest', side_effect=AssertionError('rehash')):
            self.validate()

    def test_unchanged_device_needs_no_readmission(self):
        for name, item in self.result['artifacts'].items():
            item['stamp'] = recovery.stamp((self.work / name).stat())
        self.validate()
        self.assertEqual(list(self.work.glob('readmission-*')), [])

    def test_content_change_with_preserved_stamp_is_rejected(self):
        path = self.work / 'core.rmeta'
        before = path.stat()
        path.write_bytes(b'x' * before.st_size)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.assertRaisesRegex(RuntimeError, 'content changed'):
            self.validate()
        self.assertEqual(list(self.work.glob('readmission-*')), [])
        self.assertEqual(self.ready.read_bytes(), self.original_ready)

    def test_other_stamp_changes_and_mixed_devices_are_rejected(self):
        for field in [1, 2, 3]:
            before = self.result['artifacts']['core.rmeta']['stamp'][:]
            self.result['artifacts']['core.rmeta']['stamp'][field] += 1
            with self.assertRaisesRegex(RuntimeError, 'beyond device'):
                self.validate()
            self.result['artifacts']['core.rmeta']['stamp'] = before
        self.result['artifacts']['core.rmeta']['stamp'][0] += 1
        with self.assertRaisesRegex(RuntimeError, 'beyond device'):
            self.validate()

    def test_replaced_or_missing_artifact_after_readmission_is_rejected(self):
        self.validate()
        path = self.work / 'std.rmeta'
        replacement = path.with_suffix('.new')
        replacement.write_bytes(path.read_bytes())
        replacement.replace(path)
        with self.assertRaisesRegex(RuntimeError, 'beyond device'):
            self.validate()
        path.unlink()
        with self.assertRaisesRegex(RuntimeError, 'artifact changed'):
            self.validate()

    def test_invalid_receipt_and_mutation_during_hash_are_rejected(self):
        real = recovery.file_digest
        def mutate(stream):
            result = real(stream)
            with (self.work / 'std.rmeta').open('ab') as changed:
                changed.write(b'x')
            return result
        with patch.object(recovery, 'file_digest', side_effect=mutate):
            with self.assertRaisesRegex(RuntimeError, 'during readmission'):
                self.validate()
        self.assertEqual(list(self.work.glob('readmission-*')), [])

    def test_receipt_does_not_admit_different_manifest(self):
        self.validate()
        receipt, = self.work.glob('readmission-*.json')
        receipt.write_text('{}')
        with self.assertRaisesRegex(RuntimeError, 'receipt changed'):
            self.validate()


    def test_nonregular_paths_preserve_exact_artifact_error(self):
        path = self.work / 'core.rmeta'
        cases = ('missing', 'directory', 'dangling-link', 'directory-link')
        for kind in cases:
            with self.subTest(kind=kind):
                if path.is_symlink() or path.is_file():
                    path.unlink()
                elif path.exists():
                    path.rmdir()
                if kind == 'directory':
                    path.mkdir()
                elif kind == 'dangling-link':
                    path.symlink_to('absent-target')
                elif kind == 'directory-link':
                    path.symlink_to(self.work, target_is_directory=True)
                with self.assertRaises(RuntimeError) as caught:
                    self.validate()
                self.assertEqual(str(caught.exception),
                    'standard-library MIR artifact changed: ' + str(path))
                self.assertIsNone(caught.exception.__context__)
                self.assertEqual(self.ready.read_bytes(), self.original_ready)
                self.assertEqual(list(self.work.glob('readmission-*')), [])

    def test_symlink_to_regular_artifact_retains_all_reuse_paths(self):
        path = self.work / 'core.rmeta'
        target = self.work / 'core.payload'
        path.rename(target)
        path.symlink_to(target.name)
        original = target.read_bytes()
        # The saved device differs: real readmission must follow the link and hash.
        self.validate()
        receipt, = self.work.glob('readmission-*.json')
        receipt_bytes = receipt.read_bytes()
        # The next call uses the matching readmission receipt.
        self.validate()
        self.assertEqual(receipt.read_bytes(), receipt_bytes)
        # An already matching saved device must also accept this regular target.
        for name, item in self.result['artifacts'].items():
            item['stamp'] = recovery.stamp((self.work / name).stat())
        self.validate()
        self.assertEqual(self.ready.read_bytes(), self.original_ready)
        self.assertEqual(target.read_bytes(), original)
        self.assertTrue(path.is_symlink())
        self.assertEqual(list(self.work.glob('readmission-*.json')), [receipt])

    def test_stat_failures_preserve_native_pathlib_error_policy(self):
        path = self.work / 'core.rmeta'
        native_stat = os.stat
        faults = [(str(number), lambda number=number:
                   OSError(number, os.strerror(number), str(path)))
                  for number in (errno.ENOENT, errno.ENOTDIR, errno.EACCES,
                                 errno.EPERM, errno.EIO, errno.ELOOP,
                                 errno.ENAMETOOLONG)]
        faults.append(('invalid-path', lambda: ValueError('embedded null byte')))
        for label, fault in faults:
            with self.subTest(fault=label):
                def failing_stat(value, *args, **kwargs):
                    if os.fspath(value) == str(path):
                        raise fault()
                    return native_stat(value, *args, **kwargs)
                expected_type = RuntimeError
                expected_args = ('standard-library MIR artifact changed: ' + str(path),)
                with patch.object(os, 'stat', side_effect=failing_stat):
                    # The public Path predicate is the cross-version error oracle.
                    try:
                        regular = path.is_file()
                    except (OSError, ValueError) as error:
                        expected_type, expected_args = type(error), error.args
                    else:
                        self.assertFalse(regular)
                    with self.assertRaises(expected_type) as caught:
                        self.validate()
                self.assertIs(type(caught.exception), expected_type)
                self.assertEqual(caught.exception.args, expected_args)
                self.assertIsNone(caught.exception.__cause__)
                self.assertIsNone(caught.exception.__context__)
                self.assertEqual(self.ready.read_bytes(), self.original_ready)
                self.assertEqual(list(self.work.glob('readmission-*')), [])

    def test_later_missing_artifact_precedes_earlier_stamp_mismatch(self):
        self.result['artifacts']['core.rmeta']['stamp'][3] += 1
        path = self.work / 'std.rmeta'
        path.unlink()
        with self.assertRaises(RuntimeError) as caught:
            self.validate()
        self.assertEqual(str(caught.exception),
            'standard-library MIR artifact changed: ' + str(path))
        self.assertEqual(self.ready.read_bytes(), self.original_ready)
        self.assertEqual(list(self.work.glob('readmission-*')), [])



if __name__ == '__main__':
    unittest.main()
