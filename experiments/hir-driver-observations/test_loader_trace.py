"""Pure malformed trace and receipt controls; no processes are launched."""
import copy
import hashlib
import unittest

import loader_trace
from test_observations import encode, records


PRIVATE = {'/owned/driver', '/owned/lib/librustc_driver.dylib', '/owned/lib/libLLVM.dylib'}


def trace():
    lines = ['dyld[42]: <12345678-ABCD-1234-5678-123456789abc> /owned/driver',
             'dyld[42]: /owned/lib/librustc_driver.dylib',
             'dyld[42]: /owned/lib/libLLVM.dylib',
             'dyld[42]: /usr/lib/libSystem.B.dylib',
             'dyld[42]: move loaded to delayed: libSystem.B.dylib']
    return ('\n'.join(lines) + '\n').encode()


def fixture(mode='serial'):
    stdout, stderr = encode(records(mode)), trace()
    command = ['/owned/driver', '/owned/stage1', '/owned/fixture.rs', '/owned/' + mode, mode]
    env = {'DYLD_PRINT_LIBRARIES': '1'}
    events = [dict(kind='started', elapsed=0.05, timeout=120.0, grace=5.0, reap=5.0, interval=5.0),
              dict(kind='terminal', elapsed=0.1, status='exited', returncode=0, reason=None)]
    receipt = dict(command=command, cwd='/owned', environment=env, status='passed', errors=[],
                   child_may_be_live=False, probe_may_be_live=False, pid=42, mode=mode,
                   wait=dict(status='exited', returncode=0, child_may_be_live=False,
                             events=copy.deepcopy(events), reason=None, errors=[]), events=events,
                   stdout_sha256=hashlib.sha256(stdout).hexdigest(),
                   stderr_sha256=hashlib.sha256(stderr).hexdigest())
    kwargs = dict(command=command, cwd='/owned', environment=env, allowed_private=PRIVATE)
    return receipt, stdout, stderr, kwargs


class LoaderTrace(unittest.TestCase):
    def parse(self, raw):
        return loader_trace.parse(raw, pid=42, allowed_private=PRIVATE)

    def test_both_image_forms_and_system_delayed_note(self):
        result = self.parse(trace())
        self.assertEqual(result['loaded_non_system'], sorted(PRIVATE))
        self.assertEqual(len(result['events']), 5)

    def test_pid_foreign_provider_missing_provider_and_diagnostics(self):
        raw = trace()
        for bad in [raw.replace(b'[42]', b'[43]', 1), raw + b'dyld[42]: /foreign/image\n',
                    raw.replace(b'dyld[42]: /owned/lib/libLLVM.dylib\n', b''),
                    raw + b'error: type mismatch\n', raw + b'\n']:
            with self.subTest(bad=bad[-80:]), self.assertRaises(ValueError):
                self.parse(bad)

    def test_delayed_notes_require_unique_previous_system_basename(self):
        for bad in [b'dyld[42]: move loaded to delayed: unknown.dylib\n' + trace(),
                    trace() + b'dyld[42]: move loaded to delayed: libLLVM.dylib\n',
                    trace().replace(b'dyld[42]: move loaded',
                                    b'dyld[42]: /System/Library/libSystem.B.dylib\ndyld[42]: move loaded')]:
            with self.assertRaises(ValueError):
                self.parse(bad)

    def test_uuid_and_path_grammar_fail_closed(self):
        raw = trace()
        for path in [b'//owned/driver', b'/owned/./driver', b'/owned/x/../driver',
                     b'/owned//driver', b'/owned/driver\x00', b'/owned/driver\r']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.parse(raw.replace(b'/owned/driver', path))
        for uuid in [b'-' * 36, b'1234', b'12345678-ABCD-1234-5678-123456789abg']:
            with self.assertRaises(ValueError):
                self.parse(raw.replace(b'12345678-ABCD-1234-5678-123456789abc', uuid))

    def test_input_bounds_and_explicit_allowlist(self):
        for raw in [b'', trace()[:-1], b' ' * (loader_trace.MAX_BYTES + 1), trace().decode()]:
            with self.assertRaises(ValueError):
                self.parse(raw)
        for pid in [True, 0, -1, '42']:
            with self.assertRaises(ValueError):
                loader_trace.parse(trace(), pid=pid, allowed_private=PRIVATE)
        for allowed in [set(), list(PRIVATE), PRIVATE | {'/usr/lib/libSystem.B.dylib'}]:
            with self.assertRaises(ValueError):
                loader_trace.parse(trace(), pid=42, allowed_private=allowed)

    def test_receipt_joins_successful_both_mode_stdout_and_loader(self):
        for mode in ['serial', 'parallel']:
            receipt, stdout, stderr, kwargs = fixture(mode)
            result = loader_trace.process(receipt, stdout, stderr, **kwargs)
            self.assertEqual(result['mode'], mode)
            self.assertEqual(result['observations']['contexts'], 8)

    def test_failed_unresolved_or_mismatched_actual_receipt(self):
        for key, value in [('status', 'failed'), ('child_may_be_live', True),
                           ('probe_may_be_live', True), ('errors', ['failure']), ('pid', 43),
                           ('cwd', '/foreign'), ('mode', 'parallel'), ('stdout_sha256', '0' * 64)]:
            receipt, stdout, stderr, kwargs = fixture(); receipt[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                loader_trace.process(receipt, stdout, stderr, **kwargs)

    def test_terminal_and_wait_history_cannot_hide_timeout_or_errors(self):
        for key, value in [('status', 'stopped'), ('returncode', 1), ('returncode', False),
                           ('child_may_be_live', True), ('reason', 'timeout'), ('errors', ['failure'])]:
            receipt, stdout, stderr, kwargs = fixture(); receipt['wait'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                loader_trace.process(receipt, stdout, stderr, **kwargs)
        for change in [('kind', 'stop-sent'), ('elapsed', 120), ('elapsed', float('nan'))]:
            receipt, stdout, stderr, kwargs = fixture()
            receipt['events'][1][change[0]] = change[1]
            receipt['wait']['events'] = copy.deepcopy(receipt['events'])
            with self.assertRaises(ValueError):
                loader_trace.process(receipt, stdout, stderr, **kwargs)


if __name__ == '__main__':
    unittest.main()
