import copy, math, unittest
from pathlib import Path
from benchmark import MODES, ROOT, custom_command, ratios, schedule, screen_states, validate_demand_outcome

class ComparisonTests(unittest.TestCase):
    def rows(self,candidate=.95,duplicate=1.01):
        result=[]
        for cycle,state in [(0,s) for s in [0,-1,1,2,3,4,5]]+[(1,0)]:
            for mode in MODES:
                value={'native':1.2,'baseline':1.,'duplicate':duplicate,'candidate':candidate,'anchor':1.1}[mode]
                result.append(dict(cycle=cycle,state=state,mode=mode,source_sha256=str(state),wall_seconds=value,cpu_seconds=value))
        return result
    def test_primary_requires_a_gain_beyond_variation_and_cpu_guard(self):
        result=ratios(self.rows());self.assertTrue(result['gate_passed']);self.assertEqual(result['edited_pairs'],5)
        self.assertAlmostEqual(result['medians']['wall_seconds']['candidate_baseline'],.95)
        self.assertFalse(ratios(self.rows(.995))['gate_passed'])
        rows=self.rows()
        for r in rows:
            if r['mode']=='candidate':r['cpu_seconds']=1.001
        self.assertFalse(ratios(rows)['gate_passed'])
    def test_noisy_failed_screen_is_unmeasurable_without_relabeling_a_pass(self):
        self.assertEqual(ratios(self.rows(.99,1.09))['verdict'],'unmeasurable')
        self.assertEqual(ratios(self.rows(.8,1.09))['verdict'],'passed')
        self.assertEqual(ratios(self.rows(.995,1.01))['verdict'],'failed')
    def test_original_wrong_and_restored_do_not_enter_ratios(self):
        rows=self.rows();expected=ratios(rows)
        for row in rows:
            if row['state']<=0:row.update(wall_seconds=1e6,cpu_seconds=1e6)
        self.assertEqual(ratios(rows),expected)
    def test_missing_duplicate_and_mismatched_sources_fail(self):
        for change in [lambda r:r.pop(),lambda r:r.append(r[0]),lambda r:r[2].update(mode='baseline'),lambda r:r[2].update(source_sha256='other')]:
            rows=self.rows();change(rows)
            with self.assertRaises(AssertionError):ratios(rows)
    def test_nonfinite_or_nonpositive_measurements_fail(self):
        for key in ['wall_seconds','cpu_seconds']:
            for value in [0.,-1.,math.inf,math.nan]:
                rows=self.rows();rows[10][key]=value
                with self.assertRaises(AssertionError):ratios(rows)
    def test_candidate_policy_and_scalar_composition_are_role_specific(self):
        template=['python','launcher','--tool-key','old','--suite-report','old-suite','--cache-namespace','old-cache']
        for mode in MODES[1:]:
            result=custom_command(template,'new',mode,Path('/test/fresh'),9)
            self.assertEqual('--jit-scalar-calls' in result,mode!='anchor')
            self.assertEqual('--jit-demand-regions-if-large' in result,mode=='candidate')
            self.assertNotIn('--jit-demand-regions',result)
            self.assertEqual(result[result.index('--cache-namespace')+1],'fresh:'+mode)
        self.assertEqual(template[3],'old')
        for flag in ['--jit-scalar-calls','--jit-demand-regions','--jit-demand-regions-if-large']:
            with self.assertRaises(AssertionError):custom_command(template+[flag],'x','baseline',Path('/test'),0)
    def test_schedule_rotates_all_five_modes_and_rejects_partial_history(self):
        states=[dict(cycle=c,state=s,label=str(s),source=str(s).encode()) for c,s in [(0,s) for s in [0,-1,1,2,3,4,5]]+[(1,0)]]
        rows=schedule(states);self.assertEqual(len(rows),40)
        for i in range(8):self.assertEqual({r['mode'] for r in rows[i*5:i*5+5]},set(MODES))
        for position in range(5):self.assertEqual({rows[i*5+position]['mode'] for i in range(5)},set(MODES))
        with self.assertRaises(AssertionError):schedule(states[:-1])
    def test_one_cycle_keeps_all_real_edits_and_restores_original_bytes(self):
        original=(ROOT/'.work/sources/pgrust/crates/backend/parser/gram_core/src/parse.rs').read_bytes()
        states=screen_states(original);self.assertEqual(len(states),8)
        self.assertEqual(states[0]['source'],original);self.assertEqual(states[-1]['source'],original)
        self.assertEqual(len({s['source'] for s in states}),7)
        self.assertEqual([s['state'] for s in states],[0,-1,1,2,3,4,5,0])
    def test_demand_receipts_distinguish_failed_outcomes_and_eager_arms(self):
        good=dict(status='passed',jit_demand=dict(plan_bytes=32,metadata_bytes=32))
        validate_demand_outcome(good,'candidate')
        for mode in MODES[1:]:validate_demand_outcome(dict(status='failed'),mode)
        for mode in ['baseline','duplicate','anchor']:
            validate_demand_outcome(dict(status='passed'),mode)
            with self.assertRaises(AssertionError):validate_demand_outcome(good,mode)
        for size in [0,-1,True,16*1024**2+1]:
            row=copy.deepcopy(good);row['jit_demand']['plan_bytes']=size
            with self.assertRaises(AssertionError):validate_demand_outcome(row,'candidate')
if __name__=='__main__':unittest.main()
