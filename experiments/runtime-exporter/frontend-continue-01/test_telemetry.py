"""Saved actual-output controls; no compiler or live stage is constructed."""
from pathlib import Path
import unittest
import telemetry as t

WORK = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/runtime-exporter-frontend-01')


def saved(number):
    return (WORK / 'commands' / f'{number:03d}' / 'stderr').read_bytes()


class TelemetryControls(unittest.TestCase):
    def test_basic_actual_output_is_lossless_with_empty_native_diagnostics(self):
        native = t.split_stderr(saved(16), allow_telemetry=False)
        exported = t.split_stderr(saved(17), allow_telemetry=True)
        t.compare_compiler_stderr(native, exported)
        self.assertEqual([row['kind'] for row in exported['segments']],
                         ['aggregate-frames', 'scalar-frames', 'scalar-promotion', 'cfg', 'export'])
        self.assertEqual(b''.join(bytes.fromhex(row['raw_hex']) for row in exported['segments']), saved(17))

    def test_interleaved_actual_warning_bytes_and_positions_are_preserved(self):
        native = t.split_stderr(saved(21), allow_telemetry=False)
        exported = t.split_stderr(saved(22), allow_telemetry=True)
        t.compare_compiler_stderr(native, exported)
        self.assertEqual(exported['segments'][0]['channel'], 'compiler')
        self.assertEqual(exported['segments'][-1]['channel'], 'compiler')
        self.assertTrue(any(row.get('kind') == 'forwarding' for row in exported['segments']))
        for row in exported['segments']:
            self.assertEqual(saved(22)[row['start']:row['end']], bytes.fromhex(row['raw_hex']))

    def test_actual_uncalled_error_bytes_are_identical_without_telemetry(self):
        t.compare_compiler_stderr(t.split_stderr(saved(24), allow_telemetry=False),
                                 t.split_stderr(saved(25), allow_telemetry=False))

    def test_changed_warning_bytes_are_not_normalized_away(self):
        native = t.split_stderr(saved(21), allow_telemetry=False)
        changed = saved(22).replace(b'variable does not need to be mutable', b'changed compiler warning')
        with self.assertRaisesRegex(RuntimeError, 'diagnostic bytes differ'):
            t.compare_compiler_stderr(native, t.split_stderr(changed, allow_telemetry=True))

    def test_unknown_prefixed_line_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'unknown exporter stderr line'):
            t.split_stderr(saved(17) + b'rust-interp-unreviewed: warning hidden\n', allow_telemetry=True)

    def test_malformed_known_telemetry_is_rejected(self):
        for raw in (b'rust-interp-cfg: before=6 after=6 seconds=NaN\n',
                    b'rust-interp-cfg: before=6 after=6 seconds=0.000001 warning=hidden\n'):
            with self.subTest(raw=raw), self.assertRaisesRegex(RuntimeError, 'known telemetry grammar'):
                t.split_stderr(raw, allow_telemetry=True)

    def test_aggregate_duplicate_or_boolean_counter_is_rejected(self):
        first = saved(17).splitlines(keepends=True)[0]
        for raw in (first.replace(b'"functions":0', b'"functions":0,"functions":0'),
                    first.replace(b'"functions":0', b'"functions":true')):
            with self.subTest(raw=raw), self.assertRaises(RuntimeError):
                t.split_stderr(raw, allow_telemetry=True)

    def test_unstructured_native_output_and_unknown_json_are_rejected(self):
        for raw, allow in ((saved(17), False), (b'{"$message_type":"artifact","level":"warning"}\n', True),
                           (b'{"$message_type":"diagnostic","level":"warning"}', True)):
            with self.subTest(raw=raw), self.assertRaises(RuntimeError):
                t.split_stderr(raw, allow_telemetry=allow)


if __name__ == '__main__':
    unittest.main()
