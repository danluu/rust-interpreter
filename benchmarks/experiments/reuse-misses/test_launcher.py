import contextlib
import io
import sys
import unittest
from unittest.mock import patch
import launcher

COMMAND = ['cargo', '+nightly-2026-09-08', 'check', '--message-format=json-render-diagnostics']
ENV = {'RUSTC_WRAPPER': '/owned/rust-interp-rustc-wrapper', 'KEEP': 'value'}


class LauncherTests(unittest.TestCase):
    def test_exporter_only_verify_mode_rejects_before_cargo(self):
        argv = ['launcher.py', '--reuse-misses', '1', '--package', 'fixture', '--function-cache', 'verify']
        err = io.StringIO()
        with patch.object(sys, 'argv', argv), patch.object(launcher.interpreter.subprocess, 'run') as run, \
                contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as raised:
                launcher.main()
            self.assertEqual(raised.exception.code, 2)
            self.assertIs(sys.argv, argv)
            run.assert_not_called()
        self.assertIn("argument --function-cache: invalid choice: 'verify'", err.getvalue())

    def test_explicit_values_go_only_to_owned_cargo_check(self):
        for value in [None, '0', '1', '', '2']:
            original = dict(ENV)
            got = launcher.child_environment(COMMAND, original, value)
            self.assertEqual(original, ENV)
            self.assertEqual(got.get('RUST_INTERP_REUSE_MISSES'), value)
            self.assertEqual(got['KEEP'], 'value')
        for command in [['cargo', '+nightly', 'build'], ['rustup', 'which', 'rustc'], ['rust-interp-vm']]:
            self.assertIs(launcher.child_environment(command, ENV, '1', '1'), ENV)

    def test_missing_wrapper_or_existing_observer_values_reject(self):
        for env in [{}, dict(ENV, RUST_INTERP_REUSE_MISSES='0')]:
            with self.assertRaises(AssertionError):launcher.child_environment(COMMAND, env, '1')
        with self.assertRaises(AssertionError):
            launcher.child_environment(COMMAND, dict(ENV, RUST_INTERP_REPLAY_COSTS='0'), '1', '1')

    def test_incompatible_observer_value_is_forwarded_for_rust_rejection(self):
        env = launcher.child_environment(COMMAND, ENV, '1', '1')
        self.assertEqual(env['RUST_INTERP_REUSE_MISSES'], '1')
        self.assertEqual(env['RUST_INTERP_REPLAY_COSTS'], '1')

    def test_cli_adapter_parses_both_flags_and_restores_run_and_argv(self):
        calls = []
        def original(command, **kwargs):
            calls.append((command, kwargs['env']));return 17
        def interpret():
            return launcher.interpreter.subprocess.run(COMMAND, env=ENV)
        argv = ['launcher.py', '--reuse-misses', '1', '--also-replay-costs', '1']
        with patch.object(sys, 'argv', argv), patch.object(launcher.interpreter.subprocess, 'run', original), \
                patch.object(launcher.interpreter, 'main', interpret):
            self.assertEqual(launcher.main(), 17)
            self.assertIs(sys.argv, argv)
            self.assertIs(launcher.interpreter.subprocess.run, original)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1]['RUST_INTERP_REUSE_MISSES'], '1')
        self.assertEqual(calls[0][1]['RUST_INTERP_REPLAY_COSTS'], '1')


if __name__ == '__main__':unittest.main()
