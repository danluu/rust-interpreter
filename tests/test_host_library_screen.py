"""Host-library screen boundaries; no compiler, Cargo, VM or benchmark calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_strict_warm_screen import screen, case, ORIGINAL
from test_qualified_public_tools import archive
import host_library_screen as library
from host_library_opt import receipt
import public_tool_publication as publisher


def qualified_fixture():
    tool, key, payloads = archive(library=True)
    read_tool = lambda path: payloads[str(path.relative_to(tool))]
    public = library.public_build(tool, key, read_tool)
    shared = public['correctness']['shared_std']; compiler = public['composition']['public_compiler']
    std = dict(key=shared['key'], path=public['plan']['shared_std']['path'],
        sysroot=shared['sysroot'], target=compiler['target'], compiler=shared['identity']['compiler'],
        rustc=compiler['rustc_path'], rustc_sha256=compiler['rustc_sha256'], sha256=shared['ready_sha256'])
    owner = Path('/owned/screen')
    def read(path):
        if path.is_relative_to(tool):return read_tool(path)
        if path == Path(std['path']):return payloads['provenance/std-ready.json']
        return payloads['provenance/harness/' + str(path.relative_to(owner))]
    return public, std, read


class HostLibraryScreenContracts(unittest.TestCase):
    def test_same_public_tools_shared_std_and_no_mixed_policies(self):
        key = 'a' * 64
        screen.validate_comparison('host-library-opt', key, key, None, None)
        for kwargs in [dict(candidate_key='b' * 64), dict(compiler_key='c' * 64),
                dict(candidate_std=Path('/different/std')), dict(baseline_cargo_key='d' * 64),
                dict(worker_qualification=Path('/worker/result')), dict(compiler_qualification=Path('/mono/result'))]:
            args = dict(policy='host-library-opt', baseline_key=key, candidate_key=key,
                        compiler_key=None, candidate_std=None); args.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(RuntimeError):screen.validate_comparison(**args)
        with patch.object(screen, 'require_export_option') as check:
            screen.require_candidate_policy(Path('/tools'), key, 'host-library-opt')
            check.assert_called_once_with(Path('/tools'), key, 'host-library-opt-v1')

    def test_all_27_commands_keep_14_tests_and_exact_existing_work(self):
        count = 0
        states = screen.protocol_states(ORIGINAL, case())
        self.assertEqual(len(states), 9)
        for sample in states:
            for mode in sample['modes']:
                args = (mode, 'a' * 64, Path('/source'), Path('/work'), sample)
                stock = screen.command_for(*args, candidate_policy='native-host-mir')
                actual = screen.command_for(*args, candidate_policy='host-library-opt')
                index = actual.index('--host-library-opt')
                self.assertEqual(actual[index:index + 2], ['--host-library-opt', library.MODES[mode]])
                self.assertEqual(actual[:index] + actual[index + 2:], stock)
                self.assertEqual([actual[i + 1] for i, arg in enumerate(actual) if arg == '--entry'], screen.CASE['tests'])
                self.assertEqual(len(screen.CASE['tests']), 14)
                for flag in ['--compiler-key', '--cargo-key', '--frontend-workers', '--host-proc-macro-opt',
                             '--compiler-argv-record-dir', '--query-cache-retention', '--borrowck-cache']:
                    self.assertNotIn(flag, actual)
                count += 1
        self.assertEqual(count, 27)

    def test_actual_launcher_capability_and_off_arms_reject_policy_leakage(self):
        public, std, _ = qualified_fixture(); cap = public['capability']; key = public['tool_key']
        for mode in library.MODES:
            expected = screen.launch_settings(mode, key, 'host-library-opt', library_capability=cap)
            library.validate_launch_policy(expected, mode, cap)
            expected.update(toolchain_lookup=dict(mode='cached', outcome='hit'),
                            std_mir={k: std[k] for k in ['key', 'sysroot', 'target']})
            failures = [dict(host_proc_macro_opt='on'), dict(frontend_workers={}),
                dict(query_cache_retention='demand'), dict(compiler_argv_record_dir='/instrumented'),
                dict(custom_cargo={}), dict(borrowck_cache='reuse')]
            if mode != 'candidate':failures.append(dict(host_library_opt=receipt(cap)))
            else:failures.append(dict(host_library_opt={**receipt(cap), 'opt_level': 2}))
            for change in failures:
                with self.subTest(mode=mode, change=change), self.assertRaises(RuntimeError):
                    screen.checked_launch('rust-interp-launch: ' + json.dumps({**expected, **change}),
                        mode, key, True, Path('/suite'), Path('/cache'), candidate_policy='host-library-opt',
                        prepared_std=std, library_capability=cap)
        original = screen.launch_settings('candidate', key, 'native-host-mir')
        with self.assertRaisesRegex(RuntimeError, 'unexpected host-library'):
            screen.checked_launch('rust-interp-launch: ' + json.dumps({**original, 'host_library_opt': receipt(cap)}),
                'candidate', key, True, Path('/suite'), Path('/cache'), candidate_policy='native-host-mir')

    def test_frozen_runtime_and_std_require_exact_qualified_bytes(self):
        public, std, read = qualified_fixture()
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('unexpected live source')):
            library.standard_binding(public, std)
            frozen = library.runtime_harness(public, '/owned/screen', read)
            self.assertIn('scripts/host_library_opt.py', frozen)
            self.assertIn(library.SCREEN_FILES[-1], frozen)
            for field in ['key', 'sha256', 'rustc_sha256', 'sysroot']:
                with self.subTest(field=field), self.assertRaises(RuntimeError):
                    library.standard_binding(public, {**std, field: 'wrong'})
            with self.assertRaisesRegex(RuntimeError, 'harness differs'):
                library.runtime_harness(public, '/owned/screen', lambda path: read(path) + b'changed')
            missing = copy.deepcopy(public); del missing['plan']['harness']['scripts/host_library_screen.py']
            with self.assertRaisesRegex(RuntimeError, 'not included'):
                library.runtime_harness(missing, '/owned/screen', read)

    def test_materializer_uses_actual_published_key_and_canonical_lock_without_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary).resolve(); source = owner / 'source'; source.mkdir()
            marker = dict(owner=str(owner), revision='f' * 40)
            (source / '.rust-interp-owned.json').write_text(json.dumps(marker))
            key = 'a' * 64; ready = owner / 'std/ready.json'; output = owner / 'command.json'
            plan = dict(owner='/build-owner', screen_owner=str(owner), qualification_policy=library.BUILD_POLICY,
                shared_std=dict(path=str(ready), sha256='b' * 64),
                project_preparation=dict(owner_marker=marker), harness=dict.fromkeys(library.SCREEN_FILES, 'b' * 64),
                workload_admission=dict(lock=str(library.CAMPAIGN_LOCK)), screen_request=dict(
                    python='/python', driver=str(owner / library.SCREEN_FILES[0]), run_id='fixture', source=str(source),
                    candidate_policy='host-library-opt', std_mir_ready=str(ready), lock_wait_seconds=45))
            publication = dict(status='published', tool_key=key,
                installations=[dict(owner=p) for p in [plan['owner'], str(owner)]])
            validated = dict(plan=plan, composition=dict(build=dict(plan_sha256='c' * 64)))
            typed = dict(composition=dict(public_compiler=dict(rustc_path='/rustc', rustc_sha256='d' * 64)))
            with patch.object(publisher, 'validate_public_tool', return_value=validated) as validate, \
                 patch.object(publisher, 'validate_live_inputs'), patch.object(publisher, 'file_digest', return_value='b' * 64), \
                 patch.object(library, 'public_build', return_value=typed), \
                 patch.object(library, 'standard_binding'), patch.object(library, 'runtime_harness'), \
                 patch.object(publisher, 'retained_command', side_effect=AssertionError('must not execute')):
                result = publisher.materialize_screen_command(plan, publication, output=output)
            self.assertEqual(validate.call_args.kwargs['qualification_policy'], library.BUILD_POLICY)
            argv = result['argv']
            for flag in ['--baseline-tool-key', '--candidate-tool-key']:self.assertEqual(argv[argv.index(flag) + 1], key)
            self.assertEqual(argv[argv.index('--candidate-policy') + 1], 'host-library-opt')
            self.assertEqual(argv[argv.index('--workload-lock') + 1], str(library.CAMPAIGN_LOCK))
            self.assertEqual(result['workloads_executed'], 0)


if __name__ == '__main__':
    unittest.main()
