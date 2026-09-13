import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cold_audit_upgrade', ROOT / 'experiments/hir-cold-audit-upgrade/upgrade.py')
cold = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cold
spec.loader.exec_module(cold)


class ColdContinuationTests(unittest.TestCase):
    def history(self):
        return (
            dict(owner=str(cold.PREVIOUS_ROOT), checkpoint=cold.PREVIOUS_CHECKPOINT,
                 commands=copy.deepcopy(cold.engine.old.COMMANDS)),
            dict(revision=cold.PREVIOUS_REVISION, parent=cold.PREVIOUS_PARENT,
                 plan_sha256=cold.PREVIOUS_PLAN_SHA),
            dict(owner=str(cold.PREVIOUS_ROOT), expected_plan_sha256=cold.PREVIOUS_PLAN_SHA,
                 stage='check', status='failed'))

    def test_actual_failed_predecessor_does_not_become_a_passing_or_unrelated_history(self):
        plan, source, terminal = self.history()
        self.assertEqual(cold.predecessor_state(plan, source, {'apply': {}}, terminal), 'failed')
        for field, value in [('revision', cold.PREVIOUS_PARENT), ('parent', 'unrelated'), ('plan_sha256', '0' * 64)]:
            wrong = dict(source, **{field: value})
            with self.assertRaises(RuntimeError):
                cold.predecessor_state(plan, wrong, {'apply': {}}, terminal)
        for completed, end in [({}, terminal), ({'apply': {}, 'check': {}}, terminal),
                ({'apply': {}, 'check': {}}, dict(terminal, status='passed'))]:
            with self.assertRaises(RuntimeError):
                cold.predecessor_state(plan, source, completed, end)
        unit = dict(terminal, stage='unit', status='passed')
        self.assertEqual(cold.predecessor_state(plan, source,
            {'apply': {}, 'check': {}, 'unit': {}}, unit), 'passed')
        with self.assertRaises(RuntimeError):
            cold.predecessor_state(plan, source, {'apply': {}, 'check': {}}, unit)

    def test_successor_cannot_rehash_away_required_archive_commands_or_old_controls(self):
        context = cold.context()
        _, names = cold.checkpoint()
        frozen = {'frozen-source': 'a' * 64}
        plan = dict(owner=str(context.root), source=str(cold.engine.SOURCE), inputs=frozen,
            checkpoint=context.revision, stages=cold.engine.STAGES,
            commands=copy.deepcopy(cold.engine.old.COMMANDS), old_tests=list(context.required_tests),
            added_tests=sorted(set(names) - set(context.required_tests)), initial_free_gib=16,
            running_floor_gib=8, capacity_stop_gib=9,
            archive_paths={'archive': '/owned/previous.tar.gz'},
            archive_hashes={'/owned/previous.tar.gz': cold.PREVIOUS_ARCHIVE_SHA})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'plan.json'
            path.write_text(json.dumps(plan))
            reviewed = cold.sha(path)
            self.assertEqual(cold.engine.load_plan(path, reviewed, frozen, names, context=context), plan)
            wrong_archive = copy.deepcopy(plan)
            wrong_archive['archive_hashes']['/owned/previous.tar.gz'] = '0' * 64
            wrong_command = copy.deepcopy(plan)
            wrong_command['commands']['check'] = ['./x', 'build']
            missing_old = copy.deepcopy(plan)
            missing_old['old_tests'].pop()
            for wrong in [wrong_archive, wrong_command, missing_old]:
                path.write_text(json.dumps(wrong))
                with self.assertRaises(RuntimeError):
                    cold.engine.load_plan(path, reviewed, frozen, names, context=context)
                with self.assertRaises(RuntimeError):
                    cold.engine.load_plan(path, cold.sha(path), frozen, names, context=context)

    def test_all_twenty_previous_and_two_actual_cold_controls_are_required(self):
        manifest, names = cold.checkpoint()
        previous = cold.previous_tests()
        self.assertEqual(len(previous), 20)
        self.assertEqual(len(names), 22)
        self.assertEqual(set(names) - set(previous), {
            'cold_identity_requires_exact_exit_counter_context_owner_and_source',
            'cold_arena_literal_roundtrip_preserves_bytes_suffixes_and_independent_spans'})
        self.assertTrue(manifest['cold_materialization_audit'])
        self.assertFalse(manifest['actual_cache_hit_path'])
        self.assertFalse(manifest['cached_body_materialization'])
        for missing in [previous[0], sorted(set(names) - set(previous))[0]]:
            output = ''.join('test module::' + name + ' ... ok\n' for name in names if name != missing)
            with self.assertRaisesRegex(RuntimeError, missing):
                cold.engine.checked_tests(output, previous, sorted(set(names) - set(previous)))

    def test_context_selection_keeps_original_driver_defaults_and_freezes_shared_engine(self):
        before = cold.engine.default_context()
        context = cold.context()
        self.assertEqual(cold.engine.default_context(), before)
        self.assertEqual(before.here, ROOT / 'experiments/hir-capture-upgrade')
        self.assertEqual(before.revision, cold.PREVIOUS_CHECKPOINT)
        self.assertEqual(len(before.required_tests), 5)
        self.assertIsNone(before.archive_sha256)
        self.assertNotEqual(context.work, before.work)
        frozen = cold.inputs()
        for path in [cold.ENGINE, Path(cold.__file__), ROOT / 'tests/test_hir_capture_upgrade.py',
                     ROOT / 'tests/test_hir_cold_audit_upgrade.py']:
            self.assertEqual(frozen[str(path)], cold.sha(path))


if __name__ == '__main__':
    unittest.main()
