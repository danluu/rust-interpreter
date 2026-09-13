"""Tool cache invalidation at the real launcher boundary, with compilation stubbed."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import interpreter


class ToolCacheTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ['Cargo.toml', 'Cargo.lock', 'crates/bytecode/Cargo.toml',
                     'crates/bytecode/src/lib.rs', 'crates/mir-export/Cargo.toml',
                     'crates/mir-export/src/main.rs', 'crates/function-cache/src/lib.rs',
                     'crates/rustc-dispatch/src/main.rs']:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture ' + name)
        self.builds = []
        for name, value in [('ROOT', self.root), ('TOOLCHAIN', 'nightly-fixture-a')]:
            context = patch.object(interpreter, name, value)
            context.start()
            self.addCleanup(context.stop)
        context = patch.object(interpreter.subprocess, 'run', side_effect=self.run_command)
        context.start()
        self.addCleanup(context.stop)

    def run_command(self, command, **kwargs):
        if command[0] == 'cargo':
            self.builds.append(list(command))
            release = self.root / '.work/interpreter-build/release'
            release.mkdir(parents=True, exist_ok=True)
            for name in interpreter.CURRENT_TOOL_BINARIES:
                (release / name).write_bytes((name + ':' + command[1]).encode())
            return SimpleNamespace(returncode=0)
        self.assertEqual(command[1:], ['--rust-interp-capabilities'])
        return SimpleNamespace(returncode=0, stdout=json.dumps(dict(schema_version=1)))

    def test_unchanged_sources_and_toolchain_reuse_verified_tools(self):
        first = interpreter._checked_tools_locked()
        self.assertEqual(interpreter._checked_tools_locked(), first)
        self.assertEqual(len(self.builds), 1)

    def test_changing_selected_toolchain_rebuilds_in_a_distinct_namespace(self):
        old_directory, old_key = interpreter._checked_tools_locked()
        interpreter.TOOLCHAIN = 'nightly-fixture-b'
        directory, key = interpreter._checked_tools_locked()
        self.assertNotEqual(key, old_key)
        self.assertNotEqual(directory, old_directory)
        self.assertEqual([command[1] for command in self.builds], ['+nightly-fixture-a', '+nightly-fixture-b'])
        self.assertIn(b'nightly-fixture-b', (directory / 'rust-interp-mir-export').read_bytes())

    def test_changing_compiled_source_rebuilds(self):
        _, old_key = interpreter._checked_tools_locked()
        (self.root / 'crates/bytecode/src/lib.rs').write_text('changed runtime source')
        _, key = interpreter._checked_tools_locked()
        self.assertNotEqual(key, old_key)
        self.assertEqual(len(self.builds), 2)

    def test_explicit_old_tool_keys_remain_available_after_a_toolchain_change(self):
        directory, key = interpreter._checked_tools_locked()
        interpreter.TOOLCHAIN = 'nightly-fixture-b'
        self.assertEqual(interpreter.installed_tools(key), (directory, key))
        self.assertEqual(len(self.builds), 1)

    def test_unused_archived_backend_crates_do_not_rebuild_the_custom_tool(self):
        first = interpreter._checked_tools_locked()
        for name in ['function-cache/src/lib.rs', 'rustc-dispatch/src/main.rs']:
            (self.root / 'crates' / name).write_text('changed archived backend')
        self.assertEqual(interpreter._checked_tools_locked(), first)
        self.assertEqual(len(self.builds), 1)


if __name__ == '__main__':
    unittest.main()
