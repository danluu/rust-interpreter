"""Tiny owned fixtures for reference reuse; no external commands or providers.

The stage caller still owns predecessor authorization and aggregate admission.
These cases exercise only exact route/byte preservation and snapshot accounting.
"""
import copy
import gzip
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import proof_snapshots as snapshots

LIMITS = dict(maximum_files=8, maximum_file_bytes=65536,
              maximum_logical_bytes=131072, maximum_compressed_bytes=131072,
              maximum_manifest_bytes=65536)


def record(path):
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                size=path.stat().st_size, identity=snapshots.identity(path.lstat()))


class ReferenceReuse(unittest.TestCase):
    def fixture(self, root, name, data=b'retained proof bytes\n'*31):
        path = root/name
        path.write_bytes(data)
        return record(path)

    def prior(self, root):
        source = self.fixture(root, 'original')
        projection = snapshots.measure([source], LIMITS, lambda: None)
        previous = root/'previous'
        result = snapshots.write_verified([source], previous, projection, LIMITS, lambda: None)
        key = source['sha256']
        path = Path(result['files'][source['path']]['path'])
        reference = dict(path=str(path), identity=snapshots.identity(path.lstat()),
                         blob=copy.deepcopy(projection['blobs'][key]), evidence_root=str(previous))
        roots = {str(previous): snapshots.identity(previous.lstat())}
        return source, reference, roots

    def measure(self, rows, reference, roots, limits=None):
        return snapshots.measure(rows, limits or LIMITS, lambda: None,
                                 reuse=[reference], evidence_roots=roots)

    def write(self, rows, destination, projection, reference, roots):
        return snapshots.write_verified(rows, destination, projection, LIMITS, lambda: None,
                                        reuse=[reference], evidence_roots=roots)

    def test_aliases_reuse_one_unchanged_blob_without_copy_or_compression(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            original, reference, roots = self.prior(root)
            alias = self.fixture(root, 'alias')
            path = Path(reference['path'])
            before_bytes = path.read_bytes()
            before_identity = snapshots.identity(path.lstat())
            before_names = set(Path(reference['evidence_root']).iterdir())
            with patch.object(snapshots, 'compress', side_effect=AssertionError('reuse recompressed')):
                projection = self.measure([original, alias], reference, roots)
                result = self.write([alias, original], root/'new', projection, reference, roots)
            self.assertEqual(projection['new_compressed_bytes'], 0)
            self.assertEqual(projection['new_compressed_allocated_bytes'], 0)
            self.assertEqual(projection['compressed_bytes'], reference['blob']['compressed_bytes'])
            self.assertEqual(projection['reused_compressed_bytes'], projection['compressed_bytes'])
            self.assertEqual(len(projection['blobs']), 1)
            self.assertEqual(set(result['files']), {original['path'], alias['path']})
            self.assertEqual({row['path'] for row in result['files'].values()}, {str(path)})
            self.assertEqual(result['storage'][original['sha256']], dict(kind='reused', path=str(path)))
            self.assertEqual(list((root/'new').iterdir()), [])
            self.assertEqual(path.read_bytes(), before_bytes)
            self.assertEqual(snapshots.identity(path.lstat()), before_identity)
            self.assertEqual(set(Path(reference['evidence_root']).iterdir()), before_names)

    def test_mixed_projection_keeps_total_and_new_physical_allocation_distinct(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, reference, roots = self.prior(root)
            new = self.fixture(root, 'different', bytes(range(128))*9)
            projection = self.measure([old, new], reference, roots)
            new_blob = projection['blobs'][new['sha256']]
            old_bytes = reference['blob']['compressed_bytes']
            self.assertEqual(projection['compressed_bytes'], new_blob['compressed_bytes']+old_bytes)
            self.assertEqual(projection['new_compressed_bytes'], new_blob['compressed_bytes'])
            self.assertEqual(projection['reused_compressed_bytes'], old_bytes)
            self.assertEqual(projection['new_compressed_allocated_bytes'],
                             (new_blob['compressed_bytes']+4095)//4096*4096)
            self.assertGreater(projection['compressed_allocated_bytes'],
                               projection['new_compressed_allocated_bytes'])
            result = self.write([old, new], root/'new', projection, reference, roots)
            self.assertEqual({p.name for p in (root/'new').iterdir()}, {new_blob['filename']})
            self.assertEqual(result['files'][old['path']]['path'], reference['path'])
            self.assertEqual(result['storage'][new['sha256']]['kind'], 'stored')

    def test_total_cap_cannot_be_evaded_by_zero_new_or_mixed_reuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, reference, roots = self.prior(root)
            limits = dict(LIMITS, maximum_compressed_bytes=reference['blob']['compressed_bytes']-1)
            with self.assertRaises(ValueError):
                self.measure([old], reference, roots, limits)
            new = self.fixture(root, 'different', b'new proof payload'*40)
            measured = self.measure([old, new], reference, roots)
            limits['maximum_compressed_bytes'] = measured['compressed_bytes']-1
            self.assertGreaterEqual(limits['maximum_compressed_bytes'], measured['new_compressed_bytes'])
            with self.assertRaises(ValueError):
                self.measure([old, new], reference, roots, limits)
            self.assertFalse((root/'new').exists())

    def test_duplicate_reference_and_same_payload_copy_cannot_double_credit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, reference, roots = self.prior(root)
            with self.assertRaises(ValueError):
                snapshots.measure([old], LIMITS, lambda: None,
                                  reuse=[reference, copy.deepcopy(reference)], evidence_roots=roots)
            separate = root/'separate'
            separate.mkdir()
            other = separate/reference['blob']['filename']
            other.write_bytes(Path(reference['path']).read_bytes())
            copied = dict(reference, path=str(other), identity=snapshots.identity(other.lstat()),
                          evidence_root=str(separate))
            both = dict(roots, **{str(separate): snapshots.identity(separate.lstat())})
            with self.assertRaises(ValueError):
                snapshots.measure([old], LIMITS, lambda: None,
                                  reuse=[reference, copied], evidence_roots=both)

    def test_hardlinked_reference_is_rejected_even_with_fresh_stamp(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, reference, roots = self.prior(root)
            path = Path(reference['path'])
            os.link(path, root/'hardlink')
            changed = dict(reference, identity=snapshots.identity(path.lstat()))
            with self.assertRaises(ValueError):
                self.measure([old], changed, roots)

    def test_unaccounted_root_and_outside_path_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, reference, roots = self.prior(root)
            with self.assertRaises(ValueError):
                self.measure([old], reference, {})
            outside = root/reference['blob']['filename']
            outside.write_bytes(Path(reference['path']).read_bytes())
            escaped = dict(reference, path=str(outside), identity=snapshots.identity(outside.lstat()))
            with self.assertRaises(ValueError):
                self.measure([old], escaped, roots)

    def test_symlink_ancestor_is_rejected_with_valid_target_blob(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, reference, roots = self.prior(root)
            previous = Path(reference['evidence_root'])
            alias = root/'alias-directory'
            alias.symlink_to(previous, target_is_directory=True)
            indirect = dict(reference, path=str(alias/reference['blob']['filename']),
                            evidence_root=str(alias))
            fake_roots = {str(alias): snapshots.identity(previous.lstat())}
            with self.assertRaises(ValueError):
                self.measure([old], indirect, fake_roots)

    def test_missing_blob_and_changed_root_refuse_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, reference, roots = self.prior(root)
            projection = self.measure([old], reference, roots)
            Path(reference['path']).unlink()
            with self.assertRaises((ValueError, OSError)):
                self.write([old], root/'new', projection, reference, roots)
            self.assertFalse((root/'new').exists())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, reference, roots = self.prior(root)
            projection = self.measure([old], reference, roots)
            (Path(reference['evidence_root'])/'unexpected').write_bytes(b'x')
            with self.assertRaises(ValueError):
                self.write([old], root/'new', projection, reference, roots)
            self.assertFalse((root/'new').exists())

    def test_corrupt_reused_bytes_refuse_publication_before_new_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, reference, roots = self.prior(root)
            projection = self.measure([old], reference, roots)
            path = Path(reference['path'])
            raw = path.read_bytes()
            path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
            with self.assertRaises(ValueError):
                self.write([old], root/'new', projection, reference, roots)
            self.assertFalse((root/'new').exists())
            # A fresh identity cannot make corrupt bytes match the old compressed hash.
            altered = dict(reference, identity=snapshots.identity(path.lstat()))
            with self.assertRaises(ValueError):
                self.measure([old], altered, roots)

    def test_rebound_compressed_hash_still_requires_full_crc_and_logical_eof(self):
        for kind in ['truncated', 'bad-crc', 'extra-member']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                old, reference, roots = self.prior(root)
                path = Path(reference['path'])
                original = path.read_bytes()
                if kind == 'truncated':
                    data = original[:-1]
                elif kind == 'bad-crc':
                    data = original[:-8]+bytes([original[-8]^1])+original[-7:]
                else:
                    data = original+gzip.compress(b'extra logical bytes', mtime=0)
                path.write_bytes(data)
                altered = copy.deepcopy(reference)
                altered['identity'] = snapshots.identity(path.lstat())
                altered['blob'].update(compressed_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
                with self.assertRaises((ValueError, EOFError, OSError)):
                    self.measure([old], altered, roots)

    def test_changed_duplicate_source_is_verified_even_when_old_blob_is_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, reference, roots = self.prior(root)
            alias = self.fixture(root, 'alias')
            projection = self.measure([old, alias], reference, roots)
            Path(alias['path']).write_bytes(b'X'*alias['size'])
            with self.assertRaises(ValueError):
                self.write([old, alias], root/'new', projection, reference, roots)
            self.assertFalse((root/'new').exists())
            forged = record(Path(alias['path']))
            forged.update(sha256=old['sha256'], size=old['size'])
            with self.assertRaises(ValueError):
                self.measure([old, forged], reference, roots)

    def test_mutation_after_full_blob_readback_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, reference, roots = self.prior(root)
            original_verify = snapshots.verify_blob
            def read_then_mutate(path, blob, guard):
                original_verify(path, blob, guard)
                Path(path).write_bytes(b'mutated after readback')
            with patch.object(snapshots, 'verify_blob', side_effect=read_then_mutate):
                with self.assertRaises(ValueError):
                    self.measure([old], reference, roots)

    def test_destination_inside_reused_root_cannot_change_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, reference, roots = self.prior(root)
            projection = self.measure([old], reference, roots)
            before = snapshots.identity(Path(reference['evidence_root']).lstat())
            destination = Path(reference['evidence_root'])/'new'
            with self.assertRaises(ValueError):
                self.write([old], destination, projection, reference, roots)
            self.assertFalse(destination.exists())
            self.assertEqual(snapshots.identity(Path(reference['evidence_root']).lstat()), before)

    def test_forged_storage_credit_cannot_publish(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, reference, roots = self.prior(root)
            good = self.measure([old], reference, roots)
            for field, value in [('compressed_bytes', 0), ('new_compressed_bytes', 1),
                                 ('reused_compressed_bytes', 0), ('storage', {}), ('reuse', {})]:
                bad = copy.deepcopy(good)
                bad[field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    self.write([old], root/'new', bad, reference, roots)
                self.assertFalse((root/'new').exists())

    def test_standalone_materialization_map_includes_all_logical_aliases_and_blobs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old, reference, roots = self.prior(root)
            alias = self.fixture(root, 'alias')
            fresh = self.fixture(root, 'fresh', b'distinct bytes')
            projection = self.measure([old, alias, fresh], reference, roots)
            result = self.write([old, alias, fresh], root/'new', projection, reference, roots)
            # A standalone archiver must read both stored and referenced physical paths.
            # This tests the complete map, not a claim that a stage archive was made.
            physical = {key:Path(row['path']).read_bytes() for key,row in result['storage'].items()}
            self.assertEqual(set(physical), set(result['blobs']))
            self.assertEqual(set(result['files']), {old['path'], alias['path'], fresh['path']})
            for original in [old, alias, fresh]:
                row = result['files'][original['path']]
                self.assertEqual(row['path'], result['storage'][original['sha256']]['path'])
                self.assertEqual(gzip.decompress(physical[original['sha256']]), Path(original['path']).read_bytes())
                self.assertEqual(row['sha256'], original['sha256'])
                self.assertEqual(row['size'], original['size'])
            self.assertTrue(result['full_gzip_eof'] and result['full_logical_readback'])


if __name__ == '__main__':
    unittest.main()
