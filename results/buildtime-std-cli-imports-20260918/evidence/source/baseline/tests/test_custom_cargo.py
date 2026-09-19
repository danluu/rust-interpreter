"""Owned Cargo validation and routing fixtures; no real compilers or builds."""
from contextlib import ExitStack, redirect_stderr
import hashlib
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

from test_custom_compiler import HOST, fake_install, thaw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import custom_cargo as cargo_module
import custom_cargo_libraries as libraries
import custom_compiler
import interpreter
import std_mir


def fake_cargos(root):
    home = root / 'rustup'
    sysroot = home / 'toolchains' / (interpreter.TOOLCHAIN + '-' + HOST)
    library = sysroot / 'lib/rustlib/src/rust/library'
    for directory in [sysroot / 'bin', sysroot / 'lib/rustlib' / HOST / 'lib', library]:
        directory.mkdir(parents=True, exist_ok=True)
    for name in ['Cargo.toml', 'Cargo.lock', 'std/src/lib.rs']:
        p = library / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(name)
    rustc = sysroot / 'bin/rustc'; rustc.write_text('compiler fixture')
    builder = sysroot / 'bin/cargo'; builder.write_text('builder fixture')
    version = 'rustc fixture\nhost: ' + HOST + '\n'
    raw = root / '.work/qualification'; (raw / 'logs').mkdir(parents=True)
    report = dict(owner=str(root), status='passed', candidate_source_restored=True,
                  source_revision='a' * 40, source=str(root / 'source'), supervisor_pid=1,
                  candidate_tests_passed=3, stock_existing_tests_passed=2, stock_expected_regression_failures=1,
                  source_only_production_difference='src/util/rustc.rs',
                  compiler=version, environment_overrides=dict(RUSTC=str(rustc), RUSTUP_HOME=str(home)),
                  compiler_files={p.name: cargo_module.file_identity(p) for p in [rustc, builder]},
                  commands=[], tools=[])
    for mode in ['stock', 'candidate']:
        binary = raw / (mode + '-cargo'); binary.write_text(mode); binary.chmod(0o755)
        composition = dict(mode=mode, cargo_sha256=cargo_module.file_digest(binary),
            source_revision=report['source_revision'], source_inventory={
                'src/util/rustc.rs': ('d' if mode == 'stock' else 'e') * 64, 'same.rs': 'f' * 64},
            compiler=version, compiler_sha256=cargo_module.file_digest(rustc),
            builder_sha256=cargo_module.file_digest(builder),
            environment_overrides=report['environment_overrides'], profile='release', features='default')
        key = cargo_module.digest(composition)
        manifest = raw / (mode + '-source.json')
        manifest.write_text(json.dumps(dict(tool_key=key, composition=composition)))
        report['tools'].append(dict(mode=mode, tool_key=key, binary=cargo_module.file_identity(binary),
                                   source_manifest=cargo_module.file_identity(manifest)))
        for suffix in ['build', 'regression']:
            label = mode + '-' + suffix
            code = 101 if label == 'stock-regression' else 0
            row = dict(label=label, command=[str(builder), suffix], pid=2,
                       returncode=code, expected_returncode=code,
                       source_inventory_sha256=hashlib.sha256(json.dumps(
                           composition['source_inventory'], sort_keys=True).encode()).hexdigest())
            receipt = dict(status='finished', command=row['command'], pid=2, parent_pid=1,
                           cwd=report['source'], returncode=code)
            (raw / 'logs' / (label + '-process.json')).write_text(json.dumps(receipt))
            for stream in ['stdout', 'stderr']:
                path = raw / 'logs' / (label + '.' + stream); path.write_text(label + stream)
                row[stream + '_sha256'] = cargo_module.file_digest(path)
            report['commands'].append(row)
    report['original_candidate_inventory'] = composition['source_inventory']
    report_path = raw / 'summary.json'; report_path.write_text(json.dumps(report))
    library = root / 'fixture-library.dylib'; library.write_bytes(b'library fixture')
    link = root / 'linked-library.dylib'; link.symlink_to(library.name)
    closure = dict(platform=libraries.platform_identity(), searches={}, libraries=[dict(
        logical=str(link), resolved=str(library), bytes=library.stat().st_size,
        sha256=cargo_module.file_digest(library))])
    with patch.object(cargo_module, 'library_closure', return_value=(closure, libraries.library_state(closure))):
        return [cargo_module.install_qualified_cargo(root, report_path, mode, interpreter.TOOLCHAIN)
                for mode in ['stock', 'candidate']]


class CustomCargoTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack(); self.addCleanup(stack.close)
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve(); self.addCleanup(thaw, self.root)
        self.cargos = fake_cargos(self.root)
        stack.enter_context(patch.dict(os.environ, {'PATH': '/bin', 'RUST_INTERP_LAUNCH_STATS': '1'}, clear=True))
        stack.enter_context(patch.object(interpreter, 'ROOT', self.root))
        stack.enter_context(patch.object(std_mir, 'ROOT', self.root))

    def test_load_is_immutable_and_does_not_hash_or_execute_tools(self):
        cargo = self.cargos[0]
        with patch.object(cargo_module, 'file_digest') as hash_file, \
             patch.object(subprocess, 'run') as run, patch.object(subprocess, 'check_output') as probe:
            self.assertEqual(cargo_module.load_cargo(self.root, cargo.key), cargo)
        hash_file.assert_not_called(); run.assert_not_called(); probe.assert_not_called()
        original = cargo.executable.stat()
        cargo.executable.chmod(0o755); cargo.executable.write_text('STOCK'); cargo.executable.chmod(0o555)
        os.utime(cargo.executable, ns=(original.st_atime_ns, original.st_mtime_ns))
        self.assertEqual(cargo.executable.stat().st_size, original.st_size)
        with self.assertRaisesRegex(RuntimeError, 'installation changed'):
            cargo_module.load_cargo(self.root, cargo.key)

    def test_changed_compiler_and_provenance_are_rejected(self):
        cargo = self.cargos[0]
        path = Path(cargo.identity['pinned_compiler']['sysroot']) / 'bin/rustc'
        path.write_text('different compiler')
        with self.assertRaisesRegex(RuntimeError, 'pinned compiler installation changed'):
            cargo_module.load_cargo(self.root, cargo.key)
        with self.assertRaisesRegex(RuntimeError, 'build compiler changed'):
            cargo_module.install_qualified_cargo(self.root, self.root / '.work/qualification/summary.json',
                                                'stock', interpreter.TOOLCHAIN)

    def test_changed_external_library_and_retargeted_homebrew_style_link_are_rejected(self):
        cargo = self.cargos[0]
        library = self.root / 'fixture-library.dylib'
        original = library.stat()
        library.write_bytes(b'LIBRARY fixture')
        os.utime(library, ns=(original.st_atime_ns, original.st_mtime_ns))
        with self.assertRaisesRegex(RuntimeError, 'dynamic library changed'):
            cargo_module.load_cargo(self.root, cargo.key)
        replacement = self.root / 'replacement.dylib'; replacement.write_bytes(b'library fixture')
        link = self.root / 'linked-library.dylib'; link.unlink(); link.symlink_to(replacement.name)
        with self.assertRaisesRegex(RuntimeError, 'link target changed'):
            cargo_module.load_cargo(self.root, cargo.key)

    def test_transitive_library_and_rpath_search_are_proved_without_warm_otool(self):
        directory = self.root / 'macho'; directory.mkdir()
        executable = directory / 'cargo'; executable.write_bytes(b'executable')
        direct = directory / 'direct.dylib'; direct.write_bytes(b'direct')
        nested = directory / 'nested.dylib'; nested.write_bytes(b'nested')
        missing = directory / 'missing'; missing.mkdir()
        outputs = {
            ('cargo', '-L'): f'cargo:\n\t{direct} (compatibility version 1.0.0)\n',
            ('cargo', '-l'): '',
            ('direct.dylib', '-L'): 'direct:\n\t@rpath/nested.dylib (compatibility version 1.0.0)\n',
            ('direct.dylib', '-l'): f'cmd LC_RPATH\n path {missing} (offset 12)\ncmd LC_RPATH\n path {directory} (offset 12)\n',
            ('nested.dylib', '-L'): 'nested:\n\t/usr/lib/libSystem.B.dylib (compatibility version 1.0.0)\n',
            ('nested.dylib', '-l'): '',
        }
        with patch.object(libraries.sys, 'platform', 'darwin'), \
             patch.object(libraries.subprocess, 'check_output',
                side_effect=lambda command, **kw: outputs[Path(command[-1]).name, command[-2]]) as probe:
            identity, state = libraries.library_closure(executable, HOST)
            self.assertEqual(len(identity['libraries']), 2)
            self.assertEqual(probe.call_count, 6)
            probe.reset_mock()
            self.assertEqual(libraries.library_state(identity), state)
            probe.assert_not_called()
        (missing / 'nested.dylib').write_bytes(b'shadowing library')
        with self.assertRaisesRegex(RuntimeError, 'search results changed'):
            libraries.library_state(identity)

    def test_environment_pins_public_or_selected_custom_compiler_and_rejects_conflicts(self):
        cargo = self.cargos[0]
        env = cargo.environment({'FEATURE': 'preserved'}, interpreter.TOOLCHAIN)
        rustc = str(Path(cargo.identity['pinned_compiler']['sysroot']) / 'bin/rustc')
        self.assertEqual(env['RUSTC'], rustc)
        self.assertEqual(env['CARGO'], str(cargo.executable))
        self.assertEqual(env['FEATURE'], 'preserved')
        self.assertEqual(env['RUSTUP_TOOLCHAIN'], interpreter.TOOLCHAIN + '-' + HOST)
        for values in [dict(RUSTC='/other'), dict(CARGO_BUILD_RUSTC='/other'), dict(CARGO='/other'),
                       dict(RUSTUP_TOOLCHAIN='stable'), dict(RUSTUP_HOME='/other'), dict(RUST_SYSROOT='/other')]:
            with self.subTest(values=values), self.assertRaisesRegex(RuntimeError, 'conflicts with'):
                cargo.environment(values, interpreter.TOOLCHAIN)
        custom = fake_install(self.root)
        selected = cargo.environment({}, interpreter.TOOLCHAIN, custom)
        self.assertEqual(selected['RUSTC'], str(custom.rustc))
        self.assertTrue(selected['PATH'].startswith(str(custom.sysroot / 'bin')))

    def test_launcher_keeps_one_exporter_but_isolates_cargo_caches_and_receipts(self):
        tools = self.root / 'tools'; tools.mkdir()
        binaries = {name: custom_compiler.digest(name) for name in interpreter.CURRENT_TOOL_BINARIES}
        (tools / 'ready.json').write_text(json.dumps(binaries))
        manifest = self.root / 'Cargo.toml'; manifest.write_text('fixture')
        (self.root / 'fixture.rmeta.rbc').write_bytes(b'bytecode')
        invocations = []
        def run(command, **options):
            invocations.append((command, options))
            event = dict(reason='compiler-artifact', profile=dict(test=False),
                         filenames=[str(self.root / 'fixture.rmeta')])
            return subprocess.CompletedProcess(command, 0, json.dumps(event))
        workspaces = []
        for cargo in [self.cargos[0], self.cargos[1], self.cargos[0], None]:
            invocations.clear()
            argv = ['interpreter.py', '--manifest-path', str(manifest), '--package', 'fixture',
                    '--entry', 'selected', '--tool-key', 'a' * 64]
            if cargo: argv += ['--cargo-key', cargo.key]
            output = io.StringIO()
            with patch.object(interpreter, 'installed_tools', return_value=(tools, 'a' * 64)), \
                 patch.object(interpreter.subprocess, 'run', side_effect=run), \
                 patch.object(sys, 'argv', argv), redirect_stderr(output):
                self.assertEqual(interpreter.main(), 0)
            command, options = invocations[0]
            report = json.loads(output.getvalue().split('rust-interp-launch: ')[1])
            if cargo:
                self.assertEqual(command[:2], [str(cargo.executable), 'check'])
                self.assertFalse(any(arg.startswith('+') for arg in command))
                self.assertEqual(report['custom_cargo'], cargo.receipt())
                self.assertEqual(options['env']['RUSTC'], cargo.environment({}, interpreter.TOOLCHAIN)['RUSTC'])
            else:
                self.assertEqual(command[:2], ['cargo', '+' + interpreter.TOOLCHAIN])
                self.assertNotIn('custom_cargo', report)
                self.assertNotIn('RUSTC', options['env'])
            self.assertEqual(options['env']['RUSTC_WORKSPACE_WRAPPER'], '')
            workspaces.append(options['env']['CARGO_TARGET_DIR'])
        self.assertEqual(workspaces[0], workspaces[2])
        self.assertEqual(len(set(workspaces)), 3)

    def test_std_fetch_build_and_reuse_preserve_compiler_flags_and_cargo_identity(self):
        invocations = []
        def popen(command, **options):
            invocations.append((command, options))
            target = Path(command[command.index('--target-dir') + 1])
            def wait():
                output = target / HOST / 'release/deps'; output.mkdir(parents=True)
                for crate in ['core', 'alloc', 'std', 'test', 'proc_macro']:
                    (output / ('lib' + crate + '-fixture.rmeta')).write_bytes(b'metadata')
                return 0
            return SimpleNamespace(pid=123, wait=wait)
        def fetch(command, **options):
            invocations.append((command, options))
            return subprocess.CompletedProcess(command, 0)
        results = []
        binding = self.cargos[0].identity['pinned_compiler']
        with patch('toolchain_lookup.compiler_identity', return_value=(binding['compiler'], Path(binding['sysroot']), 'fresh')), \
             patch.object(std_mir.subprocess, 'Popen', side_effect=popen), \
             patch.object(std_mir.subprocess, 'run', side_effect=fetch):
            for cargo in [self.cargos[0], self.cargos[1], self.cargos[0]]:
                results.append(std_mir.checked_std_mir(interpreter.TOOLCHAIN, fetch=True, cargo=cargo))
        self.assertEqual(len(invocations), 4)
        self.assertEqual(results[0], results[2]); self.assertNotEqual(results[0][2], results[1][2])
        for i, cargo in enumerate(self.cargos):
            for (command, options), operation in zip(invocations[i * 2:i * 2 + 2], ['fetch', 'check']):
                self.assertEqual(command[:2], [str(cargo.executable), operation])
                self.assertEqual(options['env']['RUSTFLAGS'], std_mir.FLAGS)
                self.assertEqual(options['env']['RUSTC'], str(Path(binding['sysroot']) / 'bin/rustc'))
            self.assertEqual(results[i][3]['identity']['cargo'], cargo.receipt())
            receipt = json.loads((results[i][0].parent / 'command.json').read_text())
            self.assertEqual(receipt['cargo'], cargo.receipt())


if __name__ == '__main__':
    unittest.main()
