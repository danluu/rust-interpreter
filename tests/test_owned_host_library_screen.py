"""Archived host-library selection, commands and guards; no live tools."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_owned_screen_assessment as base_assessment
from test_host_library_screen import qualified_fixture
import host_library_screen as library
import qualified_public_tools as public_tools

assess, screen = base_assessment.assess, base_assessment.screen


class OwnedHostLibraryAssessment(unittest.TestCase):
    setUp = base_assessment.OwnedScreenAssessment.setUp
    base = base_assessment.OwnedScreenAssessment.base
    std = base_assessment.OwnedScreenAssessment.std
    proc_macro = base_assessment.OwnedScreenAssessment.proc_macro

    def plan(self):
        plan = self.proc_macro()
        plan.pop('proc_macro_policy_by_mode')
        plan.update(candidate_policy='host-library-opt', host_library_policy_by_mode=library.MODES,
            host_library_public_build_policy=library.BUILD_POLICY, workload_lock=str(library.CAMPAIGN_LOCK),
            codegen_policy_amendment=library.amendment(self.root), cargo_jobs=screen.JOBS,
            suite_workers=screen.SUITE_WORKERS, instruction_limit=screen.INSTRUCTIONS,
            allocation_limit=screen.ALLOCATIONS, minimum_free_gib=screen.MINIMUM_GIB,
            guest_rustflags=[], profile_overrides={}, final_qualification=False)
        return plan

    def test_saved_selection_rejects_mixed_policy_changed_checks_jobs_or_std(self):
        plan = self.plan()
        self.assertEqual(assess.selection(plan, assess.member), (None, dict.fromkeys(screen.MODES)))
        for field, value in [('host_library_policy_by_mode', dict.fromkeys(screen.MODES, 'on')),
                ('frontend_workers_by_mode', dict.fromkeys(screen.MODES, 2)), ('cargo_jobs', 1),
                ('guest_rustflags', ['-Copt-level=3']), ('workload_lock', '/another/lock'),
                ('codegen_policy_amendment', {**plan['codegen_policy_amendment'], 'preserve_effective_ub_checks': False})]:
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                assess.selection({**plan, field: value}, assess.member)
        wrong = copy.deepcopy(plan); wrong['std_mir_by_mode']['candidate']['key'] = '0' * 64
        with self.assertRaises(RuntimeError):assess.selection(wrong, assess.member)

    def test_archived_tool_identity_binds_actual_scope_wrapper_std_and_runtime_sources(self):
        public, std, read = qualified_fixture(); key = public['tool_key']
        plan = dict(candidate_policy='host-library-opt', owner='/owned/screen',
            tools=dict.fromkeys(screen.MODES, key), binaries=dict.fromkeys(screen.MODES, public['composition']['binaries']),
            std_mir=std, host_library_capability=public['capability'])
        def snapshot(path):
            data = read(path)
            return dict(path=str(path), bytes=len(data), sha256=assess.sha(data), utf8=data.decode())
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('live compiler or dependency read')):
            actual = assess.tool_identity(plan, key, None, snapshot)
            self.assertEqual(actual['qualification_scope'], 'host-library-real-histories')
            wrong = copy.deepcopy(plan); wrong['host_library_capability']['host_library_wrapper']['sha256'] = '0' * 64
            with self.assertRaisesRegex(RuntimeError, 'actual binaries/capability'):
                assess.tool_identity(wrong, key, None, snapshot)
            wrong = copy.deepcopy(plan); wrong['std_mir']['sysroot'] = '/another/std'
            with self.assertRaisesRegex(RuntimeError, 'compiler/std'):
                assess.tool_identity(wrong, key, None, snapshot)
            def changed(path):
                item = snapshot(path)
                if str(path).endswith('/scripts/host_library_opt.py') and '/provenance/' not in str(path):
                    data = b'changed'; item.update(utf8=data.decode(), bytes=len(data), sha256=assess.sha(data))
                return item
            with self.assertRaisesRegex(RuntimeError, 'harness differs'):
                assess.tool_identity(plan, key, None, changed)

    def test_every_saved_arm_keeps_original_workload_and_complete_timing(self):
        plan = self.plan()
        for mode in screen.MODES:
            command = screen.command_for(mode, plan['tools'][mode], Path(plan['source']), self.raw,
                plan['states'][3], candidate_policy='host-library-opt')
            row = dict(mode=mode, index=3, command=command, seconds=1.0,
                       cpu=dict(user_seconds=.75, system_seconds=.25, total_seconds=1.0))
            assess.command_identity(plan, row, self.raw, None, None)
            wrong_mode = list(command); wrong_mode[wrong_mode.index('--host-library-opt') + 1] = (
                'off' if mode == 'candidate' else 'on')
            wrong_jobs = list(command); wrong_jobs[wrong_jobs.index('--jobs') + 1] = '1'
            for argv in [wrong_mode, wrong_jobs, command[:-2], command + ['--host-proc-macro-opt', 'on']]:
                with self.subTest(mode=mode, argv=argv), self.assertRaisesRegex(RuntimeError, 'timed command'):
                    assess.command_identity(plan, {**row, 'command': argv}, self.raw, None, None)
            with self.assertRaisesRegex(RuntimeError, 'CPU duration'):
                assess.command_identity(plan, {**row, 'cpu': dict(row['cpu'], total_seconds=.1)}, self.raw, None, None)

    def test_all_56_guard_boundaries_bind_the_typed_publication(self):
        public, _, _ = qualified_fixture(); directory = self.raw / 'public-input-guards'; snapshots = {}
        guard = dict(schema_version=1, policy=public_tools.GUARD_POLICY, tool_key=public['tool_key'], validation='stat',
            platform=public['platform'], files={p: r['stamp'] for p, r in public['input_records'].items()},
            searches=public['searches'])
        def retain(name, value):
            path = directory / name; data = json.dumps(value).encode()
            snapshots[str(path)] = dict(path=str(path), bytes=len(data), sha256=assess.sha(data), utf8=data.decode())
            return dict(path=str(path), sha256=assess.sha(data))
        plan = dict(public_input_guards=dict(policy=public_tools.GUARD_POLICY, directory=str(directory),
            final_path=str(directory / 'final.json'), boundaries_per_command=2,
            admission=retain('admission.json', {**guard, 'validation': 'sha256'})))
        rows = [dict(public_input_guards={when: retain(f'{index:03d}-{when}.json', guard)
                    for when in ['before', 'after']}) for index in range(27)]
        summary = dict(final_public_input_guard=retain('final.json', {**guard, 'validation': 'sha256'}))
        snapshot = lambda path: snapshots[str(path)]
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('live input read')):
            self.assertEqual(assess.public_screen_guards(plan, rows, summary, self.raw, public, snapshot)['records_verified'], 56)
        wrong = copy.deepcopy(rows); del wrong[10]['public_input_guards']['after']
        with self.assertRaises(RuntimeError):assess.public_screen_guards(plan, wrong, summary, self.raw, public, snapshot)
        wrong = copy.deepcopy(rows)
        wrong[10]['public_input_guards']['after'] = retain('010-after.json', {**guard, 'files': {}})
        with self.assertRaisesRegex(RuntimeError, 'differs from publication'):
            assess.public_screen_guards(plan, wrong, summary, self.raw, public, snapshot)


if __name__ == '__main__':
    unittest.main()
