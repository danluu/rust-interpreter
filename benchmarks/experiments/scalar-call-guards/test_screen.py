import copy
import json
from pathlib import Path
import tempfile
import unittest

import screen


class ScreenTests(unittest.TestCase):
    def artifact(self, library, executable, test=True, kind='lib'):
        return json.dumps(dict(reason='compiler-artifact', profile=dict(test=test), executable=str(executable),
                               target=dict(kind=[kind], src_path=str(library))))

    def test_matched_main_profile_rejects_mixed_tools_and_incomplete_evidence(self):
        build=dict(tool_key='new',binaries={'rust-interp-vm':'new-vm','rust-interp-mir-export':'exporter','rust-interp-rustc-wrapper':'wrapper'},
            composition=dict(kind='scalar-call-guards-composition',compiler_source_key=screen.EXPORTER_KEY))
        build['matched_control']=dict(tool_key='old',binaries=dict(build['binaries'],**{'rust-interp-vm':'old-vm'}),
            composition=dict(kind='heap-address-bias-matched-control',source_commit='ab6adbe8',compiler_source_key=screen.EXPORTER_KEY))
        profile=dict(status='passed',tool_key='new',commands=6,matched_control_key='old',control_code_matches_adopted=True,
            exact_logical_counts_memory_and_entropy=True,exact_per_pc_counts=True,exact_operation_map_reconstruction=True,
            comparisons=[dict(index=i,mode=m,statistics=dict(jit_declined_functions=0,instructions=10,jit_instructions=8,peak_guest_memory=100,entropy_calls=2,entropy_bytes=32),
                    current_native_bytes=100 if m=='control' else 110,scalar_code_bytes=0 if m=='control' else 10,
                    logical_counts=dict(total=10,native=8,interpreted=2,scalar=0 if m=='control' else 5),scalar_calls=0 if m=='control' else 1)
                for i in range(3) for m in ['control','candidate']])
        self.assertTrue(screen.validate_matched_profile(build,profile))
        for field,value in [('commands',3),('matched_control_key','new'),('control_code_matches_adopted',False),
            ('exact_per_pc_counts',False),('exact_operation_map_reconstruction',False)]:
            bad=copy.deepcopy(profile);bad[field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):screen.validate_matched_profile(build,bad)
        for field,value in [('index',2),('mode','candidate'),('scalar_code_bytes',80)]:
            bad=copy.deepcopy(profile);bad['comparisons'][0][field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):screen.validate_matched_profile(build,bad)
        bad=copy.deepcopy(build);bad['matched_control']['binaries']['rust-interp-mir-export']='different'
        with self.assertRaises(AssertionError):screen.validate_matched_profile(bad,profile)

    def test_native_artifact_accepts_nested_workspace_library_and_ignores_test_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve(); source=root/'source'; target=root/'target'
            library=source/'crates/package/src/lib.rs'; library.parent.mkdir(parents=True); library.write_text('')
            target.mkdir(); executable=target/'unit-test'; executable.write_bytes(b'native control')
            text='{ordinary test output\n'+self.artifact(library,executable,False)+'\n'+self.artifact(library,executable)
            self.assertEqual(screen.native_executable(text,source,target),executable)

    def test_native_artifact_rejects_missing_duplicate_and_non_library_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve(); source=root/'source'; target=root/'target'
            source.mkdir(); target.mkdir(); library=source/'lib.rs'; library.write_text('')
            executable=target/'unit-test'; executable.write_bytes(b'native control')
            unit=self.artifact(library,executable)
            for text in ['',unit+'\n'+unit,self.artifact(library,executable,False),self.artifact(library,executable,kind='bin')]:
                with self.assertRaises(AssertionError): screen.native_executable(text,source,target)

    def test_native_artifact_requires_checkout_source_and_exact_target_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve(); source=root/'source'; target=root/'target'
            source.mkdir(); target.mkdir(); library=source/'lib.rs'; library.write_text('')
            executable=target/'unit-test'; executable.write_bytes(b'native control')
            outside=root/'outside'; outside.write_bytes(b'unrelated')
            for lib,exe in [(outside,executable),(library,outside)]:
                with self.assertRaises(AssertionError): screen.native_executable(self.artifact(lib,exe),source,target)

    def control_proofs(self):
        binaries={'rust-interp-vm':'vm','rust-interp-mir-export':'exporter','rust-interp-rustc-wrapper':'wrapper'}
        common=dict(status='passed',tool_key=screen.BASELINE_KEY)
        build=dict(common,binaries=binaries,tests={'test-debug':dict(passed=513,ignored=5),'test-release':dict(passed=513,ignored=5)})
        integration=dict(common,binaries=dict(binaries),all_frozen_inputs_verified=True,workspace_tests_per_profile=513,
            strict_commands=119,project_commands=40,complete_parser_tests=114,remap_internal_commands=130,
            project_artifact_identity=[dict(case=name,exact=True) for name in ['token','folded','pgrust','rg-aot','nushell']])
        cache=dict(common,commands=119,automatic_cache_qualified=True,source_restored=True)
        selection=dict(common,commands=40)
        parser=dict(common,custom_tests_passed=114,source_unchanged=True)
        return [build,integration,cache,selection,parser]

    def test_baseline_rejects_incomplete_or_mismatched_qualification(self):
        self.assertTrue(screen.validate_baseline(*self.control_proofs()))
        for index,field,value in [(0,'tool_key','other'),(2,'commands',118),(2,'source_restored',False),
            (3,'commands',39),(4,'custom_tests_passed',113),(1,'all_frozen_inputs_verified',False),
            (1,'remap_internal_commands',129),(4,'source_unchanged',False)]:
            proofs=self.control_proofs();proofs[index][field]=value
            with self.assertRaises(AssertionError):screen.validate_baseline(*proofs)

    def test_baseline_requires_exact_vm_and_compiler_components(self):
        for binary in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']:
            proofs=self.control_proofs();proofs[0]['binaries'][binary]='different'
            with self.assertRaises(AssertionError):screen.validate_baseline(*proofs)
        proofs=self.control_proofs();proofs[0]['tests']['test-release']['passed']=512
        with self.assertRaises(AssertionError):screen.validate_baseline(*proofs)
        proofs=self.control_proofs();proofs[1]['project_artifact_identity'][-1]['exact']=False
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
