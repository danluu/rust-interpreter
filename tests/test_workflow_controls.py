"""Native controls preserve semantic settings and keep nested timing scopes separate."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from workflow_controls import exporter_seconds, native_command, native_environment


class NativeControlTests(unittest.TestCase):
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
