"""Focused local filesystem controls; no Git, compiler, Cargo or benchmark."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import acquire as a


class AcquisitionControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='hir-options-acquisition-control-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.namespace = self.root / 'owned'
        self.namespace.mkdir()
        self.source = self.root / 'source'
        self.source.write_bytes(b'preserve-provider\n')
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.original_stamp = a.stamp(self.source)

    def test_fresh_independent_copy_never_overwrites(self):
        destination = self.namespace / 'new' / 'copy'
        with patch.object(a, 'NAMESPACE', self.namespace):
            a.copy_new(self.source, destination, self.digest)
            with self.assertRaises(FileExistsError):
                a.copy_new(self.source, destination, self.digest)
        self.assertEqual(destination.read_bytes(), self.source.read_bytes())
        self.assertNotEqual(destination.stat().st_ino, self.source.stat().st_ino)
        self.assertEqual(a.stamp(self.source), self.original_stamp)

    def test_link_or_parent_escape_refused_before_mutation(self):
        link = self.namespace / 'link'
        link.symlink_to(self.root, target_is_directory=True)
        source_link = self.root / 'source-link'
        source_link.symlink_to(self.source)
        with patch.object(a, 'NAMESPACE', self.namespace):
            for source, destination in [(self.source, link/'escape'),
                    (self.source, self.namespace/'..'/'unexpected'/'escape'),
                    (source_link, self.namespace/'copy')]:
                with self.assertRaises(AssertionError):
                    a.copy_new(source, destination, self.digest)
        self.assertFalse((self.root/'escape').exists())
        self.assertFalse((self.root/'unexpected').exists())
        self.assertFalse((self.namespace/'copy').exists())
        self.assertEqual(a.stamp(self.source), self.original_stamp)

    def test_changed_provider_and_new_configuration_rejected(self):
        config = self.root/'config'
        frozen = dict(files={str(self.source):dict(sha256=self.digest, stamp=self.original_stamp)},
            symlinks={}, configurations={str(config):None})
        a.guard_inputs(frozen)
        config.write_bytes(b'[build]\nrustc="wrong"\n')
        with self.assertRaises(AssertionError):
            a.guard_inputs(frozen)
        config.unlink()
        self.source.write_bytes(b'changed-provider!\n')
        with self.assertRaises(AssertionError):
            a.guard_inputs(frozen)

    def test_source_hash_and_tracked_symlink_remain_exact(self):
        directory = self.root/'tree'
        directory.mkdir()
        (directory/'data').write_bytes(b'input')
        (directory/'link').symlink_to('data')
        entries = {'data':dict(mode='100644',sha256=hashlib.sha256(b'input').hexdigest()),
            'link':dict(mode='120000',target='data')}
        a.source_guard(directory, entries)
        (directory/'link').unlink()
        (directory/'link').write_bytes(b'input')
        with self.assertRaises(AssertionError):
            a.source_guard(directory, entries)
        (directory/'link').unlink()
        (directory/'link').symlink_to('data')
        (directory/'data').write_bytes(b'other')
        with self.assertRaises(AssertionError):
            a.source_guard(directory, entries)


if __name__ == '__main__':
    unittest.main(verbosity=2)
