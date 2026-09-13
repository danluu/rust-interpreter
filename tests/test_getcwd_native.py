"""Explicitly admitted native/getcwd controls; no automatic tool preparation."""
import os
from pathlib import Path
import unittest
import test_descriptor_io_native as harness

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(all(os.environ.get(name) for name in harness.REQUIRED),
                     'requires explicitly admitted compiler, exporter, VM, std and evidence directory')
class GetcwdNativeTests(harness.DescriptorIoNativeTests):
    # Reuse only the transparent process recorder/setup; do not repeat the
    # descriptor workload when selecting this independent two-test module.
    test_native_and_both_engines_create_append_truncate_errors_and_default_refusal = None
    test_unsupported_fcntl_and_bad_abi_are_export_errors_before_any_effect = None

    def test_native_null_and_buffer_contracts_both_engines_and_default_refusal(self):
        source = self.work / 'fixture.rs'
        source.write_bytes((ROOT / 'tests/getcwd_fixture.rs').read_bytes())
        native, artifact = self.work / 'native', self.work / 'fixture.rbc'
        result = self.invoke([self.rustc, source, '--edition=2024', '-Copt-level=0', '-o', native])
        self.assertEqual(result[0], 0, result[2])
        result = self.export(source, artifact)
        self.assertEqual(result[0], 0, result[2])
        cwd = self.work / 'cwd with spaces and é'
        cwd.mkdir()
        environment = {'RUST_INTERP_GETCWD_EXPECTED': str(cwd)}
        for engine in ['interpreter', 'jit']:
            result = self.invoke([self.vm, '--engine', engine, artifact, 0], cwd=cwd, env=environment)
            self.assertNotEqual(result[0], 0)
            self.assertIn(b'guest getcwd is disabled', result[2])
        for mode in range(6):
            expected = self.invoke([native, mode], cwd=cwd, env=environment)
            self.assertEqual(expected[0], 0, expected[2])
            bits = int(expected[1]) & 0xffff_ffff
            self.assertEqual(bits, 8 if mode in [1, 2] else 29 if mode >= 3 else 15)
            for engine in ['interpreter', 'jit']:
                result = self.invoke([self.vm, '--guest-getcwd', '--engine', engine, artifact, mode], cwd=cwd, env=environment)
                self.assertEqual(result, expected)
        wrong = {'RUST_INTERP_GETCWD_EXPECTED': str(cwd) + '-wrong'}
        expected = self.invoke([native, 0], cwd=cwd, env=wrong)
        self.assertEqual(expected[0], 0, expected[2])
        self.assertEqual(int(expected[1]) & 0xffff_ffff, 11)
        for engine in ['interpreter', 'jit']:
            self.assertEqual(self.invoke([self.vm, '--guest-getcwd', '--engine', engine, artifact, 0], cwd=cwd, env=wrong), expected)
            for mode in [10, 11]:
                result = self.invoke([self.vm, '--guest-getcwd', '--engine', engine, artifact, mode], cwd=cwd, env=environment)
                self.assertNotEqual(result[0], 0)
                self.assertTrue(any(message in result[2] for message in [b'guest memory', b'address overflow', b'read-only guest']), result[2])
        self.assertEqual(list(cwd.iterdir()), [])

    def test_incompatible_getcwd_abis_reject_during_export(self):
        for name, signature, call in [
            ('size', 'fn getcwd(p:*mut i8,n:u32)->*mut i8;', 'getcwd(std::ptr::null_mut(), 0)'),
            ('return', 'fn getcwd(p:*mut i8,n:usize)->u64;', 'getcwd(std::ptr::null_mut(), 0)'),
            ('const', 'fn getcwd(p:*const i8,n:usize)->*const i8;', 'getcwd(std::ptr::null(), 0)'),
            ('variadic', 'fn getcwd(p:*mut i8,n:usize,...)->*mut i8;', 'getcwd(std::ptr::null_mut(), 0)'),
        ]:
            source, artifact = self.work / (name + '.rs'), self.work / (name + '.rbc')
            source.write_text(f'unsafe extern "C" {{ {signature} }}\n'
                              f'pub fn rust_interp_entry()->u64 {{ unsafe {{ {call} as u64 }} }}\nfn main() {{}}\n')
            result = self.export(source, artifact)
            self.assertNotEqual(result[0], 0)
            self.assertIn(b'invalid getcwd signature', result[2])
            self.assertFalse(artifact.exists())


if __name__ == '__main__':
    unittest.main()
