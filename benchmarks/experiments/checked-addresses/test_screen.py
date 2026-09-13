import copy
import unittest

import screen


class ScreenTests(unittest.TestCase):
    def control_proofs(self):
        build = dict(status='passed', tool_key=screen.BASELINE_KEY,
            binaries={'rust-interp-vm':'vm', 'rust-interp-mir-export':'exporter', 'rust-interp-rustc-wrapper':'wrapper'},
            composition=dict(exporter_and_wrapper_key=screen.EXPORTER_KEY),
            tests={p:dict(passed=436, ignored=1) for p in ['test-debug','test-release']})
        integration = dict(status='passed', tool_key=screen.EXPORTER_KEY, binaries=dict(build['binaries']))
        integration['binaries']['rust-interp-vm'] = 'older-vm'
        cache = dict(status='passed', tool_key=screen.EXPORTER_KEY, commands=203,
            automatic_cache_qualified=True, source_restored=True)
        selection = dict(status='passed', tool_key=screen.BASELINE_KEY, vm_sha256='vm', commands=7,
            original_assertions_match=True, exact_instructions_memory_and_entropy=True, bytecode_and_catalogs_unchanged=True)
        profile = dict(status='passed', tool_key=screen.BASELINE_KEY, vm_sha256='vm', commands=3,
            exact_adopted_code=True, exact_per_pc_profiles=True)
        return [build, integration, cache, selection, profile]

    def test_baseline_reuses_only_identical_exporter_and_qualified_diagnostic_vm(self):
        proofs = self.control_proofs()
        self.assertTrue(screen.validate_baseline(*proofs))
        for index, field, value in [(0,'tool_key','other'), (1,'tool_key','other'),
                (2,'commands',202), (3,'vm_sha256','older-vm'), (4,'vm_sha256','older-vm'),
                (3,'exact_instructions_memory_and_entropy',False), (4,'exact_adopted_code',False),
                (4,'exact_per_pc_profiles',False), (2,'source_restored',False)]:
            changed = copy.deepcopy(proofs); changed[index][field] = value
            with self.subTest(index=index,field=field), self.assertRaises(AssertionError):
                screen.validate_baseline(*changed)

    def test_new_exporter_or_unqualified_baseline_profile_cannot_inherit_cache_proof(self):
        for binary in ['rust-interp-mir-export','rust-interp-rustc-wrapper']:
            changed = self.control_proofs(); changed[0]['binaries'][binary] = 'other'
            with self.assertRaises(AssertionError): screen.validate_baseline(*changed)
        changed = self.control_proofs(); changed[0]['tests']['test-release']['passed'] = 435
        with self.assertRaises(AssertionError): screen.validate_baseline(*changed)
        changed = self.control_proofs(); changed[0]['composition']['exporter_and_wrapper_key'] = 'other'
        with self.assertRaises(AssertionError): screen.validate_baseline(*changed)

    def rows(self, wall=.94, cpu=.98, aa_wall=1.02, aa_cpu=1.02):
        result = []
        states = [(0, s) for s in [0, -1, 1, 2, 3, 4, 5]] + [(1, 0)]
        for cycle, state in states:
            for mode in screen.MODES:
                seconds = {'baseline': 1., 'duplicate': aa_wall, 'candidate': wall,
                           'anchor': 2., 'native': .5}[mode]
                total = {'baseline': 1., 'duplicate': aa_cpu, 'candidate': cpu,
                         'anchor': 2., 'native': .5}[mode]
                result.append(dict(cycle=cycle, state=state, mode=mode,
                    source_sha256=str(state), seconds=seconds, cpu=dict(total_seconds=total)))
        return result

    def test_schedule_preserves_original_tests_and_rotates_all_modes(self):
        original = 'fn body() { 100 }\n#[cfg(test)]\nmod tests { unchanged }'
        case = dict(negative=('wrong', '100', '999'),
                    edits=[(str(i), str(100+i), str(101+i)) for i in range(5)])
        states = list(screen.protocol_states(original, case))
        self.assertEqual([(s['cycle'], s['state']) for s in states],
            [(0, s) for s in [0, -1, 1, 2, 3, 4, 5]] + [(1, 0)])
        self.assertEqual(states[-1]['source'], original.encode())
        for index, sample in enumerate(states):
            self.assertCountEqual(sample['modes'], screen.MODES)
            self.assertEqual(sample['modes'][0 if index % 2 == 0 else -1], 'native')
            self.assertTrue(sample['source'].endswith(b'mod tests { unchanged }'))
        for position in range(4):
            self.assertCountEqual([[m for m in s['modes'] if m != 'native'][position]
                                   for s in states[:4]], screen.CUSTOM)

    def test_lookup_matches_all_three_controls_and_rejects_late_misses(self):
        for mode in screen.CACHED:
            self.assertEqual(screen.lookup_args(mode), ['--toolchain-lookup', 'cached'])
            for outcome in ['hit', 'miss']:
                launch = dict(toolchain_lookup=dict(mode='cached', outcome=outcome))
                self.assertTrue(screen.validate_lookup(launch, mode, 0, 0))
                if outcome == 'miss':
                    with self.assertRaises(AssertionError):
                        screen.validate_lookup(launch, mode, 0, 1)
        self.assertTrue(screen.validate_lookup(dict(toolchain_lookup=dict(mode='fresh', outcome='fresh')), 'anchor', 0, 1))

    def test_fixed_anchor_gain_cannot_hide_primary_noise_failure(self):
        result = screen.assessment(self.rows(wall=.99, aa_wall=1.03))
        self.assertLess(result['paired_anchor_wall_ratio'], .5)
        self.assertFalse(result['gate_passed'])
        self.assertEqual(result['next_action'], 'park candidate; cancel unstarted guards')
        self.assertTrue(screen.assessment(self.rows())['gate_passed'])

    def test_cpu_ceiling_and_noise_margin_are_both_required(self):
        self.assertFalse(screen.assessment(self.rows(cpu=1.001, aa_cpu=1.0))['gate_passed'])
        self.assertFalse(screen.assessment(self.rows(cpu=.99, aa_cpu=1.07))['gate_passed'])
        self.assertTrue(screen.assessment(self.rows(cpu=1., aa_cpu=1.04))['gate_passed'])

    def test_missing_duplicate_source_mismatch_and_nonfinite_times_reject(self):
        rows = self.rows()
        with self.assertRaises(AssertionError):
            screen.assessment(rows[:-1])
        for field, value in [('mode', 'baseline'), ('source_sha256', 'other'),
                             ('seconds', float('nan')), ('seconds', 0.)]:
            changed = copy.deepcopy(rows)
            changed[1][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(AssertionError):
                screen.assessment(changed)

    def test_original_wrong_and_restored_do_not_enter_edited_ratios(self):
        rows = self.rows()
        expected = screen.assessment(rows)
        for row in rows:
            if row['state'] <= 0:
                row['seconds'] *= 1000
                row['cpu']['total_seconds'] *= .001
        self.assertEqual(screen.assessment(rows), expected)
        self.assertEqual(expected['edited_pairs'], 5)
        self.assertEqual(expected['aa_pairs'], 5)

    def test_native_failure_requires_exact_names_and_summary(self):
        text = 'test a ... ok\ntest b ... FAILED\ntest result: FAILED. 1 passed; 1 failed; 0 ignored;'
        self.assertEqual(screen.native_outcomes(text, ['a', 'b'], False), [('a', 'passed'), ('b', 'failed')])
        for wrong in [text.replace('test b', 'test c'), text.replace('1 failed', '0 failed'), text.replace('b ... FAILED', 'b ... ignored')]:
            with self.assertRaises(AssertionError):
                screen.native_outcomes(wrong, ['a', 'b'], False)


if __name__ == '__main__':
    unittest.main()
