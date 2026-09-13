"""Opt-in real compiler/Cargo regressions; caller owns the shared workload lock.

RUST_INTERP_TEST_EXPORTER selects the built exporter. RUST_INTERP_TEST_WRAPPER
optionally selects its wrapper (default: adjacent installed wrapper), and
RUST_INTERP_TEST_VM optionally executes selected bytecode. The Cargo test also
requires RUST_INTERP_TEST_STD_SYSROOT pointing at already prepared std MIR.
No tool, sysroot, dependency download or source checkout is created here.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

import test_borrowck_cache as compiler_tests


@unittest.skipUnless(os.environ.get('RUST_INTERP_TEST_EXPORTER'),
                     'set RUST_INTERP_TEST_EXPORTER for native host MIR correctness tests')
class NativeHostMirTests(unittest.TestCase):
    setUp = compiler_tests.BorrowckCacheTests.setUp
    assert_success = compiler_tests.BorrowckCacheTests.assert_success
    diagnostics = staticmethod(compiler_tests.BorrowckCacheTests.diagnostics)

    @classmethod
    def setUpClass(cls):
        compiler_tests.BorrowckCacheTests.setUpClass.__func__(cls)
        cls.wrapper = Path(os.environ.get('RUST_INTERP_TEST_WRAPPER',
                            cls.exporter.with_name('rust-interp-rustc-wrapper'))).resolve(strict=True)
        cls.cargo = cls.rustc.with_name('cargo').resolve(strict=True)
        cls.original_sysroot = cls.rustc.parent.parent
        cls.base_env = {k: v for k, v in cls.base_env.items()
                        if not k.startswith(('CARGO_', 'RUSTDEV_', 'HOST_MIR_'))}

    def invoke(self, command, env=None):
        # Keep the common retained receipts and add the environment settings
        # which distinguish the native and forced-legacy histories.
        actual = env or self.base_env
        with (self.work / 'host-mir-invocations.jsonl').open('a') as output:
            output.write(json.dumps(dict(command=list(map(str, command)), environment={
                k: v for k, v in actual.items() if k.startswith(('HOST_MIR_', 'RUST_INTERP_', 'CARGO_'))
                or k in ('RUSTC', 'RUSTDOC')})) + '\n')
        return compiler_tests.BorrowckCacheTests.invoke(self, command, actual)

    def host_environment(self):
        version = self.invoke([self.rustc, '-vV'])
        self.assert_success(version)
        self.host = next(line[6:] for line in version.stdout.splitlines() if line.startswith('host: '))
        # These host calls have no --target, so their installed sysroot remains
        # unchanged. Supplying both context variables exercises host omission.
        return dict(self.base_env, RUST_INTERP_STD_SYSROOT=str(self.original_sysroot),
                    RUST_INTERP_STD_TARGET=self.host, RUST_INTERP_EXPORT_PACKAGE='selected_elsewhere',
                    CARGO_PKG_NAME='host_helper', RUST_INTERP_BORROWCK_CACHE='off')

    def host_library(self, source, mode, env, *, incremental=False):
        directory = self.work / mode
        directory.mkdir(exist_ok=True)
        artifact = directory / 'libhost_helper.rlib'
        args = ['--crate-name', 'host_helper', '--crate-type', 'rlib', '--edition=2024',
                '--emit=link', '--error-format=json', '-Copt-level=0', '-Cdebuginfo=0',
                '-o', artifact, source]
        if incremental:
            args += ['-C', 'incremental=' + str(directory / 'incremental')]
        if mode == 'legacy':
            args += ['-Zalways-encode-mir=yes']
        command = [self.rustc, *args] if mode == 'stock' else [self.wrapper, self.rustc, *args]
        return self.invoke(command, self.base_env if mode == 'stock' else env), artifact

    def test_uncalled_errors_match_stock_and_forced_full_mir(self):
        env = self.host_environment()
        source = self.work / 'host_helper.rs'
        cases = {
            'type': ('fn uncalled() -> u32 { false }', 'E0308'),
            'borrow': ("fn uncalled() -> &'static u32 { let local = 1; &local }", 'E0515'),
            'constant': ('const UNCALLED: u32 = panic!("constant must be checked");', 'E0080'),
            'unconditional-panic': ('#[deny(unconditional_panic)]\n'
                                    'fn uncalled() -> u32 { let values = [1]; values[1] }',
                                    'unconditional_panic'),
        }
        for label, (body, code) in cases.items():
            with self.subTest(error=label):
                source.write_text('#![allow(dead_code)]\npub fn exported() -> u32 { 3 }\n' + body + '\n')
                results = {m: self.host_library(source, m, env)[0] for m in ['candidate', 'legacy', 'stock']}
                for mode, result in results.items():
                    self.assertNotEqual(result.returncode, 0, (mode, result.stderr))
                    self.assertIn(code, [d[1] for d in self.diagnostics(result)], (mode, result.stderr))
                    self.assertEqual(self.diagnostics(result), self.diagnostics(results['stock']), mode)

    @staticmethod
    def helper_source(value):
        return ('pub fn value() -> u32 { ' + str(value) + ' }\n'
                'pub fn generic<T: Copy>(value: T) -> T { value }\n'
                '#[inline] pub fn inlined(value: u32) -> u32 { value + 5 }\n'
                'pub const fn constant() -> u32 { 17 }\n'
                'pub const FIXED: u32 = 11;\n')

    def test_native_generic_inline_const_consumers_follow_edit_and_restoration(self):
        env = self.host_environment()
        source, consumer = self.work / 'host_helper.rs', self.work / 'consumer.rs'
        consumer.write_text('const LENGTH: usize = host_helper::constant() as usize;\n'
            'fn main() {\n'
            '    let array = [0u8; LENGTH];\n'
            '    let value = host_helper::generic(host_helper::value()) + host_helper::inlined(3)\n'
            '        + array.len() as u32 + host_helper::FIXED;\n'
            '    println!("{value}");\n'
            '}\n')
        original = self.helper_source(3)
        try:
            for value in [3, 7, 3]:
                source.write_text(self.helper_source(value))
                for mode in ['candidate', 'legacy', 'stock']:
                    with self.subTest(mode=mode, value=value):
                        built, library = self.host_library(source, mode, env, incremental=True)
                        self.assert_success(built)
                        executable = self.work / mode / 'consumer'
                        built = self.invoke([self.rustc, '--edition=2024', '-Copt-level=0', '-Cdebuginfo=0',
                            '--extern', 'host_helper=' + str(library), consumer, '-o', executable])
                        self.assert_success(built)
                        executed = self.invoke([executable])
                        self.assert_success(executed)
                        self.assertEqual(executed.stdout, str(value + 36) + '\n')
        finally:
            source.write_text(original)

    def test_metadata_only_dependency_retains_non_generic_guest_body(self):
        env = self.host_environment()
        helper, guest = self.work / 'helper.rs', self.work / 'guest.rs'
        helper.write_text('#[inline(never)] pub fn value() -> u32 { 23 }\n')
        guest.write_text('pub fn entry() -> u32 { host_helper::value() }\n')
        bytecodes = []
        for mode in ['candidate', 'legacy']:
            with self.subTest(mode=mode):
                directory = self.work / mode
                directory.mkdir()
                metadata = directory / 'libhost_helper.rmeta'
                args = ['--crate-name', 'host_helper', '--crate-type', 'rlib', '--edition=2024',
                        '--emit=metadata', '-Copt-level=0', '-Cdebuginfo=0', helper, '-o', metadata]
                if mode == 'legacy':
                    args.append('-Zalways-encode-mir=yes')
                self.assert_success(self.invoke([self.wrapper, self.rustc, *args], env))
                output = directory / 'guest.rbc'
                export_env = dict(env, CARGO_PKG_NAME='guest_consumer', CARGO_PRIMARY_PACKAGE='1',
                    RUST_INTERP_EXPORT_PACKAGE='guest_consumer', RUST_INTERP_EXPORT_CRATE='guest_consumer',
                    RUST_INTERP_ENTRY='entry', RUST_INTERP_OUTPUT=str(output))
                # Successful export must read this ordinary, non-inline body
                # from the just-built metadata. Native consumers alone would
                # not detect its accidental omission from metadata-only units.
                self.assert_success(self.invoke([self.wrapper, self.rustc, '--crate-name', 'guest_consumer',
                    '--crate-type', 'rlib', '--edition=2024', '--emit=metadata', '-Copt-level=0',
                    '-Cdebuginfo=0', '--extern', 'host_helper=' + str(metadata), guest,
                    '-o', directory / 'libguest_consumer.rmeta'], export_env))
                bytecodes.append(output.read_bytes())
                if self.vm:
                    executed = self.invoke([self.vm, '--engine', 'interpreter', output])
                    self.assert_success(executed)
                    self.assertEqual(executed.stdout, '23\n')
        self.assertEqual(bytecodes[0], bytecodes[1])

    def cargo_fixture(self):
        self.package = self.work / 'package'
        for folder in ['src', 'shared/src', 'macros/src']:
            (self.package / folder).mkdir(parents=True)
        (self.package / 'Cargo.toml').write_text(
            '[package]\nname="host-mir-fixture"\nversion="0.0.0"\nedition="2024"\n'
            '[workspace]\nmembers=["shared","macros"]\nresolver="2"\n'
            '[dependencies]\nhost-mir-shared={path="shared"}\nhost-mir-macros={path="macros"}\n'
            '[build-dependencies]\nhost-mir-shared={path="shared"}\n')
        (self.package / 'shared/Cargo.toml').write_text(
            '[package]\nname="host-mir-shared"\nversion="0.0.0"\nedition="2024"\n')
        (self.package / 'macros/Cargo.toml').write_text(
            '[package]\nname="host-mir-macros"\nversion="0.0.0"\nedition="2024"\n'
            '[lib]\nproc-macro=true\n[dependencies]\nhost-mir-shared={path="../shared"}\n')
        calculation = ('host_mir_shared::value() + host_mir_shared::generic(2u32) + '
                       'host_mir_shared::inlined(3) + host_mir_shared::constant()')
        (self.package / 'build.rs').write_text(
            'fn main() {\n'
            '    let value = ' + calculation + ';\n'
            '    let out = std::path::PathBuf::from(std::env::var_os("OUT_DIR").unwrap());\n'
            '    std::fs::write(out.join("generated.rs"), format!("pub const BUILT: u32 = {value};")).unwrap();\n'
            '    std::fs::write(out.join("host-value.txt"), value.to_string()).unwrap();\n'
            '    println!("cargo:rerun-if-changed=build.rs");\n'
            '}\n')
        (self.package / 'macros/src/lib.rs').write_text(
            'extern crate proc_macro;\n'
            '#[proc_macro]\npub fn host_value(_: proc_macro::TokenStream) -> proc_macro::TokenStream {\n'
            '    let value = ' + calculation + ';\n'
            '    value.to_string().parse().unwrap()\n'
            '}\n')
        (self.package / 'src/lib.rs').write_text(
            'include!(concat!(env!("OUT_DIR"), "/generated.rs"));\n'
            'pub const MACRO: u32 = host_mir_macros::host_value!();\n'
            'pub fn entry() -> u32 { ' + calculation + ' + BUILT + MACRO }\n'
            '#[test]\nfn selected() {\n'
            '    let current = ' + calculation + ';\n'
            '    assert_eq!(BUILT, current);\n'
            '    assert_eq!(MACRO, current);\n'
            '    assert_eq!(entry(), current * 3);\n'
            '}\n')
        # This fixture-only adapter records actual Cargo roles and forces the
        # former policy by adding the explicit user flag to native libraries.
        # It never changes the implementation's routing or stubs a compiler.
        self.adapter = self.work / 'recording-wrapper.py'
        self.adapter.write_text('#!' + sys.executable + '\n' + '''import json, os, pathlib, sys
args = sys.argv[1:]
library = any(a == '--crate-type' and i + 1 < len(args) and
              any(t in ('lib', 'rlib') for t in args[i + 1].split(','))
              for i, a in enumerate(args))
target = any(a == '--target' or a.startswith('--target=') for a in args)
link = any(a.startswith('--emit=') and 'link' in a.split('=', 1)[1].split(',') for a in args)
forced = os.environ.get('HOST_MIR_FORCE_LEGACY') == '1' and library and not target and link
original = args[:]
if forced:
    args.append('-Zalways-encode-mir=yes')
directory = pathlib.Path(os.environ['HOST_MIR_TRACE'])
directory.mkdir(parents=True, exist_ok=True)
(directory / (str(os.getpid()) + '.json')).write_text(json.dumps(
    dict(pid=os.getpid(), original=original, forwarded=args, forced_legacy=forced)))
wrapper = os.environ['HOST_MIR_REAL_WRAPPER']
os.execv(wrapper, [wrapper, *args])
''')
        self.adapter.chmod(0o755)

    def cargo_run(self, mode, state, std_sysroot):
        trace = self.work / 'traces' / mode / str(state)
        env = dict(self.base_env, CARGO_HOME=str(self.work / 'cargo-home'), CARGO_INCREMENTAL='1',
            CARGO_ENCODED_RUSTFLAGS='', CARGO_TERM_COLOR='never', RUSTC=str(self.rustc),
            RUSTDOC=str(self.rustc.with_name('rustdoc')), RUSTC_WORKSPACE_WRAPPER='')
        command = [self.cargo, 'test' if mode == 'stock' else 'check', '--manifest-path',
            self.package / 'Cargo.toml', '--package', 'host-mir-fixture', '--lib', '--offline', '--jobs', '2',
            '--target', self.host, '--target-dir', self.work / ('target-' + mode),
            '--message-format=json-render-diagnostics']
        output = self.work / (mode + '.rbc')
        if mode == 'stock':
            command += ['--', '--test-threads=1']
        else:
            command += ['--profile', 'test']
            env.update(RUSTC_WRAPPER=str(self.adapter), HOST_MIR_TRACE=str(trace),
                HOST_MIR_REAL_WRAPPER=str(self.wrapper), HOST_MIR_FORCE_LEGACY='1' if mode == 'legacy' else '0',
                RUST_INTERP_STD_SYSROOT=str(std_sysroot), RUST_INTERP_STD_TARGET=self.host,
                RUST_INTERP_EXPORT_PACKAGE='host-mir-fixture', RUST_INTERP_EXPORT_CRATE='host_mir_fixture',
                RUST_INTERP_EXPORT_MANIFEST=str(self.package), RUST_INTERP_EXPORT_TEST='1',
                RUST_INTERP_ENTRY='selected', RUST_INTERP_OUTPUT=str(output))
        result = self.invoke(command, env)
        self.assert_success(result)
        events = [json.loads(l) for l in result.stdout.splitlines() if l.startswith('{')]
        builds = [Path(e['out_dir']) for e in events if e.get('reason') == 'build-script-executed']
        self.assertEqual(len(builds), 1, result.stdout)
        if mode == 'stock':
            self.assertIn('1 passed', result.stdout)
            return result, builds[0], None
        selected = [e for e in events if e.get('reason') == 'compiler-artifact' and
                    e['target']['name'] == 'host_mir_fixture' and e['profile']['test']]
        self.assertEqual(len(selected), 1, result.stdout)
        sidecars = [Path(p + '.rbc') for p in selected[0]['filenames'] if Path(p + '.rbc').is_file()]
        self.assertEqual(len(sidecars), 1, selected)
        self.assertEqual(sidecars[0].read_bytes(), output.read_bytes())
        invocations = [json.loads(p.read_text()) for p in trace.glob('*.json')]
        helper = [r for r in invocations if '--crate-name' in r['original'] and
                  r['original'][r['original'].index('--crate-name') + 1] == 'host_mir_shared']
        host = [r for r in helper if '--target' not in r['original']]
        guest = [r for r in helper if '--target' in r['original']]
        self.assertEqual(len(host), 1, invocations)
        self.assertEqual(len(guest), 1, invocations)
        self.assertEqual(host[0]['forced_legacy'], mode == 'legacy')
        self.assertFalse(guest[0]['forced_legacy'])
        self.assertTrue(any('--crate-type' in r['original'] and 'proc-macro' in r['original']
                            for r in invocations), invocations)
        if self.vm:
            executed = self.invoke([self.vm, '--engine', 'interpreter', output])
            self.assert_success(executed)
            self.assertEqual(executed.stdout, '0\n')
        return result, builds[0], output.read_bytes()

    @unittest.skipUnless(os.environ.get('RUST_INTERP_TEST_STD_SYSROOT'),
                         'set RUST_INTERP_TEST_STD_SYSROOT to an existing complete std-MIR sysroot')
    def test_cargo_shared_host_guest_build_script_and_proc_macro_follow_edits(self):
        self.host_environment()
        self.cargo_fixture()
        std_sysroot = Path(os.environ['RUST_INTERP_TEST_STD_SYSROOT']).resolve(strict=True)
        source = self.package / 'shared/src/lib.rs'
        original = self.helper_source(3)
        selected_source = (self.package / 'src/lib.rs').read_bytes()
        history = []
        try:
            for state, value in enumerate([3, 7, 3]):
                source.write_text(self.helper_source(value))
                bytecodes = []
                for mode in ['candidate', 'legacy', 'stock']:
                    with self.subTest(mode=mode, state=state, value=value):
                        _, build_output, bytecode = self.cargo_run(mode, state, std_sysroot)
                        self.assertEqual((build_output / 'host-value.txt').read_text(), str(value + 27))
                        if bytecode is not None:
                            bytecodes.append(bytecode)
                self.assertEqual(bytecodes[0], bytecodes[1], 'host-only policy changed selected guest bytecode')
                history.append(bytecodes[0])
                self.assertEqual((self.package / 'src/lib.rs').read_bytes(), selected_source,
                                 'fixture assertions changed during the dependency edit')
                with (self.work / 'source-states.jsonl').open('a') as output:
                    output.write(json.dumps(dict(state=state, value=value,
                        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                        bytecode_sha256=hashlib.sha256(bytecodes[0]).hexdigest())) + '\n')
            self.assertNotEqual(history[0], history[1], 'changed dependency produced stale guest bytecode')
            self.assertEqual(history[0], history[2], 'restoration did not reproduce original guest bytecode')
        finally:
            source.write_text(original)


if __name__ == '__main__':
    unittest.main()
