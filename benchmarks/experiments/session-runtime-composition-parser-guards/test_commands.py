import copy,unittest
from pathlib import Path
from benchmark import custom_command,validate_options
from prerequisites import validate_prior
from accounting import SESSION_MODES

class Commands(unittest.TestCase):
    def test_only_session_arms_enable_indirect_and_use_current_endpoint(self):
        template=['python','launcher','--tool-key','old','--suite-report','old.json','--cache-namespace','old']
        before=template.copy();endpoints={m:Path('/owned')/m for m in SESSION_MODES}
        for mode in ['baseline','duplicate',*SESSION_MODES]:
            command=custom_command(template,'new',mode,Path('/raw'),4,endpoints)
            self.assertEqual(command[command.index('--tool-key')+1],'new')
            self.assertEqual(command[command.index('--cache-namespace')+1],f'raw:{mode}')
            self.assertEqual('--jit-indirect-calls' in command,mode in SESSION_MODES)
            self.assertIn('--jit-scalar-calls',command)
            if mode in SESSION_MODES:self.assertEqual(command[command.index('--jit-template-session')+1],str(endpoints[mode]))
        self.assertEqual(template,before)
    def test_preconfigured_runtime_options_reject_before_rebinding(self):
        for flag in ['--jit-indirect-calls','--jit-template-session','--jit-scalar-calls','--jit-shared-templates','--jit-demand-regions']:
            with self.assertRaises(AssertionError):custom_command([flag],'new','candidate',Path('/raw'),1,{})
    def test_response_options_cannot_silently_drop_indirect_or_gain_session(self):
        launch=dict(borrowck_cache='off',function_cache='auto',jit_scalar_calls=True,jit_persistent_registers=True,jit_indirect_calls=True,
            toolchain_lookup=dict(mode='cached'),template_session={})
        cmd=['--jit-indirect-calls','--jit-template-session']
        self.assertTrue(validate_options(launch,cmd,'candidate'))
        for mutate in [lambda x:x.update(jit_indirect_calls=False),lambda x:x.update(jit_scalar_calls=False),
                       lambda x:x.update(borrowck_cache='lazy'),lambda x:x.pop('template_session')]:
            broken=copy.deepcopy(launch);mutate(broken)
            with self.assertRaises(AssertionError):validate_options(broken,cmd,'candidate')
        with self.assertRaises(AssertionError):validate_options(launch,cmd,'baseline')
    def proofs(self):
        return [dict(case=c,tool_keys=dict(candidate='new'),commands=176,source_restored=True,original_assertions_unchanged=True,
                     measurement=dict(gate_passed=True,verdict='passed')) for c in ['token','folded','pgrust','rg-aot']]
    def test_every_preceding_project_gate_is_required(self):
        proofs=self.proofs();self.assertTrue(validate_prior(proofs,'new','incremental'))
        for i in range(4):
            broken=copy.deepcopy(proofs);broken[i]['measurement']['gate_passed']=False
            with self.assertRaises(AssertionError):validate_prior(broken,'new','incremental')
        with self.assertRaises(AssertionError):validate_prior(proofs[:-1],'new','incremental')
    def test_repository_defaults_require_closed_incremental_result(self):
        proofs=self.proofs()
        with self.assertRaises(AssertionError):validate_prior(proofs,'new','repository')
        p=copy.deepcopy(proofs[0]);p.update(profile='incremental',commands=110,original_tests=114)
        self.assertTrue(validate_prior([*proofs,p],'new','repository'))
        p['profile']='repository'
        with self.assertRaises(AssertionError):validate_prior([*proofs,p],'new','repository')
    def test_old_candidate_in_any_prior_result_is_not_admitted(self):
        for i in range(4):
            proofs=self.proofs();proofs[i]['tool_keys']['candidate']='old'
            with self.assertRaises(AssertionError):validate_prior(proofs,'new','incremental')

if __name__=='__main__':unittest.main()
