import copy,math,unittest
from accounting import MODES,SESSION_MODES,STATES,schedule,account,ratios

def fixture():
    states=[dict(cycle=c,state=s,label=str(s),source=str(s).encode()) for c,s in STATES]
    rows=schedule(states);sessions={}
    for mode,pid in zip(SESSION_MODES,[123,124]):
        sessions[mode]=dict(pid=pid,returncode=0,requests_consumed=22,verify_hits=False,history_bytes_per_worker=0 if mode=='session-fresh' else 64*1024**2,
            executable_sha256='a'*64,cpu_at_ready=dict(user_us=0,system_us=0),closed=dict(cpu_at_close=dict(user_us=2300000,system_us=0)),
            kernel_cpu=dict(user_seconds=2.4,system_seconds=0),startup_wall_seconds=.2,teardown_wall_seconds=.05,
            startup_parent_cpu_seconds=.01,startup_helper_cpu_seconds=.01,teardown_parent_cpu_seconds=.01)
    for row in rows:
        row['wall_seconds']={'candidate':.8,'session-fresh':.9,'native':.9}.get(row['mode'],1.0)
        row['cpu_seconds']={'candidate':.7,'session-fresh':.8,'native':.9}.get(row['mode'],1.0)
        if row['mode'] in SESSION_MODES:
            session=sessions[row['mode']];index=STATES.index((row['cycle'],row['state']))
            row['launch']=dict(template_session=dict(request_id=index+1,server_pid=session['pid'],server_executable_sha256='a'*64,status='completed',
                history_bytes_per_worker=session['history_bytes_per_worker'],verify_hits=False,
                response=dict(cpu_before=dict(user_us=index*100000,system_us=0),cpu_after=dict(user_us=(index+1)*100000,system_us=0))))
    return rows,sessions

class Accounting(unittest.TestCase):
    def test_three_cycles_balance_mode_positions_and_keep_source_transitions(self):
        rows,_=fixture();self.assertEqual(len(rows),110)
        for mode in MODES:
            selected=[r for r in rows if r['mode']==mode];self.assertEqual([(r['cycle'],r['state']) for r in selected],STATES)
            self.assertTrue(all(a['source_sha256']!=b['source_sha256'] for a,b in zip(selected,selected[1:])))
            self.assertEqual(sorted(i%5 for i,r in enumerate(rows) if r['mode']==mode and r['state']>0),sorted(list(range(5))*3))
            for cycle in range(3):
                self.assertEqual(sorted(i%5 for i,r in enumerate(rows) if r['mode']==mode and r['state']>0 and r['cycle']==cycle),list(range(5)))
    def test_all_fifteen_pairs_contribute_and_restorations_are_not_edits(self):
        rows,sessions=fixture();result=ratios(rows,sessions)
        self.assertEqual(result['edited_pairs'],15);self.assertEqual(result['aa_pairs'],15)
        self.assertEqual([(r['cycle'],r['state']) for r in result['pairs']],[(c,s) for c in range(3) for s in range(1,6)])
        for cycle in range(3):
            changed=copy.deepcopy(rows)
            next(r for r in changed if r['mode']=='duplicate' and r['state']==5 and r['cycle']==cycle)['wall_seconds']=1.3
            self.assertFalse(ratios(changed,sessions)['gate_passed'])
    def test_cpu_conserves_all_kernel_work_and_parent_setup_without_double_counting(self):
        rows,sessions=fixture();before=copy.deepcopy(rows);charged,overheads=account(rows,sessions);self.assertEqual(rows,before)
        for mode in SESSION_MODES:
            expected=sum(r['cpu_seconds'] for r in rows if r['mode']==mode)+2.43
            self.assertAlmostEqual(sum(r['accounted_cpu_seconds'] for r in charged if r['mode']==mode),expected)
            self.assertAlmostEqual(overheads[mode]['kernel_remainder_cpu_seconds'],.2)
    def test_entire_startup_shutdown_cost_is_charged_to_edited_commands(self):
        rows,sessions=fixture();charged,_=account(rows,sessions)
        for row in charged:
            overhead=.25/15 if row['mode'] in SESSION_MODES and row['state']>0 else 0
            self.assertAlmostEqual(row['accounted_wall_seconds'],row['wall_seconds']+overhead)
    def test_setup_and_tail_cpu_can_reject_a_superficial_request_only_win(self):
        rows,sessions=fixture();self.assertTrue(ratios(rows,sessions)['gate_passed'])
        sessions['candidate']['startup_wall_seconds']=4
        self.assertFalse(ratios(rows,sessions)['gate_passed'])
        rows,sessions=fixture();sessions['candidate']['kernel_cpu']['user_seconds']=7
        self.assertFalse(ratios(rows,sessions)['gate_passed'])
    def test_worst_aa_pair_keeps_the_original_noise_margin(self):
        rows,sessions=fixture()
        next(r for r in rows if r['mode']=='duplicate' and r['state']==3)['wall_seconds']=1.2
        result=ratios(rows,sessions);self.assertFalse(result['gate_passed']);self.assertEqual(result['verdict'],'unmeasurable')
        self.assertAlmostEqual(result['medians']['wall_seconds']['with_noise_margin'],1.0+.25/15)
    def test_history_off_control_is_reported_separately(self):
        rows,sessions=fixture();result=ratios(rows,sessions)
        self.assertAlmostEqual(result['medians']['wall_seconds']['candidate_session_fresh'],(.8+.25/15)/(.9+.25/15))
        self.assertAlmostEqual(result['full_history_totals']['candidate']['wall_seconds'],22*.8+.25)
    def test_missing_work_identity_bad_counters_and_nonfinite_costs_fail_closed(self):
        for change in [lambda r,s:r.pop(),lambda r,s:s['candidate'].update(pid=999),
                lambda r,s:s['candidate'].update(requests_consumed=7),lambda r,s:s['candidate'].update(verify_hits=True),
                lambda r,s:s['candidate']['kernel_cpu'].update(user_seconds=.1),
                lambda r,s:r[0].update(wall_seconds=math.nan),
                lambda r,s:s['candidate']['closed']['cpu_at_close'].update(user_us=1)]:
            rows,sessions=fixture();change(rows,sessions)
            with self.assertRaises(AssertionError):ratios(rows,sessions)

if __name__=='__main__':unittest.main()
