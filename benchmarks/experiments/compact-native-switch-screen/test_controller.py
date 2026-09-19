import unittest
from benchmark import case_states,native_outcomes
from accounting import MODES,schedule

def source_fixture():
    original='fn value() {\n'+''.join(f'let v{i} = {i};\n' for i in range(5))+'}\n#[cfg(test)]\nmod tests { const ASSERTION: bool = true; }\n'
    case=dict(negative=['wrong','let v0 = 0;','let v0 = 99;'],
        edits=[[str(i),f'let v{i} = {i};',f'let v{i} = ({i});'] for i in range(5)])
    return original.encode(),case

class Controller(unittest.TestCase):
    def test_one_source_cycle_and_restore_preserve_the_original_assertions(self):
        original,case=source_fixture();states=case_states(original,case)
        self.assertEqual(len(states),8);self.assertEqual(states[-1]['source'],original)
        suffix=original.split(b'\n#[cfg(test)]\nmod tests {')[1]
        for state in states:self.assertEqual(state['source'].split(b'\n#[cfg(test)]\nmod tests {')[1],suffix)
        self.assertEqual(sum(s['state']>0 for s in states),5)
    def test_an_edit_that_changes_the_original_tests_is_refused(self):
        original,case=source_fixture();case['edits'][0]=['forbidden','ASSERTION: bool = true','ASSERTION: bool = false']
        with self.assertRaisesRegex(ValueError,'test source changed'):case_states(original,case)
    def test_every_measured_arm_observes_a_real_source_transition(self):
        original,case=source_fixture();rows=schedule(case_states(original,case))
        for mode in MODES:
            selected=[r['source_sha256'] for r in rows if r['mode']==mode]
            self.assertEqual(len(selected),8);self.assertTrue(all(a!=b for a,b in zip(selected,selected[1:])))
    def test_native_outcomes_reject_missing_duplicate_ignored_and_inconsistent_summaries(self):
        stdout='test a ... ok\ntest b ... FAILED\ntest result: FAILED. 1 passed; 1 failed; 0 ignored;\n'
        self.assertEqual(native_outcomes(stdout,['a','b'],False),[('a','passed'),('b','failed')])
        for value in [stdout.replace('test b ... FAILED\n',''),stdout.replace('test b','test a'),
                stdout.replace('b ... FAILED','b ... ignored'),stdout.replace('1 passed','2 passed')]:
            with self.assertRaises(AssertionError):native_outcomes(value,['a','b'],False)
        with self.assertRaises(AssertionError):native_outcomes(stdout,['a','b'],True)

if __name__=='__main__':unittest.main()
