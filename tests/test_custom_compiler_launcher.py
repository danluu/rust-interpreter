"""Custom compiler routing and std namespaces with synthetic Cargo/VM children."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_custom_compiler import fake_install, thaw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import custom_compiler as custom
import build_custom_tools
import interpreter
import std_mir
import stable_mono_cgu


class CustomCompilerLauncherTests(unittest.TestCase):
    mono = False

    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.addCleanup(thaw, self.root)
        self.compiler = fake_install(self.root, mono=self.mono)
        stack.enter_context(patch.object(interpreter, 'ROOT', self.root))
        stack.enter_context(patch.object(std_mir, 'ROOT', self.root))
        stack.enter_context(patch.dict(os.environ, {'PATH': '/bin', 'RUST_INTERP_LAUNCH_STATS': '1'}, clear=True))
        binaries = {name: custom.digest(name) for name in interpreter.CURRENT_TOOL_BINARIES}
        composition = dict(kind=custom.TOOL_POLICY, compiler_key=self.compiler.key,
                           compiler_sysroot=str(self.compiler.sysroot), binaries=binaries)
        self.key = custom.digest(composition)
        self.tools = self.root / 'tools'; self.tools.mkdir()
        (self.tools / 'ready.json').write_text(json.dumps(binaries))
        (self.tools / 'compiler.json').write_text(json.dumps(composition))
        capabilities = dict(schema_version=1,
            bytecode_version=5, tool_key=self.key, exporter_sha256=binaries['rust-interp-mir-export'],
            export_options=['stable-cgu-partitioning'])
        if self.mono:
            capabilities.update(compiler_sysroot=str(self.compiler.sysroot),
                export_options=['stable-cgu-partitioning', stable_mono_cgu.OPTION, 'function-cache-auto'],
                stable_mono_cgu_wrapper=dict(policy=stable_mono_cgu.POLICY,
                    compiler_sysroot=str(self.compiler.sysroot), sha256=binaries[stable_mono_cgu.WRAPPER]))
        (self.tools / 'capabilities.json').write_text(json.dumps(capabilities))
        self.manifest = self.root / 'Cargo.toml'; self.manifest.write_text('fixture')
        (self.root / 'libfixture.rmeta.rbc').write_bytes(b'bytecode')
        stack.enter_context(patch.object(interpreter, 'installed_tools', return_value=(self.tools, self.key)))
        stack.enter_context(patch.object(interpreter.subprocess, 'run', side_effect=self.run_process))
        self.invocations = []

    def run_process(self, command, **kwargs):
        self.invocations.append((command, kwargs))
        if command[0] == 'cargo':
            event = dict(reason='compiler-artifact', profile=dict(test=False),
                         filenames=[str(self.root / 'libfixture.rmeta')])
            return subprocess.CompletedProcess(command, 0, json.dumps(event))
        self.assertEqual(command[0], str(self.tools / 'rust-interp-vm'))
        return subprocess.CompletedProcess(command, 0)

    def launch(self, *extra, compiler=True, tool=True):
        arguments = ['interpreter.py', '--manifest-path', str(self.manifest),
                     '--package', 'fixture', '--entry', 'selected']
        if tool: arguments += ['--tool-key', self.key]
        if compiler: arguments += ['--compiler-key', self.compiler.key]
        stderr = io.StringIO()
        with patch.object(sys, 'argv', [*arguments, *extra]), redirect_stderr(stderr):
            result = interpreter.main()
        return result, [json.loads(line.removeprefix('rust-interp-launch: '))
            for line in stderr.getvalue().splitlines() if line.startswith('rust-interp-launch: ')]

    def test_same_tools_and_compiler_use_separate_off_on_workspaces_and_report_policy(self):
        workspaces = []
        for mode in ['off', 'on', 'off']:
            self.invocations.clear()
            result, [report] = self.launch('--stable-cgu-partitioning', mode)
            self.assertEqual(result, 0)
            cargo, vm = self.invocations
            self.assertEqual(cargo[0][:2], ['cargo', '+' + interpreter.TOOLCHAIN])
            self.assertEqual(cargo[1]['env']['RUSTC'], str(self.compiler.rustc))
            self.assertEqual(cargo[1]['env']['RUSTC_WORKSPACE_WRAPPER'], '')
            self.assertEqual(cargo[1]['env']['RUST_INTERP_COMPILER_RUSTC'], str(self.compiler.rustc))
            self.assertEqual(cargo[1]['env']['RUST_INTERP_STABLE_CGU_PARTITIONING'], mode)
            self.assertNotIn('RUST_INTERP_STABLE_CGU_PARTITIONING', vm[1]['env'])
            self.assertEqual(report['custom_compiler']['key'], self.compiler.key)
            self.assertEqual(report['custom_compiler']['stable_cgu_partitioning'], mode)
            workspaces.append(cargo[1]['env']['CARGO_TARGET_DIR'])
        self.assertEqual(workspaces[0], workspaces[2])
        self.assertNotEqual(workspaces[0], workspaces[1])

    def test_missing_selection_association_and_conflicting_compiler_fail_before_cargo(self):
        with self.assertRaises(SystemExit):
            self.launch(tool=False)
        with self.assertRaises(SystemExit):
            self.launch('--stable-cgu-partitioning', 'on', compiler=False)
        with self.assertRaisesRegex(RuntimeError, 'require --compiler-key'):
            self.launch(compiler=False)
        with patch.dict(os.environ, {'RUSTC': '/stock/rustc'}):
            with self.assertRaisesRegex(RuntimeError, 'conflicts with RUSTC'):
                self.launch()
        (self.tools / 'compiler.json').unlink()
        with self.assertRaisesRegex(RuntimeError, 'missing or invalid compiler manifest'):
            self.launch()
        self.assertEqual(self.invocations, [])

    def test_selected_std_namespace_is_bound_to_launcher_report(self):
        def prepared(toolchain, **options):
            mode = options['namespace'].removeprefix('stable-cgu:')
            options['lookup_stats'].update(mode='cached', outcome='owned-manifest')
            return self.root / ('std-' + mode), self.compiler.host, custom.digest(mode), {}
        with patch.object(std_mir, 'checked_std_mir', side_effect=prepared):
            for mode in ['off', 'on']:
                result, [report] = self.launch('--std-mir', '--toolchain-lookup', 'cached',
                                              '--stable-cgu-partitioning', mode)
                self.assertEqual(result, 0)
                self.assertEqual(report['std_mir'], dict(key=custom.digest(mode),
                    sysroot=str(self.root / ('std-' + mode)), target=self.compiler.host))
                cargo = self.invocations[-2]
                self.assertEqual(cargo[1]['env']['RUST_INTERP_STD_SYSROOT'], report['std_mir']['sysroot'])
                self.assertEqual(cargo[1]['env']['RUST_INTERP_STD_TARGET'], report['std_mir']['target'])

    def test_custom_std_build_keeps_flags_and_selects_custom_rustc_in_separate_namespaces(self):
        children = []
        def popen(command, **kwargs):
            children.append((command, kwargs['env']))
            target = Path(command[command.index('--target-dir') + 1])
            def wait():
                output = target / self.compiler.host / 'release/deps'
                output.mkdir(parents=True)
                for crate in ['core', 'alloc', 'std', 'test', 'proc_macro']:
                    (output / ('lib' + crate + '-fixture.rmeta')).write_bytes(b'metadata')
                return 0
            return SimpleNamespace(pid=123, wait=wait)
        with patch.object(std_mir.subprocess, 'Popen', side_effect=popen):
            first = std_mir.checked_std_mir(interpreter.TOOLCHAIN, custom=self.compiler, namespace='stable-cgu:off')
            second = std_mir.checked_std_mir(interpreter.TOOLCHAIN, custom=self.compiler, namespace='stable-cgu:on')
            again = std_mir.checked_std_mir(interpreter.TOOLCHAIN, custom=self.compiler, namespace='stable-cgu:off')
        self.assertNotEqual(first[2], second[2])
        self.assertEqual(first, again)
        self.assertEqual(len(children), 2)
        for command, env in children:
            self.assertEqual(command[:2], ['cargo', '+' + interpreter.TOOLCHAIN])
            self.assertEqual(env['RUSTC'], str(self.compiler.rustc))
            self.assertEqual(env['RUSTFLAGS'], std_mir.FLAGS)
        self.assertEqual(first[3]['identity']['compiler_key'], self.compiler.key)
        self.assertEqual(first[3]['identity']['source_sha256'], self.compiler.identity['source_sha256'])

    def test_tool_build_uses_custom_rustc_and_publishes_checked_compiler_association(self):
        captures = []
        def capture(command, **kwargs):
            captures.append((command, kwargs))
            target = Path(command[command.index('--target-dir') + 1]) / 'release'
            target.mkdir(parents=True)
            for name in interpreter.CURRENT_TOOL_BINARIES:
                (target / name).write_bytes(name.encode())
            return SimpleNamespace(returncode=0, pid=123), 'build stdout', ''
        capabilities = dict(schema_version=1, bytecode_version=5,
                            compiler_sysroot=str(self.compiler.sysroot),
                            export_options=['stable-cgu-partitioning'])
        arguments = ['build_custom_tools.py', '--compiler-key', self.compiler.key, '--run-id', 'tools-fixture']
        cargo = dict(executable='/pinned/cargo', sha256='f' * 64, version='Cargo fixture', toolchain=interpreter.TOOLCHAIN)
        with patch.object(build_custom_tools, 'ROOT', self.root), \
             patch.object(build_custom_tools, 'cargo_identity', return_value=cargo), \
             patch.object(build_custom_tools, 'source_identity', return_value={'source.rs': 'e' * 64}), \
             patch.object(build_custom_tools, 'require_space'), \
             patch.object(build_custom_tools, 'capture', side_effect=capture), \
             patch.object(build_custom_tools.subprocess, 'run', return_value=
                          subprocess.CompletedProcess([], 0, json.dumps(capabilities))), \
             patch.object(sys, 'argv', arguments), redirect_stdout(io.StringIO()):
            build_custom_tools.main()
        [(command, options)] = captures
        self.assertEqual(command[:2], ['/pinned/cargo', 'build'])
        self.assertEqual(command[command.index('--jobs') + 1], '2')
        self.assertEqual(options['env']['RUSTC'], str(self.compiler.rustc))
        self.assertEqual(options['env']['RUSTC_WORKSPACE_WRAPPER'], '')
        result = json.loads((self.root / '.work/tools-fixture/result.json').read_text())
        directory = self.root / '.work/interpreter-tools' / result['tool_key']
        custom.validate_tool_compiler(directory, result['tool_key'], self.compiler)
        self.assertEqual(json.loads((directory / 'compiler.json').read_text())['cargo'], cargo)


if __name__ == '__main__':
    unittest.main()
