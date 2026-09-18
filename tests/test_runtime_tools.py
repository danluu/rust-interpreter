"""Native runtime associations and ordinary launch routing; no native children."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_custom_compiler_launcher as fixture
import custom_compiler
import interpreter
import runtime_compiler
import runtime_tools
import std_mir


class RuntimeToolsTests(unittest.TestCase):
    mono = False
    run_process = fixture.CustomCompilerLauncherTests.run_process
    launch = fixture.CustomCompilerLauncherTests.launch

    def setUp(self):
        fixture.CustomCompilerLauncherTests.setUp(self)
        identity = copy.deepcopy(self.compiler.identity)
        identity['policy'] = runtime_compiler.POLICY
        self.compiler = runtime_compiler.RuntimeCompiler(self.compiler.key, self.compiler.sysroot, identity)
        self.binding = dict(schema_version=1, policy='separate-compiler-roles-v1',
            runtime=dict(executable=dict(path=str(self.compiler.rustc),
                sha256=identity['files']['bin/rustc']), verbose_version=identity['compiler'],
                default_sysroot=str(self.compiler.sysroot)),
            runtime_source_commit=identity['provenance']['source_commit'],
            runtime_driver=dict(path=str(self.compiler.sysroot / 'lib/librustc_driver-fixture.dylib'),
                sha256=identity['files']['lib/librustc_driver-fixture.dylib']),
            build=dict(executable=dict(path='/build/rustc', sha256='a' * 64),
                verbose_version='actual build version', default_sysroot='/build'),
            private_sysroot_manifest=dict(path='/private/manifest.json', sha256='b' * 64),
            build_rustflags=['--sysroot=/private'])
        self.binaries = json.loads((self.tools / 'ready.json').read_text())
        self.capabilities = json.loads((self.tools / 'capabilities.json').read_text())
        self.capabilities.update(compiler_sysroot=str(self.compiler.sysroot), compiler_roles=self.binding)
        runtime_tools.bind_recorded_wrapper(self.capabilities, self.binaries, self.compiler,
                                             json.dumps(self.binding))
        self.composition = dict(kind=runtime_tools.POLICY, compiler_key=self.compiler.key,
            compiler_sysroot=str(self.compiler.sysroot), binaries=self.binaries, compiler_roles=self.binding)
        self.save()
        for patcher in [patch.object(interpreter, 'installed_tools', side_effect=lambda _: (self.tools, self.key)),
                        patch.object(runtime_compiler, 'load_runtime_compiler', return_value=self.compiler),
                        patch.object(custom_compiler, 'load_compiler', side_effect=AssertionError('stage2 fallback'))]:
            patcher.start()
            self.addCleanup(patcher.stop)

    def save(self):
        self.key = custom_compiler.digest(self.composition)
        self.capabilities.update(tool_key=self.key)
        (self.tools / 'compiler.json').write_text(json.dumps(self.composition))
        (self.tools / 'capabilities.json').write_text(json.dumps(self.capabilities))

    def runtime_launch(self, *flags, **kwargs):
        return self.launch('--runtime-compiler-key', self.compiler.key, *flags, compiler=False, **kwargs)

    def test_runtime_launch_routes_cargo_and_reports_actual_policy(self):
        result, [report] = self.runtime_launch()
        self.assertEqual(result, 0)
        cargo, vm = self.invocations
        self.assertEqual(cargo[1]['env']['RUSTC'], str(self.compiler.rustc))
        self.assertEqual(cargo[1]['env']['RUST_INTERP_COMPILER_RUSTC'], str(self.compiler.rustc))
        self.assertEqual(cargo[1]['env']['RUSTC_WRAPPER'], str(self.tools / runtime_tools.WRAPPER))
        self.assertEqual(report['custom_compiler']['policy'], runtime_compiler.POLICY)
        self.assertNotIn('RUST_INTERP_COMPILER_RUSTC', vm[1]['env'])

    def test_runtime_passes_exact_prepared_std_selection(self):
        std = (self.root / 'prepared/sysroot', self.compiler.host, 'e' * 64,
               dict(identity=dict(policy='metadata-sysroot-v2-source-paths-release-backtrace')))
        with patch.object(std_mir, 'checked_std_mir', return_value=std) as prepared:
            result, [report] = self.runtime_launch('--std-mir', '--std-mir-policy', 'source-paths-v2',
                                                   '--std-mir-key', 'e' * 64)
        self.assertEqual(result, 0)
        self.assertIs(prepared.call_args.kwargs['custom'], self.compiler)
        self.assertEqual(prepared.call_args.kwargs['prepared_key'], 'e' * 64)
        self.assertEqual(prepared.call_args.kwargs['namespace'], 'stable-cgu:off')
        self.assertEqual(report['std_mir']['key'], 'e' * 64)

    def test_application_flags_reach_cargo_after_clean_std_lookup(self):
        from std_mir_source_paths import validate_environment
        flags=['-Zhir-body-cache-reuse=true','--remap-path-prefix=/path with spaces=/virtual']
        def prepared(*args, **kwargs):
            validate_environment(os.environ)
            return (self.root/'std',self.compiler.host,'e'*64,
                    dict(identity=dict(policy='metadata-sysroot-v2-shared-source-paths-release-backtrace')))
        with patch.object(std_mir,'checked_std_mir',side_effect=prepared):
            result,[report]=self.runtime_launch('--std-mir','--std-mir-policy','source-paths-v2-shared',
                '--std-mir-key','e'*64,*['--rustflag='+flag for flag in flags])
        self.assertEqual(result,0)
        cargo,vm=self.invocations
        self.assertEqual(cargo[1]['env']['CARGO_ENCODED_RUSTFLAGS'],'\x1f'.join(flags))
        self.assertNotIn('RUSTFLAGS',cargo[1]['env'])
        self.assertNotIn('CARGO_ENCODED_RUSTFLAGS',vm[1]['env'])
        self.assertNotIn('CARGO_ENCODED_RUSTFLAGS',os.environ)
        self.assertEqual(report['application_rustflags'],flags)

    def test_application_flags_reject_ambiguous_environment_before_children(self):
        for name in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','CARGO_BUILD_RUSTFLAGS']:
            with self.subTest(name=name),patch.dict(os.environ,{name:''}),self.assertRaises(SystemExit):
                self.runtime_launch('--rustflag=-Zhir-body-cache-reuse=true')
        for flag in ['', 'one\x1ftwo', 'one\x00two']:
            with self.subTest(flag=flag),self.assertRaises(SystemExit):
                self.runtime_launch('--rustflag='+flag)
        self.assertEqual(self.invocations,[])

    def test_missing_ambiguous_and_unsupported_selection_fail_before_children(self):
        with self.assertRaises(SystemExit):
            self.runtime_launch(tool=False)
        for flags in [('--compiler-key', self.compiler.key), ('--std-mir',),
                      ('--cargo-key', 'c' * 64), ('--frontend-workers', '2'),
                      ('--host-library-opt', 'on'), ('--host-proc-macro-opt', 'on'),
                      ('--stable-cgu-partitioning', 'on'), ('--stable-mono-cgu-partitioning', 'off'),
                      ('--borrowck-cache', 'reuse')]:
            with self.subTest(flags=flags), self.assertRaises(SystemExit):
                self.runtime_launch(*flags)
        self.assertEqual(self.invocations, [])

    def test_changed_runtime_is_not_retried_with_stage2(self):
        with patch.object(runtime_compiler, 'load_runtime_compiler', side_effect=RuntimeError('runtime changed')):
            with self.assertRaisesRegex(RuntimeError, 'runtime changed'):
                self.runtime_launch()
        self.assertEqual(self.invocations, [])

    def test_runtime_mismatch_is_rejected_even_with_consistent_composition_digest(self):
        for field in ['version', 'compiler', 'driver', 'source', 'sysroot']:
            with self.subTest(field=field):
                original = copy.deepcopy(self.binding)
                if field == 'version': self.binding['runtime']['verbose_version'] += 'changed'
                elif field == 'compiler': self.binding['runtime']['executable']['sha256'] = '0' * 64
                elif field == 'driver': self.binding['runtime_driver']['path'] = '/other/driver.dylib'
                elif field == 'source': self.binding['runtime_source_commit'] = '0' * 40
                else: self.binding['runtime']['default_sysroot'] = '/private'
                self.save()
                with self.assertRaisesRegex(RuntimeError, 'different runtime'):
                    self.runtime_launch()
                self.binding.clear(); self.binding.update(original)
        self.assertEqual(self.invocations, [])

    def test_wrapper_probe_and_saved_binding_must_match_exporter(self):
        capabilities = copy.deepcopy(self.capabilities)
        capabilities.pop('runtime_wrapper')
        bad = copy.deepcopy(self.binding)
        bad['runtime']['default_sysroot'] = '/other'
        with self.assertRaisesRegex(RuntimeError, 'exporter and wrapper'):
            runtime_tools.bind_recorded_wrapper(capabilities, self.binaries, self.compiler, json.dumps(bad))
        for field in ['sha256', 'compiler_roles']:
            original = copy.deepcopy(self.capabilities['runtime_wrapper'])
            self.capabilities['runtime_wrapper'][field] = 'incorrect'
            self.save()
            with self.assertRaisesRegex(RuntimeError, 'matching recorded'):
                self.runtime_launch()
            self.capabilities['runtime_wrapper'] = original
        self.assertEqual(self.invocations, [])

    def test_stage2_tool_policy_cannot_be_relabelled_as_native_runtime(self):
        self.composition['kind'] = custom_compiler.TOOL_POLICY
        self.save()
        with self.assertRaisesRegex(RuntimeError, 'composition identity'):
            self.runtime_launch()
        self.assertEqual(self.invocations, [])

    def test_runtime_tools_require_explicit_runtime_selection(self):
        with self.assertRaisesRegex(RuntimeError, 'require --compiler-key'):
            self.launch(compiler=False)
        self.assertEqual(self.invocations, [])


if __name__ == '__main__':
    unittest.main()
