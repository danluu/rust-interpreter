from collections import Counter, defaultdict
import copy
import unittest
import analyze


class JoinTests(unittest.TestCase):
    def fixture(self):
        function = dict(name='duplicate', operations=['Call { ignored debug operands }', 'Return'],
            jit_blocks=[7, 7], jit_block_ends=[1, 2], interpreted=[0, 0], frame_size=8, registers=2)
        profile = dict(functions=[function, copy.deepcopy(function)])
        report = dict(functions=[dict(function=i, name='duplicate', calls=[dict(pc=0, callee=1-i)]) for i in range(2)])
        return report, profile

    def test_identity_uses_typed_ids_and_requires_every_executed_call(self):
        report, profile = self.fixture()
        calls = analyze.call_index(report, profile)
        self.assertEqual(calls[0, 0], dict(callee=1, hits=7))
        self.assertEqual(calls[1, 0], dict(callee=0, hits=7))
        for change in ['missing', 'duplicate', 'bad_target', 'name', 'end']:
            r, p = copy.deepcopy((report, profile))
            if change == 'missing': r['functions'][1]['calls'] = []
            if change == 'duplicate': r['functions'].append(r['functions'][0])
            if change == 'bad_target': r['functions'][0]['calls'][0]['callee'] = 2
            if change == 'name': r['functions'][0]['name'] = 'wrong'
            if change == 'end': p['functions'][0]['jit_block_ends'][0] = 2
            with self.subTest(change=change), self.assertRaises(AssertionError): analyze.call_index(r, p)

    def test_pc_partition_rejects_gaps_and_keeps_call_vs_return_ownership(self):
        spans = [dict(offset=0, end=8, region_pc=0, pc=0, kind='transition'),
                 dict(offset=8, end=12, region_pc=1, pc=1, kind='transition')]
        mapping = dict(arena_base=4096, functions=[dict(function=0, spans=spans)])
        fine = dict(spans=[dict(function=0, pc=0, operation='Call', kind='argument_copy', argument=0, offset=0, end=8),
                          dict(function=0, pc=1, operation='Return', kind='return_dispatch', argument=None, offset=8, end=12)])
        samples = [(3, '<unknown binary> 0x1000 0x1004', []), (2, '<unknown binary> 0x1008', [])]
        a, b, parts, generated = analyze.attribute({(0, 0): dict(callee=1)}, mapping, fine, samples)
        self.assertEqual(dict(a), {1: Counter(argument_copy=3)})
        self.assertEqual(dict(b), {0: Counter(return_dispatch=2)})
        self.assertEqual(generated, 5)
        self.assertEqual(sum(parts.values()), 5)
        for frame in ['<unknown binary> 0x100c', '<unknown binary> 0x1001', '<unknown binary> 0x1000 0x1008']:
            with self.assertRaises(AssertionError): analyze.attribute({(0, 0): dict(callee=1)}, mapping, fine, [(1, frame, [])])


if __name__ == '__main__': unittest.main()
