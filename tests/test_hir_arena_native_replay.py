import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'experiments/hir-arena-native-replay'
spec = importlib.util.spec_from_file_location('test_arena_native_replay_driver', HERE / 'check.py')
replay = importlib.util.module_from_spec(spec); sys.modules[spec.name] = replay; spec.loader.exec_module(replay)


def complete_output():
    names = ['anchor', 'add', 'method', 'double', 'shadow', 'generic', 'conditional', 'array_index',
        'uninitialized', 'raw', 'arithmetic', 'literals', 'unsafe_block', 'flow', 'early', 'field', 'choose']
    lines = [f'[hir-body-reuse] {name} hit cache_hits=1 verify_tree=1 verify_journal=1 verify_poststate=1 S=1 E=4' for name in names]
    lines += ['[hir-body-capture] anchor ' + state for state in
        ['cold-tree-and-journal-after-stock-lowering', 'same-tree-and-journal-after-stock-lowering']]
    lines += ['E0308 E0382 E0080 unconditional_panic unused_variables']
    lines += [f'-Cincremental=override-{label}-{mode}-{outcome}' for label in ['empty', 'nonempty']
              for mode in ['ordinary', 'capture', 'reuse'] for outcome in ['positive', 'negative']]
    return '\n'.join(lines)


class ArenaNativeReplay(unittest.TestCase):
    def test_actual_final_environment_and_stage0_loader(self):
        route = replay.recipe_environment((HERE / 'compiletest-command.txt').read_text(),
            {'HOME': '/owned-home', 'RUSTFLAGS': 'inherited', '__RUSTC_DEBUG_ASSERTIONS_ENABLED': '1',
             '__STD_DEBUG_ASSERTIONS_ENABLED': '1', 'CARGO': 'inherited'})
        env = route['environment']
        self.assertEqual(env['HOME'], '/owned-home')
        self.assertEqual(env['RUSTC_BOOTSTRAP'], '1')
        self.assertEqual(env['RUSTC_FORCE_RUSTC_VERSION'], 'compiletest')
        self.assertEqual(env['HOST_RUSTC_DYLIB_PATH'], str(replay.native.SYSROOT / 'lib'))
        self.assertEqual(env['DYLD_LIBRARY_PATH'].split(':'),
            [str(Path(route['options']['--run-make-support-rmeta'][0]).parent), str(replay.STAGE0_LIB)])
        self.assertEqual(env['__RMAKE_VERBOSE_SUBPROCESS_OUTPUT'], '1')
        self.assertEqual(env['__STD_REMAP_DEBUGINFO_ENABLED'], '1')
        self.assertEqual(env['__BOOTSTRAP_JOBS'], '2')
        for key in ['CARGO', 'RUSTFLAGS', 'RUSTC_LINKER', '__RUSTC_DEBUG_ASSERTIONS_ENABLED', '__STD_DEBUG_ASSERTIONS_ENABLED']:
            self.assertNotIn(key, env)
        self.assertEqual((env['CC'], env['CXX'], env['AR']), ('cc', 'c++', 'ar'))

    def test_preview_duplicate_and_changed_route_rejected(self):
        raw = (HERE / 'compiletest-command.txt').read_text()
        preview, actual = raw.splitlines()
        for changed in [preview, actual + '\n' + actual, raw.replace('"--jobs" "2"', '"--jobs" "3"'),
                        raw.replace('"--mode" "run-make"', '"--mode" "ui"')]:
            with self.subTest(changed=changed[:70]), self.assertRaises(RuntimeError):
                replay.recipe_environment(changed, {})

    def test_direct_success_requires_raw_full_roles_and_interval(self):
        good = complete_output()
        self.assertEqual(replay.checked_replay(good)['actual_verified_hits'], 17)
        self.assertNotIn('test result:', good)
        for before, after in [('S=1 E=4', 'S=4 E=4'), ('S=1 E=4', 'S=0 E=4'),
            ('S=1 E=4', 'S=1 E=4294967041'), (' S=1 E=4', ''), ('verify_tree=1', 'verify_tree=0')]:
            with self.subTest(after=after), self.assertRaises(RuntimeError):
                replay.checked_replay(good.replace(before, after, 1))

    def test_truncation_or_missing_history_is_not_a_pass(self):
        good = complete_output()
        for changed in [good + '\nTRUNCATED', good.replace('[hir-body-reuse] choose ', '[other] choose '),
            good.replace('-Cincremental=override-empty-reuse-negative', ''), good.replace('E0080', ''),
            'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 530 filtered out;']:
            with self.subTest(changed=changed[-60:]), self.assertRaises(RuntimeError):
                replay.checked_replay(changed)
