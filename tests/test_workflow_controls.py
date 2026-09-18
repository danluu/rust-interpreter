"""Native controls preserve semantic settings and keep nested timing scopes separate."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from workflow_controls import (exporter_seconds, native_command, native_environment, native_toolchain,
                               inspect_native_toolchain, revalidate_native_toolchain, native_identity_environment)


def installed_fixture(root):
    for name in ['rustc', 'cargo', 'rustup']:
        (root / name).write_bytes(name.encode())
        (root / name).chmod(0o700)
    commands = []
    def run(command):
        commands.append(command)
        if command[1] == 'which':
            output = str(root / command[-1]) + '\n'
        else:
            output = Path(command[0]).name + ' 1.98.1 (actual-commit)\nhost: aarch64-apple-darwin\n'
        return dict(returncode=0, stdout=output, stderr='')
    environment = dict(HOME=str(root), CARGO_HOME=str(root / 'cargo-home'), PATH=str(root))
    return run, commands, environment


class NativeControlTests(unittest.TestCase):
    def test_identity_probes_preserve_version_and_loader_overrides(self):
        base = dict(HOME='/home', PATH='/bin', RUSTC_OVERRIDE_VERSION_STRING='explicit version',
            RUSTC_OVERRIDE_COMMIT_HASH='explicit commit', LD_PRELOAD='/declared/library',
            DYLD_INSERT_LIBRARIES='/declared/darwin-library', DYLD_FRAMEWORK_PATH='/frameworks',
            RUSTC_BOOTSTRAP='1', UNRELATED_CREDENTIAL='not an identity input')
        expected = {key: value for key, value in base.items() if key != 'UNRELATED_CREDENTIAL'}
        self.assertEqual(native_identity_environment(base), expected)

    def test_explicit_native_toolchain_applies_to_test_and_check(self):
        args = ('1.98.1', 'Cargo.toml', 'oxc_linter', 'target', 2, 'default', ['one'])
        for check in [False, True]:
            command = native_command(*args, check=check)
            self.assertEqual(command[:2], ['cargo', '+1.98.1'])
            self.assertNotIn('--test-threads=1', command)
            explicit = native_command(*args, check=check, cargo='/owned/toolchain/bin/cargo')
            self.assertEqual(explicit[:2], ['/owned/toolchain/bin/cargo', 'check' if check else 'test'])
        for value in ['', '+nightly', '/tmp/rustc', '1.98.1 --offline', '../nightly', None]:
            with self.assertRaises(ValueError):
                native_toolchain(value)

    def test_native_identity_uses_installed_tools_and_keeps_actual_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, commands, environment = installed_fixture(root)
            identity = inspect_native_toolchain('1.98.1', run, environment=environment, source=root)
            self.assertEqual(identity['toolchain'], '1.98.1')
            self.assertEqual(set(identity['tools']), {'rustc', 'cargo'})
            self.assertEqual(len(commands), 4)
            self.assertTrue(all('actual-commit' in tool['version_stdout'] for tool in identity['tools'].values()))
            self.assertTrue(all(len(tool['sha256']) == 64 for tool in identity['tools'].values()))
            commands.clear()
            def unavailable(command):
                commands.append(command)
                return dict(returncode=1, stdout='', stderr='not installed')
            with self.assertRaisesRegex(RuntimeError, 'not installed'):
                inspect_native_toolchain('1.98.1', unavailable, environment=environment, source=root)
            self.assertEqual(commands, [[str(root / 'rustup'), 'which', '--toolchain', '1.98.1', 'rustc']])

    def test_inherited_and_configured_compiler_routes_are_not_silently_overridden(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, commands, environment = installed_fixture(root)
            for name in ['RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_BUILD_RUSTC_WRAPPER']:
                with self.assertRaisesRegex(RuntimeError, 'conflicts with inherited ' + name):
                    inspect_native_toolchain('1.98.1', run, environment=dict(environment, **{name: '/different/compiler'}), source=root)
                self.assertEqual(commands, [])
            config = root / '.cargo/config.toml'
            config.parent.mkdir()
            payload = '[build]\nrustc-wrapper = "meaningful-upstream-wrapper"\n'
            config.write_text(payload)
            with self.assertRaisesRegex(RuntimeError, 'Cargo configuration'):
                inspect_native_toolchain('1.98.1', run, environment=environment, source=root)
            self.assertEqual(commands, [])
            self.assertEqual(config.read_text(), payload)

    def test_explicit_binding_and_post_workflow_binary_revalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, commands, environment = installed_fixture(root)
            identity = inspect_native_toolchain('1.98.1', run, environment=environment, source=root)
            child = native_environment(environment, 'repository', [], compiler=identity)
            self.assertEqual(child['RUSTC'], str((root / 'rustc').resolve()))
            self.assertEqual((child['RUSTC_WRAPPER'], child['RUSTC_WORKSPACE_WRAPPER']), ('', ''))
            self.assertNotIn('RUSTC', environment)
            self.assertEqual(revalidate_native_toolchain(identity, run, environment=environment, source=root), identity)
            (root / 'rustc').write_bytes(b'replaced compiler')
            with self.assertRaisesRegex(RuntimeError, 'changed during workflow'):
                revalidate_native_toolchain(identity, run, environment=environment, source=root)

    def test_profile_changes_do_not_modify_parent_or_panic_policy(self):
        base = {'CARGO_PROFILE_TEST_PANIC': 'unwind', 'RUSTFLAGS': '-Cdebuginfo=1'}
        self.assertEqual(native_environment(base, 'repository', []), base)
        env = native_environment(base, 'o0-incremental', ['-Clinker=/path with spaces/clang'])
        self.assertEqual(env['CARGO_PROFILE_TEST_PANIC'], 'unwind')
        self.assertEqual(env['CARGO_PROFILE_TEST_OPT_LEVEL'], '0')
        self.assertEqual(env['CARGO_PROFILE_DEV_INCREMENTAL'], 'true')
        self.assertEqual(env['CARGO_ENCODED_RUSTFLAGS'], '-Clinker=/path with spaces/clang')
        self.assertNotIn('RUSTFLAGS', env)
        self.assertEqual(base, {'CARGO_PROFILE_TEST_PANIC': 'unwind', 'RUSTFLAGS': '-Cdebuginfo=1'})

    def test_check_selects_library_test_target_without_executing_a_filter(self):
        args = ('nightly', 'Cargo.toml', 'crate', 'target', 18, 'default', ['one', 'two'])
        check = native_command(*args, check=True)
        self.assertIn('check', check)
        self.assertEqual(check[-2:], ['--profile', 'test'])
        self.assertNotIn('--', check)
        self.assertNotIn('one', check)
        run = native_command(*args)
        self.assertEqual(run[-4:], ['--', '--exact', 'one', 'two'])
        run = native_command(*args[:5], '1', args[-1])
        self.assertIn('--test-threads=1', run)

    def test_nested_export_timings_are_not_added_to_lowering_or_fabricated(self):
        stderr = '''rust-interp-scalar-frames: functions=2 seconds=0.04
rust-interp-inline: sites=3 operations=100 seconds=0.02
rust-interp-export: frontend_ms=500.0 lowering_ms=120.0 functions=2
unrelated seconds=99.0
'''
        times = exporter_seconds(stderr)
        self.assertEqual(times, {'scalar-frames': .04, 'inline': .02, 'frontend': .5, 'lowering': .12})
        self.assertEqual(exporter_seconds('nothing measured'), {})


if __name__ == '__main__':
    unittest.main()
