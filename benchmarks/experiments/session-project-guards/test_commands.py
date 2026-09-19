import copy,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from commands import command,validate_options
from admission import validate_previous,CANDIDATE
from accounting import MODES,CUSTOM,SESSION_MODES

def fixture(mode):
    reference=dict(instruction_limit=123,allocation_limit=456,inline_leaves=True,trap_unsupported_calls=True,run_try_callbacks=True)
    cmd=command(ROOT,ROOT/'.work/sources/fre',{'package':'fre-kernels'},reference,['one','two'],'token_phrase::tests::',
        ROOT/'.work/session-project-edit-token-fixture',7,mode,{m:dict(tool_key=m) for m in CUSTOM},
        {m:ROOT/'.work/ts'/m/'ready.json' for m in SESSION_MODES})
    launch=dict(jit_scalar_calls=mode!='anchor',jit_indirect_calls=False,function_cache='off' if mode=='anchor' else 'auto',
        borrowck_cache='off',toolchain_lookup=dict(mode='fresh' if mode=='anchor' else 'cached',outcome='fresh' if mode=='anchor' else 'hit'))
    if mode in SESSION_MODES:launch['template_session']={}
    return cmd,launch

class Commands(unittest.TestCase):
    def test_session_controls_have_same_options_except_identity_report_and_endpoint(self):
        a,_=fixture('candidate');b,_=fixture('session-fresh')
        for option in ['--tool-key','--cache-namespace','--jit-template-session']:
            a[a.index(option)+1]=b[b.index(option)+1]='bound'
        self.assertEqual(a,b)
        for mode in SESSION_MODES:
            cmd,launch=fixture(mode);self.assertTrue(validate_options(launch,cmd,mode))
            self.assertEqual(cmd[cmd.index('--suite-workers')+1],'2')
            self.assertEqual(cmd[cmd.index('--instruction-limit')+1],'123')
            self.assertEqual(cmd[cmd.index('--allocation-limit')+1],'456')
    def test_anchor_stays_uncached_and_cannot_silently_acquire_current_options(self):
        cmd,launch=fixture('anchor');self.assertNotIn('--jit-scalar-calls',cmd);self.assertNotIn('--function-cache',cmd)
        self.assertTrue(validate_options(launch,cmd,'anchor'));launch['jit_scalar_calls']=True
        with self.assertRaises(AssertionError):validate_options(launch,cmd,'anchor')
    def test_ordinary_arms_cannot_accept_a_session_or_relaxed_borrow_check(self):
        for mode in ['baseline','duplicate']:
            cmd,launch=fixture(mode);self.assertTrue(validate_options(launch,cmd,mode));self.assertNotIn('--jit-template-session',cmd)
            for key,value in [('template_session',{}),('borrowck_cache','on'),('jit_indirect_calls',True)]:
                changed=copy.deepcopy(launch);changed[key]=value
                with self.assertRaises(AssertionError):validate_options(changed,cmd,mode)
    def test_native_commands_keep_exact_original_tests_and_explicit_worker_limit(self):
        for mode in ['native','native_lines']:
            cmd,_=fixture(mode);self.assertIn('--test-threads=2',cmd);self.assertIn('--exact',cmd)
            self.assertEqual(cmd[-2:],['one','two']);self.assertIn('--message-format=json',cmd)
        cmd,_=fixture('check');self.assertIn('check',cmd);self.assertNotIn('--',cmd);self.assertIn('--profile',cmd)
    def test_previous_gates_cannot_be_skipped_or_replaced_with_failed_or_other_binaries(self):
        self.assertTrue(validate_previous('token',[]))
        proof=dict(case='token',status='passed',commands=176,source_restored=True,original_assertions_unchanged=True,
            measurement=dict(gate_passed=True,verdict='passed'),tool_keys=dict(candidate=CANDIDATE))
        self.assertTrue(validate_previous('folded',[proof]))
        for changed in [[],[dict(proof,source_restored=False)],[dict(proof,measurement=dict(gate_passed=False,verdict='failed'))],
                [dict(proof,tool_keys=dict(candidate='different'))],[dict(proof,case='folded')]]:
            with self.assertRaises(AssertionError):validate_previous('folded',changed)
        with self.assertRaises(AssertionError):validate_previous('pgrust',[proof])
    def test_source_namespace_override_does_not_change_runtime_or_selection(self):
        cmd,_=fixture('candidate');self.assertEqual(cmd[cmd.index('--test-filter')+1],'token_phrase::tests::')
        self.assertEqual(cmd[cmd.index('--jobs')+1],'2');self.assertNotIn('--jit-shared-templates',cmd)
        self.assertEqual(cmd.count('--cache-namespace'),1);self.assertEqual(cmd.count('--suite-report'),1)

if __name__=='__main__':unittest.main()
