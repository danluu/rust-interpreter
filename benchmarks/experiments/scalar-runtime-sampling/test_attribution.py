import copy
import unittest
from attribute import assign
from native_observation import validate
from test_native_observation import fixture, Observations
from test_attribute import Attribution
from summarize_owned_sample import runtime_options


class CurrentAttribution(unittest.TestCase):
    def test_unprofiled_scalar_body_keeps_its_own_identity(self):
        args = fixture()
        args[0]['profiled'] = args[1]['profiled'] = False
        checked = validate(*args)
        labels, sites, unresolved = assign(checked, 4096, [
            (7, '??? (in <unknown binary>) [0x1000]', ()),
            (11, '??? (in <unknown binary>) [0x1004]', ()),
            (13, '??? (in <unknown binary>) [0x1000, 0x1004]', ())])
        self.assertEqual(labels, {'scalar_leaf': 7, 'operation:Imm': 11})
        self.assertEqual(sum(sites.values()), 18)
        self.assertEqual(unresolved[0]['reason'], 'multiple_operation_identities')
        self.assertEqual(unresolved[0]['count'], 13)

    def test_profile_counters_are_irrelevant_to_static_identity(self):
        args = fixture()
        before = validate(*args)
        profile = copy.deepcopy(args[3])
        for k in ['interpreted', 'jit_blocks', 'jit_tree_blocks', 'jit_scalar_hits']:
            profile['functions'][0][k] = [999, 888]
        self.assertEqual(validate(*args[:3], profile, args[4]), before)

    def test_scalar_option_must_match_recorded_command_and_resumable_mode(self):
        plan = dict(jit_resumable_calls=True, jit_scalar_calls=True)
        command = ['vm', '--jit-resumable-calls', '--jit-scalar-calls']
        self.assertTrue(runtime_options(plan, [command])['jit_scalar_calls'])
        for changed_plan, changed_command in [
                (dict(plan, jit_scalar_calls=False), command),
                (plan, command[:-1]),
                (dict(jit_scalar_calls=True), ['vm', '--jit-scalar-calls'])]:
            with self.assertRaises(RuntimeError):
                runtime_options(changed_plan, [changed_command])


if __name__ == '__main__':
    unittest.main()
