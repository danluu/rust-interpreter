"""Synthetic arithmetic/schema counterexamples, never benchmark qualification."""
import copy
import hashlib
from pathlib import Path
import statistics
import unittest

import assess


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


CANDIDATE_TOOL = digest('synthetic candidate tool')


def synthetic_history(aa, baseline=None, candidate=None):
    baseline = baseline or [10.0]*5
    candidate = candidate or ([10.0]*5 if aa else [8.0]*5)
    arms = dict(baseline=assess.BASELINE, candidate=assess.BASELINE if aa else
                assess.CANDIDATE | dict(tool_key=CANDIDATE_TOOL))
    tests = ['synthetic_test_'+str(n) for n in range(6)]
    rows = []
    for cycle, state, phase in assess.STATES:
        source = digest('synthetic source '+str(0 if state == -2 else state))
        for mode in assess.MODES:
            seconds = (baseline if mode == 'baseline' else candidate)[state-1] if state > 0 and mode != 'native' else 100.0
            launch = dict(function_cache='off', borrowck_cache='off', cargo_seconds=1.0,
                          execution_seconds=2.0, artifact_hash_seconds=0.1, launcher_seconds=0.2)
            row = dict(cycle=cycle, state=state, phase=phase, mode=mode, tests=tests,
                source_sha256=source, seconds=seconds, cpu_seconds=seconds*2,
                calls=[dict(returncode=1 if state == -1 else 0, launch=launch)])
            if mode != 'native':
                row.update(engine='jit', tool_key=arms[mode]['tool_key'],
                    artifacts=[dict(sha256=digest('synthetic RBC '+str(state)))],
                    build_to_ready_seconds=1.0, build_to_ready_cpu_seconds=2.0, cargo_cpu_seconds=1.5)
            rows.append(row)
    tools = {mode: dict(engine='jit', tool_key=arms[mode]['tool_key'], guest_rustflags=list(assess.FLAGS),
        inline_leaves=True, jit_resumable_calls=True, jit_persistent_registers=True,
        jit_native_calls=False, jit_native_call_stubs=False, trap_unsupported_calls=False,
        run_try_callbacks=False, vm_sha256=digest('synthetic same VM'),
        exporter_sha256=digest('synthetic exporter '+arms[mode]['tool_key'])) for mode in assess.CUSTOM}
    pairs = []
    for state in range(1, 6):
        group = {r['mode']: r for r in rows if r['state'] == state}
        b, c, n = [group[m] for m in ('baseline', 'candidate', 'native')]
        pairs.append(dict(cycle=0, state=state, source_sha256=b['source_sha256'],
            baseline_seconds=b['seconds'], candidate_seconds=c['seconds'], native_seconds=n['seconds'],
            baseline_cpu_seconds=b['cpu_seconds'], candidate_cpu_seconds=c['cpu_seconds'], native_cpu_seconds=n['cpu_seconds'],
            difference_seconds=c['seconds']-b['seconds'], cpu_difference_seconds=c['cpu_seconds']-b['cpu_seconds'],
            identical_bytecode=True, stage_seconds={m: {k: group[m]['calls'][0]['launch'][k]
                for k in assess.STAGES} for m in assess.CUSTOM},
            baseline_build_to_ready_seconds=1.0, candidate_build_to_ready_seconds=1.0,
            baseline_build_to_ready_cpu_seconds=2.0, candidate_build_to_ready_cpu_seconds=2.0,
            baseline_cargo_cpu_seconds=1.5, candidate_cargo_cpu_seconds=1.5,
            build_to_ready_difference_seconds=0.0, build_to_ready_cpu_difference_seconds=0.0))
    summary = dict(project='ruff', schema_version=2, cycles=1, edits=['edit'+str(n) for n in range(5)],
        batch=True, aa_control=aa, initial_mode_order=['candidate', 'native', 'baseline'] if aa else list(assess.MODES),
        test_source_unchanged=True, wrong_production_edit_rejected=True, compare_isolated_batches=False,
        cargo_timings=False, vary_selection=False, trap_unsupported_calls=False, run_try_callbacks=False,
        check_floor=None, instruction_limit=1000000000, allocation_limit=150000,
        build_jobs=2, custom_build_jobs=dict(baseline=2, candidate=2),
        native_control=dict(profile='repository', jobs=2, test_threads='1', toolchain='nightly-2026-09-08'),
        tests=tests, case_sha256=digest('synthetic same case'), revision='synthetic revision',
        scripts_sha256={'synthetic.py': digest('synthetic source')}, tool_builds=tools,
        runtime_arms=dict(arms={m: dict(tool_key=arms[m]['tool_key'], runtime=dict(key=arms[m]['runtime_key']),
            prepared_std=dict(key=arms[m]['std_key'])) for m in assess.CUSTOM}),
        std_mir_by_mode={m: dict(key=arms[m]['std_key'], setup_seconds=1.0, build_seconds=1.0) for m in assess.CUSTOM},
        cache_workspaces={m: '/synthetic/'+str(aa)+'/'+m for m in assess.CUSTOM},
        comparison=dict(engine='jit', identical_bytecode_required=True, pairs=pairs,
            baseline_tool_key=arms['baseline']['tool_key'], candidate_tool_key=arms['candidate']['tool_key']),
        restored_original=dict(verified=True, source_sha256=digest('synthetic source 0'), cycle=1,
            state=-2, commands=3, excluded_from_edited_medians=True),
        samples=[{k: copy.deepcopy(v) for k, v in r.items() if k != 'calls'} for r in rows])
    verification = dict(schema_version=1, commands=24, cycles=1, edited_pairs=5,
        measurement_controls_verified=True, build_to_ready_metrics_verified=True,
        restored_original_build_and_execution_verified=True, paired_bytecode_identical=True)
    if aa:
        verification['identical_build_isolated_caches_verified'] = True
    return dict(summary=summary, records=rows, verification=verification)


class AssessorTests(unittest.TestCase):
    def setUp(self):
        self.ab, self.aa = synthetic_history(False), synthetic_history(True)

    def result(self):
        return assess.assess(self.ab, self.aa, CANDIDATE_TOOL)

    def test_median_of_ratios_is_not_ratio_of_medians(self):
        self.ab = synthetic_history(False, [1.0, 2.0, 3.0, 100.0, 200.0], [10.0, 20.0, 1.0, 50.0, 100.0])
        result = self.result()
        self.assertEqual(result['B'], 0.5)
        self.assertGreater(statistics.median([10, 20, 1, 50, 100])/statistics.median([1, 2, 3, 100, 200]), 1)
        self.assertEqual(result['decision'], 'advance')

    def test_native_thread_count_preserves_runner_argument_string(self):
        self.assertEqual(self.result()['decision'], 'advance')
        self.ab['summary']['native_control']['test_threads'] = 1
        with self.assertRaises(ValueError): self.result()

    def test_absolute_deviations_are_taken_before_median(self):
        self.aa = synthetic_history(True, [10.0]*5, [5.0, 9.0, 10.0, 11.0, 20.0])
        self.assertAlmostEqual(self.result()['V'], 0.1)
        self.assertEqual(abs(statistics.median([0.5, 0.9, 1.0, 1.1, 2.0])-1), 0)

    def test_equality_parks_and_strict_improvement_advances(self):
        self.ab = synthetic_history(False, [8.0]*5, [7.0]*5)
        self.aa = synthetic_history(True, [8.0]*5, [9.0]*5)
        self.assertEqual(self.result()['B_plus_V'], 1.0)
        self.assertEqual(self.result()['decision'], 'park')
        self.ab = synthetic_history(False, [8.0]*5, [6.0]*5)
        self.assertEqual(self.result()['decision'], 'advance')

    def test_controls_retained_and_excluded_from_criterion(self):
        result = self.result()
        self.assertEqual(result['B'], 0.8)
        ab = result['histories']['ab']
        self.assertEqual(ab['subtotals']['restored-original']['candidate']['seconds'], 100.0)
        self.assertEqual(ab['all_command_totals']['seconds'], 1490.0)
        self.assertEqual(ab['build_to_ready_ratios'], [1.0]*5)
        self.assertEqual(len(ab['samples']), 24)
        self.assertFalse(result['qualification_gate_complete'])
        self.assertFalse(result['performance_target_met'])
        self.assertIsNone(result['owner_closures'])

    def test_missing_duplicate_or_extra_rows_reject(self):
        for change in ('missing', 'duplicate', 'extra-state'):
            with self.subTest(change=change):
                ab = copy.deepcopy(self.ab)
                if change == 'missing': ab['records'].pop()
                elif change == 'duplicate': ab['records'][-1] = copy.deepcopy(ab['records'][0])
                else: ab['records'][-1]['state'] = 6
                with self.assertRaises(ValueError): assess.assess(ab, self.aa, CANDIDATE_TOOL)

    def test_invalid_timings_and_overflow_reject(self):
        for value in (0, -1, True, '1', float('nan'), float('inf'), -float('inf')):
            with self.subTest(value=value):
                ab = copy.deepcopy(self.ab); ab['records'][6]['seconds'] = value
                with self.assertRaises(ValueError): assess.assess(ab, self.aa, CANDIDATE_TOOL)
        ab = synthetic_history(False, [1e-308]*5, [1e308]*5)
        with self.assertRaises(ValueError): assess.assess(ab, self.aa, CANDIDATE_TOOL)

    def test_summary_pair_and_sample_tampering_reject(self):
        for field in ('candidate_seconds', 'native_cpu_seconds', 'identical_bytecode', 'stage_seconds'):
            with self.subTest(field=field):
                ab = copy.deepcopy(self.ab); ab['summary']['comparison']['pairs'][0][field] = None
                with self.assertRaises(ValueError): assess.assess(ab, self.aa, CANDIDATE_TOOL)
        self.ab['summary']['samples'][0]['seconds'] = 1.0
        with self.assertRaises(ValueError): self.result()

    def test_source_tests_phase_and_bytecode_mismatch_reject(self):
        for field, value in [('source_sha256', digest('other')), ('tests', ['other']), ('phase', 'cold'),
                             ('artifacts', [dict(sha256=digest('other RBC'))])]:
            with self.subTest(field=field):
                ab = copy.deepcopy(self.ab); ab['records'][7][field] = value
                ab['summary']['samples'][7][field] = copy.deepcopy(value)
                with self.assertRaises(ValueError): assess.assess(ab, self.aa, CANDIDATE_TOOL)

    def test_missing_verification_or_wrong_call_outcome_reject(self):
        self.aa['verification']['identical_build_isolated_caches_verified'] = False
        with self.assertRaises(ValueError): self.result()
        self.aa = synthetic_history(True)
        self.ab['records'][0]['calls'][0]['returncode'] = 1
        with self.assertRaises(ValueError): self.result()

    def test_cross_history_binding_vm_and_cache_mismatch_reject(self):
        for field in ('case_sha256', 'revision', 'scripts_sha256'):
            with self.subTest(field=field):
                aa = copy.deepcopy(self.aa); aa['summary'][field] = 'other'
                with self.assertRaises(ValueError): assess.assess(self.ab, aa, CANDIDATE_TOOL)
        self.ab['summary']['tool_builds']['candidate']['vm_sha256'] = digest('other VM')
        with self.assertRaises(ValueError): self.result()
        self.ab = synthetic_history(False)
        self.aa['summary']['cache_workspaces'] = copy.deepcopy(self.ab['summary']['cache_workspaces'])
        with self.assertRaises(ValueError): self.result()

    def test_compatibility_hir_and_cache_settings_reject(self):
        for field, value in [('trap_unsupported_calls', True), ('run_try_callbacks', True),
                             ('guest_rustflags', ['-Zhir-body-cache-reuse=true'])]:
            with self.subTest(field=field):
                ab = copy.deepcopy(self.ab); ab['summary']['tool_builds']['candidate'][field] = value
                with self.assertRaises(ValueError): assess.assess(ab, self.aa, CANDIDATE_TOOL)
        self.ab['records'][1]['calls'][0]['launch']['function_cache'] = 'auto'
        with self.assertRaises(ValueError): self.result()


def synthetic_owners():
    """Invented documents for pure rejection tests; no actual process evidence."""
    plan = dict(path='/synthetic/plan.json', sha256=digest('synthetic plan'))
    result_ref = dict(path='/synthetic/result.json', sha256=digest('synthetic result'))
    parent = dict(history='ab', status='finished', observer_verified=True,
        supervisor_may_be_live=False, controller_may_be_live=False,
        returncode=0, controller_returncode=0, pid=102, parent_pid=101,
        started_at=10.0, finished_at=16.0, plan=plan, result=result_ref,
        session_wall_seconds=6.0, child_cpu=dict(user_seconds=1.5, system_seconds=0.5, total_seconds=2.0))
    outer = dict(status='finished', returncode=0, supervisor_pid=102,
        supervisor_parent_pid=101, child_pid=103, started_at=11.0, finished_at=15.0)
    observer = dict(history='ab', status='passed', pid=103, parent_pid=102,
        started_at=12.0, finished_at=14.0, plan=plan, result=result_ref,
        previous=None, observer_os_closure_observed=False, performance_qualified=False)
    result = dict(history='ab', status='passed', plan=plan, previous=None,
        observer_os_closure_observed=False, performance_qualified=False)
    return [parent, outer, observer, result]


class SuccessorTests(unittest.TestCase):
    def test_enabled_flags_and_fresh_routes_are_required(self):
        ab, aa = synthetic_history(False), synthetic_history(True)
        result = assess.assess(ab, aa, CANDIDATE_TOOL)
        self.assertEqual(result['decision'], 'advance')
        self.assertFalse(result['fastest_configuration_qualified'])
        self.assertFalse(result['holdout_admitted'])
        self.assertEqual(assess.FLAGS, ['-Zmir-opt-level=3', '-Zhir-body-cache-capture=true', '-Zhir-body-cache-reuse=true'])
        for history in ('ab', 'aa'):
            run, execution, observer, outer = assess.history_routes(Path('/synthetic/root'), history)
            self.assertEqual(run, 'hir-options-hash-ruff-screen-'+history+'-02')
            self.assertEqual([p.name for p in (execution, observer, outer)],
                             [run+'-'+suffix for suffix in ('execution', 'observer', 'supervisor')])
        with self.assertRaises(ValueError): assess.history_routes(Path('/synthetic/root'), 'replacement')
        for selected, mode in ((ab, 'candidate'), (ab, 'baseline'), (aa, 'candidate')):
            saved = selected['summary']['tool_builds'][mode]['guest_rustflags']
            selected['summary']['tool_builds'][mode]['guest_rustflags'] = [f.replace('=true', '=false') for f in saved]
            with self.assertRaises(ValueError): assess.assess(ab, aa, CANDIDATE_TOOL)
            selected['summary']['tool_builds'][mode]['guest_rustflags'] = saved

    def test_distinct_parent_os_closure_retains_session_totals(self):
        result = assess.owner_closure(*synthetic_owners(), 'ab')
        self.assertEqual(result['wall_seconds'], 6.0)
        self.assertEqual(result['child_cpu']['total_seconds'], 2.0)
        self.assertIn('queues', result['scope'])
        self.assertIn('excludes parent CPU', result['scope'])

    def test_live_failed_or_claimed_self_reap_rejects(self):
        for row, field, value in ((0, 'supervisor_may_be_live', True), (0, 'controller_may_be_live', True),
                (0, 'observer_verified', False), (0, 'returncode', False), (0, 'returncode', 1),
                (0, 'controller_returncode', 1), (1, 'returncode', 1),
                (2, 'observer_os_closure_observed', True), (3, 'performance_qualified', True),
                (2, 'status', 'failed'), (0, 'error', 'post-wait publication failed')):
            with self.subTest(row=row, field=field, value=value):
                owners = synthetic_owners(); owners[row][field] = value
                with self.assertRaises(ValueError): assess.owner_closure(*owners, 'ab')

    def test_owner_identity_chronology_and_association_rejects(self):
        for row, field, value in ((0, 'pid', 999), (1, 'child_pid', 999),
                (1, 'supervisor_parent_pid', True), (2, 'started_at', 9.0),
                (1, 'finished_at', 17.0), (3, 'plan', {}), (2, 'result', {}),
                (3, 'previous', {}), (3, 'history', 'aa')):
            with self.subTest(row=row, field=field):
                owners = synthetic_owners(); owners[row][field] = value
                with self.assertRaises(ValueError): assess.owner_closure(*owners, 'ab')

    def test_invalid_session_cpu_or_wall_rejects(self):
        for field, value in (('total_seconds', 999), ('system_seconds', -1), ('user_seconds', True)):
            owners = synthetic_owners(); owners[0]['child_cpu'][field] = value
            with self.assertRaises(ValueError): assess.owner_closure(*owners, 'ab')
        for value in (0, -1, float('nan'), float('inf'), True):
            owners = synthetic_owners(); owners[0]['session_wall_seconds'] = value
            with self.assertRaises(ValueError): assess.owner_closure(*owners, 'ab')


if __name__ == '__main__':
    unittest.main()
