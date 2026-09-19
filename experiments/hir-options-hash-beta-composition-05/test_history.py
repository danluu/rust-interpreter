"""Pure adversarial three-controller association controls; no artifact access."""
import copy
import unittest

import history


class ThreeHistoryControls(unittest.TestCase):
    def test_failed_dispatch_keeps_actual_failed_status_and_error(self):
        row=dict(status='failed',returncode=1,expected=[0],error="AssertionError('unexpected compiler-stage return code')")
        history.child_outcome(row,failed_support=True)
        for change in [dict(status='finished'),dict(returncode=0),dict(expected=[1]),dict(error='other')]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                history.child_outcome(row|change,failed_support=True)
        with self.assertRaises(ValueError):history.child_outcome(row,failed_support=False)

    def fixture(self):
        groups = [[dict(path='/evidence/'+owner+'/'+str(i), pid=100+base+i,
                        command=['compiler',owner,str(i)],sha256=hex(base+i)) for i in range(size)]
                  for owner,base,size in [('first',0,16),('middle',16,7),('last',23,3)]]
        first,middle,last = groups
        compiled=dict(saved_children=22,saved_actual_children=23,actual_continuation_children=3,
                      command_history=copy.deepcopy([*first,*middle[:6],*last]),
                      actual_command_history=copy.deepcopy([*first,*middle,*last]),
                      failed_support_attempt=copy.deepcopy(middle[6]))
        return groups,compiled

    def test_complete_actual_failure_is_retained_but_not_in_logical_success(self):
        groups,compiled=self.fixture();successful,complete=history.joined_commands(*groups,compiled)
        self.assertEqual((len(successful),len(complete)),(25,26))
        self.assertEqual(complete[22],groups[1][6]);self.assertNotIn(groups[1][6],successful)
        self.assertEqual(successful[22:],groups[2])

    def test_omitting_or_relabeling_failed_support_is_rejected(self):
        for field in ['actual_command_history','command_history']:
            groups,compiled=self.fixture()
            if field=='actual_command_history':compiled[field].pop(22)
            else:compiled[field].insert(22,groups[1][6])
            with self.subTest(field=field),self.assertRaises(ValueError):history.joined_commands(*groups,compiled)

    def test_reordering_or_substituting_actual_receipt_rejects(self):
        for change in ['order','command','hash','pid']:
            groups,compiled=self.fixture()
            if change=='order':compiled['actual_command_history'][0:2]=list(reversed(compiled['actual_command_history'][:2]))
            else:compiled['actual_command_history'][23][{'command':'command','hash':'sha256','pid':'pid'}[change]]='different'
            with self.subTest(change=change),self.assertRaises(ValueError):history.joined_commands(*groups,compiled)

    def test_wrong_failure_binding_or_saved_counts_reject(self):
        for field,value in [('failed_support_attempt',{}),('saved_children',23),('saved_actual_children',22),('actual_continuation_children',9)]:
            groups,compiled=self.fixture();compiled[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):history.joined_commands(*groups,compiled)

    def test_reusing_prior_native_probe_as_new_work_rejects(self):
        groups,compiled=self.fixture();groups[2][0]=copy.deepcopy(groups[1][1])
        compiled['command_history']=[*groups[0],*groups[1][:6],*groups[2]]
        compiled['actual_command_history']=[*groups[0],*groups[1],*groups[2]]
        with self.assertRaises(ValueError):history.joined_commands(*groups,compiled)

    def test_missing_or_extra_owning_history_rows_reject(self):
        for group in range(3):
            groups,compiled=self.fixture();groups[group].pop()
            with self.subTest(group=group),self.assertRaises(ValueError):history.joined_commands(*groups,compiled)


if __name__=='__main__':unittest.main()
