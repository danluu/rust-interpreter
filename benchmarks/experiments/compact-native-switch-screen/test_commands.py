import copy,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from commands import command,validate_options
from accounting import MODES,CUSTOM,SESSION_MODES

def fixture(mode):
    reference=dict(instruction_limit=123,allocation_limit=456,inline_leaves=True,trap_unsupported_calls=True,run_try_callbacks=True)
    cmd=command(ROOT,ROOT/'.work/sources/fre',{'package':'fre-kernels'},reference,['one','two'],'token_phrase::tests::',
        ROOT/'.work/session-project-edit-token-fixture',7,mode,{m:dict(tool_key=m) for m in CUSTOM},
        {m:ROOT/'.work/ts'/m/'ready.json' for m in SESSION_MODES})
    launch=dict(jit_scalar_calls=mode!='anchor',jit_indirect_calls=mode=='candidate',function_cache='off' if mode=='anchor' else 'auto',
        borrowck_cache='off',toolchain_lookup=dict(mode='fresh' if mode=='anchor' else 'cached',outcome='fresh' if mode=='anchor' else 'hit'))
    if mode in SESSION_MODES:launch['template_session']={}
    return cmd,launch

class Commands(unittest.TestCase):
    def test_candidate_uses_explicit_indirect_calls_and_exact_runtime_limits(self):
        cmd,launch=fixture('candidate');self.assertTrue(validate_options(launch,cmd,'candidate'))
        for flag in ['--jit-indirect-calls','--jit-scalar-calls','--jit-template-session']:
            self.assertEqual(cmd.count(flag),1)
        for key,value in [('--suite-workers','2'),('--instruction-limit','123'),('--allocation-limit','456')]:
            self.assertEqual(cmd[cmd.index(key)+1],value)
        changed=copy.deepcopy(launch);changed['jit_indirect_calls']=False
        with self.assertRaises(AssertionError):validate_options(changed,cmd,'candidate')
        with self.assertRaises(AssertionError):validate_options(launch,[x for x in cmd if x!='--jit-indirect-calls'],'candidate')
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
        for mode in ['native']:
            cmd,_=fixture(mode);self.assertIn('--test-threads=2',cmd);self.assertIn('--exact',cmd)
            self.assertEqual(cmd[-2:],['one','two']);self.assertIn('--message-format=json',cmd)
    def test_source_namespace_override_does_not_change_runtime_or_selection(self):
        cmd,_=fixture('candidate');self.assertEqual(cmd[cmd.index('--test-filter')+1],'token_phrase::tests::')
        self.assertEqual(cmd[cmd.index('--jobs')+1],'2');self.assertNotIn('--jit-shared-templates',cmd)
        self.assertEqual(cmd.count('--cache-namespace'),1);self.assertEqual(cmd.count('--suite-report'),1)

if __name__=='__main__':unittest.main()
