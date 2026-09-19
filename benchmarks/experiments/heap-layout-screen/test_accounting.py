import copy,math,unittest
from accounting import MODES,STATES,schedule,account,ratios

def fixture():
    states=[dict(cycle=c,state=s,label=str(s),source=str(s).encode()) for c,s in STATES]
    rows=schedule(states)
    for row in rows:
        row['wall_seconds']={'candidate':.8,'anchor':.9,'native':.9}.get(row['mode'],1.)
        row['cpu_seconds']={'candidate':.7,'anchor':.8,'native':.9}.get(row['mode'],1.)
    return rows,{}

class Accounting(unittest.TestCase):
    def test_five_edits_balance_every_position_and_keep_source_transitions(self):
        rows,_=fixture();self.assertEqual(len(rows),40)
        for mode in MODES:
            selected=[r for r in rows if r['mode']==mode];self.assertEqual([(r['cycle'],r['state']) for r in selected],STATES)
            self.assertTrue(all(a['source_sha256']!=b['source_sha256'] for a,b in zip(selected,selected[1:])))
            self.assertEqual(sorted(i%5 for i,r in enumerate(rows) if r['mode']==mode and r['state']>0),list(range(5)))
    def test_complete_child_costs_are_preserved_without_mutation(self):
        rows,sessions=fixture();before=copy.deepcopy(rows);charged,overheads=account(rows,sessions)
        self.assertEqual(rows,before);self.assertEqual(overheads,{})
        for row in charged:
            for key in ['wall_seconds','cpu_seconds']:self.assertEqual(row['accounted_'+key],row[key])
        with self.assertRaises(AssertionError):account(rows,{'candidate':{}})
        rows[0]['launch']={'template_session':{}}
        with self.assertRaises(AssertionError):account(rows,{})
    def test_original_wrong_and_restored_costs_do_not_enter_edit_gate(self):
        rows,sessions=fixture();expected=ratios(rows,sessions)
        for row in rows:
            if row['state']<=0:row['wall_seconds']*=1000;row['cpu_seconds']*=.001
        observed=ratios(rows,sessions)
        self.assertEqual(observed['medians'],expected['medians']);self.assertEqual(observed['pairs'],expected['pairs'])
        self.assertNotEqual(observed['full_history_totals'],expected['full_history_totals'])
    def test_cpu_ceiling_and_noise_allowance_are_both_required(self):
        for candidate,duplicate,want in [(1.001,1.,False),(.99,1.07,False),(1.,1.04,True)]:
            rows,sessions=fixture()
            for row in rows:
                if row['mode']=='candidate':row['cpu_seconds']=candidate
                if row['mode']=='duplicate':row['cpu_seconds']=duplicate
            self.assertEqual(ratios(rows,sessions)['gate_passed'],want)
    def test_worst_aa_pair_keeps_original_noise_margin(self):
        rows,sessions=fixture();next(r for r in rows if r['mode']=='duplicate' and r['state']==3)['wall_seconds']=1.25
        result=ratios(rows,sessions);self.assertFalse(result['gate_passed']);self.assertEqual(result['verdict'],'unmeasurable')
        self.assertAlmostEqual(result['medians']['wall_seconds']['with_noise_margin'],1.05)
    def test_historical_anchor_and_full_history_remain_visible(self):
        rows,sessions=fixture();result=ratios(rows,sessions)
        self.assertAlmostEqual(result['medians']['wall_seconds']['candidate_anchor'],.8/.9)
        self.assertAlmostEqual(result['full_history_totals']['candidate']['wall_seconds'],8*.8)
    def test_missing_duplicate_source_mismatch_and_nonfinite_costs_fail_closed(self):
        for change in [lambda r:r.pop(),lambda r:r[1].update(mode=r[0]['mode']),
                lambda r:r[0].update(source_sha256='other'),lambda r:r[0].update(wall_seconds=math.nan),
                lambda r:r[0].update(cpu_seconds=0)]:
            rows,sessions=fixture();change(rows)
            with self.assertRaises(AssertionError):ratios(rows,sessions)

if __name__=='__main__':unittest.main()
