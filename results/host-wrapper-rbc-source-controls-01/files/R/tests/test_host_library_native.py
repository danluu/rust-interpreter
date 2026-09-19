"""Opt-in real host-library histories; caller holds the canonical workload lock.

Reuse the existing proc-macro fixture and native command/diagnostic logging.
No tools, std libraries or dependencies are built/downloaded by setup.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

import test_host_proc_macro_native as macro_fixture

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import host_library_opt


@unittest.skipUnless(all(os.environ.get(name) for name in
    ['RUST_INTERP_TEST_EXPORTER', 'RUST_INTERP_TEST_STD_SYSROOT', 'RUST_INTERP_TEST_VM',
     'RUST_INTERP_TEST_ARTIFACT_DIR']),
    'requires an admitted host-library toolset, prepared std MIR, VM and retained artifacts')
class HostLibraryNativeTests(unittest.TestCase):
    invoke = macro_fixture.HostProcMacroNativeTests.invoke
    assert_success = macro_fixture.HostProcMacroNativeTests.assert_success
    diagnostics = staticmethod(macro_fixture.HostProcMacroNativeTests.diagnostics)

    @classmethod
    def setUpClass(cls):
        macro_fixture.HostProcMacroNativeTests.setUpClass.__func__(cls)

    def setUp(self):
        macro_fixture.HostProcMacroNativeTests.setUp(self)
        self.work = self.work.resolve(strict=True)
        self.sequence = 0
        version = self.invoke([self.rustc, '-vV']); self.assert_success(version)
        self.assertIn('commit-hash: ' + host_library_opt.COMPILER_COMMIT, version.stdout)
        self.host = next(line[6:] for line in version.stdout.splitlines() if line.startswith('host: '))
        probe = self.invoke([self.exporter, '--rust-interp-capabilities']); self.assert_success(probe)
        capabilities = json.loads(probe.stdout)
        self.assertIn(host_library_opt.POLICY, capabilities['export_options'])
        self.assertIn('compiler-argv-record-v1', capabilities['export_options'])
        self.assertEqual(capabilities['host_library_opt'], host_library_opt.CAPABILITY)
        self.assertEqual(Path(capabilities['compiler_sysroot']).resolve(strict=True), self.rustc.parent.parent)
        probe = self.invoke([self.wrapper, '--rust-interp-host-library-capability']); self.assert_success(probe)
        lines = probe.stdout.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0]), host_library_opt.CAPABILITY)
        self.assertEqual(lines[1], capabilities['compiler_sysroot'])
        self.compiled_sysroot = lines[1]

    def environment(self, mode):
        return dict(self.base_env, RUST_INTERP_STD_SYSROOT=str(self.rustc.parent.parent),
            RUST_INTERP_STD_TARGET=self.host, RUST_INTERP_EXPORT_PACKAGE='selected_elsewhere',
            CARGO_PKG_NAME='fixture_library', RUST_INTERP_HOST_LIBRARY_OPT=mode,
            RUST_INTERP_FUNCTION_CACHE='auto')

    @staticmethod
    def values(args, option):
        return [args[index + 1] if arg == option else arg[len(option) + 1:]
                for index, arg in enumerate(args)
                if arg == option or arg.startswith(option + '=')]

    def assert_forwarded(self, path, original, mode, *, cwd, selected=False, std=None):
        fields = path.read_bytes().decode().split('\0')
        self.assertEqual(fields[:4], ['rust-interp-compiler-argv-v1',
            'exported' if selected else 'native', self.compiled_sysroot, str(cwd)])
        self.assertEqual(fields[-1], '')
        self.assertEqual(original[0], str(self.rustc))
        kinds = self.values(original, '--crate-type')
        target = self.values(original, '--target')
        library = kinds in [['lib'], ['rlib']]
        expected = list(original)
        if target:
            self.assertEqual(target, [self.host])
            self.assertFalse(self.values(original, '--sysroot'))
            expected += ['--sysroot', str(std)]
        if library:
            expected.append('-Zalways-encode-mir=yes')  # Existing wrapper policy, both arms.
        linked = any(emit.split('=')[0] == 'link' for value in self.values(original, '--emit') for emit in value.split(','))
        eligible = library and linked and not target and not selected and '--test' not in original
        if mode == 'on' and eligible:
            # The real fixtures use Cargo's ordinary separated -C arguments.
            codegen = [original[i + 1] if arg == '-C' else arg[2:]
                       for i, arg in enumerate(original) if arg == '-C' or arg.startswith('-C')]
            settings = dict(value.replace('_', '-').split('=', 1) for value in codegen)
            self.assertNotIn('opt-level', settings)
            self.assertNotIn('lto', settings)
            expected += ['-Copt-level=1', '-Zmir-opt-level=1', '-Clto=off']
            if 'debug-assertions' not in settings:
                expected.append('-Cdebug-assertions=yes')
            if 'overflow-checks' not in settings:
                debug = settings.get('debug-assertions', 'yes')
                self.assertIn(debug, ['yes', 'no', 'true', 'false', 'y', 'n', 'on', 'off'])
                expected.append('-Coverflow-checks=' + ('no' if debug in ['no', 'false', 'n', 'off'] else 'yes'))
        self.assertEqual(fields[4:-1], expected, str(path))
        return eligible

    def library(self, source, mode, extra=()):
        self.sequence += 1
        directory = self.work / mode; directory.mkdir(exist_ok=True)
        output = directory / 'libfixture_library.rlib'
        args = [str(self.rustc), '--crate-name', 'fixture_library', '--crate-type', 'rlib',
            '--edition=2024', '--emit=dep-info,link', '--error-format=json', '-Cdebuginfo=0',
            '-C', 'incremental=' + str(directory / 'incremental'), '-o', str(output), str(source), *extra]
        env = self.environment('on' if mode == 'on' else 'off')
        records = self.work / 'native-argv' / str(self.sequence)
        if mode != 'stock':
            records.mkdir(parents=True)
            env['RUST_INTERP_COMPILER_ARGV_RECORD_DIR'] = str(records)
        snapshot = self.work / ('native-source-' + str(self.sequence) + '.rs')
        snapshot.write_bytes(source.read_bytes())
        result = self.invoke(args if mode == 'stock' else [self.wrapper, *args], env)
        if mode != 'stock':
            paths = list(records.glob('*.argv')); self.assertEqual(len(paths), 1)
            self.assertTrue(self.assert_forwarded(paths[0], args, mode, cwd=self.work))
        return result, output

    def test_uncalled_type_borrow_const_and_position_changes_reject_then_restore(self):
        source = self.work / 'library.rs'
        original = '#![allow(dead_code)]\npub fn value() -> u32 { 5 }\n'
        cases = [('type', 'fn uncalled() -> u32 { false }', 'E0308'),
            ('borrow', "fn uncalled() -> &'static u32 { let x = 1; &x }", 'E0515'),
            ('const', 'const BAD: u32 = panic!("must evaluate");', 'E0080'),
            ('panic', '#[deny(unconditional_panic)] fn uncalled() -> u32 { [1][1] }', 'unconditional_panic')]
        try:
            for index, (label, invalid, code) in enumerate(cases):
                source.write_text(original + '// position λ\n' * index + invalid + '\n')
                results = {m: self.library(source, m)[0] for m in ['stock', 'off', 'on']}
                for mode, result in results.items():
                    with self.subTest(case=label, mode=mode):
                        self.assertNotEqual(result.returncode, 0, result.stderr)
                        self.assertIn(code, [row[1] for row in self.diagnostics(result)])
                        self.assertEqual(self.diagnostics(result), self.diagnostics(results['stock']))
                source.write_text(original)
                for mode in ['stock', 'off', 'on']:
                    self.assert_success(self.library(source, mode)[0])
        finally:
            source.write_text(original)

    def test_native_debug_overflow_ub_cfg_generics_inline_and_drop_effects(self):
        source = self.work / 'library.rs'; consumer = self.work / 'consumer.rs'
        source.write_text('''#![feature(cfg_ub_checks)]
fn generic<T: Copy>(x: T) -> T { x }
#[inline] fn inlined(x: u32) -> u32 { x }
struct Mark<'a>(&'a std::cell::Cell<u32>);
impl Drop for Mark<'_> { fn drop(&mut self) { self.0.set(self.0.get() + 1); } }
pub fn checks() -> (bool, bool) { (cfg!(debug_assertions), cfg!(ub_checks)) }
pub fn value() -> u32 {
    let drops = std::cell::Cell::new(0);
    { let _mark = Mark(&drops); }
    generic(inlined(8)) + drops.get()
}
pub fn debug() -> u32 { debug_assert!(false, "library debug assertion"); 7 }
pub fn overflow() -> u8 { std::hint::black_box(u8::MAX) + 1 }
''')
        for flags, debug, overflow in [((), True, True),
            (('-Cdebug-assertions=no',), False, False),
            (('-Cdebug-assertions=no', '-Coverflow-checks=yes'), False, True)]:
            consumer.write_text('''fn main() {
    assert_eq!(fixture_library::checks(), (DEBUG, DEBUG));
    assert_eq!(fixture_library::value(), 9);
    let debug = std::panic::catch_unwind(fixture_library::debug);
    assert_eq!(debug.is_err(), DEBUG);
    if !DEBUG { assert_eq!(debug.unwrap(), 7); }
    let overflow = std::panic::catch_unwind(fixture_library::overflow);
    assert_eq!(overflow.is_err(), OVERFLOW);
    if !OVERFLOW { assert_eq!(overflow.unwrap(), 0); }
}
'''.replace('DEBUG', str(debug).lower()).replace('OVERFLOW', str(overflow).lower()))
            for mode in ['stock', 'off', 'on']:
                result, library = self.library(source, mode, flags); self.assert_success(result)
                executable = self.work / mode / 'consumer'
                result = self.invoke([self.rustc, '--edition=2024', consumer, '--error-format=json',
                    '--extern', 'fixture_library=' + str(library), '-o', executable])
                self.assert_success(result)
                self.assert_success(self.invoke([executable]))

    def cargo_fixture(self):
        macro_fixture.HostProcMacroNativeTests.cargo_fixture(self)
        build = self.package / 'build.rs'
        build.write_text(build.read_text().replace('assert_eq!(proc_opt_shared::value(), 5);',
            'let value = proc_opt_shared::value();\n'
            '    std::fs::write(out.join("shared-value.txt"), value.to_string()).unwrap();\n'
            '    println!("cargo:rustc-env=FIXTURE_SHARED_BUILD_VALUE={value}");'))
        # Keep the existing exec adapter; add context for matching its input to
        # the actual light-wrapper/exporter compiler-call recorder by PID.
        self.adapter.write_text(self.adapter.read_text().replace('argv=sys.argv[1:]',
            'argv=sys.argv[1:], cwd=os.getcwd()'))

    def source_state(self, body, external, shared=5, *, position=False, invalid_generated=False):
        macro_fixture.HostProcMacroNativeTests.source_state(self, body, external,
            invalid_generated=invalid_generated)
        source = self.package / 'shared/src/lib.rs'
        source.write_text('''fn generic<T: Copy>(x: T) -> T { x }
#[inline] fn inlined(x: u32) -> u32 { x }
struct Mark<'a>(&'a std::cell::Cell<u32>);
impl Drop for Mark<'_> { fn drop(&mut self) { self.0.set(self.0.get() + 1); } }
pub fn value() -> u32 {
    assert!(cfg!(debug_assertions));
    let drops = std::cell::Cell::new(0);
    { let _mark = Mark(&drops); }
    assert_eq!(drops.get(), 1);
    generic(inlined(VALUE))
}
'''.replace('VALUE', str(shared)))
        macro = self.package / 'macros/src/lib.rs'
        macro.write_text(macro.read_text().replace(
            'format!("pub const GENERATED: u32 = {value};").parse().unwrap()',
            'let site = proc_macro::Span::call_site();\n'
            '    format!("pub const GENERATED: u32 = {value}; pub const SITE: (&str, u32, u32) = ({:?}, {}, {});",\n'
            '        site.file(), site.line(), site.column()).parse().unwrap()'))
        consumer = self.package / 'src/lib.rs'
        text = consumer.read_text().replace('proc_opt_shared::value(), 5', 'proc_opt_shared::value(), ' + str(shared))
        text = text.replace('GENERATED, ' + str(body + external + 5), 'GENERATED, ' + str(body + external + shared))
        if not invalid_generated:
            text = text.replace('#[test] fn selected() {', '#[test] fn selected() {\n'
                'assert_eq!(SITE, (file!(), ' + str(3 if position else 1) + ', 1));\n'
                'assert_eq!(env!("FIXTURE_SHARED_BUILD_VALUE"), "' + str(shared) + '");')
        consumer.write_text(('// source position λ\n\n' if position else '') + text)

    def cargo_run(self, mode, state, std, *, expect_failure=False):
        records = self.work / 'final-argv' / mode / state
        records.mkdir(parents=True)
        original_env = self.base_env
        self.base_env = dict(original_env, RUST_INTERP_COMPILER_ARGV_RECORD_DIR=str(records))
        try:
            bytecode = macro_fixture.HostProcMacroNativeTests.cargo_run(
                self, mode, state, std, expect_failure=expect_failure)
        finally:
            self.base_env = original_env
        if bytecode is not None:
            artifact = self.work / 'bytecode' / mode / (state + '.rbc')
            artifact.parent.mkdir(parents=True, exist_ok=True); artifact.write_bytes(bytecode)
        if mode == 'stock':
            self.assertEqual(list(records.iterdir()), [])
            return bytecode
        roles = []
        for original in sorted((self.work / 'traces' / mode / state).glob('*.json')):
            row = json.loads(original.read_text()); args = row['argv']
            if '--crate-name' not in args or args[args.index('--crate-name') + 1] == '___':
                continue  # Cargo metadata probes, not compilation controls.
            selected = self.values(args, '--crate-name') == ['proc_opt_fixture'] and '--test' in args
            path = records / (('exported' if selected else 'native') + '-' + str(row['pid']) + '.argv')
            self.assertTrue(path.is_file(), str(path))
            eligible = self.assert_forwarded(path, args, mode, cwd=Path(row['cwd']), selected=selected, std=std)
            roles.append(dict(name=self.values(args, '--crate-name'), eligible=eligible,
                guest=bool(self.values(args, '--target')), selected=selected,
                raw_argv=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if state == 'original':
            self.assertTrue(any(r['name'] == ['proc_opt_shared'] and r['eligible'] for r in roles))
            self.assertTrue(any(r['name'] == ['proc_opt_shared'] and r['guest'] for r in roles))
            self.assertTrue(any(r['name'] == ['build_script_build'] and not r['eligible'] for r in roles))
            self.assertTrue(any(r['name'] == ['proc_opt_macros'] and not r['eligible'] for r in roles))
            self.assertTrue(any(r['selected'] for r in roles))
        (records / 'checked-roles.json').write_text(json.dumps(roles, indent=2))
        return bytecode

    def test_cargo_shared_library_macro_input_spans_error_and_restoration(self):
        self.cargo_fixture()
        std = Path(os.environ['RUST_INTERP_TEST_STD_SYSROOT']).resolve(strict=True)
        original = {}
        try:
            for state, body, external, shared, position, invalid in [
                ('original', 3, 2, 5, False, False), ('macro-body', 7, 2, 5, False, False),
                ('shared-library', 7, 2, 11, False, False), ('declared-input', 7, 9, 11, False, False),
                ('position', 7, 9, 11, True, False), ('generated-error', 7, 9, 11, True, True),
                ('restored', 3, 2, 5, False, False)]:
                self.source_state(body, external, shared, position=position, invalid_generated=invalid)
                snapshot = self.work / 'source-states' / state
                for source in self.package.rglob('*'):
                    if source.is_file():
                        saved = snapshot / source.relative_to(self.package)
                        saved.parent.mkdir(parents=True, exist_ok=True); saved.write_bytes(source.read_bytes())
                results = {m: self.cargo_run(m, state, std, expect_failure=invalid) for m in ['stock', 'off', 'on']}
                if invalid:
                    self.assertEqual(results, dict(stock=None, off=None, on=None))
                    continue
                self.assertEqual(results['off'], results['on'], state)
                if state == 'original':original = results
                elif state == 'restored':
                    self.assertEqual(results['off'], original['off'])
                    self.assertEqual(results['on'], original['on'])
                else:
                    self.assertNotEqual(results['on'], original['on'], state)
        finally:
            self.source_state(3, 2)


if __name__ == '__main__':
    unittest.main()
