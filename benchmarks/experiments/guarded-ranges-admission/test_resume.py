import copy
import unittest
from resume import CASES,ERROR,validate_prefix

def fixture():
    records=[dict(case=case,returncode=0,summary_sha256='hash') for case in CASES[:4]]
    records.append(dict(case='nushell',returncode=1,stderr_sha256=ERROR))
    summaries=[dict(case=case,status='passed',commands=154 if case in CASES[:3] else 132,
        source_restored=True,gate_passed=True) for case in CASES[:4]]
    return [records,summaries,dict(status='finished',returncode=1),False,False,ERROR]

class ResumeTests(unittest.TestCase):
    def test_exact_complete_prefix_can_resume_only_unstarted_case(self):
        self.assertTrue(validate_prefix(*fixture()))

    def test_any_prior_failed_gate_or_incomplete_case_rejects(self):
        for field,value in [('gate_passed',False),('commands',153),('status','failed'),('source_restored',False)]:
            args=fixture();args[1][0][field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):validate_prefix(*args)

    def test_existing_nushell_work_or_result_rejects_retry(self):
        for index in [3,4]:
            args=fixture();args[index]=True
            with self.assertRaises(AssertionError):validate_prefix(*args)

    def test_different_failure_or_live_controller_rejects(self):
        for change in ['error','live','success','prior_failure','nu_summary']:
            args=fixture()
            if change=='error':args[5]='different'
            elif change=='live':args[2]['status']='running'
            elif change=='success':args[2]['returncode']=0
            elif change=='prior_failure':args[0][0]['returncode']=1
            else:args[0][-1]['summary_sha256']='already completed'
            with self.subTest(change=change),self.assertRaises(AssertionError):validate_prefix(*args)

    def test_reordered_or_missing_history_rejects(self):
        for index in [0,1]:
            for change in ['reorder','remove']:
                args=fixture()
                if change=='reorder':args[index][0],args[index][1]=args[index][1],args[index][0]
                else:args[index].pop()
                with self.subTest(index=index,change=change),self.assertRaises(AssertionError):validate_prefix(*args)

if __name__=='__main__':unittest.main()
