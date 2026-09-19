import copy,math,unittest
from accounting import CUSTOM,MODES,STATES,schedule,account,ratios

def fixture():
    rows=schedule([dict(cycle=c,state=s,label=str(s),source=str(s).encode()) for c,s in STATES])
    for r in rows:
        r['wall_seconds']={'candidate':.8,'native':.9,'anchor':1.2}.get(r['mode'],1.)
        r['cpu_seconds']={'candidate':.7,'native':.9,'anchor':1.1}.get(r['mode'],1.)
    return rows,{}

class Accounting(unittest.TestCase):
    def test_three_cycles_keep_transitions_and_balanced_custom_positions(self):
        rows,_=fixture();self.assertEqual(len(rows),154)
        for mode in MODES:
            chosen=[r for r in rows if r['mode']==mode];self.assertEqual([(r['cycle'],r['state']) for r in chosen],STATES)
            self.assertTrue(all(a['source_sha256']!=b['source_sha256'] for a,b in zip(chosen,chosen[1:])))
        for mode in CUSTOM:
            positions=[]
            for c in range(3):
                for s in range(1,6):
                    group=[r['mode'] for r in rows if r['cycle']==c and r['state']==s]
                    self.assertEqual(set(group[:1]+group[-2:-1]),{'native','native_lines'});self.assertEqual(group[-1],'check')
                    positions.append(group.index(mode))
            self.assertLessEqual(max(positions.count(p) for p in range(1,5))-min(positions.count(p) for p in range(1,5)),1)
    def test_all_fifteen_pairs_are_present(self):
        rows,sessions=fixture();result=ratios(rows,sessions,'token')
        self.assertEqual(result['edited_pairs'],15);self.assertEqual(result['aa_pairs'],15)
        self.assertEqual([(r['cycle'],r['state']) for r in result['pairs']],[(c,s) for c in range(3) for s in range(1,6)])
        for c in range(3):
            changed=copy.deepcopy(rows);next(r for r in changed if r['mode']=='candidate' and r['state']==5 and r['cycle']==c)['wall_seconds']=1.3
            pair=next(r for r in ratios(changed,sessions,'token')['pairs'] if r['cycle']==c and r['state']==5)
            self.assertEqual(pair['wall_seconds']['candidate_baseline'],1.3)
    def test_complete_ordinary_process_costs_are_preserved_without_mutation(self):
        rows,sessions=fixture();original=copy.deepcopy(rows);charged,overheads=account(rows,sessions)
        self.assertEqual(rows,original);self.assertEqual(overheads,{})
        for r in charged:
            for key in ['wall_seconds','cpu_seconds']:self.assertEqual(r['accounted_'+key],r[key])
    def test_sessions_cannot_be_silently_excluded_from_costs(self):
        rows,_=fixture()
        with self.assertRaises(AssertionError):account(rows,{'candidate':{}})
        rows[0]['launch']={'template_session':{}}
        with self.assertRaises(AssertionError):account(rows,{})
    def test_original_wrong_and_restored_costs_do_not_enter_edit_gate(self):
        rows,sessions=fixture();expected=ratios(rows,sessions,'token')
        for r in rows:
            if r['state']<=0:r['wall_seconds']*=1000;r['cpu_seconds']*=.001
        actual=ratios(rows,sessions,'token');self.assertEqual(actual['medians'],expected['medians'])
        self.assertNotEqual(actual['full_history_totals'],expected['full_history_totals'])
    def test_noise_uses_three_cycle_edit_medians_and_reports_individual_outliers(self):
        rows,sessions=fixture();next(r for r in rows if r['mode']=='duplicate' and r['state']==3 and r['cycle']==0)['wall_seconds']=1.3
        first=ratios(rows,sessions,'token');self.assertTrue(first['gate_passed']);self.assertEqual(first['medians']['wall_seconds']['aa_envelope'],0)
        self.assertAlmostEqual(first['medians']['wall_seconds']['worst_individual_aa'],.3)
        next(r for r in rows if r['mode']=='duplicate' and r['state']==3 and r['cycle']==1)['wall_seconds']=1.3
        second=ratios(rows,sessions,'token');self.assertFalse(second['gate_passed']);self.assertEqual(second['verdict'],'unmeasurable')
        self.assertAlmostEqual(second['medians']['wall_seconds']['aa_envelope'],.3)
    def test_entire_command_history_remains_visible(self):
        rows,sessions=fixture();result=ratios(rows,sessions,'token')
        self.assertAlmostEqual(result['full_history_totals']['candidate']['wall_seconds'],22*.8)
        self.assertAlmostEqual(result['medians']['wall_seconds']['candidate_anchor'],.8/1.2)
    def test_missing_work_source_mismatch_and_nonfinite_costs_fail_closed(self):
        for change in [lambda r:r.pop(),lambda r:r[0].update(source_sha256='other'),
                lambda r:r[0].update(wall_seconds=math.nan),lambda r:r[0].update(cpu_seconds=0)]:
            rows,sessions=fixture();change(rows)
            with self.assertRaises(AssertionError):ratios(rows,sessions,'token')
    def test_duplicate_states_cannot_hide_missing_work_in_any_arm(self):
        for mode in MODES:
            rows,sessions=fixture();selected=[i for i,r in enumerate(rows) if r['mode']==mode]
            rows[selected[1]]=copy.deepcopy(rows[selected[0]])
            with self.assertRaises(AssertionError):ratios(rows,sessions,'token')
    def test_token_retains_anchor_requirement_and_adopted_cpu_ceiling(self):
        rows,sessions=fixture()
        for r in rows:
            if r['mode']=='anchor':r['wall_seconds']=.85
        self.assertFalse(ratios(rows,sessions,'token')['gate_passed'])
        rows,sessions=fixture()
        for r in rows:
            if r['mode']=='candidate':r['cpu_seconds']=1.001
        self.assertFalse(ratios(rows,sessions,'token')['gate_passed'])
    def test_held_out_wall_and_cpu_guards_include_both_controls_and_noise(self):
        for case in ['folded','pgrust']:
            for change in ['anchor-wall','candidate-cpu']:
                rows,sessions=fixture();self.assertTrue(ratios(rows,sessions,case)['gate_passed'])
                for r in rows:
                    if change=='anchor-wall' and r['mode']=='anchor':r['wall_seconds']=.7
                    if change=='candidate-cpu' and r['mode']=='candidate':r['cpu_seconds']=1.051
                self.assertFalse(ratios(rows,sessions,case)['gate_passed'])
    def test_native_line_tables_and_check_costs_are_retained(self):
        rows,sessions=fixture();result=ratios(rows,sessions,'token')
        self.assertEqual(set(result['full_history_totals']),set(MODES));self.assertEqual(result['full_history_totals']['check']['wall_seconds'],22)
        self.assertIn('candidate_native_lines',result['medians']['wall_seconds'])
        with self.assertRaises(AssertionError):ratios(rows,sessions,'unknown')

if __name__=='__main__':unittest.main()
