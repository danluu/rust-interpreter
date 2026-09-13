"""Synthetic screen contracts; no Cargo, exporter, guest or benchmark runs."""
import collections
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'benchmarks/experiments/strict-warm-build/screen.py'
SPEC = importlib.util.spec_from_file_location('strict_warm_screen', PATH)
screen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(screen)


def case():
    return dict(tests=['tests::original'], negative=('wrong', 'v0', 'wrong'),
                edits=[('edit-' + str(n), 'v' + str(n - 1), 'v' + str(n)) for n in range(1, 6)])


ORIGINAL = b'fn production() { v0; }\n#[cfg(test)]\nmod tests { /* original assertion */ }'


class ScreenContracts(unittest.TestCase):
    def test_source_inventory_preserves_symlink_identity_without_following_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'directory'
            directory.mkdir()
            link = root / 'link'
            link.symlink_to('directory', target_is_directory=True)
            directory_link = screen.frozen_input_hash(link)
            link.unlink()
            link.symlink_to('missing')
            dangling_link = screen.frozen_input_hash(link)
            self.assertNotEqual(directory_link, dangling_link)
            link.unlink()
            link.write_bytes(b'missing')
            self.assertNotEqual(dangling_link, screen.frozen_input_hash(link))
            with self.assertRaisesRegex(RuntimeError, 'not a file or symlink'):
                screen.frozen_input_hash(directory)

    def test_fresh_edits_and_compiled_controls_have_balanced_arm_positions(self):
        states = screen.protocol_states(ORIGINAL, case())
        self.assertEqual([s['phase'] for s in states],
            ['cold', 'wrong-edit', 'recovery', *['edit'] * 5, 'restoration'])
        self.assertEqual(len({s['source'] for s in states if s['phase'] == 'edit'}), 5)
        self.assertEqual([states[n]['source'] for n in [0, 2, 8]], [ORIGINAL] * 3)
        for mode in screen.MODES:
            self.assertEqual(collections.Counter(s['modes'].index(mode) for s in states),
                             {0: 3, 1: 3, 2: 3})
        self.assertTrue(all(s['source'].split(b'\n#[cfg(test)]')[1]
                            == ORIGINAL.split(b'\n#[cfg(test)]')[1] for s in states))

    def test_a_return_to_previously_compiled_source_cannot_be_an_edit(self):
        data = case()
        data['edits'][-1] = ('return-original', 'v4', 'v0')
        with self.assertRaisesRegex(RuntimeError, 'already compiled'):
            screen.protocol_states(ORIGINAL, data)

    def test_real_commands_keep_the_profile_and_all_original_tests(self):
        for mode in screen.MODES:
            command = screen.command_for(mode, 'a' * 64, Path('/owned/source'), Path('/owned/run'), {'index': 3})
            value = lambda option: command[command.index(option) + 1]
            self.assertEqual(value('--jobs'), '4')
            self.assertEqual(value('--suite-workers'), '2')
            self.assertEqual(value('--query-cache-retention'), 'demand' if mode == 'candidate' else 'off')
            self.assertEqual(value('--function-cache'), 'auto')
            self.assertEqual(value('--toolchain-lookup'), 'cached')
            self.assertEqual(value('--instruction-limit'), '100000000000')
            self.assertEqual(value('--allocation-limit'), '150000')
            self.assertEqual([command[i + 1] for i, arg in enumerate(command) if arg == '--entry'], screen.CASE['tests'])
            self.assertEqual(len(screen.CASE['tests']), 14)
            self.assertNotIn('--test-filter', command)
            self.assertFalse(any('mir-opt-level' in arg or 'inline-scale' in arg for arg in command))
        with self.assertRaisesRegex(RuntimeError, 'unknown screen arm'):
            screen.command_for('unknown', 'a' * 64, Path('/source'), Path('/run'), {'index': 3})

    def test_ambient_compiler_profile_overrides_cannot_change_one_arm(self):
        with patch.dict(os.environ, dict(PATH='/bin', CARGO_HOME='/cargo', RUSTFLAGS='-Zmir-opt-level=3',
                CARGO_PROFILE_TEST_OPT_LEVEL='3', RUSTC_WRAPPER='/wrong',
                RUST_INTERP_DEMAND_BODIES='1', RUST_TEST_THREADS='8'), clear=True):
            env = screen.environment()
        self.assertEqual(env, dict(PATH='/bin', CARGO_HOME='/cargo', CARGO_TERM_COLOR='never',
                                  RUST_INTERP_LAUNCH_STATS='1'))
        with patch.dict(os.environ, {'DYLD_INSERT_LIBRARIES': '/unknown'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'dynamic-loader'):
                screen.environment()

    def test_whole_command_clock_encloses_capture_without_stage_subtraction(self):
        events = []
        def clock():
            events.append('clock')
            return 10.0 if len(events) == 1 else 12.5
        def capture(*args, **kwargs):
            events.append('capture')
            return 'child', 'stdout', 'stderr'
        with patch.object(screen, 'child_usage', return_value=(1, 2)), \
             patch.object(screen, 'child_cpu_since', return_value=dict(user_seconds=3, system_seconds=1, total_seconds=4)), \
             patch.object(screen.time, 'perf_counter', side_effect=clock), \
             patch.object(screen, 'capture', side_effect=capture):
            result = screen.measure_command(['launcher'])
        self.assertEqual(events, ['clock', 'capture', 'clock'])
        self.assertEqual(result, ('child', 'stdout', 'stderr', 2.5,
                                 dict(user_seconds=3, system_seconds=1, total_seconds=4)))

    def test_receipt_capture_failure_never_becomes_a_successful_timing(self):
        with patch.object(screen, 'capture', side_effect=OSError('receipt failed')):
            with self.assertRaisesRegex(OSError, 'receipt failed'):
                screen.measure_command(['launcher'])

    def test_nonfinite_timing_and_incomplete_controls_are_rejected(self):
        with patch.object(screen, 'capture', return_value=('child', '', '')), \
             patch.object(screen.time, 'perf_counter', side_effect=[1.0, float('nan')]):
            with self.assertRaisesRegex(RuntimeError, 'wall time'):
                screen.measure_command(['launcher'])
        with self.assertRaisesRegex(RuntimeError, 'incomplete'):
            screen.assessment([])
        with self.assertRaisesRegex(RuntimeError, 'incomplete'):
            screen.assessment([dict(validated=False)] * 27)

    def test_missing_launcher_completion_and_wrong_mode_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'completed launcher report'):
            screen.checked_launch('compiler error', 'candidate', 'a' * 64, False,
                                  Path('/absent/suite'), Path('/absent/cache'))
        with self.assertRaisesRegex(RuntimeError, 'settings differ'):
            screen.checked_launch('rust-interp-launch: {"query_cache_retention":"off"}',
                                  'candidate', 'a' * 64, True, Path('/absent/suite'), Path('/absent/cache'))


if __name__ == '__main__':
    unittest.main()
