import copy
import unittest
import prefix as p

class PrefixTests(unittest.TestCase):
    def evidence(self):
        records=[dict(case=c,command=p.command_for(c),returncode=0 if i<4 else 1,
            **({'summary_sha256':'digest'} if i<4 else {})) for i,c in enumerate(p.protocol.CASES)]
        cases=[dict(case=c,status='passed',source_restored=True,gate_passed=True,
            commands=154 if i<3 else 132) for i,c in enumerate(p.PREFIX)]
        return records,cases
    def test_exact_four_case_prefix_is_accepted(self):
        rows,cases=self.evidence();self.assertTrue(p.validate_prefix(rows,cases,True))
    def test_missing_extra_or_reordered_cases_are_rejected(self):
        rows,cases=self.evidence()
        for wrong in [cases[:-1],cases+cases[-1:],list(reversed(cases))]:
            with self.assertRaises(AssertionError):p.validate_prefix(rows,wrong,True)
        rows[0],rows[1]=rows[1],rows[0]
        with self.assertRaises(AssertionError):p.validate_prefix(rows,cases,True)
    def test_failed_gate_incomplete_commands_or_dirty_source_are_rejected(self):
        for field,value in [('gate_passed',False),('status','failed'),('commands',153),('source_restored',False)]:
            rows,cases=self.evidence();cases[0][field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):p.validate_prefix(rows,cases,True)
    def test_driver_returns_and_summary_presence_must_match(self):
        for index in range(5):
            rows,cases=self.evidence();rows[index]['returncode']=1-rows[index]['returncode']
            with self.assertRaises(AssertionError):p.validate_prefix(rows,cases,True)
        rows,cases=self.evidence();rows[-1]['summary_sha256']='unexpected'
        with self.assertRaises(AssertionError):p.validate_prefix(rows,cases,True)
    def test_driver_arguments_cannot_be_substituted(self):
        rows,cases=self.evidence();rows[0]['command'][-1]='different-build'
        with self.assertRaises(AssertionError):p.validate_prefix(rows,cases,True)
    def test_started_nushell_cannot_be_repeated(self):
        rows,cases=self.evidence()
        with self.assertRaises(AssertionError):p.validate_prefix(rows,cases,False)

if __name__=='__main__':unittest.main()
