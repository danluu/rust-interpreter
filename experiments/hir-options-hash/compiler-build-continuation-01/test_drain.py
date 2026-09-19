"""Pure controls for an already-owned child's failed-supervision drain."""
from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import bounded_command_v2 as b


class FakeChild:
    pid = 12345

    def __init__(self, timeouts):
        self.timeouts = timeouts
        self.returncode = None
        self.wait_timeouts = []

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.wait_timeouts.append(timeout)
        if timeout != 5:
            raise AssertionError('failed supervision used an unmonitored wait')
        if self.timeouts:
            self.timeouts -= 1
            raise b.subprocess.TimeoutExpired(['synthetic-owned-child'], timeout)
        self.returncode = 0
        return self.returncode


class FailedDrainControls(unittest.TestCase):
    def exercise(self, observations, *, stop_error=None, receipt_failure=True):
        with tempfile.TemporaryDirectory(prefix='hir-failed-drain-control-') as temporary:
            root = Path(temporary).resolve()
            namespace = root/'namespace'
            source = namespace/'source'
            source.mkdir(parents=True)
            evidence = root/'evidence'
            evidence.mkdir()
            output = evidence/'child'
            child = FakeChild(len(observations))
            original = dict(ps='exact original synthetic identity', cwd='synthetic source')
            healthy = dict(free_bytes=10*b.GIB, namespace_allocated_bytes=0,
                           evidence_allocated_bytes=0, allocation_errors=[])
            receipts = []
            failed = False

            def write(path, value):
                nonlocal failed
                if receipt_failure and value.get('status') == 'running' and not failed:
                    failed = True
                    raise OSError('injected initial running receipt failure')
                receipts.append(json.loads(json.dumps(value)))

            with (patch.object(b, 'NAMESPACE', namespace),
                  patch.object(b, 'EVIDENCE', evidence),
                  patch.object(b.owned, 'workload_lock', return_value=nullcontext()),
                  patch.object(b.owned, 'identity', return_value=original),
                  patch.object(b.owned, 'write', side_effect=write),
                  patch.object(b.subprocess, 'Popen', return_value=child) as spawn,
                  patch.object(b, 'sample', side_effect=[healthy, *observations]) as sample,
                  patch.object(b, 'stop_owned', side_effect=stop_error) as stop):
                expected_error = (OSError, 'injected initial running receipt failure') if receipt_failure else (
                    RuntimeError, 'free space below 9 GiB stop threshold')
                with self.assertRaisesRegex(*expected_error):
                    b.run(['synthetic-owned-child'], cwd=source, environment={},
                          output=output, canonical_fd=999)
                self.assertTrue(spawn.call_args.kwargs['start_new_session'])
                self.assertEqual(sample.call_count, 1+len(observations))
                self.assertEqual(child.returncode, 0)
                self.assertEqual(child.wait_timeouts, [5]*(1+len(observations)))
                final = receipts[-1]
                self.assertEqual(final['status'], 'failed')
                self.assertIn(expected_error[1], final['error'])
                self.assertEqual(final['returncode'], 0)
                return final, stop.call_args_list, original

    @staticmethod
    def healthy():
        return dict(free_bytes=10*b.GIB, namespace_allocated_bytes=0,
                    evidence_allocated_bytes=0, allocation_errors=[])

    def test_receipt_failure_keeps_sampling_without_signal(self):
        final, stops, _ = self.exercise([self.healthy(), self.healthy()])
        self.assertEqual(len(final['samples']), 3)
        self.assertEqual(stops, [])

    def test_later_capacity_failure_uses_original_identity_once_and_keeps_sampling(self):
        low = dict(self.healthy(), free_bytes=9*b.GIB-1)
        final, stops, original = self.exercise([low, low, self.healthy()])
        self.assertEqual(len(stops), 1)
        self.assertEqual(stops[0].args[1], original)
        self.assertEqual(stops[0].args[3], 'free space below 9 GiB stop threshold')
        self.assertEqual(len(final['samples']), 4)

    def test_ownership_refusal_preserves_original_failure_and_keeps_sampling(self):
        low = dict(self.healthy(), free_bytes=9*b.GIB-1)
        final, stops, _ = self.exercise([low, self.healthy()],
                                       stop_error=AssertionError('identity changed; no signal'))
        self.assertEqual(len(stops), 1)
        self.assertEqual(len(final['samples']), 3)
        self.assertIn('identity changed; no signal', final['drain_errors'][0]['error'])

    def test_normal_capacity_stop_keeps_sampling_until_exit_without_second_signal(self):
        low = dict(self.healthy(), free_bytes=9*b.GIB-1)
        final, stops, original = self.exercise([low, low, self.healthy()], receipt_failure=False)
        self.assertEqual(len(stops), 1)
        self.assertEqual(stops[0].args[1], original)
        self.assertEqual(len(final['samples']), 4)

    def test_transient_sample_error_does_not_end_monitoring(self):
        final, stops, _ = self.exercise([OSError('transient sample failure'), self.healthy()])
        self.assertEqual(stops, [])
        self.assertEqual(len(final['samples']), 2)
        self.assertIn('transient sample failure', final['drain_errors'][0]['error'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
