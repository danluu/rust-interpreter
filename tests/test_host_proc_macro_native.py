"""Real compiler histories, opt-in and caller-serialized by the workload lock.

Use RUST_INTERP_TEST_EXPORTER/WRAPPER for one newly built public toolset.
RUST_INTERP_TEST_STD_SYSROOT enables the Cargo/guest fixture; TEST_VM optionally
executes its selected bytecode. No dependency downloads or tool builds occur.
"""
import json
import os
from pathlib import Path
import sys
import unittest

import test_borrowck_cache as compiler_tests


@unittest.skipUnless(os.environ.get('RUST_INTERP_TEST_EXPORTER'),
                     'set RUST_INTERP_TEST_EXPORTER for real proc-macro histories')
class HostProcMacroNativeTests(unittest.TestCase):
    setUp = compiler_tests.BorrowckCacheTests.setUp
    assert_success = compiler_tests.BorrowckCacheTests.assert_success
    diagnostics = staticmethod(compiler_tests.BorrowckCacheTests.diagnostics)

    @classmethod
    def setUpClass(cls):
        compiler_tests.BorrowckCacheTests.setUpClass.__func__(cls)
        cls.wrapper = Path(os.environ.get('RUST_INTERP_TEST_WRAPPER',
            cls.exporter.with_name('rust-interp-rustc-wrapper'))).resolve(strict=True)
        cls.cargo = cls.rustc.with_name('cargo')
        cls.base_env = {k: v for k, v in cls.base_env.items()
                        if not k.startswith(('CARGO_', 'PROC_OPT_'))}

    def invoke(self, command, env=None):
        actual = env or self.base_env
        with (self.work / 'macro-invocations.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(command=list(map(str, command)), environment={
                k: v for k, v in actual.items() if k.startswith(('RUST_INTERP_', 'CARGO_', 'PROC_OPT_'))
                or k in ('RUSTC', 'RUSTDOC')})) + '\n')
        return compiler_tests.BorrowckCacheTests.invoke(self, command, actual)

    def environment(self, mode):
        version = self.invoke([self.rustc, '-vV']); self.assert_success(version)
        self.host = next(line[6:] for line in version.stdout.splitlines() if line.startswith('host: '))
        return dict(self.base_env, RUST_INTERP_STD_SYSROOT=str(self.rustc.parent.parent),
            RUST_INTERP_STD_TARGET=self.host, RUST_INTERP_EXPORT_PACKAGE='selected_elsewhere',
            CARGO_PKG_NAME='fixture_macro', RUST_INTERP_HOST_PROC_MACRO_OPT=mode)

    def macro(self, source, mode, env, extra=()):
        directory = self.work / mode; directory.mkdir(exist_ok=True)
        # The pinned platform determines the native dylib suffix. Cargo handles
        # platform naming in the separate real workflow below.
        suffix = '.dylib' if sys.platform == 'darwin' else '.so'
        artifact = directory / ('libfixture_macro' + suffix)
        args = ['--crate-name', 'fixture_macro', '--crate-type', 'proc-macro', '--edition=2024',
            '--emit=dep-info,link', '--error-format=json', '-Cdebuginfo=0',
            '-o', artifact, source, *extra]
        command = [self.rustc, *args] if mode == 'stock' else [self.wrapper, self.rustc, *args]
        return self.invoke(command, env), artifact

    def test_uncalled_errors_and_restoration_match_pinned_native_compiler(self):
        environments = {m: self.environment('on' if m == 'on' else 'off') for m in ['stock', 'off', 'on']}
        source = self.work / 'macro.rs'
        original = ('#![allow(dead_code)]\nextern crate proc_macro;\n'
            '#[proc_macro] pub fn value(_: proc_macro::TokenStream) -> proc_macro::TokenStream { "3".parse().unwrap() }\n')
        cases = {
            'type': ('fn uncalled() -> u32 { false }', 'E0308'),
            'borrow': ("fn uncalled() -> &'static u32 { let x = 1; &x }", 'E0515'),
            'const': ('const BAD: u32 = panic!("must evaluate");', 'E0080'),
            'panic': ('#[deny(unconditional_panic)] fn uncalled() -> u32 { [1][1] }', 'unconditional_panic'),
        }
        try:
            for label, (invalid, code) in cases.items():
                source.write_text(original + invalid + '\n')
                results = {m: self.macro(source, m, environments[m])[0] for m in environments}
                for mode, result in results.items():
                    with self.subTest(case=label, mode=mode):
                        self.assertNotEqual(result.returncode, 0, result.stderr)
                        self.assertIn(code, [d[1] for d in self.diagnostics(result)])
                        self.assertEqual(self.diagnostics(result), self.diagnostics(results['stock']))
                source.write_text(original)
                for mode in environments:
                    self.assert_success(self.macro(source, mode, environments[mode])[0])
        finally:
            source.write_text(original)

    def test_macro_cfg_debug_and_overflow_checks_match_explicit_profile_settings(self):
        source = self.work / 'macro.rs'; consumer = self.work / 'consumer.rs'
        source.write_text('''extern crate proc_macro;
#[proc_macro]
pub fn value(input: proc_macro::TokenStream) -> proc_macro::TokenStream {
    match input.to_string().as_str() {
        "debug" => { debug_assert!(false, "macro debug assertion"); "7".parse().unwrap() },
        "overflow" => (std::hint::black_box(u8::MAX) + 1).to_string().parse().unwrap(),
        _ => if cfg!(debug_assertions) { "1" } else { "0" }.parse().unwrap(),
    }
}
''')
        for flags, debug, overflow in [((), True, True),
            (('-Cdebug-assertions=no',), False, False),
            (('-Cdebug-assertions=no', '-Coverflow-checks=yes'), False, True)]:
            for mode in ['stock', 'off', 'on']:
                env = self.environment('on' if mode == 'on' else 'off')
                built, library = self.macro(source, mode, env, flags); self.assert_success(built)
                for expression, failure, value in [('cfg', False, int(debug)),
                    ('debug', debug, 7), ('overflow', overflow, 0)]:
                    consumer.write_text('fn main() { assert_eq!(fixture_macro::value!(' + expression + '), '
                                        + str(value) + '); }\n')
                    output = self.work / mode / 'consumer'
                    result = self.invoke([self.rustc, '--edition=2024', consumer, '--error-format=json',
                        '--extern', 'fixture_macro=' + str(library), '-o', output])
                    with self.subTest(flags=flags, mode=mode, expression=expression):
                        if failure:
                            self.assertNotEqual(result.returncode, 0, result.stderr)
                            self.assertIn('proc macro panicked', result.stderr)
                        else:
                            self.assert_success(result)
                            self.assert_success(self.invoke([output]))

    def cargo_fixture(self):
        self.package = self.work / 'package'
        for folder in ['src', 'shared/src', 'macros/src']:
            (self.package / folder).mkdir(parents=True)
        (self.package / 'Cargo.toml').write_text(
            '[package]\nname="proc-opt-fixture"\nversion="0.0.0"\nedition="2024"\n'
            '[workspace]\nmembers=["shared","macros"]\nresolver="2"\n'
            '[dependencies]\nproc-opt-shared={path="shared"}\nproc-opt-macros={path="macros"}\n'
            '[build-dependencies]\nproc-opt-shared={path="shared"}\n')
        (self.package / 'shared/Cargo.toml').write_text(
            '[package]\nname="proc-opt-shared"\nversion="0.0.0"\nedition="2024"\n')
        (self.package / 'shared/src/lib.rs').write_text('pub fn value() -> u32 { 5 }\n')
        (self.package / 'macros/Cargo.toml').write_text(
            '[package]\nname="proc-opt-macros"\nversion="0.0.0"\nedition="2024"\n'
            '[lib]\nproc-macro=true\n[dependencies]\nproc-opt-shared={path="../shared"}\n')
        build = '''fn main() {
    let profile = format!("{}:{}", std::env::var("OPT_LEVEL").unwrap(), std::env::var("DEBUG").unwrap());
    let out = std::path::PathBuf::from(std::env::var_os("OUT_DIR").unwrap());
    std::fs::write(out.join("profile.txt"), &profile).unwrap();
    println!("cargo:rustc-env=FIXTURE_BUILD_PROFILE={profile}");
    println!("cargo:rerun-if-changed=build.rs");
    EXTRA
}
'''
        (self.package / 'build.rs').write_text(build.replace('EXTRA', 'assert_eq!(proc_opt_shared::value(), 5);'))
        (self.package / 'macros/build.rs').write_text(build.replace('EXTRA', '''
    let input = std::path::PathBuf::from(std::env::var_os("CARGO_MANIFEST_DIR").unwrap()).join("input.txt");
    println!("cargo:rustc-env=FIXTURE_MACRO_INPUT={}", input.display());
    println!("cargo:rerun-if-changed=input.txt");'''))
        self.adapter = self.work / 'record-wrapper.py'
        self.adapter.write_text('#!' + sys.executable + '\n' + '''import json, os, pathlib, sys
directory = pathlib.Path(os.environ['PROC_OPT_TRACE'])
directory.mkdir(parents=True, exist_ok=True)
(directory / (str(os.getpid()) + '.json')).write_text(json.dumps(dict(pid=os.getpid(), argv=sys.argv[1:])))
wrapper = os.environ['PROC_OPT_WRAPPER']
os.execv(wrapper, [wrapper, *sys.argv[1:]])
''')
        self.adapter.chmod(0o755)

    def source_state(self, body, external, *, invalid_generated=False):
        macro = '''extern crate proc_macro;
fn generic<T: Copy>(x: T) -> T { x }
#[inline] fn inlined(x: u32) -> u32 { x }
struct Mark<'a>(&'a std::cell::Cell<u32>);
impl Drop for Mark<'_> { fn drop(&mut self) { self.0.set(self.0.get() + 1); } }
const BODY: u32 = BODY_VALUE;
#[proc_macro]
pub fn make(_: proc_macro::TokenStream) -> proc_macro::TokenStream {
    assert_eq!(env!("FIXTURE_BUILD_PROFILE"), "0:true");
    assert!(cfg!(debug_assertions));
    let drops = std::cell::Cell::new(0);
    { let _mark = Mark(&drops); }
    assert_eq!(drops.get(), 1);
    let input: u32 = std::fs::read_to_string(env!("FIXTURE_MACRO_INPUT")).unwrap().parse().unwrap();
    let value = generic(inlined(BODY)) + input + proc_opt_shared::value();
    format!("pub const GENERATED: u32 = {value};").parse().unwrap()
}
'''.replace('BODY_VALUE', str(body))
        if invalid_generated:
            macro = macro.replace('pub const GENERATED: u32 = {value};', 'pub const GENERATED: u32 = false;')
        (self.package / 'macros/src/lib.rs').write_text(macro)
        (self.package / 'macros/input.txt').write_text(str(external))
        (self.package / 'src/lib.rs').write_text('proc_opt_macros::make!();\n'
            '#[test] fn selected() { assert_eq!(env!("FIXTURE_BUILD_PROFILE"), "0:true");\n'
            'assert_eq!(proc_opt_shared::value(), 5); assert_eq!(GENERATED, ' + str(body + external + 5) + '); }\n')

    def cargo_run(self, mode, state, std_sysroot, *, expect_failure=False):
        env = self.environment('on' if mode == 'on' else 'off')
        env.update(CARGO_HOME=str(self.work / 'cargo-home'), CARGO_INCREMENTAL='1',
            CARGO_ENCODED_RUSTFLAGS='', CARGO_TERM_COLOR='never', RUSTC=str(self.rustc),
            RUSTC_WORKSPACE_WRAPPER='')
        command = [self.cargo, 'test' if mode == 'stock' else 'check', '--manifest-path',
            self.package / 'Cargo.toml', '--package', 'proc-opt-fixture', '--lib', '--offline',
            '--jobs', '2', '--target', self.host, '--target-dir', self.work / ('target-' + mode),
            '--message-format=json-render-diagnostics']
        output = self.work / (mode + '.rbc')
        if mode == 'stock':
            command += ['--', '--test-threads=1']
        else:
            command += ['--profile', 'test']
            env.update(RUSTC_WRAPPER=str(self.adapter), PROC_OPT_WRAPPER=str(self.wrapper),
                PROC_OPT_TRACE=str(self.work / 'traces' / mode / state),
                RUST_INTERP_STD_SYSROOT=str(std_sysroot), RUST_INTERP_EXPORT_PACKAGE='proc-opt-fixture',
                RUST_INTERP_EXPORT_CRATE='proc_opt_fixture', RUST_INTERP_EXPORT_MANIFEST=str(self.package),
                RUST_INTERP_EXPORT_TEST='1', RUST_INTERP_ENTRY='selected', RUST_INTERP_OUTPUT=str(output))
        result = self.invoke(command, env)
        if expect_failure:
            self.assertNotEqual(result.returncode, 0, result.stderr)
            self.assertIn('E0308', result.stdout + result.stderr)
            return None  # Never execute a previous artifact after failed checking.
        self.assert_success(result)
        events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
        builds = [Path(e['out_dir']) for e in events if e.get('reason') == 'build-script-executed']
        self.assertEqual(len(builds), 2)
        self.assertEqual([p.joinpath('profile.txt').read_text() for p in builds], ['0:true', '0:true'])
        if mode == 'stock':
            self.assertIn('1 passed', result.stdout)
            return None
        selected = [e for e in events if e.get('reason') == 'compiler-artifact' and
                    e['target']['name'] == 'proc_opt_fixture' and e['profile']['test']]
        self.assertEqual(len(selected), 1)
        sidecars = [Path(p + '.rbc') for p in selected[0]['filenames'] if Path(p + '.rbc').is_file()]
        self.assertEqual(len(sidecars), 1)
        # Fresh states produce the selected sidecar; Cargo restoration can be
        # fresh and need not rewrite the convenience output path.
        bytecode = sidecars[0].read_bytes()
        if self.vm:
            self.assert_success(self.invoke([self.vm, '--engine', 'interpreter', sidecars[0]]))
        return bytecode

    @unittest.skipUnless(os.environ.get('RUST_INTERP_TEST_STD_SYSROOT'), 'requires prepared std MIR')
    def test_cargo_macro_body_declared_file_input_generated_error_and_restoration(self):
        self.cargo_fixture()
        std_sysroot = Path(os.environ['RUST_INTERP_TEST_STD_SYSROOT']).resolve(strict=True)
        try:
            for state, body, external, invalid in [
                ('original', 3, 2, False), ('body-edit', 7, 2, False),
                ('declared-input', 7, 9, False), ('generated-error', 7, 9, True),
                ('restored', 3, 2, False)]:
                self.source_state(body, external, invalid_generated=invalid)
                bytecodes = {mode: self.cargo_run(mode, state, std_sysroot, expect_failure=invalid)
                             for mode in ['stock', 'off', 'on']}
                if not invalid:
                    self.assertEqual(bytecodes['off'], bytecodes['on'], state)
            for mode in ['off', 'on']:
                records = [json.loads(p.read_text())['argv'] for p in (self.work / 'traces' / mode / 'original').glob('*.json')]
                names = [args[args.index('--crate-name') + 1] for args in records if '--crate-name' in args]
                self.assertIn('proc_opt_macros', names)
                self.assertIn('proc_opt_shared', names)
                self.assertIn('build_script_build', names)
                for args in records:
                    if '--crate-type' in args and args[args.index('--crate-type') + 1] == 'proc-macro' and '-' not in args:
                        self.assertNotIn('--target', args)
                        self.assertFalse(any('opt-level=' in arg for arg in args))
        finally:
            self.source_state(3, 2)


if __name__ == '__main__':
    unittest.main()
