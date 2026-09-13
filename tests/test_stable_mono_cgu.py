"""Prepared synthetic selector/provenance controls; no real child processes."""
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_custom_compiler_launcher as launcher_fixture

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import stable_mono_cgu as mono
import std_mir


class StableMonoLauncherTests(unittest.TestCase):
    mono = True
    setUp = launcher_fixture.CustomCompilerLauncherTests.setUp
    launch = launcher_fixture.CustomCompilerLauncherTests.launch
    run_process = launcher_fixture.CustomCompilerLauncherTests.run_process

    def test_explicit_modes_are_separate_from_each_other_and_legacy_omission(self):
        workspaces = []
        for mode in [None, 'off', 'on', 'off', None]:
            arguments = [] if mode is None else ['--stable-mono-cgu-partitioning', mode]
            result, [report] = self.launch(*arguments, '--function-cache', 'auto')
            self.assertEqual(result, 0)
            cargo, vm = self.invocations[-2:]
            workspaces.append(cargo[1]['env']['CARGO_TARGET_DIR'])
            self.assertEqual(cargo[1]['env']['RUST_INTERP_STABLE_CGU_PARTITIONING'], 'off')
            self.assertEqual(cargo[1]['env']['RUST_INTERP_FUNCTION_CACHE'], 'auto')
            self.assertNotIn('RUST_INTERP_STABLE_MONO_CGU_PARTITIONING', vm[1]['env'])
            if mode is None:
                self.assertNotIn('RUST_INTERP_STABLE_MONO_CGU_PARTITIONING', cargo[1]['env'])
                self.assertNotIn('stable_mono_cgu_partitioning', report['custom_compiler'])
            else:
                self.assertEqual(cargo[1]['env']['RUST_INTERP_STABLE_MONO_CGU_PARTITIONING'], mode)
                policy = report['custom_compiler']['stable_mono_cgu_partitioning']
                self.assertEqual(policy['namespace'], 'stable-mono-cgu:' + mode)
                self.assertEqual(policy['rustc_options'][0], '-Zstable-cgu-partitioning=no')
                self.assertEqual(policy['wrapper']['compiler_sysroot'], str(self.compiler.sysroot))
        self.assertEqual(workspaces[0], workspaces[4])
        self.assertEqual(workspaces[1], workspaces[3])
        self.assertEqual(len(set(workspaces)), 3)

    def test_std_namespaces_follow_explicit_selector_without_changing_preparation_flags(self):
        namespaces = []
        def prepared(toolchain, **options):
            namespaces.append(options['namespace'])
            return self.root / 'std', self.compiler.host, 'f' * 64, {}
        with patch.object(std_mir, 'checked_std_mir', side_effect=prepared):
            for mode in ['off', 'on']:
                self.launch('--std-mir', '--stable-mono-cgu-partitioning', mode)
        self.assertEqual(namespaces, ['stable-mono-cgu:off', 'stable-mono-cgu:on'])

    def test_missing_compiler_help_or_physical_wrapper_binding_fails_before_cargo(self):
        proof = self.compiler.identity.pop('unstable_options')
        with patch('custom_compiler.load_compiler', return_value=self.compiler):
            with self.assertRaisesRegex(RuntimeError, 'recorded -Zhelp'):
                self.launch('--stable-mono-cgu-partitioning', 'off')
        self.compiler.identity['unstable_options'] = proof
        path = self.tools / 'capabilities.json'
        original = json.loads(path.read_text())
        for field, value in [('stable_mono_cgu_wrapper', {}), ('compiler_sysroot', '/other/compiler')]:
            path.write_text(json.dumps(dict(original, **{field: value})))
            with self.assertRaisesRegex(RuntimeError, 'exporter/wrapper capability'):
                self.launch('--stable-mono-cgu-partitioning', 'on')
        self.assertEqual(self.invocations, [])

    def test_conflicting_selectors_and_environment_fail_before_cargo(self):
        for extra in [['--stable-cgu-partitioning', 'on'], ['--cargo-key', 'a' * 64],
                      ['--borrowck-cache', 'reuse']]:
            with self.subTest(extra=extra), self.assertRaises(SystemExit):
                self.launch('--stable-mono-cgu-partitioning', 'on', *extra)
        for name, value in [('RUSTFLAGS', '-Z stable_mono_cgu_partitioning=no'),
                            ('CARGO_ENCODED_RUSTFLAGS', '-Z\x1fthreads=2'),
                            ('CARGO_TARGET_AARCH64_APPLE_DARWIN_RUSTFLAGS', '@flags'),
                            ('RUST_INTERP_HOST_PROC_MACRO_OPT', 'on'),
                            ('RUST_INTERP_FRONTEND_WORKERS', '1')]:
            with self.subTest(name=name), patch.dict(os.environ, {name: value}), self.assertRaises(SystemExit):
                self.launch('--stable-mono-cgu-partitioning', 'off')
        with self.assertRaises(SystemExit):
            self.launch('--stable-mono-cgu-partitioning', 'off', compiler=False)
        self.assertEqual(self.invocations, [])

    def test_wrapper_publication_probes_exact_physical_compiler_association(self):
        manifest = json.loads((self.tools / 'ready.json').read_text())
        capabilities = dict(export_options=[mono.OPTION])
        output = mono.POLICY + '\n' + str(self.compiler.sysroot) + '\n'
        with patch.object(mono.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, output)) as probe:
            mono.bind_wrapper_capability(self.tools, manifest, capabilities, self.compiler, {})
        self.assertEqual(probe.call_args.args[0][0], str(self.tools / mono.WRAPPER))
        self.assertEqual(capabilities['stable_mono_cgu_wrapper']['sha256'], manifest[mono.WRAPPER])
        with patch.object(mono.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, mono.POLICY + '\n/other\n')):
            with self.assertRaisesRegex(RuntimeError, 'compiled sysroot differs'):
                mono.bind_wrapper_capability(self.tools, manifest, capabilities, self.compiler, {})

    def test_future_worker_macro_selectors_and_frontend_flags_cannot_mix(self):
        args = SimpleNamespace(stable_mono_cgu_partitioning='off', compiler_key=self.compiler.key,
                               stable_cgu_partitioning='off')
        for name, value in [('frontend_workers', 1), ('host_proc_macro_opt', 'on')]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                mono.validate_selection(SimpleNamespace(**vars(args), **{name: value}), {})
        mono.validate_selection(args, {'RUSTFLAGS': '--jobs-backend=2 --jobs-linker=1 -Copt-level=0'})
        for flags in ['--jobs-frontend=1', '--jobs=2', '-j2', '-Zproc-macro-execution-strategy=cross-thread']:
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                mono.validate_selection(args, {'RUSTFLAGS': flags})


if __name__ == '__main__':
    unittest.main()
