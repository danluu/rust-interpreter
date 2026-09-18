import copy,math,unittest
from pathlib import Path
from benchmark import MODES,custom_command,ratios,schedule

class ComparisonTests(unittest.TestCase):
    def rows(self,candidate=.95,duplicate=1.01):
        rows=[]
        for cycle,state in [(c,s) for c in range(3) for s in [0,-1,1,2,3,4,5]]+[(3,0)]:
            for mode in MODES:
                value={'native':1.2,'baseline':1.,'duplicate':duplicate,'candidate':candidate}[mode]
                rows.append(dict(cycle=cycle,state=state,mode=mode,source_sha256=str(state),wall_seconds=value,cpu_seconds=value))
        return rows
    def test_matching_edited_pairs_and_unchanged_guard(self):
        result=ratios(self.rows());self.assertTrue(result['gate_passed']);self.assertEqual(result['edited_pairs'],15)
        self.assertAlmostEqual(result['medians']['wall_seconds']['candidate_baseline'],.95)
        self.assertAlmostEqual(result['medians']['cpu_seconds']['with_noise_margin'],.96)
        self.assertFalse(ratios(self.rows(1.04,1.02))['gate_passed'])
    def test_original_wrong_and_restored_are_not_latency_pairs(self):
        rows=self.rows();expected=ratios(rows)
        for row in rows:
            if row['state']<=0:row.update(wall_seconds=1e6,cpu_seconds=1e6)
        self.assertEqual(ratios(rows),expected)
    def test_missing_duplicate_or_mismatched_source_cannot_pass(self):
        for change in [lambda r:r.pop(),lambda r:r.append(r[0]),lambda r:r[2].update(mode='baseline'),lambda r:r[2].update(source_sha256='other')]:
            rows=self.rows();change(rows)
            with self.assertRaises(AssertionError):ratios(rows)
    def test_invalid_elapsed_or_cpu_rejected(self):
        for key in ['wall_seconds','cpu_seconds']:
            for value in [0.,-1.,math.inf,math.nan]:
                rows=self.rows();rows[40][key]=value
                with self.assertRaises(AssertionError):ratios(rows)
    def test_scalar_option_only_on_candidate_and_fresh_namespaces(self):
        template=['python','launcher','--tool-key','old','--suite-report','old-suite','--cache-namespace','old-cache']
        for mode in MODES[1:]:
            result=custom_command(template,'new',mode,Path('/test/fresh'),9)
            self.assertEqual('--jit-scalar-calls' in result,mode=='candidate')
            self.assertEqual(result[result.index('--tool-key')+1],'new')
            self.assertEqual(result[result.index('--cache-namespace')+1],'fresh:'+mode)
        self.assertEqual(template[3],'old')
        with self.assertRaises(AssertionError):custom_command(template+['--jit-scalar-calls'],'x','baseline',Path('/test'),0)
    def test_all_states_get_four_distinct_rotated_modes(self):
        states=[dict(cycle=c,state=s,label=str(s),source=str(s).encode()) for c in range(3) for s in [0,-1,1,2,3,4,5]]+[dict(cycle=3,state=0,label='restored',source=b'0')]
        rows=schedule(states);self.assertEqual(len(rows),88)
        for i in range(22):self.assertEqual({r['mode'] for r in rows[i*4:i*4+4]},set(MODES))
        for position in range(4):self.assertEqual({rows[i*4+position]['mode'] for i in range(4)},set(MODES))
if __name__=='__main__':unittest.main()
