"""Policy isolation with synthetic launcher children; no compilers or Cargo run."""
from contextlib import ExitStack, redirect_stderr
import hashlib
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
import std_mir


class HostProcMacroLauncherTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack(); self.addCleanup(stack.close)
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        stack.enter_context(patch.object(interpreter, 'ROOT', self.root))
        stack.enter_context(patch.dict(os.environ, {'PATH': '/bin', 'RUST_INTERP_LAUNCH_STATS': '1',
            'RUST_INTERP_HOST_PROC_MACRO_OPT': 'inherited-value-must-not-leak'}, clear=True))
        self.tools = self.root / 'tools'; self.tools.mkdir()
        self.key = 'a' * 64
        self.manifest = self.root / 'Cargo.toml'; self.manifest.write_text('fixture')
        (self.root / 'libfixture.rmeta.rbc').write_bytes(b'bytecode')
        binaries = {name: hashlib.sha256(name.encode()).hexdigest() for name in interpreter.CURRENT_TOOL_BINARIES}
        (self.tools / 'ready.json').write_text(json.dumps(binaries))
        self.capabilities = self.tools / 'capabilities.json'
        self.capabilities.write_text(json.dumps(dict(schema_version=1, bytecode_version=5,
            tool_key=self.key, exporter_sha256=binaries['rust-interp-mir-export'],
            export_options=['host-proc-macro-opt-v1'])))
        stack.enter_context(patch.object(interpreter, 'installed_tools', return_value=(self.tools, self.key)))
        stack.enter_context(patch.object(interpreter.subprocess, 'run', side_effect=self.run_process))
        stack.enter_context(patch.object(std_mir, 'checked_std_mir', side_effect=self.prepared_std))
        self.invocations = []; self.std_calls = []

    def prepared_std(self, toolchain, **options):
        self.std_calls.append((toolchain, dict(options)))
        self.assertNotIn('namespace', options)
        self.assertNotIn('custom', options)
        self.assertNotIn('cargo', options)
        options['lookup_stats'].update(mode='cached', outcome='hit')
        return self.root / 'prepared-std', 'aarch64-apple-darwin', 'b' * 64, {}

    def run_process(self, command, **options):
        self.invocations.append((command, options))
        if command[0] == 'cargo':
            artifact = dict(reason='compiler-artifact', profile=dict(test=False),
                            filenames=[str(self.root / 'libfixture.rmeta')])
            return subprocess.CompletedProcess(command, 0, json.dumps(artifact))
        self.assertEqual(command[0], str(self.tools / 'rust-interp-vm'))
        return subprocess.CompletedProcess(command, 0)

    def launch(self, *extra, std=True):
        args = ['interpreter.py', '--manifest-path', str(self.manifest), '--package', 'fixture',
                '--entry', 'entry', '--tool-key', self.key]
        if std: args += ['--std-mir', '--toolchain-lookup', 'cached']
        stream = io.StringIO()
        with patch.object(sys, 'argv', [*args, *extra]), redirect_stderr(stream):
            code = interpreter.main()
        reports = [json.loads(line.removeprefix('rust-interp-launch: '))
                   for line in stream.getvalue().splitlines() if line.startswith('rust-interp-launch: ')]
        return code, reports

    def test_off_on_off_isolates_project_cache_with_same_tools_std_and_cargo(self):
        workspaces = []
        for mode in ['off', 'on', 'off']:
            self.invocations.clear()
            code, [report] = self.launch('--host-proc-macro-opt', mode)
            self.assertEqual(code, 0)
            cargo, vm = self.invocations
            self.assertEqual(cargo[0][:2], ['cargo', '+' + interpreter.TOOLCHAIN])
            self.assertEqual(cargo[1]['env']['RUSTC_WORKSPACE_WRAPPER'], '')
            self.assertEqual(cargo[1]['env'].get('RUST_INTERP_HOST_PROC_MACRO_OPT'), 'on' if mode == 'on' else None)
            self.assertNotIn('RUST_INTERP_HOST_PROC_MACRO_OPT', vm[1]['env'])
            self.assertEqual(report['host_proc_macro_opt'], mode)
            self.assertEqual(report['tool_key'], self.key)
            self.assertEqual(report['std_mir']['key'], 'b' * 64)
            workspaces.append(cargo[1]['env']['CARGO_TARGET_DIR'])
        self.assertEqual(workspaces[0], workspaces[2])
        self.assertNotEqual(workspaces[0], workspaces[1])
        self.assertEqual(len(self.std_calls), 3)

    def test_incompatible_mechanisms_and_missing_std_fail_before_children(self):
        for flags in [[], ['--compiler-key', 'c' * 64], ['--cargo-key', 'd' * 64],
                      ['--borrowck-cache', 'verify']]:
            with self.subTest(flags=flags), self.assertRaises(SystemExit):
                self.launch('--host-proc-macro-opt', 'on', *flags, std=bool(flags))
        self.assertEqual(self.invocations, [])
        self.assertEqual(self.std_calls, [])

    def test_capability_required_only_when_enabled_and_default_cache_is_unchanged(self):
        self.capabilities.unlink()
        with self.assertRaises(RuntimeError):
            self.launch('--host-proc-macro-opt', 'on')
        self.assertEqual(self.invocations, [])
        code, [default] = self.launch()
        self.assertEqual(code, 0)
        code, [explicit] = self.launch('--host-proc-macro-opt', 'off')
        self.assertEqual(code, 0)
        self.assertEqual(default['workspace_path'], explicit['workspace_path'])


if __name__ == '__main__':
    unittest.main()
