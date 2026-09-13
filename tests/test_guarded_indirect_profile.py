"""Count indirect native execution without mistaking dispatch for a hit."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from attribute_generated_sample import dump_options

spec = importlib.util.spec_from_file_location('guarded_profile',
    ROOT / 'benchmarks/experiments/guarded-indirect/profile.py')
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def function(interpreted, hits, ends):
    return dict(name='caller', operations=['Imm { .. }', 'CallIndirect { .. }', 'Return'],
        interpreted=interpreted, jit_blocks=hits, jit_block_ends=ends,
        jit_tree_blocks=[0, 0, 0], jit_tree_block_ends=[0, 0, 0])


class GuardedIndirectProfile(unittest.TestCase):
    def test_logical_intervals_and_exact_pc_mismatch(self):
        current = function([0, 1, 0], [4, 3, 4], [1, 2, 3])
        baseline = function([0, 4, 0], [4, 0, 4], [1, 0, 3])
        self.assertEqual(profile.logical_counts(current), [4, 4, 4])
        dump = {'ranges': [dict(function=0, pc=1, kind='resumable_indirect_call', offset=16, end=80)]}
        result = profile.indirect_counts({'functions': [current]}, {'functions': [baseline]}, dump)
        self.assertEqual((result['native_calls'], result['vm_calls'], result['published_thunks'], result['thunk_code_bytes']), (3, 1, 1, 64))
        # Same total, different PCs must fail.
        bad = copy.deepcopy(baseline)
        bad['interpreted'] = [1, 3, 0]
        with self.assertRaises(AssertionError):
            profile.indirect_counts({'functions': [current]}, {'functions': [bad]}, dump)

    def test_hits_need_published_single_operation_thunk(self):
        current = function([0, 1, 0], [4, 3, 4], [1, 2, 3])
        baseline = function([0, 4, 0], [4, 0, 4], [1, 0, 3])
        dispatch = dict(function=0, pc=1, kind='resumable_indirect_dispatch', offset=0, end=16)
        with self.assertRaises(AssertionError):
            profile.indirect_counts({'functions': [current]}, {'functions': [baseline]}, {'ranges': [dispatch]})
        # An emitted dispatch with no native hit is not a published specialization.
        result = profile.indirect_counts({'functions': [baseline]}, {'functions': [baseline]}, {'ranges': [dispatch]})
        self.assertEqual((result['native_calls'], result['vm_calls'], result['published_thunks']), (0, 4, 0))

    def test_overlapping_native_intervals_count_each_pc(self):
        f = function([1, 2, 3], [5, 7, 0], [3, 2, 0])
        self.assertEqual(profile.logical_counts(f), [6, 14, 8])
        f['jit_block_ends'][0] = 4
        with self.assertRaises(AssertionError):
            profile.logical_counts(f)

    def test_code_attribution_requires_resumable_mode(self):
        for kind in ['resumable_indirect_dispatch', 'resumable_indirect_call']:
            dump = dict(resumable_calls=True, ranges=[dict(kind=kind)])
            self.assertTrue(dump_options(dump, ['vm', '--jit-resumable-calls']))
            with self.assertRaises(RuntimeError):
                dump_options(dump, ['vm'])
            dump['resumable_calls'] = False
            with self.assertRaises(RuntimeError):
                dump_options(dump, ['vm'])


if __name__ == '__main__':
    unittest.main()
