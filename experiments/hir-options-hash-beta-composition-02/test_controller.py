"""Pure command/loader controls; no real process, build or B3 is created."""
import unittest
from pathlib import Path

import compose


class ControllerControls(unittest.TestCase):
    def test_nineteen_children_preserve_build_runtime_and_auxiliary_roles(self):
        plan = dict(environment={'PATH': '/usr/bin:/bin'}, otool='/qualified/otool')
        rows = compose.desired_commands(plan)
        self.assertEqual(len(rows), 19)
        self.assertTrue(all(row['cwd'] == str(compose.S) for row in rows))
        compilations = [row for row in rows if '--emit=obj' in row['argv']]
        self.assertEqual(len(compilations), 1)
        self.assertEqual(compilations[0]['argv'][0], str(compose.D / 'bin/rustc'))
        self.assertIn('--sysroot=' + str(compose.B3), compilations[0]['argv'])
        self.assertEqual([row['argv'][1] for row in rows if row['argv'][0] == str(compose.E / 'bin/rustc')], ['-vV', '--print'])
        traced = [row for row in rows if 'DYLD_PRINT_LIBRARIES' in row['environment']]
        self.assertEqual(len(traced), 2)
        self.assertTrue(all(row['argv'][0] == str(compose.B3 / compose.TOOL) for row in traced))
        self.assertNotIn('DYLD_PRINT_LIBRARIES', plan['environment'])

    def trace(self, pid=123):
        return (f'dyld[{pid}]: {compose.B3 / compose.TOOL}\n'
                f'dyld[{pid}]: {compose.B3 / compose.COPY["destination"]}\n'
                f'dyld[{pid}]: /usr/lib/libSystem.B.dylib\n'
                f'dyld[{pid}]: move loaded to delayed: libSystem.B.dylib\n').encode()

    def test_loader_requires_actual_exact_beta_provider_and_retains_lines(self):
        result = compose.dyld(self.trace(), 123)
        self.assertEqual(len(result['lines']), 4)
        self.assertEqual(result['loaded_private'], sorted([str(compose.B3 / compose.TOOL), str(compose.B3 / compose.COPY['destination'])]))

    def test_loader_rejects_missing_foreign_wrong_pid_and_unknown_diagnostics(self):
        for raw in [self.trace(456), self.trace().replace(str(compose.B3 / compose.COPY['destination']).encode(), b'/foreign/libLLVM.dylib'),
                    self.trace().replace((f'dyld[123]: {compose.B3 / compose.COPY["destination"]}\n').encode(), b''),
                    self.trace() + b'warning: failed to execute rust-objcopy\n']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                compose.dyld(raw, 123)

    def test_loader_rejects_unseen_or_private_delayed_images(self):
        for name in ['libLLVM.dylib', 'unseen.dylib']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                compose.dyld(self.trace() + f'dyld[123]: move loaded to delayed: {name}\n'.encode(), 123)

    def test_static_identity_is_separate_from_actual_dependency(self):
        raw = b'file:\nLoad command 0\n cmd LC_ID_DYLIB\n name @rpath/identity.dylib (offset 24)\nLoad command 1\n cmd LC_LOAD_DYLIB\n name /usr/lib/libSystem.B.dylib (offset 24)\nLoad command 2\n cmd LC_RPATH\n path @loader_path/../lib (offset 12)\n'
        result = compose.declarations(raw)
        self.assertEqual(result['identities'], [['LC_ID_DYLIB', '@rpath/identity.dylib']])
        self.assertEqual(result['loads'], [['LC_LOAD_DYLIB', '/usr/lib/libSystem.B.dylib']])
        self.assertEqual(result['rpaths'], ['@loader_path/../lib'])
        with self.assertRaises(ValueError):
            compose.declarations(raw + b'Load command 3\n cmd LC_DYLD_ENVIRONMENT\n')


if __name__ == '__main__':
    unittest.main()
