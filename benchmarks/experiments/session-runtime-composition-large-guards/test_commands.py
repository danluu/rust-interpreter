import copy,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from commands import command,validate_options
from admission import validate_previous,CANDIDATE
from accounting import CUSTOM,SESSION_MODES,ratios
from context import disk_need
from test_accounting import fixture as accounting_fixture

def fixture(mode,names):
    reference=dict(instruction_limit=100_000_000_000,allocation_limit=150_000,inline_leaves=True,trap_unsupported_calls=True,run_try_callbacks=True)
    cmd=command(ROOT,ROOT/'.work/sources/project',dict(package='fixture'),reference,names,'',ROOT/'.work/fixture',1,mode,
        {m:dict(tool_key=m) for m in CUSTOM},{m:ROOT/'.work/ts'/m/'ready.json' for m in SESSION_MODES})
    launch=dict(jit_scalar_calls=mode!='anchor',jit_indirect_calls=mode in SESSION_MODES,function_cache='off' if mode=='anchor' else 'auto',
        borrowck_cache='off',toolchain_lookup=dict(mode='fresh' if mode=='anchor' else 'cached',outcome='fresh' if mode=='anchor' else 'hit'))
    if mode in SESSION_MODES:launch['template_session']={}
    return cmd,launch

class Commands(unittest.TestCase):
    def test_single_test_uses_exact_filter_without_duplication_and_requests_two_slots(self):
        for mode in CUSTOM:
            cmd,launch=fixture(mode,['one'])
            self.assertEqual(cmd[cmd.index('--test-filter')+1],'one');self.assertIn('--test-exact',cmd)
            self.assertNotIn('--entry',cmd);self.assertEqual(cmd[cmd.index('--suite-workers')+1],'2')
            self.assertTrue(validate_options(launch,cmd,mode))
    def test_multiple_tests_use_exact_entry_catalog_and_fixed_limits(self):
        names=['one','two','three'];cmd,_=fixture('candidate',names)
        self.assertEqual([cmd[i+1] for i,v in enumerate(cmd) if v=='--entry'],names)
        self.assertNotIn('--test-filter',cmd);self.assertIn('--timings',cmd)
        self.assertEqual(cmd[cmd.index('--instruction-limit')+1],'100000000000')
        self.assertEqual(cmd[cmd.index('--allocation-limit')+1],'150000')
    def test_history_on_off_options_match_and_baseline_cannot_gain_indirect_or_session(self):
        a,_=fixture('candidate',['one']);b,_=fixture('session-fresh',['one'])
        for flag in ['--tool-key','--cache-namespace','--jit-template-session']:a[a.index(flag)+1]=b[b.index(flag)+1]='bound'
        self.assertEqual(a,b)
        for mode in ['baseline','duplicate','anchor']:
            cmd,launch=fixture(mode,['one'])
            self.assertTrue(validate_options(launch,cmd,mode))
            for field,value in [('jit_indirect_calls',True),('template_session',{}),('borrowck_cache','on')]:
                changed=copy.deepcopy(launch);changed[field]=value
                with self.assertRaises(AssertionError):validate_options(changed,cmd,mode)
    def test_native_keeps_exact_selection_two_workers_and_timings(self):
        for mode in ['native','native_lines']:
            cmd,_=fixture(mode,['one']);self.assertIn('--test-threads=2',cmd);self.assertIn('--exact',cmd)
            self.assertEqual(cmd[-1],'one');self.assertIn('--timings',cmd);self.assertIn('--message-format=json',cmd)
        cmd,_=fixture('check',['one']);self.assertIn('check',cmd);self.assertNotIn('--',cmd)
    def test_previous_project_and_both_parser_gates_are_mandatory_for_nushell(self):
        proofs=[dict(case=c,status='passed',commands=176,source_restored=True,original_assertions_unchanged=True,
            measurement=dict(gate_passed=True,verdict='passed'),tool_keys=dict(candidate=CANDIDATE)) for c in ['token','folded','pgrust','rg-aot']]
        self.assertTrue(validate_previous('rg-aot',proofs[:3]))
        with self.assertRaises(AssertionError):validate_previous('nushell',proofs)
        for profile in ['incremental','repository']:proofs.append(dict(proofs[0],commands=110,profile=profile,original_tests=114))
        self.assertTrue(validate_previous('nushell',proofs))
        for index in range(len(proofs)):
            broken=copy.deepcopy(proofs);broken[index]['measurement']['gate_passed']=False
            with self.assertRaises(AssertionError):validate_previous('nushell',broken)
    def test_larger_cache_campaign_preserves_floor_and_nine_namespace_allowance(self):
        self.assertEqual(disk_need('rg-aot'),12*1024**3)
        self.assertEqual(disk_need('nushell',1),47*1024**3)
        size=5*1024**3
        self.assertEqual(disk_need('nushell',size),8*1024**3+(size*9*120+99)//100)
        self.assertGreater(disk_need('nushell',size),8*1024**3+(size*6*120+99)//100)
        with self.assertRaises(AssertionError):disk_need('nushell',0)
    def test_large_and_private_cases_use_existing_full_regression_gate(self):
        rows,sessions=accounting_fixture()
        for case in ['rg-aot','nushell']:
            result=ratios(rows,sessions,case);self.assertTrue(result['gate_passed'])
            bad=copy.deepcopy(rows)
            for row in bad:
                if row['mode']=='candidate' and row['state']>0:row['wall_seconds']*=3
            self.assertFalse(ratios(bad,sessions,case)['gate_passed'])

if __name__=='__main__':unittest.main()
