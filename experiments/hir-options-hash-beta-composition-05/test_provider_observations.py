"""Unrun pure controls; saved outputs document grammar, not new qualification."""
import json
from pathlib import Path
import struct
import unittest

from compose_sysroot import digest
import provider_observations as provider


class ProviderObservationControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bindings = json.loads((Path(__file__).parent/'source-bindings.json').read_bytes())
        raw = {}
        for key, row in bindings['provider_grammar_references'].items():
            path = Path(row['path']); before = path.stat()
            assert before.st_size == row['size'] <= 4096
            value = path.read_bytes(); after = path.stat()
            fields = ['st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink']
            assert all(getattr(before, name) == getattr(after, name) for name in fields)
            assert digest(value) == row['sha256']
            raw[key] = value
        cls.beta, cls.objcopy = raw['old_beta_identity'], raw['old_objcopy_text']
        cls.pin = 'compiler_version=beta\ncompiler_git_commit_hash=cbae9b4cae2b108f6a3d18cfe6075714bb739463\n'

    def test_saved_beta_and_objcopy_grammar_agree_without_qualifying_new_files(self):
        beta = provider.beta_version(self.beta, self.pin, 'aarch64-apple-darwin')
        objcopy = provider.objcopy_version(self.objcopy, beta['fields'])
        self.assertEqual(objcopy['llvm_version'], beta['fields']['LLVM version'])
        self.assertEqual(objcopy['rust_package'], '1.99.0-beta')

    def test_beta_unknown_duplicate_or_mismatched_fields_reject(self):
        for bad in [self.beta+b'extra\n', self.beta.replace(b'binary: rustc', b'host: rustc'),
                    self.beta.replace(b'cbae9b4cae2b108f6a3d18cfe6075714bb739463', b'0'*40),
                    self.beta.replace(b'1.99.0-beta.3', b'1.99.0-nightly'), self.beta[:-1]]:
            with self.subTest(raw=bad), self.assertRaises(ValueError):
                provider.beta_version(bad, self.pin, 'aarch64-apple-darwin')

    def test_objcopy_foreign_llvm_or_rust_family_and_unknown_lines_reject(self):
        fields = provider.beta_version(self.beta, self.pin, 'aarch64-apple-darwin')['fields']
        for bad in [self.objcopy.replace(b'23.1.0', b'23.2.0'), self.objcopy.replace(b'1.99.0', b'1.98.0'),
                    self.objcopy+b'extra\n', self.objcopy[:-1]]:
            with self.subTest(raw=bad), self.assertRaises(ValueError):
                provider.objcopy_version(bad, fields)

    def test_objcopy_requires_the_actual_beta_iteration_grammar(self):
        fields = provider.beta_version(self.beta, self.pin, 'aarch64-apple-darwin')['fields']
        for value in ['1.99.0-nightly', '1.99.0-beta.3-foreign', '1.99.0']:
            with self.subTest(release=value), self.assertRaises(ValueError):
                provider.objcopy_version(self.objcopy, fields | {'release': value})


if __name__ == '__main__':
    unittest.main()
