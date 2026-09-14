import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('runtime_source_qualification_tests',
    ROOT / 'experiments/runtime-compiler-installation/source_qualification.py')
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)


class RuntimeSourceQualificationTests(unittest.TestCase):
    def setUp(self):
        self.application = Path('/owned/probe/source.rs')
        self.local = Path('/owned/E/lib/rustlib/src/rust/library')
        self.target = Path('/owned/source/library')
        self.virtual = Path('/rustc') / ('1' * 40) / 'library'
        self.payload = b'panic\n'
        self.files = {name: hashlib.sha256(self.payload).hexdigest() for name in q.REQUIRED}

    def records(self, root, *, empty=False):
        spans = [dict(file_name=str(root / name), byte_start=0, byte_end=1,
            line_start=1, line_end=1, column_start=1, column_end=2,
            text=[] if empty else [dict(text='panic', highlight_start=1, highlight_end=2)])
            for name in sorted(self.files)]
        return [dict(level='error', code=dict(code='E0080'), spans=spans)]

    def validate(self, records, virtual=False, payload_for=None):
        return q.validate_observation(records, application=self.application,
            local_roots=(self.local, self.target), virtual_root=self.virtual,
            files=self.files, payload_for=payload_for or (lambda _: self.payload), virtual=virtual)

    def test_exact_link_target_and_virtual_identity_preserve_raw_records(self):
        for root, virtual in [(self.local, False), (self.target, False), (self.virtual, True)]:
            with self.subTest(root=root):
                records = self.records(root, empty=virtual)
                original = copy.deepcopy(records)
                self.assertEqual(self.validate(records, virtual)['sources'], sorted(self.files))
                self.assertEqual(records, original)

    def test_wrong_virtual_commit_cannot_pass_with_identical_source_bytes(self):
        records = self.records(Path('/rustc') / ('2' * 40) / 'library')
        with self.assertRaisesRegex(RuntimeError, 'unexpected native standard source'):
            self.validate(records, virtual=True)

    def test_missing_standard_expansion_or_missing_local_snippet_is_rejected(self):
        for missing in sorted(self.files):
            records = self.records(self.local)
            records[0]['spans'] = [s for s in records[0]['spans'] if not s['file_name'].endswith(missing)]
            with self.subTest(missing=missing), self.assertRaisesRegex(RuntimeError, 'both core and std'):
                self.validate(records)
        with self.assertRaisesRegex(RuntimeError, 'local source snippet missing'):
            self.validate(self.records(self.local, empty=True))

    def test_current_source_mutation_and_forged_snippet_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / 'source.rs'
            path.write_bytes(self.payload)
            expected = hashlib.sha256(self.payload).hexdigest()
            self.assertEqual(q.file_bytes(path, expected, lambda: None), self.payload)
            path.write_bytes(b'other\n')
            with self.assertRaisesRegex(RuntimeError, 'source/proof bytes changed'):
                self.validate(self.records(self.local), payload_for=lambda _: q.file_bytes(path, expected, lambda: None))
        records = self.records(self.local)
        records[0]['spans'][0]['text'][0]['text'] = 'other'
        with self.assertRaisesRegex(RuntimeError, 'local source snippet missing or different'):
            self.validate(records)


if __name__ == '__main__':
    unittest.main()
