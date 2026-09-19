"""Pure ownership-proof controls; never inspect or signal an actual process."""
import copy
from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import owned_driver
from owned_driver import check_identity, prove_singleton


COMMAND = ['/owned/hash-driver', '/owned/E2', '/owned/fixture.rs', '/owned/output', 'serial']
CWD = Path('/owned')
ARGS = dict(pid=123, parent=45, command=COMMAND, cwd=CWD)


def identity():
    return dict(ps='123 45 123 Sat Sep 19 01:00:00 2026 ?? ' + ' '.join(COMMAND),
                ps_returncode=0, cwd='p123\nfcwd\nn/owned\n', cwd_returncode=0)


class OwnedProof(unittest.TestCase):
    def test_exact_singleton_with_unrelated_processes(self):
        original = identity()
        self.assertEqual(prove_singleton(original, copy.deepcopy(original),
                         [(999, 1, 999), (123, 45, 123)], **ARGS)['group'], [(123, 45, 123)])

    def test_rejects_identity_probe_failures(self):
        for key in ('ps_returncode', 'cwd_returncode'):
            current = identity(); current[key] = 1
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                check_identity(current, **ARGS)

    def test_rejects_reused_pid_or_changed_identity(self):
        for old, new in [('123 45 123', '124 45 123'), ('123 45 123', '123 46 123'),
                         ('123 45 123', '123 45 999'), ('01:00:00', '01:01:00'),
                         ('??', 'ttys003'), ('/owned/hash-driver', '/other/hash-driver')]:
            original = identity(); current = identity(); current['ps'] = current['ps'].replace(old, new)
            with self.subTest(old=old), self.assertRaises(RuntimeError):
                prove_singleton(original, current, [(123, 45, 123)], **ARGS)

    def test_rejects_changed_cwd_or_cwd_pid(self):
        for value in ('p123\nfcwd\nn/other\n', 'p999\nfcwd\nn/owned\n', ''):
            current = identity(); current['cwd'] = value
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                prove_singleton(identity(), current, [(123, 45, 123)], **ARGS)

    def test_rejects_extra_even_descendant_group_member(self):
        for extra in ((999, 123, 123), (999, 1, 123)):
            with self.subTest(extra=extra), self.assertRaises(RuntimeError):
                prove_singleton(identity(), identity(), [(123, 45, 123), extra], **ARGS)

    def test_rejects_missing_duplicate_or_malformed_table(self):
        for table in ([], [(123, 45, 999)], [(123, 45, 123)] * 2,
                      [(123, 45, 123), (999, 1)], [('123', 45, 123)], [(True, 45, 123)]):
            with self.subTest(table=table), self.assertRaises(RuntimeError):
                prove_singleton(identity(), identity(), table, **ARGS)


class Adapter(unittest.TestCase):
    """Real adapter I/O in a tiny temp tree, with all process APIs replaced."""
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.cwd = Path(self.temporary.name).resolve()
        self.output = self.cwd / 'evidence'
        self.parent = os.getpid()
        self.child = SimpleNamespace(pid=123, poll=lambda: None)
        self.identity = identity()
        self.identity['ps'] = self.identity['ps'].replace('123 45 123', f'123 {self.parent} 123')
        self.identity['cwd'] = f'p123\nfcwd\nn{self.cwd}\n'
        self.locks = []
        self.guards = []
        self.table = f'123 {self.parent} 123\n'

        @contextmanager
        def lock(path, wait, inherited_fd):
            self.locks.append((path, wait, inherited_fd)); yield inherited_fd

        def write(path, value):
            self.assertTrue(path.is_relative_to(self.output))
            path.write_text(json.dumps(value))

        self.owned = SimpleNamespace(CANONICAL_LOCK=Path('/fake/canonical.lock'),
                                     workload_lock=lock, write=write,
                                     identity=lambda pid: copy.deepcopy(self.identity))

    def invoke(self, monitor, popen=None):
        def probe(command, **kwargs):
            destination = kwargs['output']; destination.mkdir()
            self.assertEqual(kwargs['canonical_fd'], 71)
            if command[:2] == ['/bin/ps', '-axo']:
                text = self.table
            elif command[0] == '/bin/ps':
                text = self.identity['ps'] + '\n'
            else:
                self.assertEqual(command[0], '/usr/sbin/lsof')
                text = self.identity['cwd']
            (destination / 'receipt.json').write_text(json.dumps({'status': 'finished'}))
            return 0, text
        with patch.object(owned_driver.subprocess, 'Popen', popen or (lambda *a, **k: self.child)):
            with patch.object(owned_driver.deadline, 'monitor', monitor):
                with patch.object(owned_driver, 'bounded_probe', probe):
                    return owned_driver.run(COMMAND, cwd=self.cwd, environment={'ONLY': 'frozen'},
                        output=self.output, canonical_fd=71, owned=self.owned,
                        guard=lambda: self.guards.append(True),
                        resource_observation=lambda: {'free_bytes': 30 * 2**30},
                        resource_rejection=lambda row: None)

    def test_inherits_exact_lock_and_fresh_session(self):
        calls = []
        def popen(*args, **kwargs):
            calls.append((args, kwargs)); return self.child
        def monitor(child, **callbacks):
            self.assertIs(child, self.child)
            self.assertIsNone(callbacks['heartbeat']())
            callbacks['publish']({'kind': 'synthetic-exit'})
            self.assertGreater(callbacks['started_at'], 0)
            return dict(status='exited', returncode=0, child_may_be_live=False, errors=[])
        result = self.invoke(monitor, popen)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(calls[0][0], (COMMAND,))
        self.assertEqual(calls[0][1]['pass_fds'], (71,))
        self.assertIs(calls[0][1]['start_new_session'], True)
        self.assertEqual(calls[0][1]['env'], {'ONLY': 'frozen'})
        self.assertEqual(self.locks, [(self.owned.CANONICAL_LOCK, 600, 71)])
        self.assertEqual(len(self.guards), 2)

    def test_unresolved_child_has_no_false_completion_or_final_hash(self):
        def monitor(child, **callbacks):
            return dict(status='unresolved-live-child', returncode=None,
                        child_may_be_live=True, errors=[{'operation': 'stop refused'}])
        result = self.invoke(monitor)
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['child_may_be_live'])
        self.assertNotIn('child_finished_at', result)
        self.assertNotIn('stdout_sha256', result)
        self.assertEqual(len(self.guards), 1)

    def test_signal_refuses_unproved_group(self):
        def monitor(child, **callbacks):
            with self.assertRaises(RuntimeError):
                callbacks['stop_owned'](signal.SIGINT, 'synthetic timeout')
            return dict(status='unresolved-live-child', returncode=None,
                        child_may_be_live=True, errors=[])
        self.table += '999 123 123\n'
        with patch.object(owned_driver.os, 'killpg') as kill:
            result = self.invoke(monitor)
            kill.assert_not_called()
        self.assertEqual(result['status'], 'failed')

    def test_signal_proof_published_before_exact_owned_signal(self):
        def monitor(child, **callbacks):
            callbacks['stop_owned'](signal.SIGINT, 'synthetic timeout')
            return dict(status='stopped', returncode=-2, child_may_be_live=False, errors=[])
        def signal_observer(pid, signum):
            self.assertEqual((pid, signum), (123, signal.SIGINT))
            proof = json.loads((self.output / 'owned-stop-SIGINT.json').read_text())
            self.assertEqual(proof['group'], [[123, self.parent, 123]])
        with patch.object(owned_driver.os, 'getpgid', return_value=123):
            with patch.object(owned_driver.os, 'killpg', side_effect=signal_observer) as kill:
                result = self.invoke(monitor)
                kill.assert_called_once()
        self.assertEqual(result['status'], 'failed')

    def test_launch_failure_is_retained(self):
        def popen(*args, **kwargs):
            raise OSError('synthetic launch failure')
        with self.assertRaises(OSError):
            self.invoke(lambda *a, **k: self.fail('monitor must not run'), popen)
        record = json.loads((self.output / 'receipt.json').read_text())
        self.assertEqual(record['status'], 'failed')
        self.assertFalse(record['child_may_be_live'])
        self.assertIn('synthetic launch failure', record['launch_error'])

    def test_probe_timeout_keeps_its_lock_without_any_signal(self):
        self.output.mkdir()
        waits = []
        def wait(timeout):
            waits.append(timeout)
            raise subprocess.TimeoutExpired('synthetic probe', timeout)
        child = SimpleNamespace(pid=321, wait=wait)
        with patch.object(owned_driver.subprocess, 'Popen', return_value=child) as popen:
            with patch.object(owned_driver.os, 'killpg') as kill:
                with self.assertRaises(RuntimeError):
                    owned_driver.bounded_probe(['/bin/ps'], cwd=self.cwd, environment={},
                        output=self.output / 'probe', canonical_fd=71, owned=self.owned)
                kill.assert_not_called()
            self.assertEqual(popen.call_args.kwargs['pass_fds'], (71,))
        self.assertEqual(waits, [2])
        record = json.loads((self.output / 'probe/receipt.json').read_text())
        self.assertEqual(record['status'], 'unresolved-live-probe')
        self.assertEqual(record['pid'], 321)
        self.assertNotIn('finished_at', record)


if __name__ == '__main__':
    unittest.main()
