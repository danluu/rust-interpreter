import copy
import unittest

import prerequisites as p


class PrerequisiteTests(unittest.TestCase):
    def proofs(self):
        build = dict(status='passed', tool_key=p.CANDIDATE_KEY,
            tests={'test-debug': 525, 'test-release': 525}, binaries={'rust-interp-vm': 'vm'},
            composition=dict(kind='successor-only-flush-composition', compiler_source_key=p.EXPORTER_KEY))
        strict = dict(status='passed', tool_key=p.CANDIDATE_KEY, commands=119,
            source_restored=True, automatic_cache_qualified=True, strict_rejections=['type', 'borrow'])
        real = dict(status='passed', tool_key=p.CANDIDATE_KEY, commands=13, selected_tests=7,
            prepared_suites=6, vm_sha256='vm', native_assertion_outcomes_match=True, deterministic_controls_exact=True)
        profile = dict(status='passed', tool_key=p.CANDIDATE_KEY, vm_sha256='vm', commands=3,
            exact_per_pc_counts=True, exact_logical_counts_memory_and_entropy=True,
            exact_operation_map_reconstruction=True,
            comparisons=[dict(statistics=dict(jit_declined_functions=0)) for _ in range(3)])
        screen = dict(status='passed', commands=40, gate_passed=True, source_restored=True,
            test_source_unchanged=True, native_assertion_outcomes_match=True,
            candidate_control_bytecode_matches=True,
            tool_keys=dict(candidate=p.CANDIDATE_KEY, baseline=p.BASELINE_KEY, duplicate=p.BASELINE_KEY))
        emission=dict(status='passed',tool_key=p.CANDIDATE_KEY,commands=2,guest_commands=0,
            executable_code_publications=0,exact_adopted_reconstruction=True,only_dead_after_flush_words_removed=True)
        return [build, strict, real, profile, screen, emission]

    def test_complete_bound_qualification_is_accepted(self):
        self.assertTrue(p.validate_candidate(*self.proofs()))

    def test_incomplete_stages_and_missing_strict_rejections_fail(self):
        for index, field, value in [(1, 'commands', 118), (2, 'commands', 12), (2, 'prepared_suites', 5),
                                    (3, 'commands', 2), (4, 'commands', 39), (5, 'commands', 1),
                                    (5, 'only_dead_after_flush_words_removed', False), (5, 'exact_adopted_reconstruction', False),
                                    (5, 'guest_commands', 1), (5, 'executable_code_publications', 1),
                                    (1, 'strict_rejections', ['type']), (1, 'source_restored', False)]:
            proofs = self.proofs(); proofs[index][field] = value
            with self.subTest(index=index, field=field), self.assertRaises(AssertionError):
                p.validate_candidate(*proofs)
        for index in range(6):
            proofs = self.proofs(); proofs[index]['status'] = 'failed'
            with self.assertRaises(AssertionError): p.validate_candidate(*proofs)

    def test_source_components_and_executed_vm_cannot_be_substituted(self):
        for index in [0, 1, 2, 3, 5]:
            proofs = self.proofs(); proofs[index]['tool_key'] = 'different'
            with self.assertRaises(AssertionError): p.validate_candidate(*proofs)
        proofs = self.proofs(); proofs[0]['composition']['compiler_source_key'] = 'different'
        with self.assertRaises(AssertionError): p.validate_candidate(*proofs)
        for index in [2, 3]:
            proofs = self.proofs(); proofs[index]['vm_sha256'] = 'different'
            with self.assertRaises(AssertionError): p.validate_candidate(*proofs)

    def test_primary_failure_or_wrong_controls_cannot_admit_full(self):
        for field in ['gate_passed', 'source_restored', 'test_source_unchanged',
                      'native_assertion_outcomes_match', 'candidate_control_bytecode_matches']:
            proofs = self.proofs(); proofs[4][field] = False
            with self.assertRaises(AssertionError): p.validate_candidate(*proofs)
        for mode in ['candidate', 'baseline', 'duplicate']:
            proofs = self.proofs(); proofs[4]['tool_keys'][mode] = 'different'
            with self.assertRaises(AssertionError): p.validate_candidate(*proofs)

    def test_profiles_require_complete_exact_execution_without_declines(self):
        for field in ['exact_per_pc_counts', 'exact_logical_counts_memory_and_entropy',
                      'exact_operation_map_reconstruction']:
            proofs = self.proofs(); proofs[3][field] = False
            with self.assertRaises(AssertionError): p.validate_candidate(*proofs)
        proofs = self.proofs(); proofs[3]['comparisons'].pop()
        with self.assertRaises(AssertionError): p.validate_candidate(*proofs)
        proofs = self.proofs(); proofs[3]['comparisons'][1]['statistics']['jit_declined_functions'] = 1
        with self.assertRaises(AssertionError): p.validate_candidate(*proofs)


if __name__ == '__main__': unittest.main()
