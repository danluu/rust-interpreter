"""Synthetic launch and publication controls; no compiler/Cargo children."""
import json
import os
import subprocess
import unittest
from unittest.mock import patch

import test_host_proc_macro_launcher as macro_fixture
import host_library_opt


class HostLibraryLauncherTests(unittest.TestCase):
    # Share the existing mocked Cargo/std/VM fixture without inheriting its tests.
    prepared_std = macro_fixture.HostProcMacroLauncherTests.prepared_std
    run_process = macro_fixture.HostProcMacroLauncherTests.run_process
    launch = macro_fixture.HostProcMacroLauncherTests.launch

    def setUp(self):
        macro_fixture.HostProcMacroLauncherTests.setUp(self)
        os.environ.pop('RUST_INTERP_HOST_PROC_MACRO_OPT')
        os.environ['RUST_INTERP_HOST_LIBRARY_OPT'] = 'inherited-value-must-not-leak'
        self.caps = json.loads(self.capabilities.read_text())
        self.binaries = json.loads((self.tools / 'ready.json').read_text())
        self.caps.update(compiler_sysroot='/toolchain', host_library_opt=host_library_opt.CAPABILITY,
            host_library_wrapper=dict(sha256=self.binaries[host_library_opt.WRAPPER],
                capability=host_library_opt.CAPABILITY, compiler_sysroot='/toolchain'),
            export_options=[host_library_opt.POLICY, 'function-cache-auto'])
        self.capabilities.write_text(json.dumps(self.caps))

    def test_off_on_off_shares_std_but_separates_project_cache_and_preserves_cargo_environment(self):
        targets = []
        commands = []
        for mode in ['off', 'on', 'off']:
            self.invocations.clear()
            with patch.dict(os.environ, {'OPT_LEVEL': '0', 'DEBUG': 'true', 'CARGO_PROFILE_DEV_DEBUG': '2'}):
                code, [report] = self.launch('--host-library-opt', mode, '--function-cache', 'auto')
            self.assertEqual(code, 0)
            cargo, vm = self.invocations
            commands.append(cargo[0])
            env = cargo[1]['env']
            self.assertEqual(env.get('RUST_INTERP_HOST_LIBRARY_OPT'), 'on' if mode == 'on' else None)
            self.assertEqual(env['RUST_INTERP_FUNCTION_CACHE'], 'auto')
            self.assertEqual((env['OPT_LEVEL'], env['DEBUG'], env['CARGO_PROFILE_DEV_DEBUG']), ('0', 'true', '2'))
            self.assertNotIn('RUST_INTERP_HOST_LIBRARY_OPT', vm[1]['env'])
            self.assertEqual(report['tool_key'], self.key)
            self.assertEqual(report['std_mir']['key'], 'b' * 64)
            if mode == 'on':
                self.assertEqual(report['host_library_opt'], host_library_opt.receipt(self.caps))
            else:
                self.assertNotIn('host_library_opt', report)
            targets.append(env['CARGO_TARGET_DIR'])
        self.assertEqual(commands[0], commands[1])
        self.assertEqual(commands[0], commands[2])
        self.assertEqual(targets[0], targets[2])
        self.assertNotEqual(targets[0], targets[1])
        self.assertEqual(len(self.std_calls), 3)

    def test_missing_std_and_mixed_policies_fail_before_tool_std_or_cargo_children(self):
        for flags in [[], ['--compiler-key', 'c' * 64], ['--cargo-key', 'd' * 64],
                      ['--borrowck-cache', 'verify'], ['--host-proc-macro-opt', 'on'],
                      ['--frontend-workers', '1'], ['--stable-mono-cgu-partitioning', 'off'],
                      ['--stable-cgu-partitioning', 'on']]:
            with self.subTest(flags=flags), self.assertRaises(SystemExit):
                self.launch('--host-library-opt', 'on', *flags, std=bool(flags))
        self.assertEqual(self.invocations, [])
        self.assertEqual(self.std_calls, [])
        for name, value in [('RUSTC', '/other/rustc'), ('RUST_INTERP_FRONTEND_WORKERS', '2'),
                            ('RUST_INTERP_HOST_PROC_MACRO_OPT', 'on'), ('RUST_INTERP_BORROWCK_CACHE', 'reuse')]:
            with patch.dict(os.environ, {name: value}), self.assertRaises(SystemExit):
                self.launch('--host-library-opt', 'on')

    def test_old_tools_remain_usable_only_with_policy_off(self):
        self.capabilities.unlink()
        with self.assertRaises(RuntimeError):self.launch('--host-library-opt', 'on')
        self.assertEqual(self.invocations, [])
        _, [omitted] = self.launch()
        _, [explicit] = self.launch('--host-library-opt', 'off')
        self.assertEqual(omitted['workspace_path'], explicit['workspace_path'])

    def test_exact_exporter_wrapper_and_compiler_capabilities_are_required(self):
        for field in ['exporter_sha256', 'host_library_opt', 'host_library_wrapper', 'compiler_sysroot']:
            caps = dict(self.caps)
            caps.pop(field)
            self.capabilities.write_text(json.dumps(caps))
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.launch('--host-library-opt', 'on')
        for field in ['sha256', 'capability', 'compiler_sysroot']:
            caps = json.loads(json.dumps(self.caps))
            caps['host_library_wrapper'][field] = 'wrong'
            self.capabilities.write_text(json.dumps(caps))
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.launch('--host-library-opt', 'on')
        self.assertEqual(self.invocations, [])

    def test_publication_probe_binds_actual_wrapper_and_compiled_sysroot(self):
        caps = dict(self.caps)
        caps.pop('host_library_wrapper')
        output = json.dumps(host_library_opt.CAPABILITY) + '\n/toolchain\n'
        with patch.object(host_library_opt.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, output)) as probe:
            host_library_opt.bind_wrapper_capability(self.tools, self.binaries, caps)
            self.assertEqual(caps['host_library_wrapper'], self.caps['host_library_wrapper'])
            self.assertEqual(probe.call_args.args[0], [str(self.tools / host_library_opt.WRAPPER), '--rust-interp-host-library-capability'])
            for bad in [output.replace('/toolchain', '/other'), output + 'extra\n', output.replace('host-library-opt-v1', 'other-policy')]:
                probe.return_value = subprocess.CompletedProcess([], 0, bad)
                with self.assertRaises(RuntimeError):
                    host_library_opt.bind_wrapper_capability(self.tools, self.binaries, caps)
            probe.reset_mock()
            host_library_opt.bind_wrapper_capability(self.tools, self.binaries, dict(export_options=[]))
            probe.assert_not_called()


if __name__ == '__main__':
    unittest.main()
