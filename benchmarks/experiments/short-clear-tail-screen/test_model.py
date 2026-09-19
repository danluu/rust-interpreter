import json
from pathlib import Path
import tempfile
import unittest
from model import ROOT, KEY, CANDIDATE, TARGET, NAMES, MODES, CUSTOM, command, states, schedule, accounting, native_outcomes, native_executable


class IntegrationProtocol(unittest.TestCase):
    def test_original_edits_and_balanced_schedule(self):
        original=(ROOT/'.work/sources/fre/crates/fre-kernels/src/forward_anchored.rs').read_bytes()
        variants=states(original)
        self.assertEqual([s for s,_,_ in variants],[0,-1,1,2,3,4,5,'restored'])
        self.assertEqual(variants[0][2],variants[-1][2]);self.assertEqual(len({b for _,_,b in variants}),7)
        order=schedule(original);self.assertEqual(len(order),40)
        for mode in MODES:
            self.assertEqual({next(i for i,r in enumerate([x for x in order if x['state']==s]) if r['mode']==mode)
                              for s in [1,2,3,4,5]},set(range(5)))

    def test_every_command_selects_original_integration_and_two_workers(self):
        source=Path('/source');raw=Path('/raw/case')
        for mode in MODES:
            cmd=command(source,raw,3,mode)
            self.assertNotIn('--lib',cmd);self.assertEqual(cmd[cmd.index('--jobs')+1],'2')
            option='--test-target' if mode in CUSTOM else '--test'
            self.assertEqual(cmd[cmd.index(option)+1],TARGET)
            if mode in CUSTOM:
                self.assertEqual(cmd[cmd.index('--tool-key')+1],CANDIDATE if mode == 'candidate' else KEY)
                self.assertEqual(cmd[cmd.index('--suite-workers')+1],'2')
                self.assertIn('--jit-scalar-calls',cmd);self.assertEqual(cmd[cmd.index('--test-filter')+1],'')
            elif mode=='native':self.assertEqual(cmd[-2:],NAMES);self.assertIn('--test-threads=2',cmd)
        self.assertNotEqual(command(source,raw,1,'custom'),command(source,raw,1,'duplicate'))

    def test_outcomes_require_both_assertions_and_true_wrong_edit(self):
        ok='\n'.join('test '+n+' ... ok' for n in NAMES)+'\ntest result: ok. 2 passed; 0 failed; 0 ignored;'
        self.assertEqual(native_outcomes(ok,True),[(n,'passed') for n in NAMES])
        wrong=ok.replace(NAMES[0]+' ... ok',NAMES[0]+' ... FAILED').replace('result: ok. 2 passed; 0 failed','result: FAILED. 1 passed; 1 failed')
        self.assertEqual(native_outcomes(wrong,False)[0][1],'failed')
        for text,success in [(ok,False),(wrong,True),(ok.replace(NAMES[0],'unexpected'),True)]:
            with self.assertRaises(AssertionError):native_outcomes(text,success)

    def test_native_snapshot_requires_exact_test_target_and_owned_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);exe=root/'native/test';exe.parent.mkdir();exe.write_bytes(b'fixture')
            row=dict(reason='compiler-artifact',profile=dict(test=True),executable=str(exe),
                target=dict(kind=['test'],name=TARGET,src_path=str(root/'source/crates/fre-kernels/tests'/(TARGET+'.rs'))))
            text=json.dumps(row);self.assertEqual(native_executable(text,root/'source',exe.parent),exe)
            for changed in [dict(row,target=dict(row['target'],kind=['lib'])),
                            dict(row,target=dict(row['target'],name='different'))]:
                with self.assertRaises(AssertionError):native_executable(json.dumps(changed),root/'source',exe.parent)
            with self.assertRaises(AssertionError):native_executable(text+'\n'+text,root/'source',exe.parent)
            with self.assertRaises(AssertionError):native_executable(text,root/'source',root/'other')

    def test_accounting_excludes_setup_wrong_and_restored_and_keeps_all_pairs(self):
        rows=[dict(state=s,mode=m,wall_seconds=2.0 if m in CUSTOM else 1.0,cpu_seconds=2.0 if m in CUSTOM else 1.0)
              for s in [0,-1,1,2,3,4,5,'restored'] for m in MODES]
        for r in rows:
            if r['state'] in [0,-1,'restored']:r['wall_seconds']=1000
        result=accounting(rows);self.assertEqual(result['edited_pairs'],5)
        self.assertEqual(result['medians']['wall_seconds']['custom_native'],2)
        self.assertEqual(result['aa_envelope']['wall_seconds'],0)
        rows[next(i for i,r in enumerate(rows) if r['state']==3 and r['mode']=='duplicate')]['wall_seconds']=2.4
        self.assertAlmostEqual(accounting(rows)['aa_envelope']['wall_seconds'],.2)
        self.assertGreater(result['all_commands_totals']['custom']['wall_seconds'],3000)

    def test_incomplete_duplicate_or_zero_cost_records_fail(self):
        rows=[dict(state=s,mode=m,wall_seconds=1.,cpu_seconds=1.) for s in [0,-1,1,2,3,4,5,'restored'] for m in MODES]
        for changed in [rows[:-1],rows[:-1]+[rows[0]],
                        [dict(r,wall_seconds=0) if r['state']==3 else r for r in rows]]:
            with self.assertRaises(AssertionError):accounting(changed)

    def test_gate_requires_one_percent_and_full_maximum_pair_envelope(self):
        def fixture(candidate, duplicate=1.):
            return [dict(state=s,mode=m,wall_seconds=candidate if m=='candidate' else duplicate if m=='duplicate' else 1.,
                         cpu_seconds=1.) for s in [0,-1,1,2,3,4,5,'restored'] for m in MODES]
        self.assertFalse(accounting(fixture(.995))['gate_passed'])
        self.assertTrue(accounting(fixture(.98))['gate_passed'])
        self.assertFalse(accounting(fixture(.98,1.03))['gate_passed'])
        rows=fixture(.98)
        for r in rows:
            if r['mode']=='duplicate' and r['state']==4:r['wall_seconds']=1.03
        self.assertFalse(accounting(rows)['gate_passed'])
        self.assertEqual(accounting(fixture(.99))['minimum_wall_gain'],.01)

    def test_cpu_cannot_regress_beyond_aa_and_nonfinite_samples_fail(self):
        rows=[dict(state=s,mode=m,wall_seconds=.97 if m=='candidate' else 1.,cpu_seconds=1.)
              for s in [0,-1,1,2,3,4,5,'restored'] for m in MODES]
        for r in rows:
            if r['mode']=='candidate':r['cpu_seconds']=1.02
        self.assertFalse(accounting(rows)['gate_passed'])
        for r in rows:
            if r['mode']=='duplicate':r['cpu_seconds']=1.03
        self.assertTrue(accounting(rows)['gate_passed'])
        for invalid in [float('nan'),float('inf'),-1.]:
            changed=[dict(r) for r in rows];changed[12]['wall_seconds']=invalid
            with self.assertRaises(AssertionError):accounting(changed)


if __name__=='__main__':unittest.main()
