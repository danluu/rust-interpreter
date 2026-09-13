"""Pure checks for custom workspace command/results; no subprocesses or builds."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from custom_compiler import Compiler

SPEC = importlib.util.spec_from_file_location('custom_workspace_check',
    ROOT / 'experiments/stable-cgu/check-custom-workspace.py')
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)


class CustomWorkspaceCheckTests(unittest.TestCase):
    def test_exact_custom_release_command(self):
        self.assertEqual(check.command_for('/pinned/cargo', Path('/owned/target')),
            ['/pinned/cargo', 'test', '--workspace', '--release', '--locked', '--offline',
             '--jobs', '2', '--target-dir', '/owned/target'])

    def test_preserves_actual_counts_and_rejects_false_success(self):
        output = ('test result: ok. 3 passed; 0 failed; 1 ignored; 0 measured;\n'
                  'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured;\n')
        result = check.test_results(0, output)
        self.assertEqual((result['passed'], result['ignored']), (5, 1))
        for code, text in [(1, output), (0, ''),
                           (0, 'test result: FAILED. 3 passed; 1 failed; 0 ignored;'),
                           (0, 'test result: ok. 0 passed; 0 failed; 1 ignored;')]:
            with self.subTest(code=code, text=text), self.assertRaises(RuntimeError):
                check.test_results(code, text)

    def test_selects_matching_doctests_and_rejects_ambient_rustdoc(self):
        compiler = Compiler('a' * 64, Path('/owned/sysroot'), {})
        env = check.test_environment(compiler, {'PATH': '/usr/bin', 'RUSTFLAGS': '-O',
                                               'CARGO_PROFILE_RELEASE_OPT_LEVEL': '0'})
        self.assertEqual(env['RUSTC'], '/owned/sysroot/bin/rustc')
        self.assertEqual(env['RUSTDOC'], '/owned/sysroot/bin/rustdoc')
        self.assertEqual(env['PATH'], '/owned/sysroot/bin:/usr/bin')
        self.assertEqual(env['RUST_TEST_THREADS'], '2')
        self.assertNotIn('RUSTFLAGS', env)
        self.assertNotIn('CARGO_PROFILE_RELEASE_OPT_LEVEL', env)
        for name in ['RUSTDOC', 'RUSTDOCFLAGS', 'CARGO_ENCODED_RUSTDOCFLAGS']:
            for value in ['', '/public/rustdoc' if name == 'RUSTDOC' else '-Zunstable-options']:
                with self.subTest(name=name, value=value), self.assertRaises(RuntimeError):
                    check.test_environment(compiler, {name: value})

    def test_repository_cargo_configuration_presence_and_contents_are_frozen(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(check, 'ROOT', Path(temporary)):
            root = Path(temporary)
            for name in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml',
                         'experiments/stable-cgu/check-custom-workspace.py']:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture')
            with patch.object(check, '__file__', str(root / 'experiments/stable-cgu/check-custom-workspace.py')):
                absent = check.source_files()
                self.assertIsNone(absent['.cargo/config'])
                self.assertIsNone(absent['.cargo/config.toml'])
                config = root / '.cargo/config.toml'
                config.parent.mkdir()
                config.write_text('[build]\njobs=2\n')
                included = root / '.cargo/local.toml'
                included.write_text('[alias]\ncheck-all="check --workspace"\n')
                present = check.source_files()
                self.assertNotEqual(absent, present)
                self.assertEqual(present['.cargo/local.toml'], check.file_digest(included))
                config.write_text('[build]\njobs=1\n')
                self.assertNotEqual(present, check.source_files())
                included.unlink()
                included.symlink_to(config)
                with self.assertRaises(RuntimeError):
                    check.source_files()


if __name__ == '__main__':
    unittest.main()
