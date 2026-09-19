"""Pure aggregate-budget and signal-refusal controls; every process API is mocked."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import bounded_command_v2 as b


class AggregateControls(unittest.TestCase):
    def observation(self, amounts, failure=None):
        visited=[]
        def allocation(root):
            visited.append(root)
            if root == failure:
                raise OSError('injected unavailable prior evidence')
            return dict(bytes=amounts[root],raced_entries=1,entries_visited=2)
        with (patch.object(b,'allocated',side_effect=allocation),
              patch.object(b.shutil,'disk_usage',side_effect=[SimpleNamespace(free=11*b.GIB),SimpleNamespace(free=10*b.GIB)]) as disk):
            row=b.sample()
        self.assertEqual(disk.call_count,2)
        self.assertEqual(visited,[b.NAMESPACE,*b.PRIOR_EVIDENCE,b.EVIDENCE])
        self.assertEqual(row['free_bytes'],10*b.GIB)
        return row

    def test_individually_small_histories_exceed_combined_cap(self):
        amounts={root:100*2**20 for root in [b.NAMESPACE,*b.PRIOR_EVIDENCE,b.EVIDENCE]}
        row=self.observation(amounts)
        self.assertEqual(row['evidence_allocated_bytes'],300*2**20)
        self.assertIn('256 MiB',b.rejection(row))
        self.assertEqual(set(row['evidence_allocation_sample']['roots']),set(map(str,[*b.PRIOR_EVIDENCE,b.EVIDENCE])))

    def test_exact_combined_cap_is_accepted(self):
        amounts={b.NAMESPACE:14*b.GIB,b.PRIOR_EVIDENCE[0]:64*2**20,b.PRIOR_EVIDENCE[1]:64*2**20,b.EVIDENCE:128*2**20}
        row=self.observation(amounts)
        self.assertEqual(row['evidence_allocated_bytes'],256*2**20)
        self.assertIsNone(b.rejection(row))

    def test_unavailable_prior_allocation_fails_closed_with_free_space_bracket(self):
        amounts={root:0 for root in [b.NAMESPACE,*b.PRIOR_EVIDENCE,b.EVIDENCE]}
        row=self.observation(amounts,b.PRIOR_EVIDENCE[0])
        self.assertEqual(row['allocation_errors'][0]['root'],str(b.PRIOR_EVIDENCE[0]))
        self.assertTrue(row['evidence_allocation_sample']['roots'][str(b.PRIOR_EVIDENCE[0])]['unavailable'])
        self.assertIn('inventory unavailable',b.rejection(row))


class SignalControls(unittest.TestCase):
    @staticmethod
    def identity(pid=101,parent=90):
        return dict(ps=f'{pid} {parent} 101 Fri Sep 18 00:00:00 2026 ?? synthetic',ps_returncode=0,
                    cwd=f'p{pid}\nn/owned/source\n',cwd_returncode=0)

    def exercise(self,which=None,delta=None):
        child=SimpleNamespace(pid=101,poll=lambda:None)
        original=self.identity();current=self.identity();member=self.identity(102,101)
        if which=='original':original.update(delta)
        if which=='current':current.update(delta)
        if which=='member':member.update(delta)
        with (patch.object(b.owned,'identity',side_effect=[current,current,member]) as identities,
              patch.object(b.os,'getpgid',return_value=101),
              patch.object(b.subprocess,'check_output',return_value='101 90 101\n102 101 101\n'),
              patch.object(b.owned,'write') as write,
              patch.object(b.os,'killpg') as signal):
            if which:
                with self.assertRaises(AssertionError):
                    b.stop_owned(child,original,Path('/synthetic/owned-stop.json'),'capacity')
                signal.assert_not_called();write.assert_not_called()
            else:
                b.stop_owned(child,original,Path('/synthetic/owned-stop.json'),'capacity')
                signal.assert_called_once_with(101,b.signal.SIGINT)
                self.assertEqual(set(write.call_args.args[1]['group']),{101,102})
                self.assertEqual(identities.call_count,3)

    def invalid_probes(self,which):
        for delta in [dict(ps_returncode=1),dict(cwd_returncode=1),dict(ps=''),dict(cwd=''),dict(ps='  '),dict(cwd='\n')]:
            with self.subTest(which=which,delta=delta):self.exercise(which,delta)

    def test_missing_original_probe_refuses_signal(self):self.invalid_probes('original')
    def test_missing_current_probe_refuses_signal(self):self.invalid_probes('current')
    def test_missing_group_member_probe_refuses_signal(self):self.invalid_probes('member')
    def test_complete_unchanged_owned_identities_allow_one_signal(self):self.exercise()

    def test_refused_signal_keeps_drain_monitoring(self):
        class Child:
            pid=101
            returncode=None
            remaining=2
            def poll(self):return self.returncode
            def wait(self,timeout=None):
                assert timeout==5
                if self.remaining:
                    self.remaining-=1
                    raise b.subprocess.TimeoutExpired(['synthetic'],timeout)
                self.returncode=0
        child=Child();original=dict(self.identity(),cwd='',cwd_returncode=1)
        record=dict(error='original receipt failure',identity=original,samples=[])
        low=dict(free_bytes=9*b.GIB-1,namespace_allocated_bytes=0,evidence_allocated_bytes=0,allocation_errors=[])
        with (patch.object(b,'sample',return_value=low) as sample,
              patch.object(b.owned,'identity',return_value=original),
              patch.object(b.owned,'write'),patch.object(b.os,'killpg') as signal,
              patch.object(b.subprocess,'check_output') as table):
            b.drain_failed_child(child,record,Path('/synthetic'))
        self.assertEqual(sample.call_count,2);self.assertEqual(len(record['samples']),2)
        self.assertEqual(len(record['drain_errors']),2)
        self.assertEqual(record['error'],'original receipt failure')
        signal.assert_not_called();table.assert_not_called()
        self.assertEqual(child.returncode,0)


if __name__=='__main__':unittest.main(verbosity=2)
