"""Synthetic filesystem and mocked process controls; no real child or signal."""
import contextlib
import copy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import monitor as m


def identity(pid):
    return dict(ps=f'{pid} 70 {101 if pid != 101 else pid} Fri Sep 18 12:00:00 2026 ?? owned-{pid}',
                ps_returncode=0, cwd=f'p{pid}\nn/owned/source\n', cwd_returncode=0)


class SignalControls(unittest.TestCase):
    @contextlib.contextmanager
    def scenario(self, *, original=None, current=None, member=None,
                 table='101 70 101\n102 101 101\n999 1 999\n', group=101, exited=False):
        original = identity(101) if original is None else original
        current = identity(101) if current is None else current
        member = identity(102) if member is None else member
        child = mock.Mock(pid=101)
        child.poll.return_value = 0 if exited else None
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(m.owned, 'identity', side_effect=lambda pid: current if pid == 101 else member))
            stack.enter_context(mock.patch.object(m.os, 'getpgid', return_value=group))
            stack.enter_context(mock.patch.object(m.subprocess, 'check_output', return_value=table))
            stack.enter_context(mock.patch.object(m.subprocess, 'Popen', side_effect=AssertionError('unexpected real process')))
            write = stack.enter_context(mock.patch.object(m.owned, 'write'))
            signal = stack.enter_context(mock.patch.object(m.os, 'killpg'))
            yield child, original, signal, write

    def reject(self, **kwargs):
        with self.scenario(**kwargs) as (child, original, signal, write):
            with self.assertRaises(AssertionError):
                m.stop_owned(child, original, Path('/mock/stop.json'), 'mock capacity')
            signal.assert_not_called()
            write.assert_not_called()

    def test_complete_owned_group_signals_only_fresh_group(self):
        with self.scenario() as (child, original, signal, write):
            m.stop_owned(child, original, Path('/mock/stop.json'), 'mock capacity')
            signal.assert_called_once_with(101, m.signal.SIGINT)
            record = write.call_args.args[1]
            self.assertEqual(set(record['group']), {101, 102})
            self.assertEqual(record['reason'], 'mock capacity')
            self.assertEqual(record['group'][102]['identity'], identity(102))

    def test_exited_child_never_signals(self):
        with self.scenario(exited=True) as (child, original, signal, write):
            m.stop_owned(child, original, Path('/mock/stop.json'), 'mock capacity')
            signal.assert_not_called(); write.assert_not_called()

    def test_missing_or_failed_original_probe_refuses(self):
        for key, value in [('ps', ''), ('ps', '  '), ('ps_returncode', 1),
                           ('cwd', ''), ('cwd', '\n'), ('cwd_returncode', 1)]:
            with self.subTest(key=key, value=value):
                broken = identity(101) | {key: value}
                self.reject(original=broken, current=broken)

    def test_missing_or_failed_current_probe_refuses(self):
        for key, value in [('ps', ''), ('ps_returncode', 1), ('cwd', ''), ('cwd_returncode', 1)]:
            with self.subTest(key=key):
                self.reject(current=identity(101) | {key: value})

    def test_changed_root_identity_or_group_refuses(self):
        self.reject(current=identity(101) | {'cwd': 'p101\nn/foreign\n'})
        self.reject(current=identity(101) | {'ps': identity(101)['ps'] + ' changed'})
        self.reject(group=999)

    def test_incomplete_descendant_probe_refuses(self):
        for key, value in [('ps', ''), ('ps_returncode', 1), ('cwd', ''), ('cwd_returncode', 1)]:
            with self.subTest(key=key):
                self.reject(member=identity(102) | {key: value})

    def test_unproved_parent_or_missing_group_root_refuses(self):
        self.reject(table='101 70 101\n102 999 101\n')
        self.reject(table='102 101 101\n')


class EvidenceControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve(strict=True)
        self.owners = tuple(self.base / name for name in ['owner', 'controller', 'oxc', 'root'])
        for owner in self.owners:
            (owner / '.work').mkdir(parents=True)
        self.namespace = self.owners[0] / '.work/namespace'
        self.namespace.mkdir()
        self.root = self.owners[1] / '.work/hir-options-hash-beta-composition-04'
        self.root.mkdir()
        self.future = self.owners[3] / '.work/hir-options-hash-driver-01'
        for name, value in [('EVIDENCE_OWNERS', self.owners), ('OWNER', self.owners[0]), ('NAMESPACE', self.namespace)]:
            patch = mock.patch.object(m, name, value)
            patch.start(); self.addCleanup(patch.stop)

    def test_existing_and_declared_future_roots_are_counted(self):
        (self.root / 'receipt').write_bytes(b'evidence')
        self.assertEqual(m.evidence_contract(self.root, [self.root, self.future]), (self.root, self.future))
        row = m.sample(evidence_root=self.root, evidence_roots=[self.root, self.future])
        self.assertEqual(row['allocation_errors'], [])
        self.assertEqual(row['stage_evidence_allocation_samples'][str(self.future)], {'bytes': 0, 'absent': True})
        self.assertGreater(row['evidence_allocated_bytes'], 0)

    def test_omitted_existing_root_and_new_root_both_reject(self):
        roots = [self.root, self.future]
        m.evidence_contract(self.root, roots)
        other = self.owners[2] / '.work/hir-options-hash-run-make-01'
        other.mkdir()
        with self.assertRaisesRegex(AssertionError, 'unbudgeted'):
            m.evidence_contract(self.root, roots)
        self.assertEqual(m.evidence_contract(self.root, roots + [other]), tuple(roots + [other]))

    def test_alias_and_dangling_evidence_roots_reject(self):
        for target in [self.root, self.base / 'absent']:
            with self.subTest(target=target):
                self.future.symlink_to(target, target_is_directory=True)
                try:
                    with self.assertRaisesRegex(AssertionError, 'symlink'):
                        m.evidence_contract(self.root, [self.root, self.future])
                finally:
                    self.future.unlink()

    def test_duplicate_foreign_nested_or_missing_active_root_rejects(self):
        invalid = [[self.root, self.root], [self.root, self.base / 'foreign'],
                   [self.root, self.root / 'hir-options-hash-driver-nested'], [self.future]]
        for roots in invalid:
            with self.subTest(roots=roots), self.assertRaises(AssertionError):
                m.evidence_contract(self.root, roots)

    def test_contract_failure_still_samples_namespace_and_free_space(self):
        self.future.mkdir()
        row = m.sample(evidence_root=self.root, evidence_roots=[self.root])
        self.assertTrue(row['allocation_errors'])
        self.assertIn('unbudgeted', row['allocation_errors'][0]['error'])
        self.assertIn('bytes', row['namespace_allocation_sample'])
        self.assertEqual(row['free_bytes'], min(row['free_bytes_before'], row['free_bytes_after']))
        self.assertIn('inventory unavailable', m.rejection(row | {'free_bytes': 10*m.GIB}))

    def test_allocated_counts_hardlink_once_and_does_not_follow_symlinks(self):
        data = self.namespace / 'data'
        data.write_bytes(b'x' * 8192)
        os.link(data, self.namespace / 'alias')
        external = self.base / 'external'
        external.mkdir(); (external / 'large').write_bytes(b'z' * 65536)
        link = self.namespace / 'link'; link.symlink_to(external, target_is_directory=True)
        expected = sum(path.lstat().st_blocks * 512 for path in [self.namespace, data, link])
        self.assertEqual(m.allocated(self.namespace, (self.namespace,))['bytes'], expected)

    def test_resource_boundaries_preserve_namespace_and_aggregate_caps(self):
        row = dict(free_bytes=9*m.GIB, namespace_allocated_bytes=14*m.GIB,
                   evidence_allocated_bytes=256*2**20, allocation_errors=[])
        self.assertIsNone(m.rejection(row))
        for name, value, reason in [('free_bytes', 9*m.GIB-1, 'free space'),
                                    ('namespace_allocated_bytes', 14*m.GIB+1, '14 GiB'),
                                    ('evidence_allocated_bytes', 256*2**20+1, '256 MiB')]:
            with self.subTest(name=name):
                self.assertIn(reason, m.rejection(row | {name: value}))


class DrainControls(unittest.TestCase):
    def test_failed_identity_drain_preserves_error_without_signalling(self):
        child = mock.Mock(pid=101)
        child.poll.side_effect = [None, 0]
        child.wait.side_effect = subprocess.TimeoutExpired(['mock'], 5)
        record = dict(samples=[], error='original validation error')
        with mock.patch.object(m, 'sample', return_value={'mock': True}), \
             mock.patch.object(m, 'rejection', return_value='mock capacity'), \
             mock.patch.object(m, 'stop_owned') as stop, \
             mock.patch.object(m.owned, 'write') as write, \
             mock.patch.object(m.os, 'killpg') as signal:
            m.drain_failed_child(child, record, Path('/mock'), evidence_root=Path('/mock'), evidence_roots=[Path('/mock')])
            stop.assert_not_called(); signal.assert_not_called(); write.assert_called_once()
        self.assertEqual(record['error'], 'original validation error')
        self.assertEqual(record['samples'], [{'mock': True}])
        self.assertIn('missing original child identity', record['drain_errors'][0]['error'])

    def test_failed_signal_proof_is_retained_and_child_is_drained(self):
        child = mock.Mock(pid=101)
        child.poll.side_effect = [None, 0]
        child.wait.side_effect = subprocess.TimeoutExpired(['mock'], 5)
        record = dict(samples=[], error='original validation error', identity=identity(101))
        with mock.patch.object(m, 'sample', return_value={'mock': True}), \
             mock.patch.object(m, 'rejection', return_value='mock capacity'), \
             mock.patch.object(m, 'stop_owned', side_effect=AssertionError('probe unavailable')) as stop, \
             mock.patch.object(m.owned, 'write'), mock.patch.object(m.os, 'killpg') as signal:
            m.drain_failed_child(child, record, Path('/mock'), evidence_root=Path('/mock'), evidence_roots=[Path('/mock')])
            stop.assert_called_once(); signal.assert_not_called()
        self.assertEqual(record['error'], 'original validation error')
        self.assertIn('probe unavailable', record['drain_errors'][0]['error'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
