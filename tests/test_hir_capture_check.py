import importlib.util
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hir_capture_check', ROOT / 'experiments/hir-capture-check/check.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class ConfigurationGuardTests(unittest.TestCase):
    def test_new_untracked_source_and_build_configs_change_the_frozen_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            source, owner, cargo = base / 'compiler', base / 'owner', base / 'cargo-home'
            with patch.object(check, 'SOURCE', source), patch.object(check, 'ROOT', owner), \
                    patch.dict(os.environ, {'CARGO_HOME': str(cargo)}):
                original = check.configurations()
                for directory in [source, source / 'build', source / 'src/bootstrap']:
                    config = directory / '.cargo/config.toml'
                    self.assertIn(str(config), original)
                    self.assertIsNone(original[str(config)])
                    config.parent.mkdir(parents=True, exist_ok=True)
                    config.write_text('[build]\nrustflags=["--cfg", "unexpected"]\n')
                    self.assertNotEqual(check.configurations(), original)
                    config.unlink()
                self.assertEqual(check.configurations(), original)

    def test_config_file_and_directory_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            source, owner, cargo = base / 'compiler', base / 'owner', base / 'cargo-home'
            with patch.object(check, 'SOURCE', source), patch.object(check, 'ROOT', owner), \
                    patch.dict(os.environ, {'CARGO_HOME': str(cargo)}):
                target = base / 'external-config'
                target.write_text('[build]\n')
                config = source / '.cargo/config'
                config.parent.mkdir(parents=True)
                config.symlink_to(target)
                with self.assertRaisesRegex(RuntimeError, 'symlink'):
                    check.configurations()
                config.unlink()
                config.parent.rmdir()
                config.parent.symlink_to(cargo, target_is_directory=True)
                with self.assertRaisesRegex(RuntimeError, 'symlink'):
                    check.configurations()


class CopiedArchiveTests(unittest.TestCase):
    def test_pinned_cache_destinations_and_distribution_override(self):
        copies = check.copied_archives()
        self.assertEqual(len(copies), 6)
        for original, expected in check.ARCHIVES.items():
            archive = Path(original)
            directory = ('llvm-aarch64-apple-darwin-cea272fa356e94bd2ee2cadf376630aa0683867a-false'
                         if archive == check.LLVM else '2026-08-30')
            destination = check.SOURCE / 'build/cache' / directory / archive.name
            self.assertEqual(copies[str(destination)], {'source': original, 'sha256': expected})
        with patch.dict(os.environ, {'RUSTUP_DIST_SERVER': 'https://unexpected.example'}, clear=True):
            env = check.environment()
        self.assertEqual(env['RUSTUP_DIST_SERVER'], 'file:///dev/null')
        self.assertEqual(env['CARGO_NET_OFFLINE'], 'true')
        self.assertEqual(env['CARGO_BUILD_JOBS'], '2')

    def seed(self, base):
        original = base / 'donor/component.tar.xz'
        data = b'owned test archive bytes'
        archives = {str(original): hashlib.sha256(data).hexdigest()}
        destination = base / 'source/build/cache/2026-08-30/component.tar.xz'
        destination.parent.mkdir(parents=True)
        destination.write_bytes(data)
        return archives, destination, data

    def test_missing_or_corrupt_copied_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            archives, destination, data = self.seed(base)
            with patch.object(check, 'SOURCE', base / 'source'), patch.object(check, 'ARCHIVES', archives):
                check.verify_copied_archives()
                destination.unlink()
                with self.assertRaisesRegex(RuntimeError, 'missing'):
                    check.verify_copied_archives()
                destination.write_bytes(data + b'corrupt')
                with self.assertRaisesRegex(RuntimeError, 'content changed'):
                    check.verify_copied_archives()
                destination.write_bytes(data)
                check.verify_copied_archives()

    def test_copied_archive_file_and_parent_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            archives, destination, _ = self.seed(base)
            with patch.object(check, 'SOURCE', base / 'source'), patch.object(check, 'ARCHIVES', archives):
                external = base / 'external-archive'
                destination.rename(external)
                destination.symlink_to(external)
                with self.assertRaisesRegex(RuntimeError, 'symlink'):
                    check.verify_copied_archives()
                destination.unlink()
                external.rename(destination)
                moved = base / 'external-directory'
                destination.parent.rename(moved)
                destination.parent.symlink_to(moved, target_is_directory=True)
                with self.assertRaisesRegex(RuntimeError, 'symlink'):
                    check.verify_copied_archives()

    def test_copied_archive_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            archives, destination, _ = self.seed(base)
            with patch.object(check, 'SOURCE', base / 'source'), patch.object(check, 'ARCHIVES', archives):
                destination.unlink()
                destination.mkdir()
                with self.assertRaisesRegex(RuntimeError, 'not an ordinary file'):
                    check.verify_copied_archives()


if __name__ == '__main__':
    unittest.main()
