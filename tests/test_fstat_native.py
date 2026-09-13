"""Explicitly admitted SDK/native/fstat comparisons; no automatic tool preparation."""
import json
import os
from pathlib import Path
import unittest
import test_descriptor_io_native as harness

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = harness.REQUIRED + ['RUST_INTERP_TEST_CC', 'RUST_INTERP_TEST_SDK']
OFFSETS = [0, 4, 6, 8, 16, 20, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 116, 120, 124, 128, 136]
WIDTHS = [4, 2, 2, 8, 4, 4, 4, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 4, 4, 4, 4, 8, 8]


@unittest.skipUnless(all(os.environ.get(name) for name in REQUIRED),
                     'requires admitted compiler/exporter/VM/std/evidence and exact SDK C compiler')
class FstatNativeTests(harness.DescriptorIoNativeTests):
    test_native_and_both_engines_create_append_truncate_errors_and_default_refusal = None
    test_unsupported_fcntl_and_bad_abi_are_export_errors_before_any_effect = None

    def compile_pair(self, folder, expected):
        folder.mkdir()
        source = folder / 'fixture.rs'
        source.write_bytes((ROOT / 'tests/fstat_fixture.rs').read_bytes())
        (folder / 'oracle-expectation.json').write_text(json.dumps(expected, sort_keys=True, indent=2) + '\n')
        (folder / 'expected.rs').write_text(
            f'const EXPECTED_BYTES: [u8; 144] = {expected["bytes"]!r};\n'
            f'const EXPECTED_FIELDS: [u128; 23] = {expected["fields"]!r};\n'
            f'const EXPECTED_RETURN: i32 = {expected["returncode"]};\n'
            f'const EXPECTED_ERRNO: i32 = {expected["errno"]};\n')
        native, artifact = folder / 'native', folder / 'fixture.rbc'
        result = self.invoke([self.rustc, source, '--edition=2024', '-Copt-level=0', '-o', native])
        self.assertEqual(result[0], 0, result[2])
        result = self.export(source, artifact)
        self.assertEqual(result[0], 0, result[2])
        return native, artifact

    def test_sdk_layout_full_bytes_named_fields_growth_errno_and_negative_expectations(self):
        cc = Path(os.environ['RUST_INTERP_TEST_CC']).resolve(strict=True)
        sdk = Path(os.environ['RUST_INTERP_TEST_SDK']).resolve(strict=True)
        c_source, oracle = self.work / 'oracle.c', self.work / 'oracle'
        c_source.write_bytes((ROOT / 'tests/fstat_layout_oracle.c').read_bytes())
        result = self.invoke([cc, '-isysroot', sdk, '-std=c11', '-Wall', '-Wextra', '-Werror',
                              '-MD', '-MF', self.work / 'oracle.d', c_source, '-o', oracle])
        self.assertEqual(result[0], 0, result[2])
        result = self.invoke([oracle, '--layout'])
        self.assertEqual(result[0], 0, result[2])
        self.assertEqual(json.loads(result[1]), dict(size=144, align=8, offsets=OFFSETS, widths=WIDTHS))
        # All probes use the same physical file. No differing inode/timestamp normalization.
        cwd = self.work / 'data'
        cwd.mkdir()
        for phase, contents in enumerate([b'abc', b'longer\x00contents\xff']):
            (cwd / 'data.bin').write_bytes(contents)
            oracle_result = self.invoke([oracle, '--stat', cwd / 'data.bin'])
            self.assertEqual(oracle_result[0], 0, oracle_result[2])
            expected = json.loads(oracle_result[1])
            self.assertEqual(expected['returncode'], 0)
            self.assertEqual(len(expected['bytes']), 144)
            self.assertTrue(all(type(n) is int and 0 <= n <= 255 for n in expected['bytes']))
            self.assertEqual(len(expected['fields']), 23)
            expected['fields'] = [n & ((1 << (8 * width)) - 1) for n, width in zip(expected['fields'], WIDTHS)]
            # Independently ensure the SDK member values and raw buffer agree.
            self.assertEqual(expected['fields'], [int.from_bytes(bytes(expected['bytes'][offset:offset + width]), 'little')
                for offset, width in zip(OFFSETS, WIDTHS)])
            self.assertEqual(expected['fields'][15], len(contents))
            folder = self.work / f'phase-{phase}'
            native, artifact = self.compile_pair(folder, expected)
            for mode in [0, 1, 2]:
                actual = self.invoke([native, mode], cwd=cwd)
                self.assertEqual(actual, (0, b'15\n', b''))
                for engine in ['interpreter', 'jit']:
                    self.assertEqual(self.invoke([self.vm, '--guest-descriptor-io', '--engine', engine, artifact, mode], cwd=cwd), actual)
            if phase == 0:
                for engine in ['interpreter', 'jit']:
                    result = self.invoke([self.vm, '--engine', engine, artifact, 0], cwd=cwd)
                    self.assertNotEqual(result[0], 0)
                    self.assertIn(b'guest descriptor I/O is disabled', result[2])
                    for mode in [10, 11]:
                        result = self.invoke([self.vm, '--guest-descriptor-io', '--engine', engine, artifact, mode], cwd=cwd)
                        self.assertNotEqual(result[0], 0)
                        self.assertTrue(any(s in result[2] for s in [b'guest memory', b'address overflow', b'read-only guest']), result[2])
        # Alter a byte and a named field independently. Each comparison must
        # actually fail in native and both engines, with all other bits intact.
        for name, field, index, answer in [('wrong-byte', 'bytes', 96, 11), ('wrong-field', 'fields', 15, 7)]:
            wrong = json.loads(json.dumps(expected))
            wrong[field][index] ^= 1
            native, artifact = self.compile_pair(self.work / name, wrong)
            actual = self.invoke([native, 0], cwd=cwd)
            self.assertEqual(actual, (0, f'{answer}\n'.encode(), b''))
            for engine in ['interpreter', 'jit']:
                self.assertEqual(self.invoke([self.vm, '--guest-descriptor-io', '--engine', engine, artifact, 0], cwd=cwd), actual)
        self.assertEqual((cwd / 'data.bin').read_bytes(), contents)

    def test_incompatible_fstat_signature_and_equal_size_layout_reject_before_export(self):
        declaration = (ROOT / 'tests/fstat_fixture.rs').read_text().split('unsafe extern "C"')[0]
        for name, signature, call, structure, abi in [
            ('fd-width', 'fn fstat(fd:i64,p:*mut Stat)->i32;', 'fstat(3, std::ptr::null_mut())', declaration, 'C'),
            ('return-width', 'fn fstat(fd:i32,p:*mut Stat)->i64;', 'fstat(3, std::ptr::null_mut())', declaration, 'C'),
            ('const-pointer', 'fn fstat(fd:i32,p:*const Stat)->i32;', 'fstat(3, std::ptr::null())', declaration, 'C'),
            ('variadic', 'fn fstat(fd:i32,p:*mut Stat,...)->i32;', 'fstat(3, std::ptr::null_mut())', declaration, 'C'),
            ('short-layout', 'fn fstat(fd:i32,p:*mut Stat)->i32;', 'fstat(3, std::ptr::null_mut())', '#[repr(C)] struct Stat { value:u64 }\n', 'C'),
            ('equal-size-wrong-type', 'fn fstat(fd:i32,p:*mut Stat)->i32;', 'fstat(3, std::ptr::null_mut())', declaration.replace('dev: i32', 'dev: u32', 1), 'C'),
            ('unwind-abi', 'fn fstat(fd:i32,p:*mut Stat)->i32;', 'fstat(3, std::ptr::null_mut())', declaration, 'C-unwind'),
        ]:
            source, artifact = self.work / (name + '.rs'), self.work / (name + '.rbc')
            source.write_text(structure + f'unsafe extern "{abi}" {{ {signature} }}\n'
                + f'pub fn rust_interp_entry()->u64 {{ unsafe {{ {call} as u64 }} }}\nfn main() {{}}\n')
            result = self.export(source, artifact)
            self.assertNotEqual(result[0], 0)
            self.assertIn(b'invalid fstat signature', result[2])
            self.assertFalse(artifact.exists())


if __name__ == '__main__':
    unittest.main()
