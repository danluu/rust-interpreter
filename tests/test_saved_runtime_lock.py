"""Benchmark lock waits respect a separate task-owned holder process."""
import argparse
from contextlib import contextmanager
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from compare_saved_runtime import acquire_lock, lock_wait_seconds


HOLDER = '''
import fcntl
import sys
with open(sys.argv[1], 'a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    print('locked', flush=True)
    sys.stdin.readline()
    fcntl.flock(lock, fcntl.LOCK_UN)
'''


class SavedRuntimeLockTests(unittest.TestCase):
    @contextmanager
    def held_lock(self, path):
        holder = subprocess.Popen([sys.executable, '-u', '-c', HOLDER, str(path)],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)
        released = False

        def release():
            nonlocal released
            if not released:
                _, stderr = holder.communicate(input='release\n')
                released = True
                self.assertEqual(holder.returncode, 0, stderr)

        try:
            ready, _, _ = select.select([holder.stdout], [], [], 5)
            self.assertTrue(ready, 'task-owned holder did not become ready')
            self.assertEqual(holder.stdout.readline(), 'locked\n')
            yield holder, release
        finally:
            # Release only this exact child through its own input protocol.
            # No signals or process-name searches are used during cleanup.
            release()

    def test_timeout_does_not_bypass_or_release_an_external_holder(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'benchmark.lock'
            with self.held_lock(path) as (holder, _):
                for seconds in [0, 0.03]:
                    with path.open('a') as lock:
                        with self.assertRaisesRegex(TimeoutError, 'waiting for benchmark lock'):
                            acquire_lock(lock, seconds)
                    self.assertIsNone(holder.poll())

    def test_waiter_acquires_only_after_the_exact_holder_releases(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'benchmark.lock'
            with self.held_lock(path) as (_, release):
                started = threading.Event()
                acquired = threading.Event()
                errors = []

                def wait_for_lock():
                    try:
                        with path.open('a') as lock:
                            started.set()
                            acquire_lock(lock, 5)
                            acquired.set()
                    except Exception as error:
                        errors.append(error)

                waiter = threading.Thread(target=wait_for_lock)
                waiter.start()
                try:
                    self.assertTrue(started.wait(5))
                    self.assertFalse(acquired.wait(0.05), 'waiter bypassed the held lock')
                    release()
                    self.assertTrue(acquired.wait(5), errors)
                finally:
                    release()
                    waiter.join(6)
                self.assertFalse(waiter.is_alive())
                self.assertEqual(errors, [])

    def test_wait_limit_accepts_only_finite_nonnegative_values(self):
        for value in ['nan', 'inf', '-inf', '-1', 'not a number']:
            with self.assertRaises(argparse.ArgumentTypeError):
                lock_wait_seconds(value)
        for value in ['0', '0.25', '300']:
            self.assertEqual(lock_wait_seconds(value), float(value))
        with tempfile.TemporaryDirectory() as directory:
            with (Path(directory) / 'benchmark.lock').open('a') as lock:
                acquire_lock(lock, 0)


if __name__ == '__main__':
    unittest.main()
