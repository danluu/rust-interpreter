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


if __name__ == '__main__':
    unittest.main()
