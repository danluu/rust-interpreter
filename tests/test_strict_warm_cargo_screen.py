"""Cargo-only comparison contracts; synthetic inputs, no benchmark execution."""
from dataclasses import replace
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_custom_cargo import cargo_module, fake_cargos, thaw
from test_strict_warm_screen import screen, case, ORIGINAL


class CargoScreenContracts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve(); self.addCleanup(thaw, self.root)
        self.baseline, self.candidate = fake_cargos(self.root)

    def test_policy_matrix_requires_same_tools_public_compiler_and_distinct_cargos(self):
        a, b = self.baseline.key, self.candidate.key
        tool, std = 'a' * 64, Path('/candidate/ready.json')
        screen.validate_comparison('cargo-info-cache', tool, tool, None, std, a, b)
        for args in [(tool, 'b' * 64, None, std, a, b),
                     (tool, tool, 'c' * 64, std, a, b),
                     (tool, tool, None, None, a, b),
                     (tool, tool, None, std, a, a),
                     (tool, tool, None, std, None, b)]:
            with self.subTest(args=args), self.assertRaises(RuntimeError):
                screen.validate_comparison('cargo-info-cache', *args)
        for policy in ['stable-cgu', 'demand-retention', 'native-host-mir']:
            with self.subTest(policy=policy), self.assertRaisesRegex(RuntimeError, 'Cargo arguments'):
                screen.validate_comparison(policy, tool, tool, 'c' * 64, std, a, b)
        with patch.object(screen, 'require_export_option') as capability:
            screen.require_candidate_policy(Path('/same/tools'), tool, 'cargo-info-cache')
            capability.assert_not_called()

    def test_all_27_commands_only_add_selected_cargo_and_keep_the_original_tests(self):
        count = 0
        for sample in screen.protocol_states(ORIGINAL, case()):
            for mode in sample['modes']:
                cargo = self.candidate if mode == 'candidate' else self.baseline
                args = (mode, 'a' * 64, Path('/source'), Path('/work'), sample)
                base = screen.command_for(*args, candidate_policy='native-host-mir')
                actual = screen.command_for(*args, candidate_policy='cargo-info-cache', cargo_key=cargo.key)
                index = actual.index('--cargo-key')
                self.assertEqual(actual[index:index + 2], ['--cargo-key', cargo.key])
                self.assertEqual(actual[:index] + actual[index + 2:], base)
                self.assertEqual([actual[i + 1] for i, v in enumerate(actual) if v == '--entry'], screen.CASE['tests'])
                self.assertEqual(len(screen.CASE['tests']), 14)
                for flag in ['--compiler-key', '--stable-cgu-partitioning', '--query-cache-retention']:
                    self.assertNotIn(flag, actual)
                count += 1
        self.assertEqual(count, 27)
        with self.assertRaisesRegex(RuntimeError, 'installed Cargo key'):
            screen.command_for(*args, candidate_policy='cargo-info-cache')
        with self.assertRaisesRegex(RuntimeError, 'Cargo arguments'):
            screen.command_for(*args, candidate_policy='native-host-mir', cargo_key=self.baseline.key)

    def test_matched_pair_requires_actual_binary_difference_and_source_only_build_provenance(self):
        proof = cargo_module.validate_matched_pair(self.baseline, self.candidate)
        self.assertEqual(proof['source_only_production_difference'], ['src/util/rustc.rs'])
        altered = copy.deepcopy(self.candidate.identity)
        altered['files']['cargo'] = self.baseline.identity['files']['cargo']
        with self.assertRaisesRegex(RuntimeError, 'actual binary hashes'):
            cargo_module.validate_matched_pair(self.baseline, replace(self.candidate, identity=altered))
        altered = copy.deepcopy(self.candidate.identity)
        altered['pinned_compiler']['compiler'] = 'different compiler'
        with self.assertRaisesRegex(RuntimeError, 'compiler or dynamic libraries'):
            cargo_module.validate_matched_pair(self.baseline, replace(self.candidate, identity=altered))
        source = self.candidate.directory / 'payload/source'
        manifest = json.loads(source.read_bytes())
        manifest['composition']['profile'] = 'debug'
        manifest['tool_key'] = cargo_module.digest(manifest['composition'])
        source.chmod(0o644); source.write_text(json.dumps(manifest))
        altered = copy.deepcopy(self.candidate.identity)
        altered['files']['source'] = cargo_module.file_digest(source)
        altered['provenance']['qualified_tool_key'] = manifest['tool_key']
        with self.assertRaisesRegex(RuntimeError, 'build profile'):
            cargo_module.validate_matched_pair(self.baseline, replace(self.candidate, identity=altered))

    def test_wrong_cargo_or_std_receipt_cannot_enter_validated_measurements(self):
        cargo = self.candidate
        expected = screen.launch_settings('candidate', 'a' * 64, 'cargo-info-cache', cargo=cargo)
        expected['toolchain_lookup'] = dict(mode='cached', outcome='hit')
        std = dict(key='f' * 64, sysroot='/candidate/std', target='aarch64-apple-darwin')
        expected['std_mir'] = std
        bad = copy.deepcopy(expected); bad['custom_cargo'] = self.baseline.receipt()
        for row in [bad, {**expected, 'custom_cargo': {**cargo.receipt(), 'sha256': '0' * 64}}]:
            with self.assertRaisesRegex(RuntimeError, 'settings differ'):
                screen.checked_launch('rust-interp-launch: ' + json.dumps(row), 'candidate', 'a' * 64,
                    True, Path('/suite'), Path('/cache'), candidate_policy='cargo-info-cache',
                    cargo=cargo, prepared_std=std)
        for row, error in [({**expected, 'custom_compiler': {}}, 'unexpected custom compiler'),
                           ({**expected, 'std_mir': {**std, 'key': 'e' * 64}}, 'different standard-library')]:
            with self.assertRaisesRegex(RuntimeError, error):
                screen.checked_launch('rust-interp-launch: ' + json.dumps(row), 'candidate', 'a' * 64,
                    True, Path('/suite'), Path('/cache'), candidate_policy='cargo-info-cache',
                    cargo=cargo, prepared_std=std)

    def test_prepared_std_must_match_the_selected_cargo_before_compiler_probe(self):
        cargo = self.baseline
        binding = cargo.identity['pinned_compiler']
        original = Path(binding['sysroot'])
        identity = dict(policy=screen.STD_POLICY, flags=screen.STD_FLAGS, compiler=binding['compiler'],
            target=binding['host'], lock_sha256=screen.sha(original / 'lib/rustlib/src/rust/library/Cargo.lock'),
            cargo=cargo.receipt())
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        work = self.root / '.work/std-mir' / key
        lib = work / 'sysroot/lib/rustlib' / binding['host'] / 'lib'; lib.mkdir(parents=True)
        artifacts = {}
        for crate in ['core', 'alloc', 'std', 'test', 'proc_macro']:
            path = lib / ('lib' + crate + '-fixture.rmeta'); path.write_bytes(crate.encode())
            artifacts[str(path.relative_to(work))] = dict(stamp=screen.stamp(path), sha256=screen.sha(path))
        ready = work / 'ready.json'
        ready.write_text(json.dumps(dict(owner=str(self.root), identity=identity, artifacts=artifacts)))
        env = dict(RUSTUP_HOME=binding['rustup_home'])
        with patch.object(screen, 'ROOT', self.root), \
             patch.object(screen.subprocess, 'check_output', return_value=binding['compiler']) as probe:
            result = screen.validate_std_ready(ready, env, cargo=cargo)
            self.assertEqual(result['key'], key)
            probe.reset_mock()
            with self.assertRaisesRegex(RuntimeError, 'different Cargo identity'):
                screen.validate_std_ready(ready, env, cargo=self.candidate)
            with self.assertRaisesRegex(RuntimeError, 'requires Cargo selection'):
                screen.validate_std_ready(ready, env)
            probe.assert_not_called()


if __name__ == '__main__':
    unittest.main()
