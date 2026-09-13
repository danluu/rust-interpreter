"""Saved-evidence boundary tests; no compiler, Cargo, VM or benchmark runs."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_custom_cargo import fake_cargos, thaw, cargo_module
from test_custom_compiler import HOST, fake_install

DIRECTORY = Path(__file__).resolve().parents[1] / 'benchmarks/experiments/strict-warm-build'
sys.path.insert(0, str(DIRECTORY))
import assess_owned_screen as assess
import custom_compiler
import screen
from std_mir import FLAGS, POLICY


class OwnedScreenAssessment(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve(); self.addCleanup(thaw, self.root)
        self.raw = self.root / '.work/screen-fixture'

    def base(self, policy):
        return dict(owner=str(self.root), candidate_policy=policy,
            source=str(self.root / 'source'), case=json.loads(json.dumps(screen.CASE)),
            tools=dict.fromkeys(screen.MODES, 'a' * 64), states=[dict(index=i) for i in range(9)])

    def std(self, identity):
        identity = dict(policy=POLICY, flags=FLAGS, target=HOST,
            compiler='rustc fixture\nhost: ' + HOST + '\n', lock_sha256='b' * 64) | identity
        key = assess.sha(json.dumps(identity, sort_keys=True).encode())
        path = self.root / '.work/std-mir' / key / 'ready.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        artifacts = {'sysroot/lib/rustlib/' + identity['target'] + '/lib/lib' + crate + '-fixture.rmeta':
            dict(sha256='c' * 64, stamp=[1, 2, 3, 4]) for crate in ['core', 'alloc', 'std', 'test', 'proc_macro']}
        path.write_text(json.dumps(dict(owner=str(self.root), identity=identity, artifacts=artifacts)))
        return dict(key=key, path=str(path), sysroot=str(path.parent / 'sysroot'),
                    target=identity['target'], compiler=identity['compiler'], sha256=assess.sha(path.read_bytes()),
                    artifacts={str(path.parent / name): proof for name, proof in artifacts.items()})

    def cargos(self):
        baseline, candidate = fake_cargos(self.root)
        plan = self.base('cargo-info-cache')
        cargos = dict(baseline=baseline, candidate=candidate, duplicate=baseline)
        plan['cargos_by_mode'] = {m: c.receipt() for m, c in cargos.items()}
        plan['cargo_comparison'] = cargo_module.validate_matched_pair(baseline, candidate)
        off, on = [self.std(dict(cargo=c.receipt())) for c in [baseline, candidate]]
        plan['std_mir_by_mode'] = dict(baseline=off, candidate=on, duplicate=off)
        return plan, cargos

    def proc_macro(self):
        plan = self.base('host-proc-macro-opt')
        std = self.std({})
        plan.update(std_mir=std, std_mir_by_mode=dict.fromkeys(screen.MODES, std),
            proc_macro_policy_by_mode=dict(baseline='off', candidate='on', duplicate='off'),
            codegen_policy_amendment=dict(
                path=str(self.root / 'benchmarks/experiments/strict-warm-build/HOST_PROC_MACRO_OPT.md'),
                capability='host-proc-macro-opt-v1', optimized_role='unselected linked host proc-macro target',
                original_opt_level='0 (no explicit optimization flag)', opt_level='1', mir_opt_level=1,
                lto='off', preserve_effective_debug_assertions=True, preserve_effective_overflow_checks=True,
                application_profiles_changed=False,
                std_preparation_policy='unchanged and outside application wrapper'))
        tool = self.root / '.work/interpreter-tools' / plan['tools']['baseline']
        tool.mkdir(parents=True)
        # This is a selection fixture only; the separate complete publication
        # validator must qualify source.json before the assessor emits results.
        (tool / 'source.json').write_text(json.dumps(dict(composition=dict(public_compiler=dict(
            target=HOST, version_stdout_sha256=assess.sha(std['compiler'].encode()))))))
        return plan

    def compiler(self):
        compiler = fake_install(self.root)
        key = compiler.key
        plan = self.base('stable-cgu')
        plan['custom_compiler'] = dict(key=key, sysroot=str(compiler.sysroot),
            manifest=str(compiler.sysroot.parent / 'ready.json'), identity=compiler.identity)
        plan['cgu_policy_by_mode'] = dict(baseline='off', candidate='on', duplicate='off')
        off, on = [self.std(dict(compiler_key=key, namespace='stable-cgu:' + mode,
            compiler=compiler.identity['compiler'], source_sha256=compiler.identity['source_sha256'],
            lock_sha256=compiler.identity['files']['lib/rustlib/src/rust/library/Cargo.lock']))
            for mode in ['off', 'on']]
        plan['std_mir_by_mode'] = dict(baseline=off, candidate=on, duplicate=off)
        return plan, compiler

    def tool(self, plan, compiler, changes=None, capability_changes=None):
        binaries = {name: str(index + 1) * 64 for index, name in enumerate(
            ['rust-interp-vm', 'rust-interp-mir-export', 'rust-interp-rustc-wrapper'])}
        composition = dict(kind=custom_compiler.TOOL_POLICY, compiler_key=compiler.key,
            compiler_sysroot=str(compiler.sysroot), binaries=binaries)
        composition.update(changes or {})
        key = custom_compiler.digest(composition)
        path = self.root / '.work/interpreter-tools' / key
        path.mkdir(parents=True, exist_ok=True)
        capability = dict(schema_version=1, bytecode_version=5, tool_key=key,
            exporter_sha256=binaries['rust-interp-mir-export'], compiler_sysroot=str(compiler.sysroot),
            export_options=['stable-cgu-partitioning'])
        capability.update(capability_changes or {})
        for name, value in [('compiler.json', composition), ('ready.json', binaries),
                            ('capabilities.json', capability)]:
            (path / name).write_text(json.dumps(value))
        plan['tools'] = dict.fromkeys(screen.MODES, key)
        plan['binaries'] = dict.fromkeys(screen.MODES, binaries)
        return key

    def test_frozen_cargo_identity_and_std_mismatch_rejection_without_subprocesses(self):
        plan, cargos = self.cargos()
        with patch.object(subprocess, 'run', side_effect=AssertionError('must not execute')), \
             patch.object(subprocess, 'check_output', side_effect=AssertionError('must not probe')):
            custom, reconstructed = assess.selection(plan, assess.member)
            self.assertIsNone(custom); self.assertEqual(reconstructed, cargos)
            wrong = copy.deepcopy(plan)
            wrong['std_mir_by_mode']['candidate'] = wrong['std_mir_by_mode']['baseline']
            with self.assertRaisesRegex(RuntimeError, 'std Cargo differs'):
                assess.selection(wrong, assess.member)
            wrong = copy.deepcopy(plan)
            wrong['cargos_by_mode']['candidate']['sha256'] = '0' * 64
            with self.assertRaisesRegex(RuntimeError, 'receipt differs'):
                assess.selection(wrong, assess.member)

    def test_frozen_compiler_rejects_another_tool_or_policy(self):
        plan, compiler = self.compiler()
        self.assertEqual(assess.selection(plan, assess.member)[0], compiler)
        for key, value in [('tools', dict(baseline='a' * 64, candidate='b' * 64, duplicate='a' * 64)),
                           ('cgu_policy_by_mode', dict(baseline='on', candidate='on', duplicate='off'))]:
            wrong = {**plan, key: value}
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                assess.selection(wrong, assess.member)
        wrong = copy.deepcopy(plan)
        wrong['custom_compiler']['identity']['compiler'] = 'a different compiler'
        with self.assertRaisesRegex(RuntimeError, 'manifest differs'):
            assess.selection(wrong, assess.member)

    def test_archived_cargo_proof_cannot_claim_a_differently_built_binary_is_source_only(self):
        plan, cargos = self.cargos()
        snapshots = {}
        for cargo in [cargos['baseline'], cargos['candidate']]:
            for path in [cargo.directory / 'ready.json', cargo.directory / 'payload/source',
                         cargo.directory / 'payload/qualification']:
                snapshots[str(path)] = assess.member(path)
        for std in plan['std_mir_by_mode'].values():
            snapshots[std['path']] = assess.member(Path(std['path']))
        snapshot = lambda path: snapshots[str(path)]
        self.assertEqual(assess.selection(plan, snapshot)[1], cargos)
        candidate = cargos['candidate']
        path = candidate.directory / 'payload/source'
        manifest = json.loads(snapshots[str(path)]['utf8'])
        manifest['composition']['profile'] = 'a different profile'
        manifest['tool_key'] = custom_compiler.digest(manifest['composition'])
        data = json.dumps(manifest).encode()
        snapshots[str(path)] = dict(path=str(path), bytes=len(data), sha256=assess.sha(data), utf8=data.decode())
        identity = copy.deepcopy(candidate.identity)
        identity['files']['source'] = assess.sha(data)
        identity['provenance']['qualified_tool_key'] = manifest['tool_key']
        with self.assertRaisesRegex(RuntimeError, 'build profile'):
            assess.cargo_pair(cargos['baseline'], replace(candidate, identity=identity), snapshot)

    def test_compiler_std_rejects_hash_consistent_routing_or_source_substitutions(self):
        plan, compiler = self.compiler()
        original = plan['std_mir_by_mode']['candidate']
        for name, value in [('sysroot', str(self.root / 'another-sysroot')),
                            ('target', 'a-different-target'), ('compiler', 'a-different-compiler'),
                            ('sha256', '0' * 64)]:
            wrong = copy.deepcopy(plan); wrong['std_mir_by_mode']['candidate'][name] = value
            with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, 'std manifest or actual routing'):
                assess.selection(wrong, assess.member)
        wrong = copy.deepcopy(plan)
        wrong['std_mir_by_mode']['candidate']['artifacts'] = {}
        with self.assertRaisesRegex(RuntimeError, 'std artifact proof'):
            assess.selection(wrong, assess.member)
        identity = json.loads(Path(original['path']).read_text())['identity']
        for name, value in [('flags', FLAGS + ' -Zno-codegen'), ('policy', 'different-policy'),
                            ('source_sha256', '0' * 64), ('lock_sha256', '0' * 64),
                            ('compiler', 'another-compiler'), ('target', 'another-host')]:
            wrong = copy.deepcopy(plan)
            wrong['std_mir_by_mode']['candidate'] = self.std(identity | {name: value})
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                assess.selection(wrong, assess.member)

    def test_custom_tool_embeds_the_selected_physical_prefix_and_capability(self):
        plan, compiler = self.compiler()
        key = self.tool(plan, compiler)
        assess.tool_identity(plan, key, compiler, assess.member)
        for changes, capabilities in [({'kind': 'another-tool-policy'}, {}),
                ({'compiler_sysroot': str(self.root / 'another-prefix')}, {}),
                ({}, {'compiler_sysroot': str(self.root / 'another-prefix')}),
                ({}, {'exporter_sha256': '0' * 64}), ({}, {'export_options': []}),
                ({}, {'tool_key': '0' * 64})]:
            key = self.tool(plan, compiler, changes, capabilities)
            with self.subTest(changes=changes, capabilities=capabilities), self.assertRaises(RuntimeError):
                assess.tool_identity(plan, key, compiler, assess.member)

    def test_actual_cache_history_and_original_workload_are_required(self):
        plan = self.base('stable-cgu'); plan['case'] = copy.deepcopy(plan['case'])
        plan['case']['tests'][0] = 'different-test'
        with self.assertRaisesRegex(RuntimeError, 'original workflow'):
            assess.selection(plan, assess.member)
        workspaces = {}
        workspace = self.raw / 'caches/baseline/identity'
        row = dict(mode='baseline', launch=dict(workspace_path=str(workspace),
            artifact_path=str(workspace / 'target/artifact.rbc')))
        assess.workspace_identity(row, self.raw, workspaces)
        assess.workspace_identity(row, self.raw, workspaces)
        for mode, actual, artifact in [
                ('candidate', workspace, workspace / 'target/artifact.rbc'),
                ('baseline', workspace.parent / 'replacement', workspace.parent / 'replacement/target/file'),
                ('baseline', workspace, self.root / 'elsewhere/artifact.rbc'),
                ('baseline', workspace / '../escaped', workspace / '../escaped/target/file')]:
            with self.subTest(mode=mode, actual=actual), self.assertRaises(RuntimeError):
                assess.workspace_identity(dict(mode=mode, launch=dict(workspace_path=str(actual),
                    artifact_path=str(artifact))), self.raw, workspaces.copy())

    def test_saved_command_cannot_drop_tests_mix_policies_or_hide_bad_timing(self):
        plan, cargos = self.cargos()
        cargo = cargos['candidate']
        command = screen.command_for('candidate', plan['tools']['candidate'], Path(plan['source']),
            self.raw, plan['states'][3], candidate_policy='cargo-info-cache', cargo_key=cargo.key)
        row = dict(mode='candidate', index=3, command=[str(x) for x in command], seconds=1.0,
                   cpu=dict(user_seconds=.75, system_seconds=.25, total_seconds=1.0))
        assess.command_identity(plan, row, self.raw, None, cargo)
        for command in [row['command'][:-2], row['command'] + ['--query-cache-retention', 'demand']]:
            with self.subTest(command=command), self.assertRaisesRegex(RuntimeError, 'timed command differs'):
                assess.command_identity(plan, {**row, 'command': command}, self.raw, None, cargo)
        for value in [float('nan'), float('inf'), -1, 0, False]:
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                assess.command_identity(plan, {**row, 'seconds': value}, self.raw, None, cargo)
        row['cpu']['total_seconds'] = .5
        with self.assertRaisesRegex(RuntimeError, 'inconsistent'):
            assess.command_identity(plan, row, self.raw, None, cargo)

    def test_macro_selection_requires_shared_public_std_and_exact_amendment(self):
        plan = self.proc_macro()
        self.assertEqual(assess.selection(plan, assess.member), (None, dict.fromkeys(screen.MODES)))
        for field, value in [('cargos_by_mode', {}), ('custom_compiler', {}),
                ('proc_macro_policy_by_mode', dict.fromkeys(screen.MODES, 'on')),
                ('codegen_policy_amendment', {**plan['codegen_policy_amendment'], 'opt_level': '3'})]:
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                assess.selection({**plan, field: value}, assess.member)
        identity = json.loads(Path(plan['std_mir']['path']).read_text())['identity']
        for field, value in [('compiler', 'another compiler'), ('target', 'another target'),
                ('namespace', 'macro:on'), ('cargo', {}), ('lock_sha256', '0' * 64)]:
            wrong = copy.deepcopy(plan)
            wrong['std_mir_by_mode']['candidate'] = self.std(identity | {field: value})
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                assess.selection(wrong, assess.member)

    def test_macro_saved_commands_require_exact_off_on_off_policy(self):
        plan = self.proc_macro()
        for mode in screen.MODES:
            command = screen.command_for(mode, plan['tools'][mode], Path(plan['source']),
                self.raw, plan['states'][3], candidate_policy='host-proc-macro-opt')
            row = dict(mode=mode, index=3, command=command, seconds=1.0,
                       cpu=dict(user_seconds=.75, system_seconds=.25, total_seconds=1.0))
            assess.command_identity(plan, row, self.raw, None, None)
            wrong_policy = list(command)
            wrong_policy[wrong_policy.index('--host-proc-macro-opt') + 1] = (
                'off' if mode == 'candidate' else 'on')
            for value in [wrong_policy, command + ['--borrowck-cache', 'reuse'],
                          command + ['--cargo-key', 'b' * 64], command[:-2]]:
                with self.subTest(mode=mode, value=value), self.assertRaisesRegex(RuntimeError, 'timed command'):
                    assess.command_identity(plan, {**row, 'command': value}, self.raw, None, None)

    def test_macro_measured_std_must_be_the_qualified_artifact(self):
        plan = self.proc_macro()
        measured = plan['std_mir']
        shared = dict(key=measured['key'], ready_sha256=measured['sha256'], sysroot=measured['sysroot'],
            identity=json.loads(Path(measured['path']).read_text())['identity'])
        validated = dict(correctness=dict(shared_std=shared))
        assess.qualified_std(plan, validated, assess.member)
        for field, value in [('key', '0' * 64), ('ready_sha256', '0' * 64),
                ('sysroot', '/another/sysroot'), ('identity', {**shared['identity'], 'flags': 'changed'})]:
            wrong = copy.deepcopy(validated)
            wrong['correctness']['shared_std'][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, 'public-tool qualification'):
                assess.qualified_std(plan, wrong, assess.member)

    def test_all_macro_input_boundaries_are_required_from_saved_bytes(self):
        from test_qualified_public_tools import archive
        import qualified_public_tools as public
        tool, key, payloads = archive()
        validated = public.validate_public_tool(tool, key, lambda p: payloads[str(p.relative_to(tool))])
        directory = self.raw / 'public-input-guards'
        snapshots = {}
        guard = dict(schema_version=1, policy=public.GUARD_POLICY, tool_key=key, validation='stat',
            platform=validated['platform'], files={p: r['stamp'] for p, r in validated['input_records'].items()},
            searches=validated['searches'])

        def retain(name, value):
            path = directory / name
            data = json.dumps(value).encode()
            snapshots[str(path)] = dict(path=str(path), bytes=len(data), sha256=assess.sha(data), utf8=data.decode())
            return dict(path=str(path), sha256=assess.sha(data))

        plan = dict(public_input_guards=dict(policy=public.GUARD_POLICY, directory=str(directory),
            final_path=str(directory / 'final.json'), boundaries_per_command=2,
            admission=retain('admission.json', {**guard, 'validation': 'sha256'})))
        rows = [dict(public_input_guards={boundary: retain(f'{i:03d}-{boundary}.json', guard)
                                         for boundary in ['before', 'after']}) for i in range(27)]
        summary = dict(final_public_input_guard=retain('final.json', {**guard, 'validation': 'sha256'}))
        snapshot = lambda path: snapshots[str(path)]
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('live dependency read')):
            result = assess.public_screen_guards(plan, rows, summary, self.raw, validated, snapshot)
        self.assertEqual(result['records_verified'], 56)
        wrong = copy.deepcopy(rows)
        del wrong[10]['public_input_guards']['after']
        with self.assertRaisesRegex(RuntimeError, 'command boundary'):
            assess.public_screen_guards(plan, wrong, summary, self.raw, validated, snapshot)
        wrong = copy.deepcopy(rows)
        wrong[10]['public_input_guards']['before'] = rows[9]['public_input_guards']['before']
        with self.assertRaisesRegex(RuntimeError, 'path differs'):
            assess.public_screen_guards(plan, wrong, summary, self.raw, validated, snapshot)
        # Updating the record hash does not make changed compiler inputs valid.
        wrong = copy.deepcopy(rows)
        wrong[10]['public_input_guards']['after'] = retain('010-after.json', {**guard, 'files': {}})
        with self.assertRaisesRegex(RuntimeError, 'differs from publication'):
            assess.public_screen_guards(plan, wrong, summary, self.raw, validated, snapshot)


if __name__ == '__main__':
    unittest.main()
