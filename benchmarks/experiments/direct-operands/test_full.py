import copy
import unittest
import workflows


def rows(candidate=1.8, duplicate=2.02, anchor=2.2):
    result=[]
    for cycle in range(3):
        for state in range(1,6):
            for mode in workflows.MODES:
                seconds=dict(baseline=2.,duplicate=duplicate,candidate=candidate,anchor=anchor,native=1.,native_lines=.9,check=.3)[mode]
                result.append(dict(cycle=cycle,state=state,mode=mode,source_sha256=str(state),seconds=seconds,cpu=dict(total_seconds=seconds)))
    return result


class FullComparisonTests(unittest.TestCase):
    def test_primary_requires_incremental_total_and_cpu_gains(self):
        self.assertTrue(workflows.assessment(rows(),'token')['gate_passed'])
        for changed in [rows(candidate=2),rows(anchor=1.9),rows(duplicate=2.22)]:
            self.assertFalse(workflows.assessment(changed,'token')['gate_passed'])
        changed=rows()
        for row in changed:
            if row['mode']=='candidate':row['cpu']['total_seconds']=2.0001
        self.assertFalse(workflows.assessment(changed,'token')['gate_passed'])

    def test_heldouts_accept_only_the_declared_summed_margin(self):
        for case in ['folded','pgrust']:
            self.assertTrue(workflows.assessment(rows(candidate=2.02,duplicate=2.04),case)['gate_passed'])
            for duplicate,passed in [(2.098,True),(2.102,False),(2.108,False)]:
                self.assertEqual(workflows.assessment(rows(candidate=2,duplicate=duplicate),case)['gate_passed'],passed)
            self.assertFalse(workflows.assessment(rows(anchor=1.9,candidate=2,duplicate=2.02),case)['gate_passed'])

    def test_missing_duplicate_and_mixed_sources_reject(self):
        original=rows()
        for changed in [original[:-1],original+[copy.deepcopy(original[0])]]:
            with self.assertRaises(AssertionError):workflows.assessment(changed,'token')
        original[0]['source_sha256']='different'
        with self.assertRaises(AssertionError):workflows.assessment(original,'token')

    def test_custom_schedule_covers_every_position_in_each_four_row_block(self):
        original='fn body(){100}\n#[cfg(test)]\nmod tests { unchanged }'
        case=dict(negative=('wrong','100','999'),edits=[(str(i),str(100+i),str(101+i)) for i in range(5)])
        states=list(workflows.protocol_states(original,case))
        self.assertEqual(len(states),21)
        edited=[s for s in states if s['state']>0]
        self.assertEqual(len(edited),15)
        for start in [0,4,8]:
            for position in range(4):
                self.assertCountEqual([s['modes'][position] for s in edited[start:start+4]],workflows.CUSTOM)
        self.assertTrue(all(s['source'].endswith(b'mod tests { unchanged }') for s in states))

    def test_all_three_runtime_controls_use_matching_cached_lookup(self):
        for mode in workflows.CACHED:
            self.assertEqual(workflows.lookup_args(mode),['--toolchain-lookup','cached'])
            self.assertTrue(workflows.validate_lookup(dict(toolchain_lookup=dict(mode='cached',outcome='hit')),mode,1,3))
            with self.assertRaises(AssertionError):
                workflows.validate_lookup(dict(toolchain_lookup=dict(mode='cached',outcome='miss')),mode,1,0)
        self.assertEqual(workflows.lookup_args('anchor'),['--toolchain-lookup','fresh'])

    def test_native_failure_must_match_original_names_and_counts(self):
        failure='test a ... FAILED\ntest b ... ok\ntest result: FAILED. 1 passed; 1 failed; 0 ignored;'
        self.assertEqual(workflows.native_outcomes(failure,['a','b'],False),[('a','failed'),('b','passed')])
        for wrong in [failure.replace('test a','test c'),failure.replace('1 failed','0 failed')]:
            with self.assertRaises(AssertionError):workflows.native_outcomes(wrong,['a','b'],False)
