"""Launcher correctness for optional query retention; no compiler runs."""
import os
from unittest.mock import patch
import unittest

import test_borrowck_cache_launcher as helpers


class DemandRetentionLauncherTests(unittest.TestCase):
    capabilities = helpers.BorrowckCacheLauncherTests.capabilities
    run_process = helpers.BorrowckCacheLauncherTests.run_process
    launch = helpers.BorrowckCacheLauncherTests.launch

    def setUp(self):
        helpers.BorrowckCacheLauncherTests.setUp(self)
        self.capabilities(['query-cache-retention', 'borrowck-cache', 'function-cache-reuse'])

    def test_mode_reaches_only_compiler_and_is_reported(self):
        result, stats = self.launch('--query-cache-retention', 'demand')
        self.assertEqual(result, 0)
        cargo, vm = self.invocations
        self.assertEqual(cargo[1]['env']['RUST_INTERP_QUERY_CACHE_RETENTION'], 'demand')
        self.assertNotIn('RUST_INTERP_QUERY_CACHE_RETENTION', vm[1]['env'])
        self.assertEqual(stats[0]['query_cache_retention'], 'demand')

    def test_default_and_explicit_off_discard_ambient_mode(self):
        for arguments in [(), ('--query-cache-retention', 'off')]:
            with self.subTest(arguments=arguments):
                self.invocations.clear()
                with patch.dict(os.environ, {'RUST_INTERP_QUERY_CACHE_RETENTION': 'demand'}):
                    result, stats = self.launch(*arguments)
                self.assertEqual(result, 0)
                self.assertEqual(stats[0]['query_cache_retention'], 'off')
                self.assertTrue(all('RUST_INTERP_QUERY_CACHE_RETENTION' not in args['env']
                                    for _, args in self.invocations))

    def test_mode_and_user_namespaces_cannot_alias_cargo_freshness(self):
        paths = []
        for arguments in [(), ('--query-cache-retention', 'off'),
                          ('--query-cache-retention', 'demand'),
                          ('--query-cache-retention', 'demand'),
                          ('--cache-namespace', 'query-cache-retention-v1\0demand'),
                          ('--query-cache-retention', 'demand', '--borrowck-cache', 'reuse')]:
            self.invocations.clear()
            self.assertEqual(self.launch(*arguments)[0], 0)
            paths.append(self.invocations[0][1]['env']['CARGO_TARGET_DIR'])
        self.assertEqual(paths[0], paths[1])
        self.assertEqual(paths[2], paths[3])
        self.assertEqual(len(set(paths)), 4)

    def test_other_reuse_modes_can_be_enabled_together(self):
        self.assertEqual(self.launch('--query-cache-retention', 'demand',
            '--borrowck-cache', 'verify', '--function-cache', 'reuse')[0], 0)
        cargo, vm = self.invocations
        self.assertEqual(cargo[1]['env']['RUST_INTERP_QUERY_CACHE_RETENTION'], 'demand')
        self.assertEqual(cargo[1]['env']['RUST_INTERP_BORROWCK_CACHE'], 'verify')
        self.assertEqual(cargo[1]['env']['RUST_INTERP_FUNCTION_CACHE'], 'reuse')
        self.assertNotIn('RUST_INTERP_QUERY_CACHE_RETENTION', vm[1]['env'])

    def test_failed_compilation_cannot_execute_cached_program(self):
        self.cargo_returncode = 101
        result, stats = self.launch('--query-cache-retention', 'demand')
        self.assertEqual(result, 101)
        self.assertEqual(stats, [])
        self.assertEqual(len(self.invocations), 1)

    def test_old_tools_decline_before_starting_processes(self):
        self.capabilities(['borrowck-cache'])
        with self.assertRaisesRegex(RuntimeError, 'does not support --query-cache-retention'):
            self.launch('--query-cache-retention', 'demand')
        self.assertEqual(self.invocations, [])
        self.assertEqual(self.launch('--query-cache-retention', 'off')[0], 0)

    def test_invalid_cli_mode_fails_before_loading_tools(self):
        with self.assertRaises(SystemExit) as error:
            self.launch('--query-cache-retention', 'unchecked')
        self.assertEqual(error.exception.code, 2)
        self.installed.assert_not_called()


if __name__ == '__main__':
    unittest.main()
