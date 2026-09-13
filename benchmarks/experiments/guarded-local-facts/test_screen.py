import copy
import unittest

import screen


class ScreenTests(unittest.TestCase):
    def control_proofs(self):
        build=dict(status='passed',tool_key=screen.BASELINE_KEY,
            binaries={'rust-interp-vm':'vm','rust-interp-mir-export':'exporter','rust-interp-rustc-wrapper':'wrapper'},
            tests={'test-debug':98,'test-release':98})
        integration=dict(status='passed',binaries={'rust-interp-vm':'vm'},tests={'test-debug':484,'test-release':484})
        cache=dict(status='passed',tool_key=screen.BASELINE_KEY,commands=119,automatic_cache_qualified=True,source_restored=True)
        selection=dict(status='passed',tool_key=screen.BASELINE_KEY,commands=40)
        profile=dict(status='passed',tool_key=screen.BASELINE_KEY,binaries=dict(build['binaries']),
                     exact_existing_and_parser_artifacts=True,strict_commands=119,project_commands=40,complete_parser_tests=114)
        return [build,integration,cache,selection,profile]

    def test_baseline_rejects_incomplete_or_mismatched_qualification(self):
        self.assertTrue(screen.validate_baseline(*self.control_proofs()))
        for index,field,value in [(0,'tool_key','other'),(2,'commands',118),(2,'source_restored',False),
                                   (3,'commands',39),(4,'complete_parser_tests',113),(4,'exact_existing_and_parser_artifacts',False)]:
            proofs=self.control_proofs();proofs[index][field]=value
            with self.assertRaises(AssertionError):screen.validate_baseline(*proofs)

    def test_baseline_requires_exact_vm_and_compiler_components(self):
        for binary in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']:
            proofs=self.control_proofs();proofs[0]['binaries'][binary]='different'
            with self.assertRaises(AssertionError):screen.validate_baseline(*proofs)
        proofs=self.control_proofs();proofs[0]['tests']['test-release']=97
        with self.assertRaises(AssertionError):screen.validate_baseline(*proofs)

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
