"""Unmeasured synthetic admission controls; no compiler or Cargo children."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('mono_screen',
    ROOT / 'benchmarks/experiments/strict-warm-build/screen.py')
screen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(screen)
import stable_mono_qualification as qualification


def fixture():
    owner = Path('/owned/project')
    path = owner / '.work/integration/result.json'
    stds = {mode: dict(key=letter * 64, sysroot='/std/' + mode, target='host')
            for mode, letter in [('off', 'd'), ('on', 'e')]}
    files = {}
    def put(name, data):
        files[name] = data if isinstance(data, bytes) else json.dumps(data, sort_keys=True).encode()
        return hashlib.sha256(files[name]).hexdigest()
    result = dict(status='passed', kind='real-custom-compiler-integration', benchmark=False,
        qualification_policy=qualification.POLICY, diagnostic_comparison='strict',
        qualification_scope='strict-integration', full_presentation_qualified=True,
        diagnostic_presentation='strict-structured-match', presentation_gap_count=0,
        semantic_controls='passed', source_restored=True, compiler_key='c' * 64,
        tool_key='a' * 64, commands=36, launcher_commands=22, public_commands=11,
        expected_rejections=24, std_mir_policy='source-paths-v2', std_mir=stds,
        module_policy_by_mode=dict(off='off', on='off'), mono_policy_by_mode=dict(off='off', on='on'))
    result['plan_sha256'] = put('plan.json', dict(compiler_key='c' * 64, tool_key='a' * 64))
    commands = []
    for index in range(36):
        row = dict(label=str(index), command=['/compiler', str(index)], returncode=0)
        commands.append(row)
        put(f'{index:02d}-child.json', row | dict(status='finished', started_at=1, finished_at=2))
    put('commands.json', commands)
    records = []
    for mode in ['off', 'on']:
        for role in ['native-host', 'selected-guest']:
            prefix = mode + '-' + role
            argv = ['/compiler/sysroot/bin/rustc', '--crate-name', 'custom_compiler_fixture', '-Zstable-cgu-partitioning=no',
                '-Zstable-mono-cgu-partitioning=' + ('yes' if mode == 'on' else 'no')]
            route = 'native' if role == 'native-host' else 'exported'
            if role == 'selected-guest':
                argv += ['--target', 'host']
            original = '\0'.join(['rust-interp-compiler-argv-v1', route, '/compiler/sysroot',
                                   '/fixture', *argv, '']).encode()
            raw = dict(path=prefix + '.argv', sha256=put(prefix + '.argv', original))
            digest = put(prefix + '.json', dict(schema_version=1, role=route,
                compiler_sysroot='/compiler/sysroot', cwd='/fixture', argv=argv, raw=raw))
            records.append(dict(mode=mode, role=role, path=prefix + '.json', sha256=digest))
    result['compiler_flag_proof'] = dict(path='flags.json', sha256=put('flags.json',
        dict(schema_version=1, policy=qualification.POLICY, records=records)))
    def finish():
        result['evidence_files'] = {name: hashlib.sha256(data).hexdigest()
                                   for name, data in files.items() if name != 'result.json'}
        put('result.json', result)
    def validate():
        finish()
        return qualification.validate_qualification(path, owner, 'c' * 64, 'a' * 64, stds,
            compiler_sysroot='/compiler/sysroot', read_bytes=lambda p: files[str(p.relative_to(path.parent))])
    return result, files, put, validate


class MonoScreenContracts(unittest.TestCase):
    def test_comparison_and_all_27_commands_keep_exact_common_work(self):
        key, compiler, std, receipt = 'a' * 64, 'c' * 64, Path('/std/on/ready.json'), Path('/owned/result.json')
        screen.validate_comparison('stable-mono-cgu', key, key, compiler, std,
                                   compiler_qualification=receipt)
        for changes in [dict(candidate_key='b' * 64), dict(compiler_key=None),
                        dict(candidate_std=None), dict(compiler_qualification=None),
                        dict(baseline_cargo_key='f' * 64)]:
            arguments = dict(policy='stable-mono-cgu', baseline_key=key, candidate_key=key,
                             compiler_key=compiler, candidate_std=std, compiler_qualification=receipt)
            with self.assertRaises(RuntimeError):
                screen.validate_comparison(**(arguments | changes))
        for index in range(9):
            for mode in screen.MODES:
                args = (mode, key, Path('/owned/source'), Path('/owned/run'), dict(index=index))
                normal = screen.command_for(*args, candidate_policy='native-host-mir')
                command = screen.command_for(*args, candidate_policy='stable-mono-cgu',
                    compiler_key=compiler, prepared_std=dict(key=('e' if mode == 'candidate' else 'd') * 64))
                start = command.index('--compiler-key')
                self.assertEqual(command[:start] + command[start + 10:], normal)
                self.assertEqual(command[start + 2:start + 8], ['--stable-cgu-partitioning', 'off',
                    '--stable-mono-cgu-partitioning', 'on' if mode == 'candidate' else 'off',
                    '--std-mir-policy', 'source-paths-v2'])
                self.assertNotIn('--compiler-argv-record-dir', command)

    def test_archived_receipt_requires_full_strict_matching_qualification(self):
        result, files, put, validate = fixture()
        self.assertEqual(validate()['result']['commands'], 36)
        for key, value in [('qualification_policy', 'old-module-qualification'),
                           ('full_presentation_qualified', False),
                           ('diagnostic_comparison', 'verified-std-source'),
                           ('presentation_gap_count', 1), ('tool_key', 'b' * 64),
                           ('module_policy_by_mode', dict(off='off', on='on')),
                           ('std_mir', {})]:
            original = result[key]
            result[key] = value
            with self.assertRaises(RuntimeError):
                validate()
            result[key] = original

    def test_consistently_rehashed_json_cannot_replace_actual_recorder_bytes(self):
        result, files, put, validate = fixture()
        name = 'on-selected-guest.json'
        raw = json.loads(files[name])
        raw['argv'][-1] = 'different-target'
        changed = put(name, raw)
        proof = json.loads(files['flags.json'])
        next(r for r in proof['records'] if r['path'] == name)['sha256'] = changed
        result['compiler_flag_proof']['sha256'] = put('flags.json', proof)
        with self.assertRaisesRegex(RuntimeError, 'raw recorder bytes'):
            validate()

    def test_missing_completion_or_actual_role_cannot_qualify(self):
        result, files, put, validate = fixture()
        child = files.pop('12-child.json')
        with self.assertRaisesRegex(RuntimeError, 'completion receipt'):
            validate()
        files['12-child.json'] = child
        proof = json.loads(files['flags.json'])
        proof['records'] = proof['records'][:-1]
        result['compiler_flag_proof']['sha256'] = put('flags.json', proof)
        with self.assertRaisesRegex(RuntimeError, 'role/mode'):
            validate()

    def test_launch_rejects_module_on_and_wrong_mono_receipts_before_execution_checks(self):
        custom = SimpleNamespace(key='c' * 64, rustc=Path('/compiler/bin/rustc'),
            identity=dict(files={'bin/rustc': 'f' * 64}, compiler='compiler',
                          unstable_options=dict(sha256='9' * 64)))
        wrapper = dict(policy='stable-mono-cgu-routing-v1', sha256='8' * 64,
                       compiler_sysroot='/compiler')
        expected = screen.launch_settings('candidate', 'a' * 64, 'stable-mono-cgu', custom,
                                          mono_wrapper=wrapper)
        for key, value in [('stable_cgu_partitioning', 'on'),
                           ('stable_mono_cgu_partitioning', {})]:
            launch = copy.deepcopy(expected)
            launch['custom_compiler'][key] = value
            with self.assertRaisesRegex(RuntimeError, 'settings differ'):
                screen.checked_launch('rust-interp-launch: ' + json.dumps(launch),
                    'candidate', 'a' * 64, True, Path('/suite'), Path('/cache'),
                    candidate_policy='stable-mono-cgu', custom=custom, mono_wrapper=wrapper)

    def test_v2_loader_is_authoritative_and_smoke_scope_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            directory = root / '.work/std-mir' / ('d' * 64)
            directory.mkdir(parents=True)
            ready_path = directory / 'ready.json'
            ready_path.write_text('{}')
            custom = SimpleNamespace(rustc=Path('/compiler/bin/rustc'),
                identity=dict(compiler='compiler', files={'bin/rustc': 'f' * 64}))
            ready = dict(identity=dict(policy=qualification.STD_POLICY),
                         full_presentation_qualified=False, metadata={})
            module = SimpleNamespace(POLICY=qualification.STD_POLICY)
            with patch.dict('sys.modules', std_mir_source_paths=module), patch.object(screen, 'ROOT', root):
                with patch.object(module, 'load', create=True,
                        return_value=(directory / 'sysroot', 'host', 'd' * 64, ready)) as load:
                    selected = screen.validate_mono_std_ready(ready_path, custom, 'on')
                    load.assert_called_once_with(root, 'd' * 64, custom, 'stable-mono-cgu:on', rehash=True)
                    self.assertFalse(selected['readiness']['full_presentation_qualified'])
                with patch.object(module, 'load', create=True, side_effect=RuntimeError('source changed')):
                    with self.assertRaisesRegex(RuntimeError, 'source changed'):
                        screen.validate_mono_std_ready(ready_path, custom, 'off')


if __name__ == '__main__':
    unittest.main()
