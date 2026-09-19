"""Tiny task-owned fixtures for a narrowly bounded directory mode transition."""
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

import directory_modes as m

f = m.f


def identity(path):
    return f.identity(path.lstat())


def snapshot(root):
    rows = {'.': dict(kind='directory', identity=identity(root))}
    for path in sorted(root.rglob('*')):
        value = identity(path)
        if stat.S_ISDIR(value['mode']):
            row = dict(kind='directory', identity=value)
        else:
            assert stat.S_ISREG(value['mode'])
            row = dict(kind='file', identity=value, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        rows[str(path.relative_to(root))] = row
    return rows


class DirectoryModeControls(unittest.TestCase):
    def fixture(self, base):
        root = base / 'tree'
        (root / 'a/deep').mkdir(parents=True)
        (root / 'z').mkdir()
        (root / 'a/deep/payload').write_bytes(b'retained payload')
        (root / 'root-file').write_bytes(b'root payload')
        os.chmod(root, 0o700)
        for path in root.rglob('*'):
            os.chmod(path, 0o555 if path.is_dir() else 0o444)
        ledger = base / 'modes.jsonl'; ledger.touch()
        return root, ledger

    def run_modes(self, root, rows, ledger):
        return m.make_writable(root, rows, identity(root.parent), ledger, lambda: None)

    def events(self, ledger):
        return [json.loads(raw) for raw in ledger.read_text().splitlines()]

    def test_exact_directory_modes_and_qualified_removal_interoperate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, ledger = self.fixture(Path(tmp)); before = snapshot(root)
            after, result = self.run_modes(root, before, ledger)
            self.assertEqual(result, dict(changed_directories=3, chmod_calls=3, changed_files=0, changed_root=False))
            self.assertEqual(snapshot(root), after)
            self.assertEqual(before['.'], after['.'])
            for name, row in before.items():
                if row['kind'] == 'file':
                    self.assertEqual(row, after[name])
            events = self.events(ledger)
            self.assertEqual([r['event'] for r in events], ['intent', 'applied', 'validated'] * 3)
            self.assertEqual([r['relative'] for r in events if r['event'] == 'validated'], ['a', 'a/deep', 'z'])
            removal = Path(tmp) / 'removal.jsonl'; removal.touch()
            removed = f.remove_tree(root, after, identity(Path(tmp)), removal, lambda: None)
            self.assertTrue(removed['root_absent']); self.assertEqual(removed['removed_entries'], len(before))
            self.assertEqual(set(f.ledger_summary(removal)['validated']), set(before))

    def test_unexpected_mode_refused_before_any_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, ledger = self.fixture(Path(tmp)); os.chmod(root / 'z', 0o755); rows = snapshot(root)
            with self.assertRaisesRegex(RuntimeError, 'unadmitted directory mode'):
                self.run_modes(root, rows, ledger)
            self.assertEqual(snapshot(root), rows); self.assertEqual(ledger.read_bytes(), b'')

    def test_unadmitted_member_refused_before_first_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, ledger = self.fixture(Path(tmp)); rows = snapshot(root)
            (root / 'extra').write_bytes(b'extra'); rows['.']['identity'] = identity(root)
            with self.assertRaisesRegex(RuntimeError, 'membership'):
                self.run_modes(root, rows, ledger)
            self.assertEqual(stat.S_IMODE((root / 'a').stat().st_mode), 0o555)
            self.assertEqual(ledger.read_bytes(), b'')

    def test_replaced_directory_symlink_never_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); root, ledger = self.fixture(base); rows = snapshot(root)
            outside = base / 'outside'; outside.mkdir(); (outside / 'keep').write_bytes(b'keep')
            outside_before = identity(outside)
            (root / 'z').rmdir(); (root / 'z').symlink_to(outside, target_is_directory=True)
            rows['.']['identity'] = identity(root)
            with self.assertRaisesRegex(RuntimeError, 'inventory entry'):
                self.run_modes(root, rows, ledger)
            self.assertEqual(identity(outside), outside_before)
            self.assertEqual((outside / 'keep').read_bytes(), b'keep'); self.assertEqual(ledger.read_bytes(), b'')

    def test_outside_file_hardlink_refused_before_first_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); root, ledger = self.fixture(base)
            os.link(root / 'root-file', base / 'alias'); rows = snapshot(root)
            with self.assertRaisesRegex(RuntimeError, 'single-link'):
                self.run_modes(root, rows, ledger)
            self.assertEqual(snapshot(root), rows); self.assertEqual(ledger.read_bytes(), b'')

    def test_route_change_after_intent_refused_before_fchmod(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); root, ledger = self.fixture(base); rows = snapshot(root); original = m.event
            outside = base / 'outside'; outside.mkdir(); outside_before = identity(outside)
            def change(fd, row):
                original(fd, row)
                if row['event'] == 'intent':
                    (root / 'a').rename(root / 'moved')
                    (root / 'a').symlink_to(outside, target_is_directory=True)
            with mock.patch.object(m, 'event', side_effect=change):
                with self.assertRaisesRegex(RuntimeError, 'root route changed'):
                    self.run_modes(root, rows, ledger)
            self.assertEqual(stat.S_IMODE((root / 'moved').stat().st_mode), 0o555)
            self.assertEqual(identity(outside), outside_before)
            self.assertEqual([r['event'] for r in self.events(ledger)], ['intent'])

    def test_postcondition_failure_retains_actual_applied_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, ledger = self.fixture(Path(tmp)); rows = snapshot(root)
            with mock.patch.object(m, 'post_mode', side_effect=RuntimeError('injected postcondition')):
                with self.assertRaisesRegex(RuntimeError, 'injected postcondition'):
                    self.run_modes(root, rows, ledger)
            self.assertEqual(stat.S_IMODE((root / 'a').stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE((root / 'a/deep').stat().st_mode), 0o555)
            self.assertEqual([r['event'] for r in self.events(ledger)], ['intent', 'applied'])

    def test_completion_publication_failure_preserves_uncertain_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, ledger = self.fixture(Path(tmp)); rows = snapshot(root); original = m.event
            def fail(fd, row):
                if row['event'] == 'applied':
                    raise OSError('injected completion publication')
                original(fd, row)
            with mock.patch.object(m, 'event', side_effect=fail):
                with self.assertRaisesRegex(OSError, 'completion publication'):
                    self.run_modes(root, rows, ledger)
            self.assertEqual(stat.S_IMODE((root / 'a').stat().st_mode), 0o755)
            self.assertEqual([r['event'] for r in self.events(ledger)], ['intent'])

    def test_ledger_bound_prevents_first_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, ledger = self.fixture(Path(tmp)); rows = snapshot(root)
            with mock.patch.object(m, 'MAX_LEDGER_BYTES', 1):
                with self.assertRaisesRegex(RuntimeError, 'mode ledger bound'):
                    self.run_modes(root, rows, ledger)
            self.assertEqual(snapshot(root), rows); self.assertEqual(ledger.read_bytes(), b'')

    def test_partial_completion_write_retains_honest_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, ledger = self.fixture(Path(tmp)); rows = snapshot(root); original = m.event
            def fail(fd, row):
                if row['event'] == 'applied':
                    os.write(fd, b'{"event":'); os.fsync(fd)
                    raise OSError('injected partial completion')
                original(fd, row)
            with mock.patch.object(m, 'event', side_effect=fail):
                with self.assertRaisesRegex(OSError, 'partial completion'):
                    self.run_modes(root, rows, ledger)
            self.assertEqual(stat.S_IMODE((root / 'a').stat().st_mode), 0o755)
            raw = ledger.read_bytes().splitlines()
            self.assertEqual(len(raw), 2); self.assertEqual(json.loads(raw[0])['event'], 'intent')
            self.assertEqual(raw[1], b'{"event":')


if __name__ == '__main__':
    unittest.main()
