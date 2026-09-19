"""Tiny owned fixtures exercise lossless retention and failed publication."""
import copy
import gzip
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

import proof_snapshots as snapshots

LIMITS = dict(maximum_files=8, maximum_file_bytes=65536, maximum_logical_bytes=131072,
              maximum_compressed_bytes=131072, maximum_manifest_bytes=65536)


def record(path):
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                size=path.stat().st_size, identity=snapshots.identity(path.lstat()))


class ProofSnapshots(unittest.TestCase):
    def fixture(self, root, name='source', data=b'proof bytes\n'*100):
        path = root/name; path.write_bytes(data)
        return record(path)

    def test_measure_is_readonly_and_roundtrip_preserves_all_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            records = [self.fixture(root, 'a'), self.fixture(root, 'b'), self.fixture(root, 'empty', b'')]
            before = set(root.iterdir())
            projection = snapshots.measure(records, LIMITS, lambda: None)
            self.assertEqual(before, set(root.iterdir()))
            self.assertEqual(projection, snapshots.measure(list(reversed(records)), LIMITS, lambda: None))
            self.assertEqual(len(projection['files']), 3)
            self.assertEqual(len(projection['blobs']), 2)
            result = snapshots.write_verified(records, root/'snapshots', projection, LIMITS, lambda: None)
            self.assertTrue(result['full_gzip_eof'] and result['full_logical_readback'])
            self.assertEqual(set(result['files']), {row['path'] for row in records})
            for row in records:
                self.assertEqual(gzip.decompress(Path(result['files'][row['path']]['path']).read_bytes()),
                                 Path(row['path']).read_bytes())

    def test_changed_source_and_changed_duplicate_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); rows = [self.fixture(root, 'a'), self.fixture(root, 'b')]
            projection = snapshots.measure(rows, LIMITS, lambda: None)
            Path(rows[1]['path']).write_bytes(b'different')
            with self.assertRaises(ValueError):
                snapshots.write_verified(rows, root/'snapshots', projection, LIMITS, lambda: None)
            self.assertFalse((root/'snapshots').exists())
            # Even a freshly supplied stamp cannot hide wrong bytes under the old hash.
            current = record(Path(rows[1]['path'])); current['sha256'] = rows[1]['sha256']
            with self.assertRaises(ValueError):
                snapshots.measure([current], LIMITS, lambda: None)

    def test_missing_or_tampered_projection_cannot_create_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); rows = [self.fixture(root)]
            good = snapshots.measure(rows, LIMITS, lambda: None)
            for field in ['files', 'blobs', 'compressed_bytes']:
                projection = copy.deepcopy(good)
                projection[field] = {} if field != 'compressed_bytes' else good[field]+1
                with self.subTest(field=field), self.assertRaises(ValueError):
                    snapshots.write_verified(rows, root/'snapshots', projection, LIMITS, lambda: None)
                self.assertFalse((root/'snapshots').exists())

    def test_input_and_encoded_bounds_fail_without_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); rows = [self.fixture(root)]
            for key in ['maximum_file_bytes', 'maximum_logical_bytes', 'maximum_compressed_bytes', 'maximum_manifest_bytes']:
                limits = dict(LIMITS); limits[key] = 1
                with self.subTest(key=key), self.assertRaises(ValueError):
                    snapshots.measure(rows, limits, lambda: None)
            limits = dict(LIMITS); limits['maximum_files'] = 1
            with self.assertRaises(ValueError):
                snapshots.measure([*rows, self.fixture(root, 'second')], limits, lambda: None)

    def test_corrupt_truncated_and_extra_gzip_members_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); rows = [self.fixture(root)]
            projection = snapshots.measure(rows, LIMITS, lambda: None)
            snapshots.write_verified(rows, root/'snapshots', projection, LIMITS, lambda: None)
            expected = next(iter(projection['blobs'].values()))
            path = root/'snapshots'/expected['filename']; original = path.read_bytes()
            for data in [original[:-1], original[:-8]+bytes([original[-8]^1])+original[-7:],
                         original+gzip.compress(b'extra', mtime=0)]:
                path.write_bytes(data)
                # Bind the altered compressed bytes to exercise logical/CRC checks too.
                altered = dict(expected, compressed_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
                with self.subTest(size=len(data)), self.assertRaises((ValueError, EOFError, OSError)):
                    snapshots.verify_blob(path, altered, lambda: None)

    def test_guard_failure_preserves_partial_attempt_and_refuses_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); rows = [self.fixture(root)]
            projection = snapshots.measure(rows, LIMITS, lambda: None)
            destination = root/'snapshots'
            def guard():
                if destination.exists() and any(destination.iterdir()):
                    raise RuntimeError('capacity rejected')
            with self.assertRaises(RuntimeError):
                snapshots.write_verified(rows, destination, projection, LIMITS, guard)
            self.assertTrue(destination.exists())
            with self.assertRaises(ValueError):
                snapshots.write_verified(rows, destination, projection, LIMITS, lambda: None)

    def test_symlink_source_and_destination_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); row = self.fixture(root)
            alias = root/'alias'; alias.symlink_to(row['path'])
            forged = dict(row, path=str(alias))
            with self.assertRaises(ValueError):
                snapshots.measure([forged], LIMITS, lambda: None)
            projection = snapshots.measure([row], LIMITS, lambda: None)
            destination = root/'snapshots'; destination.symlink_to(root/'missing')
            with self.assertRaises(ValueError):
                snapshots.write_verified([row], destination, projection, LIMITS, lambda: None)


if __name__ == '__main__':
    unittest.main()
