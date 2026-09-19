import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fixture_env_upgrade',ROOT/'experiments/hir-fixture-env-upgrade/upgrade.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)


class FixtureEnvironmentUpgradeTests(unittest.TestCase):
    def test_snapshot_changes_only_fixture_phase_diagnostics_and_identity_preserving_all_twenty_six(self):
        current,names=m.checkpoint();old,old_names=m.native.checkpoint()
        self.assertEqual(names,old_names);self.assertEqual(len(names),26)
        self.assertEqual(len(current['files']),25)
        self.assertEqual({n for n in current['files'] if current['files'][n]!=old['files'][n]},
            {'tests/run-make/hir-body-cache-capture/rmake.rs','compiler/rustc_ast_lowering/src/body_cache/source_identity.rs',
             'compiler/rustc_ast_lowering/src/body_cache/mod.rs'})
        self.assertTrue(current['actual_cache_hit_path']);self.assertFalse(current['reuse_default'])
        sentinel=object()
        with patch.object(m.engine,'arguments',return_value=sentinel),patch.object(m.engine,'execute') as execute:
            m.main();self.assertIs(execute.call_args.args[0],sentinel)
            self.assertEqual(execute.call_args.kwargs['context'].revision,m.CHECKPOINT)
        with patch.object(m,'PATCH_SHA','0'*64):
            with self.assertRaisesRegex(RuntimeError,'wrong fixture-environment checkpoint'):m.checkpoint()

    def test_failed_native_archive_cannot_be_replaced_by_success_or_wrong_source(self):
        summary=json.loads((ROOT/'results/hir-native-correctness-failed-01/summary.json').read_text())
        manifest=json.loads((ROOT/'results/hir-native-correctness-failed-01/manifest.json').read_text())
        result=m.failed_native_reference(summary,manifest)
        self.assertEqual(len(result['required']),203)
        for field,value in [('source_revision','0'*40),('native_hit_qualified',True),('verified_cache_hit_lines',1)]:
            wrong=copy.deepcopy(summary);wrong[field]=value
            with self.assertRaises(RuntimeError):m.failed_native_reference(wrong,manifest)
        wrong=copy.deepcopy(summary);wrong['stages'][1]['status']='passed'
        with self.assertRaises(RuntimeError):m.failed_native_reference(wrong,manifest)
        wrong=copy.deepcopy(summary);wrong['source_postguard']['all_tracked_content_verified_twice']=False
        with self.assertRaises(RuntimeError):m.failed_native_reference(wrong,manifest)
        bad=copy.deepcopy(manifest);del bad[str(m.FAILED_TERMINAL).lstrip('/')]
        with self.assertRaises(RuntimeError):m.failed_native_reference(summary,bad)

    @patch.object(m, 'FAILURE', ROOT / 'results/hir-native-correctness-failed-01')
    def test_separate_archive_verification_propagates_any_missing_payload(self):
        references=[dict(paths=dict(archive=f'/a/{i}.tar.gz',manifest=f'/a/{i}.json',summary=f'/a/{i}-summary.json'),
                         hashes={},required={f'/old/{i}.rs':'a'*64}) for i in range(3)]
        marker=object()
        with patch.object(m,'checkpoint',return_value=marker),patch.object(m,'references',return_value=references),\
                patch.object(m.engine,'verify_archive') as verify:
            self.assertIs(m.stage_checkpoint(),marker);self.assertEqual(verify.call_count,3)
            verify.side_effect=RuntimeError('historical archive incomplete')
            with self.assertRaisesRegex(RuntimeError,'incomplete'):m.stage_checkpoint()
        with patch.object(m,'sha',return_value='0'*64):
            with self.assertRaisesRegex(RuntimeError,'fixed native failure archive changed'):m.read_failure()

    def test_fourth_context_retains_fixed_engine_commands_capacity_and_reviewed_archive(self):
        original=m.engine.default_context();context=m.context();names=m.checkpoint()[1]
        self.assertEqual(m.engine.default_context(),original);self.assertNotEqual(context.work,original.work)
        plan=dict(owner=str(context.root),source=str(m.engine.SOURCE),inputs={'helper':'a'*64},checkpoint=context.revision,
                  stages=m.engine.STAGES,commands=copy.deepcopy(m.engine.old.COMMANDS),old_tests=list(names),added_tests=[],
                  initial_free_gib=16,running_floor_gib=8,capacity_stop_gib=9,
                  archive_paths={'archive':'/ready.tar.gz'},archive_hashes={'/ready.tar.gz':m.PREVIOUS_ARCHIVE_SHA})
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'plan.json';p.write_text(json.dumps(plan));reviewed=m.sha(p)
            self.assertEqual(m.engine.load_plan(p,reviewed,plan['inputs'],names,context=context),plan)
            for field,value in [('initial_free_gib',8),('old_tests',names[:-1]),('added_tests',['fabricated'])]:
                bad=copy.deepcopy(plan);bad[field]=value;p.write_text(json.dumps(bad))
                for digest in [reviewed,m.sha(p)]:
                    with self.assertRaises(RuntimeError):m.engine.load_plan(p,digest,plan['inputs'],names,context=context)
            bad=copy.deepcopy(plan);bad['archive_hashes']['/ready.tar.gz']=m.FAILURE_HASHES['archive'];p.write_text(json.dumps(bad))
            with self.assertRaises(RuntimeError):m.engine.load_plan(p,m.sha(p),plan['inputs'],names,context=context)

if __name__=='__main__':unittest.main()
