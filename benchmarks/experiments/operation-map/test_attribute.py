import unittest
from attribute import assign, detail


def index():
    rows = [dict(offset=0, end=4, function=0, region_pc=0, pc=None, kind='entry', label='entry'),
        dict(offset=4, end=12, function=0, region_pc=0, pc=1, kind='operation', label='operation:Store'),
        dict(offset=12, end=16, function=0, region_pc=0, pc=None, kind='fault_tail', label='fault_tail')]
    return dict(rows=rows, starts=[0, 4, 12])


class Attribution(unittest.TestCase):
    def test_ambiguous_truncated_and_outside_addresses_remain_unassigned(self):
        frames = [(2, '??? (in <unknown binary>) [0x1004, 0x1008]', ()),
                  (3, '??? (in <unknown binary>) [0x1004, 0x100c]', ()),
                  (5, '??? (in <unknown binary>) [0x1004 ...]', ()),
                  (7, '??? (in <unknown binary>) [0x2000]', ())]
        labels, sites, unresolved = assign(index(), 4096, frames)
        self.assertEqual(labels, {'operation:Store': 2})
        self.assertEqual(sum(sites.values()), 2)
        self.assertEqual(sum(r['count'] for r in unresolved), 15)
        self.assertEqual([r['reason'] for r in unresolved],
                         ['multiple_operation_identities', 'incomplete_addresses', 'outside_published_word'])

    def test_host_self_pc_and_generated_ancestors_do_not_become_generated_self_time(self):
        labels, sites, unresolved = assign(index(), 4096,
            [(17, 'host_symbol [0x1004]', ('??? (in <unknown binary>) [0x1004]',)),
             (11, '??? (in <unknown binary>) [0x100c]', ())])
        self.assertEqual(labels, {'fault_tail': 11})
        self.assertEqual(sum(sites.values()), 11)
        self.assertFalse(unresolved)

    def test_operand_width_and_arithmetic_details_are_descriptive_only(self):
        profile = dict(functions=[dict(operations=[
            'Binary { dst: 0, overflow: 1, op: Add, a: 2, b: 3, bits: 64, signed: false }',
            'Store { address: 0, src: 1, size: 8 }'])])
        self.assertEqual(detail(dict(label='operation:Binary', function=0, pc=0), profile), 'operation:Binary/Add/64')
        self.assertEqual(detail(dict(label='operation:Store', function=0, pc=1), profile), 'operation:Store/8')
        self.assertEqual(detail(dict(label='flush', function=0, pc=None), profile), 'flush')


if __name__ == '__main__': unittest.main()
