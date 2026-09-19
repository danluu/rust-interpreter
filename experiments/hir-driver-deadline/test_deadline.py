"""Pure clock/child controls. No actual processes are created or signaled."""
import signal
import subprocess
import unittest

import deadline


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, duration):
        assert 0 <= duration <= 5
        self.now += duration


class Child:
    def __init__(self, clock, exits_at=None, wait_error=False, poll_error=False):
        self.clock = clock
        self.exits_at = exits_at
        self.wait_error = wait_error
        self.poll_error = poll_error
        self.waits = []
        self.returncode = None

    def poll(self):
        if self.poll_error:
            raise OSError('synthetic poll error')
        if self.exits_at is not None and self.clock() >= self.exits_at:
            self.returncode = 0
        return self.returncode

    def wait(self, timeout):
        assert 0 < timeout <= 5
        self.waits.append(timeout)
        if self.wait_error:
            raise OSError('synthetic wait error')
        duration = timeout
        if self.exits_at is not None:
            duration = min(timeout, max(0, self.exits_at-self.clock()))
        self.clock.sleep(duration)
        result = self.poll()
        if result is None:
            raise subprocess.TimeoutExpired('synthetic-child', timeout)
        return result


class DeadlineControls(unittest.TestCase):
    def run_case(self, *, exits_at=None, heartbeat=None, publish=None,
                 stop_error=False, exit_on=None, wait_error=False,
                 poll_error=False, identity_seconds=0):
        clock = Clock()
        started_at = clock()
        clock.now += identity_seconds
        child = Child(clock, exits_at=exits_at, wait_error=wait_error, poll_error=poll_error)
        stops = []
        beats = []

        def sample():
            beats.append(clock())
            return heartbeat(clock()) if heartbeat else None

        def stop(signum, reason):
            stops.append((clock(), signum, reason))
            if stop_error:
                raise RuntimeError('owned identity changed; refusing signal')
            if signum == exit_on:
                child.returncode = -int(signum)

        result = deadline.monitor(child, heartbeat=sample, stop_owned=stop,
                                  publish=publish or (lambda row: None),
                                  clock=clock, sleep=clock.sleep, started_at=started_at)
        return result, stops, beats, child.waits

    def test_ordinary_exit_has_no_signal(self):
        result, stops, _, waits = self.run_case(exits_at=2)
        self.assertEqual((result['status'], result['returncode'], result['elapsed']), ('exited', 0, 2))
        self.assertEqual(stops, [])
        self.assertEqual(waits, [5])

    def test_deadline_interrupt_then_revalidated_kill(self):
        result, stops, beats, _ = self.run_case(exit_on=signal.SIGKILL)
        self.assertEqual([(s[0], s[1]) for s in stops], [(120, signal.SIGINT), (125, signal.SIGKILL)])
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual(result['reason'], 'execution deadline exceeded')
        self.assertFalse(result['child_may_be_live'])
        self.assertIn(125, beats)

    def test_kill_wait_is_also_finite(self):
        result, stops, beats, _ = self.run_case()
        self.assertEqual(result['status'], 'unresolved-live-child')
        self.assertEqual(result['elapsed'], 130)
        self.assertEqual(len(stops), 2)
        self.assertIn(130, beats)

    def test_refused_identity_never_retries_signal(self):
        result, stops, _, _ = self.run_case(stop_error=True)
        self.assertEqual(result['status'], 'unresolved-live-child')
        self.assertEqual(result['elapsed'], 120)
        self.assertEqual(len(stops), 1)
        self.assertIn('refusing signal', result['errors'][0]['error'])

    def test_resource_stop_retains_reason_and_monitoring(self):
        result, stops, beats, _ = self.run_case(heartbeat=lambda now: 'capacity' if now >= 10 else None)
        self.assertEqual([(s[0], s[2]) for s in stops], [(10, 'capacity'), (15, 'capacity')])
        self.assertEqual(result['elapsed'], 20)
        self.assertIn(20, beats)

    def test_publication_failure_does_not_disable_timeout(self):
        def broken(row):
            raise OSError('receipt unavailable')
        result, stops, _, _ = self.run_case(publish=broken, exit_on=signal.SIGINT)
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual(stops[0][0], 120)
        self.assertTrue(result['errors'])

    def test_sample_failure_does_not_disable_timeout(self):
        def broken(now):
            raise OSError('inventory unavailable')
        result, stops, _, _ = self.run_case(heartbeat=broken)
        self.assertEqual(result['elapsed'], 130)
        self.assertEqual(len(stops), 2)
        self.assertTrue(any(e['operation'] == 'heartbeat' for e in result['errors']))

    def test_wait_failure_keeps_finite_deadlines(self):
        result, stops, _, _ = self.run_case(wait_error=True)
        self.assertEqual(result['elapsed'], 130)
        self.assertEqual(len(stops), 2)
        self.assertTrue(any(e['operation'] == 'wait' for e in result['errors']))

    def test_poll_failure_with_identity_refusal_has_finite_unresolved_result(self):
        result, stops, _, _ = self.run_case(poll_error=True, stop_error=True)
        self.assertEqual(result['status'], 'unresolved-live-child')
        self.assertEqual(result['elapsed'], 120)
        self.assertEqual(len(stops), 1)
        self.assertTrue(any(e['operation'] == 'poll' for e in result['errors']))
        self.assertTrue(any(e['operation'] == 'stop_owned' for e in result['errors']))

    def test_initial_identity_capture_consumes_same_deadline(self):
        result, stops, _, _ = self.run_case(identity_seconds=119, exit_on=signal.SIGINT)
        self.assertEqual(stops[0][0], 120)
        self.assertEqual(result['reason'], 'execution deadline exceeded')

    def test_late_exit_is_not_a_pass(self):
        result, stops, _, _ = self.run_case(exits_at=120)
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual(result['reason'], 'execution deadline exceeded')
        self.assertEqual(stops, [])

    def test_invalid_limits_rejected_without_wait(self):
        for bad in [0, -1, float('inf'), float('nan'), True]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                deadline.monitor(None, heartbeat=None, stop_owned=None, publish=None, timeout=bad)


if __name__ == '__main__':
    unittest.main(verbosity=2)
