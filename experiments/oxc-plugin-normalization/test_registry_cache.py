"""Synthetic integrity controls; no Cargo/compiler/download subprocesses."""
import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

import registry_cache


class RegistryControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='oxc-registry-control-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / 'example-1.0.0'
        (self.root / 'src').mkdir(parents=True)
        (self.root / 'src/lib.rs').write_bytes(b'pub fn example() {}\n')
        (self.root / '.cargo-ok').write_bytes(b'{"v":1}')
        self.archive = self.base / 'example-1.0.0.crate'
        self.write_archive()

    def write_archive(self, extras=()):
        with tarfile.open(self.archive, 'w:gz') as output:
            data = b'pub fn example() {}\n'
            member = tarfile.TarInfo('example-1.0.0/src/lib.rs')
            member.size = len(data)
            output.addfile(member, io.BytesIO(data))
            for name, kind in extras:
                member = tarfile.TarInfo(name)
                member.type = kind
                if kind in [tarfile.SYMTYPE, tarfile.LNKTYPE]:
                    member.linkname = 'src/lib.rs'
                output.addfile(member, io.BytesIO(b''))

    def verify(self, checksum=None):
        checksum = checksum or hashlib.sha256(self.archive.read_bytes()).hexdigest()
        return registry_cache.verify(self.archive, self.root, checksum)

    def test_ordinary_members_and_marker_pass(self):
        self.assertEqual(list(self.verify()['members']), ['src/lib.rs'])

    def test_wrong_archive_checksum(self):
        with self.assertRaisesRegex(RuntimeError, 'Cargo.lock'):
            self.verify('0' * 64)

    def test_changed_source_bytes(self):
        (self.root / 'src/lib.rs').write_bytes(b'pub fn changed() {}\n')
        with self.assertRaisesRegex(RuntimeError, 'bytes differ'):
            self.verify()

    def test_extra_source_file(self):
        (self.root / 'extra.rs').write_bytes(b'')
        with self.assertRaisesRegex(RuntimeError, 'membership'):
            self.verify()

    def test_extra_empty_directory(self):
        (self.root / 'extra').mkdir()
        with self.assertRaisesRegex(RuntimeError, 'membership'):
            self.verify()

    def test_source_symlink(self):
        path = self.root / 'src/lib.rs'
        path.rename(self.base / 'outside.rs')
        path.symlink_to(self.base / 'outside.rs')
        with self.assertRaisesRegex(RuntimeError, 'link'):
            self.verify()

    def test_source_hardlink(self):
        (self.base / 'outside.rs').hardlink_to(self.root / 'src/lib.rs')
        with self.assertRaisesRegex(RuntimeError, 'ordinary unlinked'):
            self.verify()

    def test_marker_bytes_are_exact(self):
        (self.root / '.cargo-ok').write_bytes(b'{"v":2}')
        with self.assertRaisesRegex(RuntimeError, 'Cargo marker'):
            self.verify()

    def test_duplicate_archive_member(self):
        self.write_archive([('example-1.0.0/src/lib.rs', tarfile.REGTYPE)])
        with self.assertRaisesRegex(RuntimeError, 'duplicate'):
            self.verify()

    def test_parent_archive_path(self):
        self.write_archive([('example-1.0.0/../outside', tarfile.REGTYPE)])
        with self.assertRaisesRegex(RuntimeError, 'invalid registry archive path'):
            self.verify()

    def test_archive_link(self):
        for kind in [tarfile.SYMTYPE, tarfile.LNKTYPE]:
            with self.subTest(kind=kind):
                self.write_archive([('example-1.0.0/link', kind)])
                with self.assertRaisesRegex(RuntimeError, 'link or special'):
                    self.verify()

    def test_archive_marker_rejected(self):
        self.write_archive([('example-1.0.0/.cargo-ok', tarfile.REGTYPE)])
        with self.assertRaisesRegex(RuntimeError, 'Cargo-generated'):
            self.verify()


if __name__ == '__main__':
    unittest.main(verbosity=2)
