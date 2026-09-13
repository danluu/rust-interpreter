"""Check opt-in compiler-cache wiring without invoking Cargo or the VM."""
from contextlib import ExitStack, redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import interpreter


class BorrowckCacheLauncherTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        self.tools = self.root / 'tools'
        self.tools.mkdir()
        self.key = 'a' * 64
        (self.tools / 'ready.json').write_text(json.dumps({
            name: 'b' * 64 for name in interpreter.CURRENT_TOOL_BINARIES}))
        self.capabilities(['borrowck-cache', 'function-cache-reuse'])
        self.manifest = self.root / 'Cargo.toml'
        self.manifest.write_text('[package]\nname="fixture"\nversion="0.1.0"\n')
        self.artifact = self.root / 'libfixture.rmeta.rbc'
        self.artifact.write_bytes(b'selected bytecode')
        self.invocations = []
        self.cargo_returncode = 0
        stack.enter_context(patch.object(interpreter, 'ROOT', self.root))
        self.installed = stack.enter_context(patch.object(
            interpreter, 'installed_tools', return_value=(self.tools, self.key)))
        stack.enter_context(patch.object(interpreter.subprocess, 'run', self.run_process))

    def capabilities(self, options):
        (self.tools / 'capabilities.json').write_text(json.dumps(dict(
            schema_version=1, bytecode_version=5, tool_key='a' * 64,
            exporter_sha256='b' * 64, export_options=options)))

    def run_process(self, command, **kwargs):
        self.invocations.append((command, kwargs))
        if command[0] == 'cargo':
            event = dict(reason='compiler-artifact', profile=dict(test=False),
                         filenames=[str(self.root / 'libfixture.rmeta')])
            return subprocess.CompletedProcess(command, self.cargo_returncode, json.dumps(event))
        self.assertEqual(command[0], str(self.tools / 'rust-interp-vm'))
        return subprocess.CompletedProcess(command, 0)

    def launch(self, *extra):
        stderr = io.StringIO()
        argv = ['interpreter.py', '--manifest-path', str(self.manifest),
                '--package', 'fixture', '--tool-key', self.key, '--entry', 'selected', *extra]
        with patch.object(sys, 'argv', argv), \
                patch.dict(os.environ, {'RUST_INTERP_LAUNCH_STATS': '1'}), \
                redirect_stderr(stderr):
            result = interpreter.main()
        prefix = 'rust-interp-launch: '
        stats = [json.loads(line[len(prefix):]) for line in stderr.getvalue().splitlines()
                 if line.startswith(prefix)]
        return result, stats

    def test_enabled_modes_reach_only_cargo_and_report_the_mode(self):
        for mode in ['verify', 'reuse']:
            with self.subTest(mode=mode):
                self.invocations.clear()
                result, stats = self.launch('--borrowck-cache', mode)
                self.assertEqual(result, 0)
                cargo, vm = self.invocations
                self.assertEqual(cargo[1]['env']['RUST_INTERP_BORROWCK_CACHE'], mode)
                self.assertNotIn('RUST_INTERP_BORROWCK_CACHE', vm[1]['env'])
                self.assertEqual(stats[0]['borrowck_cache'], mode)
                self.assertEqual(Path(cargo[1]['env']['RUSTC_WRAPPER']).name,
                                 'rust-interp-rustc-wrapper')

    def test_ambient_cache_settings_cannot_enable_default_or_explicit_off(self):
        for mode in [(), ('--borrowck-cache', 'off')]:
            for ambient in ['reuse', 'invalid']:
                with self.subTest(mode=mode, ambient=ambient):
                    self.invocations.clear()
                    with patch.dict(os.environ, {'RUST_INTERP_BORROWCK_CACHE': ambient}):
                        result, stats = self.launch(*mode)
                    self.assertEqual(result, 0)
                    self.assertEqual(stats[0]['borrowck_cache'], 'off')
                    self.assertTrue(all('RUST_INTERP_BORROWCK_CACHE' not in args['env']
                                        for _, args in self.invocations))

    def test_each_enabled_mode_has_an_independent_cargo_workspace(self):
        paths = []
        for mode in [(), ('--borrowck-cache', 'off'), ('--borrowck-cache', 'verify'),
                     ('--borrowck-cache', 'reuse'), ('--borrowck-cache', 'reuse')]:
            self.invocations.clear()
            self.assertEqual(self.launch(*mode)[0], 0)
            paths.append(self.invocations[0][1]['env']['CARGO_TARGET_DIR'])
        self.assertEqual(paths[0], paths[1])
        self.assertEqual(paths[3], paths[4])
        self.assertEqual(len(set(paths)), 3)

    def test_borrowck_and_function_cache_modes_both_reach_cargo(self):
        self.assertEqual(self.launch('--borrowck-cache', 'verify', '--function-cache', 'reuse')[0], 0)
        cargo, vm = self.invocations
        self.assertEqual(cargo[1]['env']['RUST_INTERP_BORROWCK_CACHE'], 'verify')
        self.assertEqual(cargo[1]['env']['RUST_INTERP_FUNCTION_CACHE'], 'reuse')
        for name in ['RUST_INTERP_BORROWCK_CACHE', 'RUST_INTERP_FUNCTION_CACHE']:
            self.assertNotIn(name, vm[1]['env'])

    def test_user_namespace_cannot_alias_an_enabled_mode(self):
        paths = []
        for arguments in [('--cache-namespace', 'borrowck-cache:reuse'),
                          ('--borrowck-cache', 'reuse'),
                          ('--cache-namespace', 'borrowck-cache:verify'),
                          ('--borrowck-cache', 'verify')]:
            self.invocations.clear()
            self.assertEqual(self.launch(*arguments)[0], 0)
            paths.append(self.invocations[0][1]['env']['CARGO_TARGET_DIR'])
        self.assertEqual(len(set(paths)), 4)

    def test_failed_check_never_starts_execution(self):
        self.cargo_returncode = 101
        for mode in ['verify', 'reuse']:
            with self.subTest(mode=mode):
                self.invocations.clear()
                result, stats = self.launch('--borrowck-cache', mode)
                self.assertEqual(result, 101)
                self.assertEqual(stats, [])
                self.assertEqual(len(self.invocations), 1)
                self.assertEqual(self.invocations[0][0][0], 'cargo')

    def test_old_tools_reject_opt_in_before_any_process_is_started(self):
        self.capabilities(['entry-catalog'])
        for mode in ['verify', 'reuse']:
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(RuntimeError, 'does not support --borrowck-cache'):
                    self.launch('--borrowck-cache', mode)
        self.assertEqual(self.invocations, [])
        self.assertEqual(self.launch('--borrowck-cache', 'off')[0], 0)

    def test_capability_must_be_bound_to_the_installed_binary(self):
        path = self.tools / 'capabilities.json'
        data = json.loads(path.read_text())
        data['exporter_sha256'] = 'c' * 64
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError, 'does not support --borrowck-cache'):
            self.launch('--borrowck-cache', 'reuse')
        self.assertEqual(self.invocations, [])

    def test_invalid_cli_mode_fails_before_loading_tools(self):
        for mode in ['auto', '', 'Reuse', '/some/cache']:
            with self.subTest(mode=mode):
                with self.assertRaises(SystemExit) as error:
                    self.launch('--borrowck-cache', mode)
                self.assertEqual(error.exception.code, 2)
        self.installed.assert_not_called()
        self.assertEqual(self.invocations, [])


if __name__ == '__main__':
    unittest.main()
