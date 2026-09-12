import contextlib
import fcntl
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import interpreter
from workspace_cache import cache_subdirectory, external_cache_root, workspace_cache_base


class WorkspaceCacheTests(unittest.TestCase):
    def test_default_path_and_owner_tool_selection_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            owner = parent / 'checkout'
            self.assertEqual(workspace_cache_base(owner), owner / '.work/interpreter-workspaces')
            self.assertFalse(owner.exists())
            unrelated = parent / 'user-file'; unrelated.write_text('preserve')
            base = workspace_cache_base(owner, parent)
            self.assertEqual(base, workspace_cache_base(owner, parent))
            other = workspace_cache_base(parent / 'another-checkout', parent)
            self.assertNotEqual(base, other)
            paths = [cache_subdirectory(base, tool, selection)
                     for tool, selection in [('a' * 64, 'x'), ('b' * 64, 'x'), ('a' * 64, 'y')]]
            self.assertEqual(len(set(paths)), 3)
            self.assertEqual(unrelated.read_text(), 'preserve')

    def test_unowned_and_changed_markers_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory); owner = parent / 'checkout'
            root = external_cache_root(parent, owner)
            marker = root / '.rust-interp-cache.json'
            original = marker.read_bytes()
            for content in [b'{}', b'{', b'x' * 4097,
                            json.dumps(dict(schema_version=1, kind='rust-interp-cache', owner='someone else')).encode()]:
                marker.write_bytes(content)
                with self.subTest(content=content[:30]), self.assertRaises(ValueError):
                    external_cache_root(parent, owner)
                self.assertEqual(marker.read_bytes(), content)
            marker.unlink()
            with self.assertRaises(ValueError): external_cache_root(parent, owner)
            self.assertEqual(list(root.iterdir()), [])
            marker.write_bytes(original)
            self.assertEqual(external_cache_root(parent, owner), root)

    def test_symlinks_and_missing_parents_do_not_create_or_modify_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory); owner = parent / 'checkout'
            missing = parent / 'missing'
            with self.assertRaises(ValueError): workspace_cache_base(owner, missing)
            self.assertFalse(missing.exists())
            alias = parent / 'alias'; alias.symlink_to(parent, target_is_directory=True)
            with self.assertRaises(ValueError): workspace_cache_base(owner, alias)
            base = workspace_cache_base(owner, parent)
            target = parent / 'unrelated'; target.mkdir()
            replaced = base / ('a' * 64); replaced.symlink_to(target, target_is_directory=True)
            with self.assertRaises(ValueError): cache_subdirectory(base, 'a' * 64, 'entry')
            self.assertEqual(list(target.iterdir()), [])
            marker = base.parent / '.rust-interp-cache.json'; marker.unlink(); marker.symlink_to(missing)
            with self.assertRaises(ValueError): workspace_cache_base(owner, parent)
            self.assertFalse(missing.exists())

    def test_invalid_parent_is_rejected_before_tool_build_or_cargo(self):
        with tempfile.TemporaryDirectory() as directory:
            arguments = ['interpreter.py', '--package', 'fixture', '--entry', 'entry',
                         '--workspace-cache-root', str(Path(directory) / 'missing')]
            with patch.object(sys, 'argv', arguments), patch.object(interpreter, 'checked_tools') as tools, \
                    patch.object(interpreter.subprocess, 'run') as run, contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit) as error:
                interpreter.main()
            self.assertEqual(error.exception.code, 2)
            tools.assert_not_called(); run.assert_not_called()

    def test_launcher_routes_cargo_sidecars_and_vm_under_the_same_locked_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory); owner = parent / 'checkout'; owner.mkdir()
            tools = parent / 'tools'; tools.mkdir()
            (tools / 'ready.json').write_text(json.dumps({'rust-interp-vm': 'v', 'rust-interp-mir-export': 'e'}))
            scratch = parent / 'scratch'; scratch.mkdir()
            calls = []; paths = []; manifests = []
            def run(command, **kwargs):
                calls.append(command)
                env = kwargs['env']
                work = Path(env['CARGO_TARGET_DIR']).parent
                with (work / 'invocation.lock').open('a') as lock:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                if command[0] == 'cargo':
                    paths.append(work); manifests.append(env['RUST_INTERP_OUTPUT'])
                    self.assertEqual(env['RUSTC_WRAPPER'], str(tools / 'rust-interp-mir-export'))
                    self.assertTrue(work.is_relative_to(scratch.resolve()))
                    self.assertEqual(Path(env['RUST_INTERP_OUTPUT']), work / 'program.rbc')
                    metadata = work / 'target/debug/deps/fixture.rmeta'
                    metadata.parent.mkdir(parents=True, exist_ok=True)
                    Path(str(metadata) + '.rbc').write_bytes(b'fixture sidecar')
                    event = dict(reason='compiler-artifact', profile=dict(test=False), filenames=[str(metadata)])
                    return subprocess.CompletedProcess(command, 0, json.dumps(event))
                self.assertEqual(command[0], str(tools / 'rust-interp-vm'))
                self.assertEqual(Path(command[-1]), work / 'target/debug/deps/fixture.rmeta.rbc')
                return subprocess.CompletedProcess(command, 0)
            base = ['interpreter.py', '--package', 'fixture', '--entry', 'entry',
                    '--manifest-path', str(owner / 'Cargo.toml'), '--workspace-cache-root', str(scratch),
                    '--tool-key', 'a' * 64]
            with patch.object(interpreter, 'ROOT', owner), \
                    patch.object(interpreter, 'installed_tools', return_value=(tools, 'a' * 64)), \
                    patch.object(interpreter.subprocess, 'run', run), \
                    patch.dict(interpreter.os.environ, {'CARGO_TARGET_DIR': str(parent / 'unrelated')}):
                for namespace in ['first', 'first', 'second']:
                    with patch.object(sys, 'argv', base + ['--cache-namespace', namespace]):
                        self.assertEqual(interpreter.main(), 0)
            self.assertEqual(len(calls), 6)
            self.assertEqual(paths[0], paths[1]); self.assertNotEqual(paths[0], paths[2])
            self.assertEqual(manifests[0], manifests[1]); self.assertNotEqual(manifests[0], manifests[2])
            self.assertFalse((owner / '.work').exists())
            self.assertFalse((parent / 'unrelated').exists())


if __name__ == '__main__': unittest.main()
