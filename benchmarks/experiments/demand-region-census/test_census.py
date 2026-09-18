from copy import deepcopy
import unittest
from census import analyze


def fixtures():
    f = dict(name='ordinary', frame_size=16, registers=2, operations=['opaque']*6,
        interpreted=[0, 0, 2, 1, 0, 0], jit_blocks=[3, 0, 0, 0, 0, 0],
        jit_block_ends=[2, 0, 4, 0, 6, 0], jit_tree_blocks=[0]*6,
        jit_tree_block_ends=[0]*6, jit_scalar_hits=[0]*6)
    s = dict(name='scalar', frame_size=0, registers=0, operations=['opaque']*2,
        interpreted=[0]*2, jit_blocks=[0]*2, jit_block_ends=[0]*2,
        jit_tree_blocks=[0]*2, jit_tree_block_ends=[0]*2, jit_scalar_hits=[2, 2])
    regions = [dict(function=0, name='ordinary', offset=i*8, end=i*8+8,
                    pc=i*2, pc_end=i*2+2, kind='resumable_region') for i in range(3)]
    regions.append(dict(function=1, name='scalar', offset=24, end=32,
                        pc=None, pc_end=None, kind='scalar_leaf'))
    mapping = dict(schema_version=1, architecture='aarch64', byte_order='little',
                   profiled=True, resumable_calls=True, native_call_stubs=False,
                   code_bytes=32, ranges=regions)
    return dict(functions=[f,s]), mapping


class Census(unittest.TestCase):
    def test_complete_disjoint_partition_and_scalar_accounting(self):
        p,m = fixtures()
        r = analyze(p,m)
        t = r['totals']
        for key in ['charged','interpreted_only','no_recorded_work']:
            self.assertEqual(t[key+'_regions'],1)
            self.assertEqual(t[key+'_bytes'],8)
        self.assertEqual(t['ordinary_charged_operations'],6)
        self.assertEqual(r['logical_counts'], dict(native=10, interpreted=3, scalar=4, total=13))

    def test_zero_charged_entries_do_not_hide_interpreter_fallback(self):
        p,m = fixtures()
        p['functions'][0]['interpreted'][4]=9
        t=analyze(p,m)['totals']
        self.assertEqual(t['interpreted_only_regions'],2)
        self.assertNotIn('no_recorded_work_regions',t)

    def test_missing_duplicate_overlapping_and_out_of_range_regions_reject(self):
        p,m=fixtures()
        for mutation in [lambda v:v['ranges'].pop(),
                         lambda v:v['ranges'].__setitem__(1,deepcopy(v['ranges'][0])),
                         lambda v:v['ranges'][1].update(pc=1),
                         lambda v:v['ranges'][0].update(pc_end=7),
                         lambda v:v['ranges'][1].update(offset=4)]:
            bad=deepcopy(m);mutation(bad)
            with self.assertRaises(AssertionError):analyze(p,bad)

    def test_profile_shapes_endpoints_and_counters_reject(self):
        p,m=fixtures()
        for mutation in [lambda f:f['jit_blocks'].pop(),
                         lambda f:f['jit_block_ends'].__setitem__(0,0),
                         lambda f:f['jit_blocks'].__setitem__(0,-1),
                         lambda f:f['jit_tree_blocks'].__setitem__(0,1),
                         lambda f:f.update(name='different')]:
            bad=deepcopy(p);mutation(bad['functions'][0])
            with self.assertRaises(AssertionError):analyze(bad,m)

    def test_zero_scalar_counts_keep_emitted_cold_body(self):
        p,m=fixtures();p['functions'][1]['jit_scalar_hits']=[0,0]
        t=analyze(p,m)['totals']
        self.assertEqual(t['scalar_no_hits_bytes'],8)
        self.assertEqual(t['all_bytes'],32)

    def test_transition_regions_use_their_own_counter(self):
        p,m=fixtures();m['ranges'][0].update(kind='resumable_call',pc_end=1)
        p['functions'][0]['jit_block_ends'][0]=1
        r=analyze(p,m)
        self.assertEqual(r['totals']['ordinary_charged_operations'],3)
        self.assertEqual(r['regions'][0]['kind'],'resumable_call')


if __name__=='__main__':unittest.main()
