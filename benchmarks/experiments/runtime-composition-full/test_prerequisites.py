import copy
import unittest
import prerequisites as p


class PrerequisiteTests(unittest.TestCase):
    def proofs(self):
        import json
        names = ['build-01', 'qualification-02', 'real-controls-01', 'profile-02', 'screen-token-01']
        proofs = [json.loads((p.ROOT / 'results' / ('runtime-composition-' + name) / 'summary.json').read_text()) for name in names]
        proofs.append(json.loads((p.ROOT / 'results/runtime-composition-screen-token-01/closure.json').read_text()))
        return proofs

    def test_complete_bound_qualification_accepts_accounted_code_growth(self):
        self.assertTrue(p.validate_candidate(*self.proofs()))

    def test_incomplete_stages_and_missing_strict_rejections_fail(self):
        for index,field,value in [(0,'ignored_per_profile',24),(1,'commands',121),(2,'commands',25),(2,'prepared_suites',5),
            (2,'jit_scalar_calls',False),(2,'jit_indirect_calls',False),(2,'fresh_baseline_commands',12),(1,'indirect_partial_artifact_rejections',0),(1,'indirect_enabled_strict_cargo',False),(3,'commands',5),(3,'python_controls_reused',4),(3,'launcher_controls_reused',8),
            (4,'commands',39),(5,'parked',True),(5,'repeated_screen_commands',40),
            (5,'held_out_commands',1),(5,'full_comparison_commands',154),
            (1,'scalar_enabled_strict_cargo',False),(1,'actual_demand_artifact',False),
            (1,'scalar_partial_artifact_rejections',0),(1,'strict_rejections',['type']),(1,'source_restored',False)]:
            proofs=self.proofs();proofs[index][field]=value
            with self.subTest(index=index,field=field),self.assertRaises(AssertionError):p.validate_candidate(*proofs)
        for index in range(6):
            proofs=self.proofs();proofs[index]['status']='failed'
            with self.assertRaises(AssertionError):p.validate_candidate(*proofs)

    def test_source_components_and_executed_vm_cannot_be_substituted(self):
        for index in [0,1,2,3]:
            proofs=self.proofs();proofs[index]['tool_key']='different'
            with self.assertRaises(AssertionError):p.validate_candidate(*proofs)
        for target in ['composition','matched_control']:
            proofs=self.proofs()
            if target=='composition':proofs[0][target]['compiler_source_key']='different'
            else:proofs[0][target]['tool_key']='different'
            with self.assertRaises(AssertionError):p.validate_candidate(*proofs)
        for index in [2]:
            proofs=self.proofs();proofs[index]['vm_sha256']='different'
            with self.assertRaises(AssertionError):p.validate_candidate(*proofs)
        for field in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']:
            proofs=self.proofs();proofs[0]['matched_control']['binaries'][field]=proofs[0]['binaries']['rust-interp-vm'] if field=='rust-interp-vm' else 'other'
            with self.assertRaises(AssertionError):p.validate_candidate(*proofs)

    def test_primary_failure_or_wrong_controls_cannot_admit_full(self):
        for field in ['gate_passed','source_restored','test_source_unchanged','native_assertion_outcomes_match',
                      'candidate_control_bytecode_matches']:
            proofs=self.proofs();proofs[4][field]=False
            with self.assertRaises(AssertionError):p.validate_candidate(*proofs)
        for mode in ['candidate','baseline','duplicate']:
            proofs=self.proofs();proofs[4]['tool_keys'][mode]='different'
            with self.assertRaises(AssertionError):p.validate_candidate(*proofs)
        proofs=self.proofs();proofs[5]['performance_gate_passed']=False
        with self.assertRaises(AssertionError):p.validate_candidate(*proofs)

    def test_profiles_require_complete_exact_execution_without_declines(self):
        for field in ['exact_per_pc_counts','exact_logical_counts_memory_and_entropy',
                      'exact_operation_map_reconstruction','control_vm_matches_adopted']:
            proofs=self.proofs();proofs[3][field]=False
            with self.assertRaises(AssertionError):p.validate_candidate(*proofs)
        for mutate in [lambda r:r.pop(),lambda r:r[1]['statistics'].update(jit_declined_functions=1),
                       lambda r:r[1]['logical_counts'].update(total=1),
                       lambda r:r[1]['logical_counts'].update(scalar=0),
                       lambda r:r[1].update(scalar_code_bytes=0),
                       lambda r:r[1].update(current_native_bytes=1),
                       lambda r:r[1].update(mode='control'),
                       lambda r:r[0].update(scalar_calls=0)]:
            proofs=self.proofs();mutate(proofs[3]['comparisons'])
            with self.assertRaises(AssertionError):p.validate_candidate(*proofs)


if __name__=='__main__':unittest.main()
