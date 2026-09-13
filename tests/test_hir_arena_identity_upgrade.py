import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hir_arena_identity_upgrade',
    ROOT / 'experiments/hir-arena-identity-upgrade/upgrade.py')
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


class ArenaIdentityUpgradeTests(unittest.TestCase):
    def test_repair_keeps_every_old_control_and_changes_only_arena_identity(self):
        current, names = m.checkpoint()
        previous, old_names = m.diagnostic.upgrade.checkpoint()
        self.assertEqual(names, sorted([*old_names, m.NEW_TEST]))
        self.assertEqual(len(names), 27)
        self.assertEqual({n for n in current['files'] if current['files'][n] != previous['files'][n]},
            {'compiler/rustc_ast_lowering/src/body_cache/mod.rs',
             'compiler/rustc_ast_lowering/src/body_cache/source_identity.rs'})
        self.assertFalse(current['reuse_default'])
        with patch.object(m, 'PATCH_SHA', '0' * 64):
            with self.assertRaisesRegex(RuntimeError, 'wrong arena-identity'): m.checkpoint()

    def test_diagnostic_cannot_be_promoted_to_native_success_or_change_source_or_observation(self):
        reference = m.diagnostic_reference()
        self.assertEqual(len(reference['required']), 250)
        original_loads = json.loads
        for field, value in [('native_qualified', True), ('source_revision', '0' * 40),
                             ('executed_native_binary', True), ('compiler_returncode', 1)]:
            def altered(data, *args, **kwargs):
                result = original_loads(data, *args, **kwargs)
                if isinstance(result, dict) and result.get('status') == 'diagnostic-completed':
                    result[field] = value
                return result
            with self.subTest(field=field), patch.object(m.json, 'loads', side_effect=altered):
                with self.assertRaisesRegex(RuntimeError, 'must not become native hit qualification'):
                    m.diagnostic_reference()
        def wrong_observation(data, *args, **kwargs):
            result = original_loads(data, *args, **kwargs)
            if isinstance(result, dict) and result.get('records') == 24:
                result['state_counts'] = {'cold-tree-and-journal-after-stock-lowering': 24}
            return result
        with patch.object(m.json, 'loads', side_effect=wrong_observation):
            with self.assertRaisesRegex(RuntimeError, 'observed cold-audit failure changed'):
                m.diagnostic_reference()

    def test_all_five_separate_archives_are_verified_and_failures_propagate(self):
        refs = [dict(paths=dict(archive=f'/a/{i}.tar.gz', manifest=f'/a/{i}.json', summary=f'/a/{i}-summary.json'),
                     hashes={}, required={f'/old/{i}.rs': 'a' * 64}) for i in range(5)]
        sentinel = object()
        with patch.object(m, 'checkpoint', return_value=sentinel), patch.object(m, 'references', return_value=refs), \
                patch.object(m.engine, 'verify_archive') as verify:
            self.assertIs(m.stage_checkpoint(), sentinel)
            self.assertEqual(verify.call_count, 5)
            for call, ref in zip(verify.call_args_list, refs):
                self.assertEqual(call.args, (*ref['paths'].values(), ref['required']))
            verify.side_effect = RuntimeError('historical archive incomplete')
            with self.assertRaisesRegex(RuntimeError, 'incomplete'): m.stage_checkpoint()

    def test_reviewed_plan_keeps_twenty_seven_tests_and_positive_predecessor_archive(self):
        context = m.context()
        names = m.checkpoint()[1]
        plan = dict(owner=str(context.root), source=str(m.engine.SOURCE), inputs={'helper': 'a' * 64},
            checkpoint=context.revision, stages=m.engine.STAGES, commands=copy.deepcopy(m.engine.old.COMMANDS),
            old_tests=list(context.required_tests), added_tests=[m.NEW_TEST],
            initial_free_gib=16, running_floor_gib=8, capacity_stop_gib=9,
            archive_paths={'archive': '/selected-check.tar.gz'},
            archive_hashes={'/selected-check.tar.gz': m.diagnostic.CURRENT_ARCHIVE_SHA})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'plan.json'
            path.write_text(json.dumps(plan)); reviewed = m.sha(path)
            self.assertEqual(m.engine.load_plan(path, reviewed, plan['inputs'], names, context=context), plan)
            for field, value in [('initial_free_gib', 8), ('old_tests', list(context.required_tests)[:-1]),
                                 ('added_tests', []), ('archive_hashes',
                                  {'/selected-check.tar.gz': m.ARCHIVE_HASHES['archive']})]:
                changed = copy.deepcopy(plan); changed[field] = value
                path.write_text(json.dumps(changed))
                for digest in [reviewed, m.sha(path)]:
                    with self.subTest(field=field), self.assertRaises(RuntimeError):
                        m.engine.load_plan(path, digest, plan['inputs'], names, context=context)


if __name__ == '__main__': unittest.main()
