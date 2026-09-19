"""Bound actual source-route metadata and tiny no-follow inventory fixtures."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

import sysroot_inventory as inventory


def stamp(path):
    value = path.lstat()
    return [value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink]


def file(path):
    return dict(stamp=stamp(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


class SysrootInventory(unittest.TestCase):
    def test_actual_stage0_source_link_and_stage1_only_absence(self):
        saved = json.loads((Path(__file__).with_name('actual-source-links.json')).read_bytes())
        self.assertEqual(set(saved['links']), {'lib/rustlib/rustc-src/rust'})
        for relative, row in saved['links'].items():
            path = Path(row['path'])
            self.assertEqual(stamp(path), row['stamp'])
            self.assertEqual(os.readlink(path), row['target'])
            self.assertEqual(str(path.resolve(strict=True)), row['resolved'])
            self.assertTrue(inventory.link_allowed(relative, row['resolved'], saved['root'], saved['source']))
            self.assertEqual(stamp(path), row['stamp'])
        for name in saved['absent']:
            self.assertFalse(Path(name).exists() or Path(name).is_symlink())

    def fixture(self, temporary):
        source = Path(temporary).resolve()/'source'
        root = source/'build'/inventory.HOST/'stage0-sysroot'
        (root/'lib/rustlib/rustc-src').mkdir(parents=True)
        (source/'outside-sysroot.txt').write_bytes(b'never inventory through the source link')
        (root/'lib/example.rlib').write_bytes(b'fixture library')
        (root/'lib/rustlib/rustc-src/rust').symlink_to(source, target_is_directory=True)
        return source, root

    def test_complete_inventory_keeps_source_link_without_traversing_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, root = self.fixture(temporary)
            observed = inventory.inventory(root, source, stamp, file)
            self.assertEqual({name for name, row in observed.items() if row['kind']=='file'}, {'lib/example.rlib'})
            self.assertEqual({name for name, row in observed.items() if row['kind']=='link'}, {'lib/rustlib/rustc-src/rust'})
            self.assertEqual(observed['lib/rustlib/rustc-src/rust']['resolved'], str(source))
            self.assertEqual(observed['lib/example.rlib']['sha256'], hashlib.sha256(b'fixture library').hexdigest())

    def test_internal_link_preserves_exact_route_and_target_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, root = self.fixture(temporary)
            (root/'lib/alias.rlib').symlink_to('example.rlib')
            observed = inventory.inventory(root, source, stamp, file)
            self.assertEqual(observed['lib/alias.rlib']['target'], 'example.rlib')
            self.assertEqual(observed['lib/alias.rlib']['resolved'], str(root/'lib/example.rlib'))

    def test_foreign_and_same_source_subdirectory_routes_reject(self):
        source = Path('/owned/source'); root = source/'build'/inventory.HOST/'stage0-sysroot'
        for target in [Path('/foreign/source'), source/'compiler', Path('/owned/source-other'), root/'lib']:
            with self.subTest(target=target), self.assertRaises(ValueError):
                inventory.link_allowed('lib/rustlib/rustc-src/rust', target, root, source)

    def test_arbitrary_or_stage1_only_source_alias_rejects(self):
        source = Path('/owned/source'); root = source/'build'/inventory.HOST/'stage0-sysroot'
        for relative in ['lib/other', 'lib/rustlib/src/rust', '../escape', '/absolute']:
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                inventory.link_allowed(relative, source, root, source)

    def test_inventory_rejects_foreign_and_missing_source_links(self):
        for fault in ['foreign', 'missing-source']:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                source, root = self.fixture(temporary)
                if fault == 'foreign':
                    foreign = Path(temporary).resolve()/'foreign'; foreign.mkdir()
                    (root/'lib/foreign').symlink_to(foreign, target_is_directory=True)
                else:
                    (root/'lib/rustlib/rustc-src/rust').unlink()
                with self.assertRaises(ValueError):
                    inventory.inventory(root, source, stamp, file)


if __name__ == '__main__':
    unittest.main()
