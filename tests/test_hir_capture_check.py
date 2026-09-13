import importlib.util
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


if __name__ == '__main__':
    unittest.main()
