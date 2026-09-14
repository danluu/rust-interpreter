import copy
import unittest
from accounting import analyze


def suite():
    return dict(status='passed',mode='prepared',failed=0,passed=3,workers=2,
        preparation_ns=1_000_000_000,seconds_before_report_write=8,
        tests=[dict(status='passed',worker=0,seconds=3,jit_compile_ns=2_000_000_000,jit_bytes=100,jit_compiled_functions=4),
               dict(status='passed',worker=1,seconds=5,jit_compile_ns=3_000_000_000,jit_bytes=80,jit_compiled_functions=3),
               dict(status='passed',worker=0,seconds=2,jit_compile_ns=1_000_000_000,jit_bytes=120,jit_compiled_functions=5)])


class Accounting(unittest.TestCase):
    def test_new_compile_durations_but_cumulative_code_sizes(self):
        result=analyze(suite(),10,9)
        self.assertEqual(result['compile_sum_seconds'],6)
        self.assertEqual(result['per_worker'][0]['code_bytes'],120)
        self.assertEqual(result['per_worker'][0]['compiled_functions'],5)

    def test_worker_overlap_is_not_reported_as_elapsed_saving(self):
        result=analyze(suite(),10,9)
        self.assertEqual(result['largest_worker_compile_seconds'],3)
        self.assertEqual(result['constructor_sum_seconds'],1)
        self.assertEqual(result['constructor_plus_compile_interval_sum_to_command'],0.7)
        self.assertNotIn('predicted_speedup',result)

    def test_invalid_or_decreasing_counters_are_rejected(self):
        for field,value in [('jit_compile_ns',-1),('jit_compile_ns',4_000_000_000),('worker',2),('jit_bytes',-1),('seconds',float('nan'))]:
            bad=copy.deepcopy(suite());bad['tests'][0][field]=value
            with self.assertRaises(AssertionError):analyze(bad,10,9)
        bad=suite();bad['tests'][2]['jit_bytes']=50
        with self.assertRaises(AssertionError):analyze(bad,10,9)


if __name__=='__main__':unittest.main()
