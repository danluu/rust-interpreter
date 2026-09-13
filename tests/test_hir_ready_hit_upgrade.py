import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ready_hit_upgrade', ROOT / 'experiments/hir-ready-hit-upgrade/upgrade.py')
ready = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ready
spec.loader.exec_module(ready)


class ReadyHitContinuationTests(unittest.TestCase):
    def test_actual_cold_unit_completion_cannot_be_replaced_by_failure_or_partial_check(self):
        plan = dict(owner=str(ready.PREVIOUS_ROOT), checkpoint=ready.PREVIOUS_CHECKPOINT,
                    commands=copy.deepcopy(ready.engine.old.COMMANDS))
        source = dict(revision=ready.PREVIOUS_REVISION, parent=ready.PREVIOUS_PARENT,
                      plan_sha256=ready.PREVIOUS_PLAN_SHA)
        end = dict(owner=str(ready.PREVIOUS_ROOT), stage='unit', status='passed',
                   plan_sha256=ready.PREVIOUS_PLAN_SHA)
        complete = dict(apply={}, check={}, unit={})
        self.assertEqual(ready.predecessor_state(plan, source, complete, end), 'passed')
        for completed, terminal in [({'apply': {}, 'check': {}}, end),
                (complete, dict(end, status='failed')), (complete, dict(end, stage='check'))]:
            with self.assertRaises(RuntimeError):
                ready.predecessor_state(plan, source, completed, terminal)
        for field in ['revision', 'parent', 'plan_sha256']:
            with self.assertRaises(RuntimeError):
                ready.predecessor_state(plan, dict(source, **{field: '0' * 64}), complete, end)

    def test_all_twenty_two_previous_and_four_replay_controls_are_required(self):
        manifest, names = ready.checkpoint()
        previous = ready.previous_tests()
        added = sorted(set(names) - set(previous))
        self.assertEqual(len(previous), 22)
        self.assertEqual(len(names), 26)
        self.assertEqual(set(added), {
            'preflight_binding_and_debug_reservations_never_overwrite',
            'preflight_rejects_occupied_body_slots_and_preserves_exclusive_end',
            'replay_trait_equality_retains_imports_lints_order_and_duplicates',
            'valid_checksum_does_not_bypass_tree_preflight'})
        self.assertTrue(manifest['actual_cache_hit_path'])
        self.assertTrue(manifest['cached_body_materialization'])
        self.assertFalse(manifest['reuse_default'])
        for missing in [previous[0], *added]:
            output = ''.join('test module::' + name + ' ... ok\n' for name in names if name != missing)
            with self.assertRaisesRegex(RuntimeError, missing):
                ready.engine.checked_tests(output, previous, added)

    def test_stage_entry_verifies_referenced_payload_and_propagates_missing_member_failure(self):
        paths = {key: str(ready.REFERENCED_ARCHIVE / name) for key, name in
                 [('archive', 'evidence.tar.gz'), ('manifest', 'manifest.json'), ('summary', 'summary.json')]}
        hashes = {paths[key]: value for key, value in ready.REFERENCED_HASHES.items()}
        plan = dict(archive_paths=paths, archive_hashes=hashes,
                    archive_required={'/previous/patched-source.rs': 'a' * 64})
        marker = object()
        with patch.object(ready, 'checkpoint', return_value=marker), \
                patch.object(ready, 'predecessor_plan', return_value=plan), \
                patch.object(ready, 'sha', side_effect=lambda path: hashes[str(path)]), \
                patch.object(ready.engine, 'verify_archive') as verify:
            self.assertIs(ready.stage_checkpoint(), marker)
            verify.assert_called_once_with(paths['archive'], paths['manifest'], paths['summary'],
                                           plan['archive_required'])
            verify.side_effect = RuntimeError('historical archive is incomplete')
            with self.assertRaisesRegex(RuntimeError, 'incomplete'):
                ready.stage_checkpoint()
        for field in ['archive_paths', 'archive_hashes', 'archive_required']:
            wrong = copy.deepcopy(plan)
            wrong[field] = {}
            with self.assertRaises(RuntimeError):
                ready.historical_reference(wrong)
        with patch.object(ready, 'sha', return_value='0' * 64):
            with self.assertRaisesRegex(RuntimeError, 'cold-audit plan changed'):
                ready.predecessor_plan()

    def test_shared_engine_defaults_and_fixed_plan_constraints_survive_third_context(self):
        original = ready.engine.default_context()
        cold = ready.cold.context()
        context = ready.context()
        self.assertEqual(ready.engine.default_context(), original)
        self.assertEqual(ready.cold.context(), cold)
        self.assertNotEqual(context.work, original.work)
        self.assertNotEqual(context.work, cold.work)
        self.assertIs(context.read_checkpoint, ready.stage_checkpoint)
        frozen = ready.inputs()
        for path in [ready.COLD, ready.cold.ENGINE, Path(ready.__file__),
                     ROOT / 'tests/test_hir_capture_upgrade.py',
                     ROOT / 'tests/test_hir_cold_audit_upgrade.py',
                     ROOT / 'tests/test_hir_ready_hit_upgrade.py']:
            self.assertEqual(frozen[str(path)], ready.sha(path))
        _, names = ready.checkpoint()
        plan = dict(owner=str(context.root), source=str(ready.engine.SOURCE), inputs=frozen,
            checkpoint=context.revision, stages=ready.engine.STAGES,
            commands=copy.deepcopy(ready.engine.old.COMMANDS), old_tests=list(context.required_tests),
            added_tests=sorted(set(names) - set(context.required_tests)), initial_free_gib=16,
            running_floor_gib=8, capacity_stop_gib=9,
            archive_paths={'archive': '/owned/cold.tar.gz'},
            archive_hashes={'/owned/cold.tar.gz': ready.PREVIOUS_ARCHIVE_SHA})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'plan.json'
            path.write_text(json.dumps(plan))
            reviewed = ready.sha(path)
            self.assertEqual(ready.engine.load_plan(path, reviewed, frozen, names, context=context), plan)
            wrong_archive = copy.deepcopy(plan)
            wrong_archive['archive_hashes']['/owned/cold.tar.gz'] = ready.cold.PREVIOUS_ARCHIVE_SHA
            wrong_command = copy.deepcopy(plan)
            wrong_command['commands']['unit'] = ['./x', 'test', '--test-args', 'only-one']
            missing_old = copy.deepcopy(plan)
            missing_old['old_tests'].pop()
            missing_new = copy.deepcopy(plan)
            missing_new['added_tests'].pop()
            for wrong in [wrong_archive, wrong_command, missing_old, missing_new]:
                path.write_text(json.dumps(wrong))
                for expected in [reviewed, ready.sha(path)]:
                    with self.assertRaises(RuntimeError):
                        ready.engine.load_plan(path, expected, frozen, names, context=context)


if __name__ == '__main__':
    unittest.main()
