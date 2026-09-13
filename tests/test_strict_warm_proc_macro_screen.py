"""Proc-macro-only screen contracts; no compiler or benchmark execution."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from test_strict_warm_screen import screen, case, ORIGINAL


class ProcMacroScreenContracts(unittest.TestCase):
    def test_one_public_toolset_shared_std_and_no_other_compiler_policy(self):
        key = 'a' * 64
        screen.validate_comparison('host-proc-macro-opt', key, key, None, None)
        for args in [(key, 'b' * 64, None, None, None, None),
                     (key, key, 'c' * 64, None, None, None),
                     (key, key, None, Path('/candidate/std/ready.json'), None, None),
                     (key, key, None, None, 'd' * 64, 'e' * 64)]:
            with self.subTest(args=args), self.assertRaises(RuntimeError):
                screen.validate_comparison('host-proc-macro-opt', *args)
        with patch.object(screen, 'require_export_option') as check:
            screen.require_candidate_policy(Path('/tools'), key, 'host-proc-macro-opt')
            check.assert_called_once_with(Path('/tools'), key, 'host-proc-macro-opt-v1')

    def test_all_27_commands_preserve_all_14_tests_and_only_add_off_on_off_policy(self):
        count = 0
        for sample in screen.protocol_states(ORIGINAL, case()):
            for mode in sample['modes']:
                args = (mode, 'a' * 64, Path('/source'), Path('/work'), sample)
                original = screen.command_for(*args, candidate_policy='native-host-mir')
                actual = screen.command_for(*args, candidate_policy='host-proc-macro-opt')
                index = actual.index('--host-proc-macro-opt')
                self.assertEqual(actual[index:index + 2], ['--host-proc-macro-opt',
                    'on' if mode == 'candidate' else 'off'])
                self.assertEqual(actual[:index] + actual[index + 2:], original)
                self.assertEqual([actual[i + 1] for i, v in enumerate(actual) if v == '--entry'], screen.CASE['tests'])
                self.assertEqual(len(screen.CASE['tests']), 14)
                for flag in ['--compiler-key', '--cargo-key', '--stable-cgu-partitioning', '--query-cache-retention', '--borrowck-cache']:
                    self.assertNotIn(flag, actual)
                count += 1
        self.assertEqual(count, 27)
        for extra in [dict(compiler_key='c' * 64), dict(cargo_key='d' * 64)]:
            with self.assertRaises(RuntimeError):
                screen.command_for(*args, candidate_policy='host-proc-macro-opt', **extra)

    def test_launcher_receipt_rejects_missing_wrong_or_combined_policy(self):
        key = 'a' * 64
        std = dict(key='b' * 64, sysroot='/shared/std', target='aarch64-apple-darwin')
        expected = screen.launch_settings('candidate', key, 'host-proc-macro-opt')
        self.assertEqual(expected['host_proc_macro_opt'], 'on')
        self.assertEqual(screen.launch_settings('duplicate', key, 'host-proc-macro-opt')['host_proc_macro_opt'], 'off')
        expected.update(toolchain_lookup=dict(mode='cached', outcome='hit'), std_mir=std)
        missing = dict(expected); missing.pop('host_proc_macro_opt')
        for value, error in [(missing, 'settings differ'),
            ({**expected, 'host_proc_macro_opt': 'off'}, 'settings differ'),
            ({**expected, 'borrowck_cache': 'reuse'}, 'settings differ'),
            ({**expected, 'custom_compiler': {}}, 'unexpected custom compiler'),
            ({**expected, 'custom_cargo': {}}, 'unexpected custom Cargo'),
            ({**expected, 'query_cache_retention': 'demand'}, 'unexpected retention'),
            ({**expected, 'std_mir': {**std, 'key': 'c' * 64}}, 'different standard-library')]:
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, error):
                screen.checked_launch('rust-interp-launch: ' + json.dumps(value), 'candidate', key,
                    True, Path('/suite'), Path('/cache'), candidate_policy='host-proc-macro-opt', prepared_std=std)
        with self.assertRaisesRegex(RuntimeError, 'prepared std identity'):
            screen.checked_launch('rust-interp-launch: ' + json.dumps(expected), 'candidate', key,
                True, Path('/suite'), Path('/cache'), candidate_policy='host-proc-macro-opt')

    def test_other_policies_cannot_silently_enable_macro_optimization(self):
        for policy in ['demand-retention', 'native-host-mir']:
            expected = screen.launch_settings('candidate', 'a' * 64, policy)
            expected['host_proc_macro_opt'] = 'on'
            with self.subTest(policy=policy), self.assertRaisesRegex(RuntimeError, 'unexpected proc-macro'):
                screen.checked_launch('rust-interp-launch: ' + json.dumps(expected), 'candidate', 'a' * 64,
                    True, Path('/suite'), Path('/cache'), candidate_policy=policy)


if __name__ == '__main__':
    unittest.main()
