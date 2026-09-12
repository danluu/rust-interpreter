"""Check build measurement controls with synthetic receipts, without running Cargo."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from bench_e2e_workflow import build_metrics, cache_workspace, check_aa_settings, restored_sample
from workflow_measurements import mode_order
import verify_repeated_workflow as verifier


MODES = ['native', 'baseline', 'candidate']
KEY = 'a' * 64


def cpu(user, system):
    return dict(user_seconds=user, system_seconds=system, total_seconds=user + system)


def launch_metrics():
    return dict(build_to_ready_seconds=10.0, cargo_seconds=8.0,
                execution_seconds=4.0, launcher_seconds=15.0,
                build_to_ready_cpu=dict(**cpu(7.0, 2.0), self=cpu(1.0, .5), children=cpu(6.0, 1.5)),
                cargo_cpu=cpu(5.0, 1.0))


class BuildBoundaryTests(unittest.TestCase):
    def test_build_cpu_uses_self_and_children_without_execution_subtraction(self):
        launch = launch_metrics()
        measured = build_metrics(launch)
        self.assertEqual(measured, dict(build_to_ready_seconds=10.0,
            build_to_ready_cpu_seconds=9.0, cargo_cpu_seconds=6.0))
        launch.update(execution_seconds=40.0, launcher_seconds=51.0)
        self.assertEqual(build_metrics(launch), measured)

    def test_invalid_or_missing_boundaries_are_rejected(self):
        for value in [float('nan'), float('inf'), -1.0, True, '10']:
            launch = launch_metrics()
            launch['build_to_ready_seconds'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_metrics(launch)
        for change in [
            lambda x: x.pop('build_to_ready_cpu'),
            lambda x: x['build_to_ready_cpu'].pop('self'),
            lambda x: x['build_to_ready_cpu'].__setitem__('total_seconds', 10.0),
            lambda x: x['build_to_ready_cpu'].__setitem__('self', cpu(2.0, .5)),
            lambda x: x.__setitem__('cargo_cpu', cpu(7.0, 2.0)),
            lambda x: x.__setitem__('build_to_ready_seconds', 7.0),
            lambda x: x.__setitem__('launcher_seconds', 13.0),
        ]:
            launch = launch_metrics()
            change(launch)
            with self.assertRaises(ValueError):
                build_metrics(launch)

    def test_same_build_requires_matching_settings_and_distinct_namespaces(self):
        config = dict(tool_key=KEY, guest_flags=[], inline_leaves=True)
        configs = dict(baseline=copy.deepcopy(config), candidate=copy.deepcopy(config))
        check_aa_settings(configs, dict(baseline=2, candidate=2))
        with self.assertRaises(ValueError):
            check_aa_settings(configs, dict(baseline=2, candidate=4))
        configs['candidate']['guest_flags'] = ['-Zmir-opt-level=3']
        with self.assertRaises(ValueError):
            check_aa_settings(configs, dict(baseline=2, candidate=2))
        with tempfile.TemporaryDirectory() as name:
            scope = Path(name)
            artifact = scope / 'identity' / 'target' / 'program.rbc'
            self.assertEqual(cache_workspace(['launcher', '--cache-namespace', 'run:baseline'],
                artifact, scope, 'run:baseline'), str(scope.resolve() / 'identity'))
            with self.assertRaises(ValueError):
                cache_workspace(['launcher', '--cache-namespace', 'run:candidate'], artifact, scope, 'run:baseline')
            with self.assertRaises(ValueError):
                cache_workspace(['launcher', '--cache-namespace', 'run:baseline'], scope / 'program.rbc', scope, 'run:baseline')

    def test_restoration_is_a_separate_nonedit_after_the_last_cycle(self):
        sample = restored_sample(3, MODES, True, b'original')
        self.assertEqual((sample['cycle'], sample['state'], sample['phase']), (3, -2, 'restored-original'))
        self.assertEqual(sample['source'], b'original')
        self.assertEqual(set(sample['modes']), set(MODES))
        self.assertLess(sample['state'], 0)


class BuildWorkflowVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.raw = self.root / '.work/runs/control'
        self.raw.mkdir(parents=True)
        self.rows = []
        self.transitions = []
        self.report = self.make_report()
        self.root_patch = patch.object(verifier, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def make_report(self):
        states = [0, -1, 1, 2, 3, 4, 5]
        orders = [dict(cycle=c, state=s,
            phase=('cold' if c == 0 else 'anchor') if s == 0 else ('wrong-edit' if s == -1 else 'edit'),
            modes=mode_order(MODES, c, s, True)) for c in range(3) for s in states]
        orders.append(dict(cycle=3, state=-2, phase='restored-original', modes=mode_order(MODES, 3, -2, True)))
        scopes = {m: self.root / '.work/interpreter-workspaces' / KEY / m for m in MODES[1:]}
        previous = dict.fromkeys(MODES)
        for order in orders:
            c, s = order['cycle'], order['state']
            source = hashlib.sha256(str(0 if s == -2 else s).encode()).hexdigest()
            self.transitions.append(dict(**order, source_sha256=source, content_changed=True))
            for mode in order['modes']:
                call = dict(command=['command', '--jobs', '2'], returncode=1 if s == -1 else 0,
                    stdout='0\n', stderr='', cpu=cpu(10.0, 2.0))
                row = dict(cycle=c, state=s, phase=order['phase'], mode=mode,
                    source_sha256=source, previous_source_sha256=previous[mode], tests=['tests::body'],
                    seconds=100.0 if s <= 0 else float(20 + s), cpu_seconds=12.0, calls=[call])
                previous[mode] = source
                if mode == 'native':
                    call['stderr'] = '   Compiling fixture v0.1.0\n'
                    call['stdout'] = ('test tests::body ... FAILED\ntest result: FAILED.\n' if s == -1 else 'test result: ok. 1 passed\n')
                else:
                    payload = source.encode()
                    artifact = self.raw / f'{mode}-{c}-{s}.rbc'
                    artifact.write_bytes(payload)
                    digest = hashlib.sha256(payload).hexdigest()
                    row['artifacts'] = [dict(path=str(artifact.relative_to(self.root)), sha256=digest)]
                    launch = launch_metrics()
                    launch.update(tool_key=KEY, artifact_path=str(scopes[mode] / 'target' / 'program.rbc'),
                        artifact_sha256=digest, artifact_bytes=len(payload))
                    call.update(launch=launch)
                    call['command'] += ['--cache-namespace', 'control:' + mode]
                    call['stderr'] = '    Checking fixture v0.1.0\n'
                    if s == -1:
                        call['stderr'] += 'rust-interp-vm: guest trap: assertion failed\n'
                        call['stdout'] = ''
                    call['stderr'] += 'rust-interp-launch: ' + json.dumps(launch) + '\n'
                    row.update(build_to_ready_seconds=10.0, build_to_ready_cpu_seconds=9.0, cargo_cpu_seconds=6.0)
                self.rows.append(row)
        pairs = []
        for c in range(3):
            for s in range(1, 6):
                pair = dict(cycle=c, state=s, build_to_ready_difference_seconds=0.0, build_to_ready_cpu_difference_seconds=0.0)
                for mode in MODES[1:]:
                    pair.update({mode+'_build_to_ready_seconds':10.0, mode+'_build_to_ready_cpu_seconds':9.0,
                        mode+'_cargo_cpu_seconds':6.0})
                pairs.append(pair)
        return dict(schema_version=2, raw='.work/runs/control', cycles=3, edits=list(range(5)),
            test_source_unchanged=True, wrong_production_edit_rejected=True, batch=True, aa_control=True,
            build_jobs=2, native_control=dict(jobs=2), custom_build_jobs=dict(baseline=2, candidate=2),
            tool_builds={m:dict(tool_key=KEY) for m in MODES[1:]},
            build_controls=dict(package='fixture'),
            cache_namespaces={m:'control:'+m for m in MODES[1:]},
            cache_workspaces={m:str(scopes[m]) for m in MODES[1:]}, mode_orders=orders,
            restored_original=dict(verified=True, source_sha256=self.rows[0]['source_sha256'], cycle=3,
                state=-2, commands=3, excluded_from_edited_medians=True),
            build_metrics=dict(median_seconds=dict(baseline=10.0, candidate=10.0),
                median_cpu_seconds=dict(baseline=9.0, candidate=9.0)),
            median_seconds={m:23.0 for m in MODES}, median_cpu_seconds={m:12.0 for m in MODES},
            cold_success_seconds={m:100.0 for m in MODES}, cycle_anchor_seconds=[{}, {}],
            comparison=dict(baseline_tool_key=KEY, candidate_tool_key=KEY, pairs=pairs))

    def verify(self):
        (self.raw / 'records.json').write_text(json.dumps(self.rows))
        (self.raw / 'source-transitions.json').write_text(json.dumps(self.transitions))
        return verifier.verify(self.report)

    def test_complete_aa_history_and_final_restore_are_verified(self):
        verified = self.verify()
        self.assertEqual((verified['commands'], verified['edited_pairs'], verified['exact_artifact_hashes_verified']), (66, 15, 44))
        self.assertTrue(verified['build_to_ready_metrics_verified'])
        self.assertTrue(verified['restored_original_build_and_execution_verified'])
        self.assertTrue(verified['identical_build_isolated_caches_verified'])

    def test_shared_cache_is_rejected_even_with_identical_tool_keys(self):
        self.report['cache_workspaces']['candidate'] = self.report['cache_workspaces']['baseline']
        with self.assertRaisesRegex(RuntimeError, 'not isolated'):
            self.verify()

    def test_different_suite_preparation_is_not_an_aa_control(self):
        self.report['compare_isolated_batches'] = True
        with self.assertRaisesRegex(RuntimeError, 'identical batched paired jobs/settings'):
            self.verify()

    def test_aa_and_restoration_each_require_batched_comparisons(self):
        self.report.pop('build_metrics')
        self.report['batch'] = False
        with self.assertRaisesRegex(RuntimeError, 'restoration verification requires a batched paired comparison'):
            self.verify()
        self.report.pop('restored_original')
        with self.assertRaisesRegex(RuntimeError, 'A/A control requires identical batched paired jobs/settings'):
            self.verify()

    def test_case_file_history_is_checked_before_separate_restoration(self):
        self.report['case_file'] = {'snapshot': 'case.json'}
        with patch('workflow_case_file.verify_snapshot') as check_case:
            verified = self.verify()
        _, report, rows = check_case.call_args.args
        self.assertEqual((len(report['mode_orders']), len(rows)), (21, 63))
        self.assertTrue(all(row['state'] != -2 for row in rows))
        self.assertEqual(verified['commands'], 66)
        self.assertTrue(verified['restored_original_build_and_execution_verified'])

    def test_namespace_must_match_the_executed_command(self):
        row = next(r for r in self.rows if r['mode'] == 'candidate')
        row['calls'][0]['command'][-1] = 'control:baseline'
        with self.assertRaisesRegex(ValueError, 'namespace differs'):
            self.verify()

    def test_negative_compile_failure_cannot_replace_runtime_failure(self):
        row = next(r for r in self.rows if r['state'] == -1 and r['mode'] == 'candidate')
        row['calls'][0]['stderr'] = 'Checking fixture v0.1.0\nerror: could not compile\n'
        with self.assertRaisesRegex(RuntimeError, 'guest assertion'):
            self.verify()

    def test_restore_must_have_fresh_compilation_and_original_source(self):
        row = next(r for r in self.rows if r['state'] == -2 and r['mode'] == 'candidate')
        call = row['calls'][0]
        previous = call['stderr']
        call['stderr'] = previous.replace('Checking fixture', 'Fresh fixture')
        with self.assertRaisesRegex(RuntimeError, 'freshly compiled'):
            self.verify()
        call['stderr'] = previous
        row['source_sha256'] = 'wrong restored original'
        with self.assertRaisesRegex(RuntimeError, 'original source'):
            self.verify()

    def test_missing_restore_or_control_in_edited_pairs_is_rejected(self):
        original = self.rows
        self.rows = self.rows[:-3]
        with self.assertRaisesRegex(RuntimeError, 'command order'):
            self.verify()
        self.rows = original
        self.report['comparison']['pairs'][-1]['state'] = -2
        with self.assertRaisesRegex(RuntimeError, 'pairs include a control'):
            self.verify()

    def test_edited_build_medians_and_pairs_must_match_raw_receipts(self):
        self.report['build_metrics']['median_seconds']['baseline'] = 11.0
        with self.assertRaisesRegex(RuntimeError, 'build medians'):
            self.verify()
        self.report['build_metrics']['median_seconds']['baseline'] = 10.0
        self.report['comparison']['pairs'][0]['candidate_build_to_ready_cpu_seconds'] = 8.0
        with self.assertRaisesRegex(RuntimeError, 'paired build timing'):
            self.verify()

    def test_legacy_receipts_need_no_new_metrics_or_restoration(self):
        self.rows = [r for r in self.rows if r['state'] != -2]
        self.transitions.pop()
        self.report['mode_orders'].pop()
        for field in ['build_metrics', 'aa_control', 'restored_original', 'cache_namespaces', 'cache_workspaces', 'build_controls']:
            self.report.pop(field)
        verified = self.verify()
        self.assertEqual(verified['commands'], 63)
        self.assertNotIn('build_to_ready_metrics_verified', verified)
        self.assertNotIn('restored_original_build_and_execution_verified', verified)


if __name__ == '__main__':
    unittest.main()
