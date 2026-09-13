"""Real compiler correctness histories, opt-in and under the caller's shared lock."""
import hashlib
import json
import os
from pathlib import Path
import unittest

import test_borrowck_cache as helpers


PREFIX = 'rust-interp-query-cache-retention: '
NAMESPACE = '.rust-interp-query-demand-v1'


@unittest.skipUnless(os.environ.get('RUST_INTERP_TEST_EXPORTER'),
                     'set RUST_INTERP_TEST_EXPORTER to run compiler correctness tests')
class DemandRetentionTests(unittest.TestCase):
    setUp = helpers.BorrowckCacheTests.setUp
    invoke = helpers.BorrowckCacheTests.invoke
    assert_success = helpers.BorrowckCacheTests.assert_success
    assert_output = helpers.BorrowckCacheTests.assert_output
    diagnostics = staticmethod(helpers.BorrowckCacheTests.diagnostics)
    native_matches = helpers.BorrowckCacheTests.native_matches

    @classmethod
    def setUpClass(cls):
        helpers.BorrowckCacheTests.setUpClass.__func__(cls)

    def compile(self, source, mode='demand', native=False, env_overrides=None, **kwargs):
        env = dict(env_overrides or {})
        if not native:
            env['RUST_INTERP_QUERY_CACHE_RETENTION'] = mode
        return helpers.BorrowckCacheTests.compile(self, source, mode='off', native=native,
                                                   env_overrides=env, **kwargs)

    def report(self, result, disabled=False):
        records = [json.loads(line[len(PREFIX):]) for line in result.stderr.splitlines()
                   if line.startswith(PREFIX)]
        self.assertEqual(len(records), 1, result.stderr)
        report = records[0]
        self.assertEqual(report['mode'], 'demand')
        self.assertTrue(report['strict_checking'])
        self.assertEqual(bool(report['disabled_reason']), disabled, report)
        if disabled:
            self.assertFalse(report['provider_installed'], report)
            self.assertEqual(report['original_incremental_directory'],
                             report['effective_incremental_directory'], report)
            self.assertEqual(report['promotion_passes_omitted'], 0, report)
        else:
            original = Path(report['original_incremental_directory'])
            self.assertEqual(Path(report['effective_incremental_directory']), original / NAMESPACE)
            self.assertTrue(report['provider_installed'], report)
            if result.returncode == 0:
                self.assertEqual(report['promotion_passes_omitted'], 1, report)
                self.assertGreater(report['serialized_bytes'], 7, report)
                self.assertGreaterEqual(report['serialization_attempts'], 1, report)
        return report

    @staticmethod
    def source(value, calls=False):
        return ('#![allow(dead_code)]\n'
                'fn changed() -> u32 { ' + str(value) + ' }\n'
                'fn ordinary(x: u32) -> u32 { x + 5 }\n'
                'fn opaque() -> impl Iterator<Item=u32> { [11, 13].into_iter() }\n'
                'fn generic<T: Into<u32>>(x: T) -> u32 { x.into() + 7 }\n'
                'fn main() { println!("{}", changed()' +
                (' + ordinary(2) + opaque().sum::<u32>() + generic(3u8)' if calls else '') +
                '); }\n')

    def test_edited_histories_new_value_demands_and_stock_round_trips(self):
        # Two warm sparse steps can evict previously checked, undemanded values.
        # Newly reachable generic/opaque functions then demand their values.
        states = [('demand', 1, False), ('demand', 2, False), ('demand', 3, False),
                  ('demand', 4, True), ('off', 5, True), ('demand', 6, False),
                  ('demand', 7, True), ('off', 8, False), ('demand', 9, True)]
        for mode, value, calls in states:
            with self.subTest(mode=mode, value=value, calls=calls):
                source = self.source(value, calls)
                expected = str(value + (41 if calls else 0))
                result, executable = self.compile(source, mode=mode)
                self.assert_success(result)
                self.assert_output(executable, expected)
                self.native_matches(source, result, expected)
                if mode == 'demand':
                    self.report(result)
        original = self.work / 'fixture-custom-incr'
        self.assertTrue(list((original / NAMESPACE).glob('*/s-*/query-cache.bin')))
        self.assertTrue([path for path in original.glob('*/s-*/query-cache.bin')
                         if path.parts[-4] != NAMESPACE])

    def test_diagnostics_errors_and_failed_session_publication(self):
        valid = ('pub fn entry() -> u32 { let mut warning = 2; warning }\n'
                 '#[expect(unused_variables)] fn expectation() { let unused = 3; }\n')
        flags = dict(crate_type='lib', extra=('--emit=metadata',),
                     output_path=self.work / 'libfixture.rmeta')
        for _ in range(3):
            result, _ = self.compile(valid, **flags)
            self.assert_success(result)
            self.native_matches(valid, result, **flags)
            self.assertIn('unused_mut', [row[1] for row in self.diagnostics(result)])
            report = self.report(result)
            self.assertGreater(report['retained_side_effects'], 0, report)
        namespace = self.work / 'fixture-custom-incr' / NAMESPACE
        successful = {path for path in namespace.glob('*/s-*')
                      if path.is_dir() and not path.name.endswith('-working')}
        for error_body in ["fn uncalled() -> &'static u32 { let local = 1; &local }\n",
                           'fn uncalled() -> u32 { "wrong" }\n']:
            invalid = valid + error_body
            result, _ = self.compile(invalid, **flags)
            self.assertNotEqual(result.returncode, 0)
            self.native_matches(invalid, result, **flags)
            current = {path for path in namespace.glob('*/s-*')
                       if path.is_dir() and not path.name.endswith('-working')}
            self.assertTrue(current <= successful, current - successful)
        unfulfilled = valid.replace('let unused = 3;', '')
        for source in [unfulfilled, valid]:
            result, _ = self.compile(source, **flags)
            self.assert_success(result)
            self.native_matches(source, result, **flags)
            self.report(result)

    def test_unsupported_options_use_stock_cache_before_context_creation(self):
        for mode, extra, disabled in [('demand', (), False),
                ('demand', ('-Zincremental-verify-ich=yes',), True),
                ('demand', (), False), ('demand', ('-Zquery-dep-graph=yes',), True),
                ('demand', (), False), ('off', (), False)]:
            with self.subTest(mode=mode, extra=extra):
                source = self.source(12, True)
                result, executable = self.compile(source, mode=mode, extra=extra)
                self.assert_success(result)
                self.assert_output(executable, '53')
                self.native_matches(source, result, '53', extra=extra)
                if mode == 'demand':
                    self.report(result, disabled)
        result, executable = self.compile(self.source(9), incremental=False)
        self.assert_success(result)
        self.report(result, True)
        self.assert_output(executable, '9')

    def test_prior_successful_cache_inode_is_not_modified(self):
        result, _ = self.compile(self.source(1))
        self.assert_success(result)
        report = self.report(result)
        namespace = Path(report['effective_incremental_directory'])
        previous = list(namespace.glob('*/s-*/query-cache.bin'))
        self.assertEqual(len(previous), 1)
        previous = previous[0]
        # A private hard link models rustc's inherited previous-session inode.
        preserved = self.work / 'prior-query-cache.bin'
        os.link(previous, preserved)
        digest = hashlib.sha256(preserved.read_bytes()).hexdigest()
        result, _ = self.compile(self.source(2))
        self.assert_success(result)
        self.report(result)
        self.assertEqual(hashlib.sha256(preserved.read_bytes()).hexdigest(), digest)
        self.assertFalse(list(namespace.glob('*/s-*/query-cache.demand-*.new')))

    def test_foreign_static_allocations_tls_and_link_attributes(self):
        dependency = self.work / 'libretention_dep.rlib'
        source = ('#[unsafe(no_mangle)] pub static RETENTION_IMPORTED: i64 = 23;\n'
                  'pub fn marker() -> i64 { 2 }\n')
        built, _ = self.compile(source, native=True, name='retention_dep',
                                crate_type='rlib', output_path=dependency)
        self.assert_success(built)
        original = ('#![feature(thread_local)]\n'
            'unsafe extern "C" { #[link_name="RETENTION_IMPORTED"] static IMPORTED: i64; }\n'
            'const POINTER: &i64 = unsafe { &IMPORTED };\n'
            '#[used] #[unsafe(link_section="__DATA,__retention")] static LOCAL: i64 = 17;\n'
            '#[thread_local] static THREAD: i64 = 7;\n'
            'const LOCAL_POINTER: &i64 = &LOCAL;\n'
            'fn changed() -> i64 { VALUE }\n'
            'fn main() { println!("{}", changed() + *POINTER + *LOCAL_POINTER + THREAD + retention_dep::marker()); }\n')
        flags = ('--extern', 'retention_dep=' + str(dependency))
        for value in range(4):
            source = original.replace('VALUE', str(value))
            result, executable = self.compile(source, extra=flags)
            self.assert_success(result)
            self.report(result)
            self.assert_output(executable, str(value + 49))
            self.native_matches(source, result, str(value + 49), extra=flags)
        # Metadata-only binaries do not force native codegen or rlib metadata's
        # eager attribute reads. This is a distinct cache-demand history.
        for value in range(4, 8):
            source = original.replace('VALUE', str(value))
            arguments = dict(extra=(*flags, '--emit=metadata'), history='metadata',
                             output_path=self.work / 'binary.rmeta')
            result, _ = self.compile(source, **arguments)
            self.assert_success(result)
            self.report(result)
            self.native_matches(source, result, **dict(arguments, history='native-metadata'))
        invalid = source + 'const BAD_THREAD_ADDRESS: &i64 = &THREAD;\n'
        result, _ = self.compile(invalid, extra=flags)
        self.assertNotEqual(result.returncode, 0)
        self.native_matches(invalid, result, extra=flags)

    def test_selected_export_matches_stock_and_checks_uncalled_bodies(self):
        original = (helpers.FIXTURES / 'test_export.rs').read_text()
        flags = ('--test', '--emit=metadata', '-Zalways-encode-mir=yes', '-Zmir-opt-level=3')
        bytecode = self.work / 'selected.rbc'
        control = self.work / 'control.rbc'
        for value in [3, 7, 9, 11]:
            source = original.replace('3 // changed body', str(value) + ' // changed body')
            env = {'RUST_INTERP_EXPORT_CRATE': 'fixture', 'RUST_INTERP_EXPORT_TEST': '1',
                   'RUST_INTERP_ENTRY': 'selected', 'RUST_INTERP_OUTPUT': str(bytecode),
                   'RUST_INTERP_BORROWCK_CACHE': 'reuse'}
            arguments = dict(crate_type='lib', extra=flags,
                             output_path=self.work / 'selected.rmeta')
            result, _ = self.compile(source, env_overrides=env, **arguments)
            self.assert_success(result)
            self.report(result)
            plain, _ = self.compile(source, mode='off', history='control',
                env_overrides=dict(env, RUST_INTERP_OUTPUT=str(control),
                                   RUST_INTERP_BORROWCK_CACHE='off'), **arguments)
            self.assert_success(plain)
            self.assertEqual(self.diagnostics(result), self.diagnostics(plain))
            self.assertEqual(bytecode.read_bytes(), control.read_bytes())
            native, executable = self.compile(source, native=True, crate_type='lib',
                                               extra=('--test', '-Zmir-opt-level=3'))
            self.assert_success(native)
            self.assertEqual(self.diagnostics(result), self.diagnostics(native))
            self.assert_success(self.invoke([executable, '--exact', 'selected', '--test-threads=1']))
            if self.vm:
                execution = self.invoke([self.vm, '--engine', 'interpreter', bytecode])
                self.assert_success(execution)
                self.assertEqual(execution.stdout, '0\n')
        invalid = source + '\nfn uncalled_bad() -> u32 { "bad" }\n'
        result, _ = self.compile(invalid, env_overrides=env, **arguments)
        self.assertNotEqual(result.returncode, 0)
        self.native_matches(invalid, result, crate_type='lib', extra=('--test', '-Zmir-opt-level=3'))


if __name__ == '__main__':
    unittest.main()
