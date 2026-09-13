"""Counterfactual qualification evidence checks; no compiler is executed."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import mono_qualification as m


class MonoEvidenceTests(unittest.TestCase):
    def test_record_preserves_unicode_spaces_and_argument_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'native-1.argv'
            fields = ['rust-interp-compiler-argv-v1', 'native', '/compiler root', '/cwd é',
                      '/compiler root/bin/rustc', '--cfg', 'value="a b\\c"', 'file\nname.rs']
            path.write_bytes(b'\0'.join(x.encode() for x in fields) + b'\0')
            actual = m.decode_record(path)
            self.assertEqual(actual['argv'], fields[4:])
            self.assertEqual(actual['cwd'], '/cwd é')
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaisesRegex(RuntimeError, 'incomplete'):
                m.decode_record(path)

    def test_flags_reject_missing_duplicate_wrong_or_mixed_policy(self):
        good = ['/compiler/bin/rustc', '-Zstable-cgu-partitioning=no', '-Zstable-mono-cgu-partitioning=yes']
        m.validate_flags(good, 'on')
        for broken in [good[:-1], good + [good[-1]], good + ['-Z', 'stable_cgu_partitioning=yes'],
                       good + ['@response'], good + ['-Zthreads=2'], good + ['--jobs=2'],
                       good + ['-Zcache-proc-macros']]:
            with self.subTest(broken=broken), self.assertRaises(RuntimeError):
                m.validate_flags(broken, 'on')
        with self.assertRaises(RuntimeError):
            m.validate_flags(good, 'off')

    def test_native_target_is_not_misclassified_as_selected_guest(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary).resolve(); directory = work / 'argv'; directory.mkdir()
            compiler = SimpleNamespace(sysroot=work / 'compiler', rustc=work / 'compiler/bin/rustc', host='target')
            args = [str(compiler.rustc), '--crate-name', 'custom_compiler_fixture', '--target', 'target',
                    '-Zstable-cgu-partitioning=no', '-Zstable-mono-cgu-partitioning=no']
            fields = ['rust-interp-compiler-argv-v1', 'native', str(compiler.sysroot), str(work), *args]
            path = directory / 'native-123.argv'; path.write_bytes(b'\0'.join(x.encode() for x in fields) + b'\0')
            self.assertEqual(m.retain_records(work, directory, 'off', compiler), [])
            saved = json.loads(path.with_suffix('.json').read_text())
            self.assertEqual(saved['argv'], args)
            self.assertEqual(saved['raw']['path'], 'argv/native-123.argv')

    def test_proof_needs_all_modes_and_roles(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            rows = [dict(mode=mode, role=role) for mode in ['off', 'on']
                    for role in ['native-host', 'selected-guest']]
            for missing in range(4):
                with self.assertRaisesRegex(RuntimeError, 'missing actual'):
                    m.publish_proof(work, rows[:missing] + rows[missing + 1:])
            proof = m.publish_proof(work, rows)
            self.assertEqual(proof['path'], 'compiler-flag-proof.json')

    def test_legacy_arguments_unchanged_and_mono_module_always_off(self):
        for mode in ['off', 'on']:
            self.assertEqual(m.mode_arguments(False, mode), ['--stable-cgu-partitioning', mode])
            self.assertEqual(m.mode_arguments(True, mode), ['--stable-cgu-partitioning', 'off',
                '--stable-mono-cgu-partitioning', mode])
            self.assertEqual(m.namespace(True, mode), 'stable-mono-cgu:' + mode)


if __name__ == '__main__':
    unittest.main()
