import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify_repeated_workflow import verify_entry_catalog


class CatalogEvidenceTests(unittest.TestCase):
    def test_missing_or_changed_evidence_cannot_pass_as_a_legacy_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = dict(artifact_sha256='a'*64, entries=[dict(name='one', function=3), dict(name='two', function=7)])
            path = root / 'program.rbc.entries.json'
            payload = json.dumps(catalog).encode(); path.write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            artifact = dict(path='program.rbc', sha256='a'*64,
                            entry_catalog=dict(path=path.name, sha256=digest))
            launch = dict(artifact_path='/cargo/output.rbc', entry_catalog_path='/cargo/output.rbc.entries.json',
                          entry_catalog_sha256=digest)
            suite = dict(entry_source='artifact-bound catalog', tests=copy.deepcopy(catalog['entries']))
            verify_entry_catalog(root, artifact, launch, ['one', 'two'], suite)
            for missing in ['entry_catalog_path', 'entry_catalog_sha256']:
                bad = dict(launch); del bad[missing]
                with self.subTest(missing=missing), self.assertRaises(RuntimeError):
                    verify_entry_catalog(root, artifact, bad, ['one', 'two'], suite)
            bad_artifact = dict(artifact); del bad_artifact['entry_catalog']
            for bad_launch in [launch, dict(artifact_path=launch['artifact_path'])]:
                with self.assertRaises(RuntimeError):
                    verify_entry_catalog(root, bad_artifact, bad_launch, ['one', 'two'], suite)
            for field, value in [('entry_catalog_sha256', 'b'*64), ('entry_catalog_path', '/other.entries.json')]:
                with self.subTest(field=field), self.assertRaises(RuntimeError):
                    verify_entry_catalog(root, artifact, dict(launch, **{field: value}), ['one', 'two'], suite)
            bad_suite = copy.deepcopy(suite); bad_suite['tests'][0]['function'] = 8
            with self.assertRaises(RuntimeError):
                verify_entry_catalog(root, artifact, launch, ['one', 'two'], bad_suite)
            with self.assertRaises(RuntimeError):
                verify_entry_catalog(root, artifact, launch, ['two', 'one'], suite)
            with self.assertRaises(RuntimeError):
                verify_entry_catalog(root, dict(artifact, sha256='b'*64), launch, ['one', 'two'], suite)
            path.write_bytes(payload + b' ')
            with self.assertRaises(RuntimeError):
                verify_entry_catalog(root, artifact, launch, ['one', 'two'], suite)

    def test_legacy_evidence_remains_valid_without_catalog_claims(self):
        verify_entry_catalog(Path('/unused'), {}, {}, ['one', 'two'])
        verify_entry_catalog(Path('/unused'), {}, {}, ['one', 'two'], dict(entry_source='legacy batch descriptor'))


if __name__ == '__main__':
    unittest.main()
