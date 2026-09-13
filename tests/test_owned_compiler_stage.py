"""Small admission/failure controls; never build a compiler or run a benchmark."""
import fcntl
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1] / 'experiments/stable-cgu'
sys.path.insert(0, str(HERE))
import owned_stage


class OwnedCompilerStageContracts(unittest.TestCase):
    def test_inherited_lock_rejects_an_unrelated_file_and_another_open_description(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            lock_path, unrelated = root / 'lock', root / 'unrelated'
            lock_path.touch()
            unrelated.touch()
            with patch.object(owned_stage, 'CANONICAL_LOCK', lock_path):
                with owned_stage.workload_lock(lock_path, 1) as held:
                    with unrelated.open('r+') as wrong:
                        with self.assertRaisesRegex(RuntimeError, 'not the canonical'):
                            with owned_stage.workload_lock(lock_path, 1, wrong.fileno()):
                                self.fail('entered with wrong file')
                    with lock_path.open('r+') as independent:
                        with self.assertRaisesRegex(RuntimeError, 'different lock owner'):
                            with owned_stage.workload_lock(lock_path, 1, independent.fileno()):
                                self.fail('entered through unheld open description')
                    with owned_stage.workload_lock(lock_path, 1, held) as inherited:
                        self.assertEqual(inherited, held)
                    with lock_path.open('r+') as other:
                        with self.assertRaises(BlockingIOError):
                            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_initial_running_receipt_failure_still_waits_for_started_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            marker = root / 'finished'
            real_write = owned_stage.write
            def failing_write(path, value):
                if value.get('status') == 'running':
                    raise OSError('receipt unavailable')
                real_write(path, value)
            program = 'from pathlib import Path; import time; time.sleep(.02); Path(' + repr(str(marker)) + ').write_text("done")'
            with patch.object(owned_stage, 'write', side_effect=failing_write), \
                    patch.object(owned_stage, 'identity', return_value={'ps': 'test child'}), \
                    patch.object(owned_stage, 'disk', return_value=40 * 2**30):
                with self.assertRaisesRegex(OSError, 'receipt unavailable'):
                    owned_stage.run([sys.executable, '-c', program], cwd=root, env={},
                                    out=root / 'command', capacity_root=root)
            self.assertEqual(marker.read_text(), 'done')
            result = json.loads((root / 'command/receipt.json').read_text())
            self.assertEqual((result['status'], result['returncode']), ('finished', 0))

    def test_inventory_rejects_live_directory_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            target = root / 'outside'
            target.mkdir()
            component = root / 'component'
            component.mkdir()
            (component / 'linked').symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, 'directory link'):
                owned_stage.inventory(component)

    @staticmethod
    def bootstrap_layout(root):
        source, sysroot = root / 'checkout', root / 'stage2'
        source.mkdir()
        (source / 'not-a-runtime-file').write_text('source stays outside package')
        for name in ['src', 'rustc-src']:
            directory = sysroot / 'lib/rustlib' / name
            directory.mkdir(parents=True)
            (directory / 'rust').symlink_to(source, target_is_directory=True)
        (sysroot / 'bin').mkdir()
        (sysroot / 'bin/rustc').write_bytes(b'runtime')
        return source, sysroot

    def test_both_bootstrap_source_links_are_recorded_separately_from_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, sysroot = self.bootstrap_layout(Path(temporary).resolve())
            links = owned_stage.bootstrap_source_links(sysroot, source)
            self.assertEqual(links, {f'lib/rustlib/{name}/rust': {
                'link_text': str(source), 'resolved_target': str(source)}
                for name in ['src', 'rustc-src']})
            files = owned_stage.inventory(sysroot, source_checkout=source)
            self.assertEqual(set(files), {'bin/rustc'})
            self.assertEqual(files['bin/rustc']['size'], 7)
            with self.assertRaisesRegex(RuntimeError, 'directory link'):
                owned_stage.inventory(sysroot)

    def test_bootstrap_source_links_reject_a_different_checkout(self):
        for name in ['src', 'rustc-src']:
            with self.subTest(component=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                source, sysroot = self.bootstrap_layout(root)
                foreign = root / 'foreign'
                foreign.mkdir()
                link = sysroot / 'lib/rustlib' / name / 'rust'
                link.unlink()
                link.symlink_to(foreign, target_is_directory=True)
                with self.assertRaisesRegex(RuntimeError, 'source link target'):
                    owned_stage.inventory(sysroot, source_checkout=source)

    def test_bootstrap_source_omission_rejects_extra_directory_contents(self):
        for name in ['src', 'rustc-src']:
            with self.subTest(component=name), tempfile.TemporaryDirectory() as temporary:
                source, sysroot = self.bootstrap_layout(Path(temporary).resolve())
                (sysroot / 'lib/rustlib' / name / 'unexpected.rs').write_text('extra')
                with self.assertRaisesRegex(RuntimeError, 'source directory contents'):
                    owned_stage.bootstrap_source_links(sysroot, source)


if __name__ == '__main__':
    unittest.main()
