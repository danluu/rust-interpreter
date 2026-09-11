"""Check edit replay and accounting independently of a Rust workload."""
import itertools
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from workflow_measurements import child_usage, child_cpu_since, per_edit_spread, sample_path, source_states


ORIGINAL = 'fn value() -> u32 { 10 }\n#[cfg(test)]\nmod tests { const EXPECTED: u32 = 10; }\n'
CASE = dict(negative=['wrong', '{ 10 }', '{ 99 }'], edits=[
    ['first', '{ 10 }', '{ 5 + 5 }'],
    ['second', '{ 5 + 5 }', '{ 2 * 5 }'],
    ['third', '{ 2 * 5 }', '{ 20 / 2 }'],
    ['fourth', '{ 20 / 2 }', '{ 11 - 1 }'],
    ['fifth', '{ 11 - 1 }', '{ 10 + 0 }'],
])
MODES = ['native', 'baseline', 'candidate']


class RepeatedEditTests(unittest.TestCase):
    def test_every_cycle_rebuilds_an_anchor_and_changes_each_modes_source(self):
        states = list(source_states(ORIGINAL, CASE, 3, MODES, True))
        self.assertEqual(len(states), 21)
        self.assertEqual([s['phase'] for s in states].count('cold'), 1)
        self.assertEqual([s['phase'] for s in states].count('anchor'), 2)
        self.assertEqual([s['phase'] for s in states].count('wrong-edit'), 3)
        self.assertEqual([s['phase'] for s in states].count('edit'), 15)
        previous = dict.fromkeys(MODES)
        reference = {}
        for state in states:
            self.assertEqual(state['source'].split(b'#[cfg(test)]')[1], ORIGINAL.encode().split(b'#[cfg(test)]')[1])
            if state['state'] == 0:
                self.assertEqual(state['source'], ORIGINAL.encode())
            reference.setdefault(state['state'], state['source'])
            self.assertEqual(reference[state['state']], state['source'])
            for mode in state['modes']:
                self.assertNotEqual(previous[mode], state['source'])
                previous[mode] = state['source']

    def test_every_edit_has_balanced_positions_and_all_six_orders(self):
        states = list(source_states(ORIGINAL, CASE, 6, MODES, True))
        for edit in range(1, 6):
            orders = [s['modes'] for s in states if s['state'] == edit]
            self.assertEqual({tuple(order) for order in orders}, set(itertools.permutations(MODES)))
            for mode in MODES:
                self.assertEqual(sorted(order.index(mode) for order in orders[:3]), [0, 1, 2])

    def test_single_cycle_keeps_old_order_and_snapshot_names(self):
        states = list(source_states(ORIGINAL, CASE, 1, MODES, True))
        self.assertEqual([s['modes'] for s in states], [
            MODES, list(reversed(MODES)), ['native', 'baseline', 'candidate'],
            ['native', 'candidate', 'baseline'], ['baseline', 'native', 'candidate'],
            ['candidate', 'native', 'baseline'], ['baseline', 'candidate', 'native']])
        self.assertEqual(sample_path(states[0], 0, 1, 'rbc'), '0-0.rbc')
        repeated = list(source_states(ORIGINAL, CASE, 3, MODES, True))
        paths = [sample_path(s, i, 3, 'rbc') for s in repeated for i in range(2)]
        self.assertEqual(len(paths), len(set(paths)))

    def test_unchanged_or_test_mutating_edits_are_rejected(self):
        for edit in [['same', '{ 10 }', '{ 10 }'], ['assertion', 'EXPECTED: u32 = 10', 'EXPECTED: u32 = 99']]:
            with self.assertRaises(ValueError):
                list(source_states(ORIGINAL, dict(CASE, edits=[edit]), 1, MODES, True))

    def test_spread_keeps_each_source_edit_separate(self):
        pairs = [dict(cycle=c, state=s, source_sha256=str(s), baseline_seconds=10.0,
            candidate_seconds=10.0 + c - s, native_seconds=3.0,
            difference_seconds=float(c - s), cpu_difference_seconds=float(c - s) / 2)
            for c in range(3) for s in [1, 2]]
        rows = per_edit_spread(pairs)
        self.assertEqual([r['samples'] for r in rows], [3, 3])
        self.assertEqual(rows[0]['spread']['difference_seconds'], dict(min=-1.0, median=0.0, max=1.0))
        self.assertEqual(rows[1]['spread']['difference_seconds'], dict(min=-2.0, median=-1.0, max=0.0))
        with self.assertRaises(ValueError):
            per_edit_spread(pairs + [pairs[0]])
        pairs[-1]['source_sha256'] = 'different edit'
        with self.assertRaises(ValueError):
            per_edit_spread(pairs)


class ChildCpuTests(unittest.TestCase):
    def test_waited_grandchild_cpu_is_included(self):
        # The fixture reports separate RUSAGE_SELF totals from the child and
        # grandchild. Their sum is an independent reference for the harness's
        # RUSAGE_CHILDREN delta. Busy work uses process CPU, not elapsed time.
        grandchild = '''import json, os, resource, time
start=time.process_time()
while time.process_time()-start < .20: pass
r=resource.getrusage(resource.RUSAGE_SELF)
print(json.dumps(dict(cpu=r.ru_utime+r.ru_stime,pid=os.getpid(),parent=os.getppid())))
'''
        child = '''import json, os, resource, subprocess, sys, time
grand=json.loads(subprocess.check_output([sys.executable,'-c',sys.argv[1]],text=True))
start=time.process_time()
while time.process_time()-start < .05: pass
r=resource.getrusage(resource.RUSAGE_SELF)
print(json.dumps(dict(cpu=r.ru_utime+r.ru_stime,pid=os.getpid(),parent=os.getppid(),grandchild=grand)))
'''
        before = child_usage()
        process = subprocess.Popen([sys.executable, '-c', child, grandchild], stdout=subprocess.PIPE, text=True)
        output, _ = process.communicate()
        measured = child_cpu_since(before)
        self.assertEqual(process.returncode, 0)
        reported = json.loads(output)
        self.assertEqual(reported['pid'], process.pid)
        self.assertEqual(reported['grandchild']['parent'], process.pid)
        expected = reported['cpu'] + reported['grandchild']['cpu']
        self.assertGreaterEqual(measured['total_seconds'], .24)
        self.assertAlmostEqual(measured['total_seconds'], expected, delta=.03)


if __name__ == '__main__':
    unittest.main()
