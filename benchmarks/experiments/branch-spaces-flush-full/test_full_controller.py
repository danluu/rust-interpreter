import unittest
from full import CASES,next_case


def result(case,passed=True):
    return dict(case=case,status='passed',source_restored=True,commands=154 if case in CASES[:3] else 132,gate_passed=passed)


class ControllerTests(unittest.TestCase):
    def test_all_five_are_required_in_order(self):
        completed=[]
        for case in CASES:
            self.assertEqual(next_case(completed),case);completed.append(result(case))
        self.assertIsNone(next_case(completed))
        with self.assertRaises(AssertionError):next_case([result('folded')])

    def test_failure_cancels_every_unstarted_case(self):
        for index in range(len(CASES)):
            completed=[result(case) for case in CASES[:index]]+[result(CASES[index],False)]
            self.assertIsNone(next_case(completed))
            if index+1<len(CASES):
                with self.assertRaises(AssertionError):next_case(completed+[result(CASES[index+1])])

    def test_incomplete_or_unrestored_history_cannot_advance(self):
        for field,value in [('commands',153),('status','failed'),('source_restored',False)]:
            broken=result('token');broken[field]=value
            with self.assertRaises(AssertionError):next_case([broken])
