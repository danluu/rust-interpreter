import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import toolchain_lookup as lookup


class ToolchainLookupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.toolchain = 'nightly-2026-09-08'
        self.host = 'aarch64-apple-darwin'
        self.home = self.root/'rustup'
        self.original = self.home/'toolchains'/(self.toolchain+'-'+self.host)
        for part in ['bin', 'lib/rustlib/'+self.host+'/lib']:
            (self.original/part).mkdir(parents=True)
        for part in ['bin/rustc', 'lib/librustc_driver.dylib',
                     'lib/rustlib/multirust-channel-manifest.toml',
                     'lib/rustlib/'+self.host+'/lib/libstd.dylib']:
            (self.original/part).write_text('initial bytes')
        self.bin = self.root/'bin'; self.bin.mkdir()
        self.proxy = self.bin/'rustup'; self.proxy.write_text('proxy')
        self.proxy.chmod(0o755)
        (self.bin/'rustc').symlink_to(self.proxy)
        self.environment = patch.dict(os.environ, dict(PATH=str(self.bin),
                                      HOME=str(self.root), RUSTUP_HOME=str(self.home)), clear=True)
        self.environment.start(); self.addCleanup(self.environment.stop)
        self.compiler = 'rustc fixture\nhost: '+self.host+'\ncommit-hash: original\n'
        self.probe_patch = patch.object(lookup, '_discover', return_value=(self.compiler, self.original))
        self.probe = self.probe_patch.start(); self.addCleanup(self.probe_patch.stop)
        self.cache = self.root/'cache'

    def cached(self):
        return lookup.compiler_identity(self.toolchain, self.cache)

    def test_hit_reuses_exact_identity_without_compiler_processes(self):
        self.assertEqual(self.cached(), (self.compiler, self.original, 'miss'))
        self.assertEqual(self.probe.call_count, 2)
        self.probe.reset_mock()
        self.assertEqual(self.cached(), (self.compiler, self.original, 'hit'))
        self.probe.assert_not_called()
        self.assertEqual(lookup.compiler_identity(self.toolchain)[2], 'fresh')
        self.probe.assert_called_once()

    def test_compiler_libraries_and_manifests_invalidate_even_with_restored_mtime(self):
        self.cached()
        for name in ['bin/rustc', 'lib/librustc_driver.dylib',
                     'lib/rustlib/multirust-channel-manifest.toml',
                     'lib/rustlib/'+self.host+'/lib/libstd.dylib']:
            path = self.original/name
            with self.subTest(name=name):
                before = path.stat()
                path.write_text('changed bytes')
                os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
                self.assertEqual(self.cached()[2], 'miss')
                self.assertEqual(self.cached()[2], 'hit')
        (self.original/'lib/new-driver.dylib').write_text('new')
        self.assertEqual(self.cached()[2], 'miss')

    def test_proxy_settings_and_environment_invalidate_without_recording_secrets(self):
        self.cached()
        self.proxy.write_text('proxy upgrade')
        self.assertEqual(self.cached()[2], 'miss')
        (self.home/'settings.toml').write_text('default_host = "'+self.host+'"')
        self.assertEqual(self.cached()[2], 'miss')
        secret = 'https://user:credential@example.invalid'
        with patch.dict(os.environ, {'RUSTUP_DIST_SERVER': secret}):
            self.assertEqual(self.cached()[2], 'miss')
            self.assertEqual(self.cached()[2], 'hit')
            self.assertFalse(any(secret in p.read_text() for p in self.cache.glob('*.json')))

    def test_unrecognized_or_custom_dispatch_keeps_fresh_discovery(self):
        for name in ['nightly', 'stable', 'my-custom', '/custom/sysroot']:
            with self.subTest(name=name):
                self.assertEqual(lookup.compiler_identity(name, self.cache)[2], 'unsupported')
        with patch.dict(os.environ, {'DYLD_LIBRARY_PATH': '/custom'}):
            self.assertEqual(self.cached()[2], 'unsupported')
        (self.bin/'rustc').unlink()
        (self.bin/'rustc').write_text('a custom compiler dispatcher')
        (self.bin/'rustc').chmod(0o755)
        self.assertEqual(self.cached()[2], 'unsupported')
        self.assertFalse(self.cache.exists())

    def test_sysroot_replacement_and_symlink_are_not_silently_reused(self):
        self.cached()
        replacement = self.original.with_name('custom-installation')
        self.original.rename(replacement)
        self.original.symlink_to(replacement, target_is_directory=True)
        self.assertEqual(self.cached()[2], 'uncached')
        self.probe.assert_called()  # Old record cannot supply the identity.

    def test_corrupted_partial_or_oversized_records_are_cache_misses(self):
        self.cached()
        path = next(self.cache.glob('*.json'))
        for data in ['{', 'null', '{}', 'x'*(128*1024+1),
                     json.dumps({'payload': {}, 'sha256': lookup._digest({})})]:
            with self.subTest(data=data[:30]):
                path.write_text(data)
                self.assertEqual(self.cached()[2], 'miss')
                self.assertEqual(self.cached()[2], 'hit')
        changed = json.loads(path.read_text())
        changed['payload']['compiler'] = 'corrupt-but-valid-json'
        path.write_text(json.dumps(changed))
        self.assertEqual(self.cached()[2], 'miss')

    def test_installer_changes_during_discovery_are_not_published(self):
        self.probe.side_effect = [(self.compiler, self.original),
                                 (self.compiler.replace('original', 'updated'), self.original)]
        self.assertEqual(self.cached()[2], 'unstable')
        self.assertFalse(self.cache.exists())

    def test_cache_symlink_does_not_overwrite_its_target(self):
        self.cached()
        path = next(self.cache.glob('*.json'))
        target = self.root/'other'; target.write_text('preserve')
        path.unlink(); path.symlink_to(target)
        self.assertEqual(self.cached()[2], 'miss')
        self.assertEqual(target.read_text(), 'preserve')
        self.assertFalse(path.is_symlink())


if __name__ == '__main__':
    unittest.main()
