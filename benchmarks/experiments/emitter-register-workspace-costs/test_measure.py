import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
from measure import BASELINE,measure


def fixture():
    tests=[dict(name=name,status='passed',worker=worker,seconds=duration,
        jit_compile_ns=compile_ns,jit_bytes=code,jit_compiled_functions=code//10,
        jit_declined_functions=0) for name,worker,duration,compile_ns,code in [
            ('a',0,.4,200_000_000,100),('b',1,.6,100_000_000,80),('c',0,.3,50_000_000,120)]]
    suite=dict(schema_version=1,status='passed',mode='prepared',tests=tests,passed=3,failed=0,
        workers=2,requested_workers=2,seconds_before_report_write=.8,preparation_ns=30_000_000,
        jit_code_limit_bytes=1000)
    launch=dict(tool_key=BASELINE,isolated_batch='prepared',jit_scalar_calls=True,
        jit_resumable_calls=True,jit_persistent_registers=True,jit_indirect_calls=False,
        jit_native_calls=False,jit_native_call_stubs=False,suite_workers=2,suite_workers_requested=2,execution_seconds=1.)
    row=dict(mode='baseline',cycle=0,state=1,returncode=0,source_sha256='new',previous_source_sha256='old',
        launch=launch,seconds=2.,outcomes=[[t['name'],'passed'] for t in tests])
    return row,suite


class Measurements(unittest.TestCase):
    def test_worker_intervals_overlap_and_cumulative_counters_are_not_summed(self):
        result=measure(*fixture())
        self.assertAlmostEqual(result['compile_interval_sum_seconds'],.35)
        self.assertEqual(result['largest_worker_compile_seconds'],.25)
        self.assertEqual(result['retained_code_bytes'],200)
        self.assertEqual(result['retained_function_owners'],20)
        self.assertEqual(result['constructor_interval_sum_seconds'],.03)

    def test_zero_new_compilation_and_one_worker_are_valid(self):
        row,suite=fixture();suite['tests']=suite['tests'][:1]
        suite.update(passed=1,workers=1);row['launch']['suite_workers']=1
        row['outcomes']=row['outcomes'][:1];suite['tests'][0]['jit_compile_ns']=0
        row['wall_seconds']=row.pop('seconds')
        self.assertEqual(measure(row,suite)['compile_interval_sum_seconds'],0)

    def test_original_single_worker_request_is_retained_and_must_match_launcher(self):
        row,suite=fixture();suite['tests']=suite['tests'][:1]
        suite.update(passed=1,workers=1,requested_workers=1)
        row['launch'].update(suite_workers=1,suite_workers_requested=1)
        row['outcomes']=row['outcomes'][:1]
        self.assertEqual(measure(row,suite)['tests'],1)
        row['launch']['suite_workers_requested']=2
        with self.assertRaises(AssertionError):measure(row,suite)

    def test_invalid_numeric_values_and_timer_domains_are_rejected(self):
        for field,value in [('jit_compile_ns',-1),('jit_compile_ns',True),('jit_compile_ns',.2),
                            ('jit_bytes',float('inf')),('seconds',float('nan')),('seconds',True),
                            ('jit_compile_ns',500_000_000)]:
            row,suite=fixture();suite['tests'][0][field]=value
            with self.assertRaises(AssertionError):measure(row,suite)

    def test_invalid_workers_and_decreasing_owner_counters_are_rejected(self):
        for field,value in [('worker',2),('worker',True),('jit_bytes',90),('jit_compiled_functions',9),('seconds',.9)]:
            row,suite=fixture();suite['tests'][2][field]=value
            with self.assertRaises(AssertionError):measure(row,suite)

    def test_mixed_tools_modes_unchanged_sources_and_failed_outcomes_are_rejected(self):
        for mutation in [lambda r:r.update(mode='candidate'),lambda r:r.update(state=0),
                         lambda r:r.update(returncode=1),lambda r:r.update(previous_source_sha256='new'),
                         lambda r:r['launch'].update(tool_key='other'),
                         lambda r:r['launch'].update(jit_indirect_calls=True),
                         lambda r:r['launch'].update(isolated_batch='fresh'),
                         lambda r:r['outcomes'][0].__setitem__(1,'failed')]:
            row,suite=fixture();mutation(row)
            with self.assertRaises(AssertionError):measure(row,suite)

    def test_duplicate_names_and_inconsistent_scope_are_rejected(self):
        for mutation in [lambda s:s.update(passed=2),lambda s:s.update(workers=3),
                         lambda s:s['tests'][1].update(name='a'),
                         lambda s:s.update(seconds_before_report_write=2.),
                         lambda s:s.update(jit_code_limit_bytes=100)]:
            row,suite=fixture();mutation(suite)
            with self.assertRaises(AssertionError):measure(row,suite)


class CandidateMeasurements(unittest.TestCase):
    def test_candidate_identity_preserves_independent_owner_preparation(self):
        row,suite=fixture();row['mode']='candidate';row['launch']['tool_key']='new-tool'
        result=measure(row,suite,'candidate','new-tool')
        self.assertEqual(result['mode'],'candidate')
        self.assertEqual(result['store_preparation_seconds'],0)
        self.assertAlmostEqual(result['compile_interval_sum_seconds'],.35)
        with self.assertRaises(AssertionError):measure(row,suite,'candidate',BASELINE)

    def test_duplicate_control_keeps_its_identity(self):
        row,suite=fixture();row['mode']='duplicate'
        result=measure(row,suite,'duplicate',BASELINE)
        self.assertEqual(result['mode'],'duplicate')
        self.assertEqual(result['retained_code_bytes'],200)

    def test_no_arm_can_claim_template_sharing(self):
        for mode in ['baseline','duplicate','candidate']:
            row,suite=fixture();row['mode']=mode;row['launch']['jit_shared_templates']=True
            with self.assertRaises(AssertionError):measure(row,suite,mode,BASELINE)
            row['launch']['jit_shared_templates']=False
            suite['shared_templates']={'requested':True,'active':True}
            with self.assertRaises(RuntimeError):measure(row,suite,mode,BASELINE)

if __name__=='__main__':unittest.main()
