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
from test_custom_compiler import fake_install

DIRECTORY = Path(__file__).resolve().parents[1] / 'benchmarks/experiments/strict-warm-build'
sys.path.insert(0, str(DIRECTORY))
import assess_owned_screen as assess
import custom_compiler
import screen


class OwnedScreenAssessment(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve(); self.addCleanup(thaw, self.root)
        self.raw = self.root / '.work/screen-fixture'

    def base(self, policy):
        return dict(owner=str(self.root), candidate_policy=policy,
            source=str(self.root / 'source'), case=screen.CASE,
            tools=dict.fromkeys(screen.MODES, 'a' * 64), states=[dict(index=i) for i in range(9)])

    def std(self, identity):
        key = assess.sha(json.dumps(identity, sort_keys=True).encode())
        path = self.root / '.work/std-mir' / key / 'ready.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(dict(owner=str(self.root), identity=identity)))
        return dict(key=key, path=str(path), sysroot=str(path.parent / 'sysroot'), target='fixture-host')

    def cargos(self):
        baseline, candidate = fake_cargos(self.root)
        plan = self.base('cargo-info-cache')
        cargos = dict(baseline=baseline, candidate=candidate, duplicate=baseline)
        plan['cargos_by_mode'] = {m: c.receipt() for m, c in cargos.items()}
        plan['cargo_comparison'] = cargo_module.validate_matched_pair(baseline, candidate)
        off, on = [self.std(dict(cargo=c.receipt())) for c in [baseline, candidate]]
        plan['std_mir_by_mode'] = dict(baseline=off, candidate=on, duplicate=off)
        return plan, cargos

    def compiler(self):
        compiler = fake_install(self.root)
        key = compiler.key
        plan = self.base('stable-cgu')
        plan['custom_compiler'] = dict(key=key, sysroot=str(compiler.sysroot),
            manifest=str(compiler.sysroot.parent / 'ready.json'), identity=compiler.identity)
        plan['cgu_policy_by_mode'] = dict(baseline='off', candidate='on', duplicate='off')
        off, on = [self.std(dict(compiler_key=key, namespace='stable-cgu:' + mode)) for mode in ['off', 'on']]
        plan['std_mir_by_mode'] = dict(baseline=off, candidate=on, duplicate=off)
        return plan, compiler

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


if __name__ == '__main__':
    unittest.main()
