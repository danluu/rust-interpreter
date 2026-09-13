"""Synthetic installation/provenance tests; no compiler or Cargo processes."""
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import custom_compiler as custom

HOST = 'aarch64-apple-darwin'
PROVENANCE = dict(stage=2, source_commit='a' * 40, patch_sha256='b' * 64,
                  bootstrap_sha256='c' * 64, build_receipt_sha256='d' * 64)


def thaw(root):
    for path in [root, *root.rglob('*')]:
        if not path.is_symlink():
            path.chmod(0o755 if path.is_dir() else 0o644)


def fake_install(root):
    source = root / 'packaged'
    files = ['bin/rustc', 'lib/librustc_driver-fixture.dylib']
    lib = 'lib/rustlib/' + HOST + '/lib/'
    files += [lib + 'lib' + crate + '-fixture.rlib' for crate in ['core', 'alloc', 'std', 'test', 'proc_macro']]
    files += [lib + 'lib' + crate + '-fixture.rmeta' for crate in custom.PRIVATE_CRATES]
    files += ['lib/rustlib/src/rust/library/' + name for name in
              ['Cargo.toml', 'Cargo.lock', 'core/src/lib.rs', 'std/src/lib.rs', 'proc_macro/src/lib.rs']]
    for name in files:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fixture data')
    (source / 'bin/rustc').chmod(0o755)
    def probe(command, **kwargs):
        if command[-1] == '-vV':
            return 'rustc fixture\nhost: ' + HOST + '\ncommit-hash: ' + 'a' * 40 + '\n'
        if command[-1] == 'sysroot':
            return str(Path(command[0]).parents[1]) + '\n'
        if command[-1] == '-Zhelp':
            return 'stable-cgu-partitioning = val\n'
        raise AssertionError(command)
    with patch.object(custom, 'audit_macos_libraries'), \
         patch.object(custom.subprocess, 'check_output', side_effect=probe):
        return custom.install_compiler(root, source, PROVENANCE)


class CustomCompilerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.addCleanup(thaw, self.root)
        self.compiler = fake_install(self.root)

    def test_owned_installation_hits_need_no_compiler_process_or_content_rehash(self):
        with patch.object(custom.subprocess, 'check_output') as probe, \
             patch.object(custom, 'file_digest') as hash_file:
            self.assertEqual(custom.load_compiler(self.root, self.compiler.key), self.compiler)
        probe.assert_not_called()
        hash_file.assert_not_called()
        self.assertEqual(self.compiler.rustc, self.compiler.sysroot / 'bin/rustc')

    def test_changed_bytes_with_restored_size_mtime_and_permissions_are_rejected(self):
        path = self.compiler.sysroot / 'lib/librustc_driver-fixture.dylib'
        original = path.stat()
        path.chmod(0o644)
        path.write_bytes(b'changed data')
        path.chmod(0o444)
        os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
        self.assertEqual(path.stat().st_size, original.st_size)
        self.assertEqual(path.stat().st_mtime_ns, original.st_mtime_ns)
        with self.assertRaisesRegex(RuntimeError, 'installation changed'):
            custom.load_compiler(self.root, self.compiler.key)

    def test_extra_files_writable_installations_and_symlinks_are_rejected(self):
        self.compiler.sysroot.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, 'installation changed'):
            custom.load_compiler(self.root, self.compiler.key)
        (self.compiler.sysroot / 'unexpected').write_text('extra')
        with self.assertRaisesRegex(RuntimeError, 'installation changed'):
            custom.load_compiler(self.root, self.compiler.key)
        (self.compiler.sysroot / 'redirect').symlink_to('/tmp')
        with self.assertRaisesRegex(RuntimeError, 'symlink'):
            custom.load_compiler(self.root, self.compiler.key)

    def test_partial_components_stage1_and_wrong_ownership_are_rejected(self):
        files = self.compiler.identity['files'].copy()
        del files['lib/rustlib/' + HOST + '/lib/librustc_middle-fixture.rmeta']
        with self.assertRaisesRegex(RuntimeError, 'missing rustc-dev rustc_middle'):
            custom.require_complete(files, HOST)
        with self.assertRaisesRegex(RuntimeError, 'stage2'):
            custom.install_compiler(self.root, self.root / 'packaged', dict(PROVENANCE, stage=1))
        ready_path = self.compiler.sysroot.parent / 'ready.json'
        ready = json.loads(ready_path.read_text())
        ready['owner'] = '/another/worktree'
        ready_path.chmod(0o644)
        ready_path.write_text(json.dumps(ready))
        with self.assertRaisesRegex(RuntimeError, 'ownership'):
            custom.load_compiler(self.root, self.compiler.key)

    def test_custom_selection_rejects_compiler_and_loader_overrides(self):
        environment = self.compiler.environment({'PATH': '/bin', 'FEATURE': 'preserved'})
        self.assertEqual(environment['RUSTC'], str(self.compiler.rustc))
        self.assertTrue(environment['PATH'].startswith(str(self.compiler.sysroot / 'bin') + os.pathsep))
        self.assertEqual(environment['FEATURE'], 'preserved')
        for override in [dict(RUSTC='/stock/rustc'), dict(RUST_SYSROOT='/stock'),
                         dict(DYLD_LIBRARY_PATH='/live/compiler'), dict(LD_PRELOAD='/unknown')]:
            with self.assertRaises(RuntimeError):
                self.compiler.environment(override)

    def test_tool_association_rejects_missing_compiler_mismatched_compiler_and_binary_manifest(self):
        binaries = {'rust-interp-vm': 'e' * 64, 'rust-interp-mir-export': 'f' * 64}
        composition = dict(kind=custom.TOOL_POLICY, compiler_key=self.compiler.key,
                           compiler_sysroot=str(self.compiler.sysroot), binaries=binaries)
        key = custom.digest(composition)
        tools = self.root / 'tools'; tools.mkdir()
        (tools / 'compiler.json').write_text(json.dumps(composition))
        (tools / 'ready.json').write_text(json.dumps(binaries))
        custom.validate_tool_compiler(tools, key, self.compiler)
        with self.assertRaisesRegex(RuntimeError, 'require --compiler-key'):
            custom.validate_tool_compiler(tools, key, None)
        with self.assertRaisesRegex(RuntimeError, 'different compiler'):
            custom.validate_tool_compiler(tools, key, replace(self.compiler, key='0' * 64))
        (tools / 'ready.json').write_text('{}')
        with self.assertRaisesRegex(RuntimeError, 'binary mismatch'):
            custom.validate_tool_compiler(tools, key, self.compiler)

    def test_macos_audit_rejects_live_build_library_paths(self):
        with patch.object(custom.sys, 'platform', 'darwin'), \
             patch.object(custom.subprocess, 'check_output', return_value=
                'rustc:\n\t/live/build/libLLVM.dylib (compatibility version 0.0.0, current version 0.0.0)\n'):
            with self.assertRaisesRegex(RuntimeError, 'outside its installation'):
                custom.audit_macos_libraries(self.compiler.sysroot)


if __name__ == '__main__':
    unittest.main()
