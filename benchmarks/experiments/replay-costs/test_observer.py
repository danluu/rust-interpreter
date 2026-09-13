import copy
import json
import unittest

from launcher import child_environment
from observe import observation, require_cargo_export


class ObserverTests(unittest.TestCase):
    def test_cargo_build_script_fixture_uses_compiling_or_checking(self):
        for prefix in ['   Compiling', '    Checking']:
            require_cargo_export(prefix + ' host-mir-app v0.1.0 (/fixture/app)', 'host-mir-app')
        for text in ['       Fresh host-mir-app v0.1.0', '    Checking host-mir-app-helper v0.1.0',
                     'rust-interp-export: frontend_ms=1']:
            with self.assertRaises(AssertionError):
                require_cargo_export(text, 'host-mir-app')

    def test_option_is_confined_to_owned_cargo_check_without_mutating_input(self):
        env = dict(RUSTC_WRAPPER='/tools/rust-interp-rustc-wrapper', KEEP='value')
        command = ['cargo', '+nightly', 'check', '--message-format=json-render-diagnostics']
        result = child_environment(command, env, '1')
        self.assertNotIn('RUST_INTERP_REPLAY_COSTS', env)
        self.assertEqual(result['RUST_INTERP_REPLAY_COSTS'], '1')
        for other in [['cargo', '+nightly', 'test'], ['vm'], command[:-1]]:
            self.assertIs(child_environment(other, env, '1'), env)
        self.assertEqual(child_environment(command, env, None), env)
        with self.assertRaises(AssertionError):
            child_environment(command, dict(env, RUSTC_WRAPPER='/unexpected'), '1')

    def test_invalid_values_reach_exporter_validation(self):
        command = ['cargo', '+nightly', 'check', '--message-format=json-render-diagnostics']
        env = dict(RUSTC_WRAPPER='/tools/rust-interp-rustc-wrapper')
        for value in ['0', '1', '', '2']:
            self.assertEqual(child_environment(command, env, value)['RUST_INTERP_REPLAY_COSTS'], value)

    def test_counts_and_residual_reconcile_and_mismatches_fail(self):
        row = dict(schema_version=1, performance_measurement=False,
            totals=dict(functions=2, instructions=10, immediate_sites=3, events=4,
                        call_sites=1, setup_seconds=.01, events_seconds=.02, patch_seconds=.01),
            binding_seconds=.05, phase_seconds=.04, unassigned_seconds=.01)
        cache = dict(mode='reuse', skipped_functions=2, previous_binding_seconds=.05)
        def stderr(value):
            return 'rust-interp-replay-costs: ' + json.dumps(value) + '\nrust-interp-function-cache: ' + json.dumps(cache)
        self.assertEqual(observation(stderr(row), True), row)
        for field, value in [('unassigned_seconds', -.01), ('phase_seconds', .08), ('binding_seconds', float('nan'))]:
            changed = dict(row, **{field: value})
            with self.assertRaises(AssertionError):
                observation(stderr(changed), True)
        changed = copy.deepcopy(row); changed['totals']['functions'] = 1
        with self.assertRaises(AssertionError):
            observation(stderr(changed), True)
        with self.assertRaises(AssertionError):
            observation(stderr(row), False)

    def test_cold_observation_is_empty_and_disabled_emits_nothing(self):
        self.assertIsNone(observation('', False))
        totals = dict(functions=0, instructions=0, immediate_sites=0, events=0,
                      call_sites=0, setup_seconds=0., events_seconds=0., patch_seconds=0.)
        row = dict(schema_version=1, performance_measurement=False, totals=totals,
                   binding_seconds=0., phase_seconds=0., unassigned_seconds=0.)
        cache = dict(mode='reuse', skipped_functions=0, previous_binding_seconds=0.)
        text = 'rust-interp-replay-costs: ' + json.dumps(row) + '\nrust-interp-function-cache: ' + json.dumps(cache)
        self.assertEqual(observation(text, True), row)


if __name__ == '__main__':
    unittest.main()
