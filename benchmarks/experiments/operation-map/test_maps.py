import copy
import hashlib
import unittest
from pathlib import Path
import sys
from maps import validate, locate

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from summarize_owned_sample import runtime_options


def fixture():
    code = bytes(range(16))
    common = dict(schema_version=1, pid=42, arena_base=4096, code_bytes=len(code),
                  profiled=False, persistent_registers=True, resumable_calls=True)
    region = dict(common, architecture='aarch64', byte_order='little', native_call_stubs=False,
        ranges=[dict(offset=0, end=16, function=0, name='f', kind='resumable_region', pc=0, pc_end=2)])
    operation = dict(common, complete=True, reconstructed_bytes_match=True,
        code_sha256=hashlib.sha256(code).hexdigest(), spans=4, functions=[dict(
            function=0, name='f', offset=0, end=16, assertion_base=0, assertion_count=0,
            spans=[dict(offset=0, end=4, region_pc=0, pc=None, kind='entry'),
                   dict(offset=4, end=4, region_pc=0, pc=0, kind='operation'),
                   dict(offset=4, end=12, region_pc=0, pc=1, kind='operation'),
                   dict(offset=12, end=16, region_pc=0, pc=None, kind='fault_tail')])])
    profile = dict(functions=[dict(name='f', operations=['Imm { dst: 0, value: 1 }',
        'Store { address: 1, src: 0, size: 8 }'], jit_block_ends=[2, 0])])
    return operation, region, code, profile, 42


class Maps(unittest.TestCase):
    def test_zero_word_pcs_are_preserved_but_never_steal_a_sample_address(self):
        index = validate(*fixture())
        self.assertEqual(index['mapped_pcs'], 2)
        self.assertEqual(index['spans'], 4)
        self.assertEqual(index['static_words'], {'entry': 1, 'operation:Imm': 0, 'operation:Store': 2, 'fault_tail': 1})
        self.assertEqual(locate(index, 0)['label'], 'entry')
        self.assertEqual(locate(index, 4)['pc'], 1)
        self.assertEqual(locate(index, 8)['pc'], 1)
        self.assertEqual(locate(index, 12)['label'], 'fault_tail')
        for offset in [-4, 3, 16]:
            with self.assertRaises(AssertionError): locate(index, offset)

    def test_bytes_identity_boundaries_and_pc_coverage_must_all_match(self):
        for change in range(10):
            values = list(copy.deepcopy(fixture()))
            op, region, _, profile, _ = values
            rows = op['functions'][0]['spans']
            if change == 0: op['pid'] += 1
            elif change == 1: values[2] = b'X' + values[2][1:]
            elif change == 2: rows[1]['end'] = 8
            elif change == 3: rows[2]['pc'] = 0
            elif change == 4: rows[3]['region_pc'] = 1
            elif change == 5: rows.pop(1)
            elif change == 6: profile['functions'][0]['jit_block_ends'][0] = 1
            elif change == 7: op['complete'] = False
            elif change == 8: op['resumable_calls'] = False
            elif change == 9: rows[2]['kind'] = 'transition'
            with self.assertRaises((AssertionError, KeyError)):
                validate(*values)

    def test_empty_map_and_nonempty_prefix_disagree_explicitly(self):
        operation, regions, _, profile, pid = fixture()
        for value in [operation, regions]: value.update(arena_base=0, code_bytes=0)
        operation.update(functions=[], spans=0, code_sha256=hashlib.sha256(b'').hexdigest())
        regions['ranges'] = []
        self.assertEqual(validate(operation, regions, b'', profile, pid)['mapped_pcs'], 0)
        operation['code_bytes'] = 4
        with self.assertRaises(AssertionError): validate(operation, regions, b'', profile, pid)


class SampleOptions(unittest.TestCase):
    def test_operation_map_flag_is_bound_to_recorded_commands_and_compatible_modes(self):
        plan = dict(jit_operation_map=True, dump_code=True)
        self.assertTrue(runtime_options(plan, [['--jit-operation-map']])['jit_operation_map'])
        for changed, command in [(plan, []), ({}, ['--jit-operation-map']),
                (dict(plan, dump_code=False), ['--jit-operation-map']),
                (dict(plan, jit_native_calls=True), ['--jit-operation-map', '--jit-native-calls']),
                (dict(plan, jit_operation_map=1), ['--jit-operation-map'])]:
            with self.assertRaises(RuntimeError): runtime_options(changed, [command])

    def test_legacy_sample_options_remain_compatible_without_a_map(self):
        self.assertEqual(runtime_options({}, [[]]), dict(jit_native_calls=False,
            jit_native_call_stubs=False, jit_persistent_registers=False, jit_resumable_calls=False))


if __name__ == '__main__': unittest.main()
