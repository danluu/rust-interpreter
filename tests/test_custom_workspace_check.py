"""Pure checks for custom workspace command/results; no subprocesses or builds."""
import importlib.util
from pathlib import Path
import sys
import unittest

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
        with self.assertRaises(RuntimeError):
            check.test_environment(compiler, {'RUSTDOC': '/public/rustdoc'})


if __name__ == '__main__':
    unittest.main()
