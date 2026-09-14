import copy
import unittest
import prerequisites as p


class PrerequisiteTests(unittest.TestCase):
    def proofs(self):
        binaries={'rust-interp-vm':'vm','rust-interp-mir-export':'exporter','rust-interp-rustc-wrapper':'wrapper'}
        matched=dict(tool_key=p.BASELINE_KEY, binaries=dict(binaries, **{'rust-interp-vm':'control'}),
            composition=dict(kind='heap-address-bias-matched-control', source_commit=p.CONTROL_SOURCE,
                             compiler_source_key=p.EXPORTER_KEY))
        build=dict(status='passed', tool_key=p.CANDIDATE_KEY, tests={'test-debug':553,'test-release':553},
            binaries=binaries, matched_control=matched, distinct_control_and_candidate_executables=True,
            composition=dict(kind='heap-address-bias-composition',compiler_source_key=p.EXPORTER_KEY))
        strict=dict(status='passed',tool_key=p.CANDIDATE_KEY,commands=119,source_restored=True,
                    automatic_cache_qualified=True,strict_rejections=['type','borrow'])
        real=dict(status='passed',tool_key=p.CANDIDATE_KEY,commands=13,selected_tests=7,prepared_suites=6,
                  vm_sha256='vm',native_assertion_outcomes_match=True,deterministic_controls_exact=True)
        exact=dict(exact_per_pc_counts=True,exact_logical_counts_memory_and_entropy=True,
                   exact_operation_map_reconstruction=True)
        comparisons=[]
        for i in range(3):
            for mode in ['control','candidate']:
                comparisons.append(dict(index=i,mode=mode,statistics=dict(jit_declined_functions=0),
                    current_native_bytes=100 if mode=='control' else 110,**exact,
                    mechanism=None if mode=='control' else dict(status='passed',
                        entry_replacement_words_verified=True,stable_span_shapes_and_unaffected_word_counts=True,
                        added_entry_bytes=20,removed_checked_bytes=10,net_code_bytes=10)))
        profile=dict(status='passed',tool_key=p.CANDIDATE_KEY,vm_sha256='vm',commands=6,new_executions=4,
                     reused_executions=2,code_partition_verified=True,matched_control_key=p.BASELINE_KEY,
                     control_code_matches_adopted=True,comparisons=comparisons,**exact)
        screen=dict(status='passed',commands=40,gate_passed=True,source_restored=True,test_source_unchanged=True,
                    native_assertion_outcomes_match=True,candidate_control_bytecode_matches=True,
                    tool_keys=dict(candidate=p.CANDIDATE_KEY,baseline=p.BASELINE_KEY,duplicate=p.BASELINE_KEY))
        closure=dict(status='passed',performance_gate_passed=True,parked=False,actual_profile_guest_executions=6,
                     profile_prefix_executions_reused=True,rejected_tool_key=p.REJECTED_KEY,
                     rejected_tool_benchmark_executions=0,full_comparison_commands=0,held_out_commands=0,
                     repeated_screen_commands=0)
        return [build,strict,real,profile,screen,closure]

    def test_complete_bound_qualification_accepts_accounted_code_growth(self):
        self.assertTrue(p.validate_candidate(*self.proofs()))

    def test_incomplete_stages_and_missing_strict_rejections_fail(self):
        for index,field,value in [(1,'commands',118),(2,'commands',12),(2,'prepared_suites',5),
            (3,'commands',5),(3,'new_executions',3),(3,'reused_executions',3),(3,'code_partition_verified',False),
            (4,'commands',39),(5,'actual_profile_guest_executions',7),(5,'rejected_tool_benchmark_executions',1),
            (5,'repeated_screen_commands',40),(5,'held_out_commands',1),(5,'full_comparison_commands',154),
            (5,'profile_prefix_executions_reused',False),(1,'strict_rejections',['type']),(1,'source_restored',False)]:
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
            else:proofs[0][target]['composition']['source_commit']='different'
            with self.assertRaises(AssertionError):p.validate_candidate(*proofs)
        for index in [2,3]:
            proofs=self.proofs();proofs[index]['vm_sha256']='different'
            with self.assertRaises(AssertionError):p.validate_candidate(*proofs)
        for field in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']:
            proofs=self.proofs();proofs[0]['matched_control']['binaries'][field]='vm' if field=='rust-interp-vm' else 'other'
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
                      'exact_operation_map_reconstruction']:
            for index in [None,0,1,5]:
                proofs=self.proofs();target=proofs[3] if index is None else proofs[3]['comparisons'][index]
                target[field]=False
                with self.assertRaises(AssertionError):p.validate_candidate(*proofs)
        for mutate in [lambda r:r.pop(),lambda r:r[1]['statistics'].update(jit_declined_functions=1),
                       lambda r:r[1]['mechanism'].update(net_code_bytes=11),
                       lambda r:r[1]['mechanism'].update(entry_replacement_words_verified=False),
                       lambda r:r[1].update(mode='control')]:
            proofs=self.proofs();mutate(proofs[3]['comparisons'])
            with self.assertRaises(AssertionError):p.validate_candidate(*proofs)


if __name__=='__main__':unittest.main()
