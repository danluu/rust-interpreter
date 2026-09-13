"""Exact inventory equivalence and refusal controls; no compiler subprocesses."""
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import custom_compiler as custom
from custom_compiler import tree_stamps


def reference(directory):
    """Independent pathlib inventory with the original six identity fields."""
    result = {}
    for path in [directory, *directory.rglob('*')]:
        info = path.lstat()
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise RuntimeError('unsupported fixture')
        result[str(path.relative_to(directory))] = [info.st_dev, info.st_ino,
            info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns]
    return result


class OwnedTreeStampsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def test_full_tree_and_all_identity_fields_match_independent_inventory(self):
        for name in ['.hidden', 'a.rs', 'a/deep/b', 'unicode-λ/雪.rs', 'spaces here/x']:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
        (self.root / 'empty').mkdir()
        os.link(self.root / 'a.rs', self.root / 'hardlink')
        self.assertEqual(tree_stamps(self.root), reference(self.root))

    def test_same_length_child_rewrite_with_restored_mtime_changes_inventory(self):
        path = self.root / 'child'
        path.write_bytes(b'before')
        original = path.stat()
        before = tree_stamps(self.root)
        path.write_bytes(b'after!')
        os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
        after = tree_stamps(self.root)
        self.assertEqual(before['.'], after['.'])
        self.assertEqual(before['child'][3:5], after['child'][3:5])
        self.assertNotEqual(before['child'][5], after['child'][5])
        self.assertEqual(after, reference(self.root))

    def test_nested_add_remove_replace_and_mode_changes_remain_visible(self):
        nested = self.root / 'nested'
        nested.mkdir()
        initial = tree_stamps(self.root)
        path = nested / 'new'
        path.write_bytes(b'x')
        added = tree_stamps(self.root)
        self.assertEqual(initial['.'], added['.'])
        self.assertIn('nested/new', added)
        path.chmod(0o400)
        changed = tree_stamps(self.root)
        self.assertNotEqual(added['nested/new'][2], changed['nested/new'][2])
        replacement = nested / 'replacement'
        replacement.write_bytes(b'x')
        replacement.replace(path)
        replaced = tree_stamps(self.root)
        self.assertNotEqual(changed['nested/new'][1], replaced['nested/new'][1])
        path.unlink()
        self.assertNotIn('nested/new', tree_stamps(self.root))

    def test_symlinks_are_rejected_including_dangling_and_directory_cycles(self):
        (self.root / 'file').write_text('x')
        for target in ['file', 'missing', '.']:
            with self.subTest(target=target):
                link = self.root / 'link'
                link.symlink_to(target)
                try:
                    with self.assertRaisesRegex(RuntimeError, 'symlink'):
                        tree_stamps(self.root)
                finally:
                    link.unlink()
        alias = self.root / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'ordinary directory'):
            tree_stamps(alias)

    def test_special_entries_are_rejected_without_opening_them(self):
        os.mkfifo(self.root / 'fifo')
        with self.assertRaisesRegex(RuntimeError, 'unsupported'):
            tree_stamps(self.root)

    def test_directory_replaced_after_entry_stat_cannot_reuse_stale_identity(self):
        nested = self.root / 'nested'
        nested.mkdir()
        (nested / 'file').write_bytes(b'unchanged')
        moved = self.root / 'moved'
        ordinary_scandir = os.scandir
        replaced = False

        def swap_before_scan(path):
            nonlocal replaced
            if Path(path) == nested and not replaced:
                replaced = True
                nested.rename(moved)
                nested.symlink_to(moved, target_is_directory=True)
            return ordinary_scandir(path)

        with patch.object(custom.os, 'scandir', side_effect=swap_before_scan):
            with self.assertRaisesRegex(RuntimeError, 'changed during inspection|symlink'):
                tree_stamps(self.root)
        self.assertTrue(replaced)


if __name__ == '__main__':
    unittest.main()
