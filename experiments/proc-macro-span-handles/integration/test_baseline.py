"""Pure boundary controls for the prepared native bridge baseline runner."""
from pathlib import Path
from types import SimpleNamespace
import unittest

import baseline


def output(names=baseline.TESTS, summary='ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out'):
    return ('running 4 tests\n' + ''.join('test ' + name + ' ... ok\n' for name in names)
            + '\ntest result: ' + summary + '; finished in 0.01s\n')


class BaselineContract(unittest.TestCase):
    def test_requires_all_four_names_once_and_unfiltered_success(self):
        self.assertEqual(baseline.test_result(0, output())['passed'], 4)
        for text in (output(baseline.TESTS[:-1]), output(baseline.TESTS + baseline.TESTS[:1]),
                     output(('unrelated_test',) + baseline.TESTS[1:]),
                     output(summary='ok. 4 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out'),
                     output(summary='ok. 3 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out'),
                     output() + output(), output().replace('running 4 tests', 'running 3 tests')):
            with self.assertRaises(RuntimeError):
                baseline.test_result(0, text)
        with self.assertRaises(RuntimeError):
            baseline.test_result(1, output())

    def test_two_commands_use_actual_native_sysroot_and_one_unfiltered_process(self):
        compiler = SimpleNamespace(rustc=Path('/owned/sysroot/bin/rustc'), sysroot=Path('/owned/sysroot'))
        rows = baseline.commands(compiler, Path('/owned/run'))
        self.assertEqual([label for label, _ in rows], ['compile', 'tests'])
        build, run = rows[0][1], rows[1][1]
        self.assertEqual(build[0], str(compiler.rustc))
        self.assertIn('--test', build)
        self.assertEqual(build[build.index('--sysroot') + 1], str(compiler.sysroot))
        self.assertEqual(run, ['/owned/run/artifacts/span_bridge_baseline', '--test-threads=1',
                              '--nocapture', '--format=pretty', '--color=never'])
        self.assertFalse(any(arg.startswith(('-C', '-Z')) for arg in build))

    def test_environment_does_not_forward_compiler_flags_or_loader_overrides(self):
        class Compiler:
            def environment(self, env):
                return dict(env, RUSTC='/owned/sysroot/bin/rustc')
        inherited = dict(HOME='/owned/home', PATH='/unrelated/bin', RUSTFLAGS='--cfg unwanted',
                         RUSTC_WRAPPER='/unrelated/wrapper', RUST_TEST_THREADS='12',
                         RUST_TEST_NOCAPTURE='0', BRIDGE_VALUE='999', SDKROOT='/unrelated/sdk')
        env = baseline.environment(Compiler(), Path('/owned/run'), inherited)
        self.assertEqual(env['RUST_TEST_THREADS'], '1')
        self.assertEqual(env['PATH'], '/usr/bin:/bin:/usr/sbin:/sbin')
        self.assertEqual(env['HOME'], inherited['HOME'])
        self.assertFalse(set(env) & {'RUSTFLAGS', 'RUSTC_WRAPPER', 'BRIDGE_VALUE', 'SDKROOT'})
        with self.assertRaises(RuntimeError):
            baseline.environment(Compiler(), Path('/owned/run'), dict(DYLD_LIBRARY_PATH='/unrelated/lib'))

    def test_native_source_proof_rejects_changed_span_store(self):
        prefix = 'lib/rustlib/host/lib/'
        files = {'bin/rustc': 'rustc'}
        files.update({prefix + 'lib' + crate + '-123.rlib': crate
                      for crate in ('proc_macro', 'std', 'core', 'alloc', 'test')})
        source = 'lib/rustlib/src/rust/library/proc_macro/src/bridge/handle.rs'
        files[source] = 'stock'
        compiler = SimpleNamespace(key=baseline.COMPILER_KEY, host='host', identity=dict(
            files=files, provenance=dict(source_commit=baseline.COMPILER_SOURCE, stage=2)))
        specification = dict(native_source_files={source: 'stock'})
        self.assertEqual(baseline.native_inputs(compiler, specification)[source], 'stock')
        files[source] = 'patched'
        with self.assertRaises(RuntimeError):
            baseline.native_inputs(compiler, specification)


if __name__ == '__main__':
    unittest.main()
