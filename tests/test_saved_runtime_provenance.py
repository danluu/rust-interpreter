"""A declared artifact mismatch must fail before creating or executing a run."""
import json
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / 'scripts/compare_saved_runtime.py'
spec = importlib.util.spec_from_file_location('runtime_comparison', RUNNER)
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


class SavedRuntimeProvenance(unittest.TestCase):
    def test_entropy_library_and_tape_hashes_are_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            library = root / 'library'
            library.write_bytes(b'fixture-qualified-library')
            qualification = root / 'qualification.json'
            qualification.write_text(json.dumps(dict(status='passed', commands=17, expected_rejections=10,
                library=str(library), library_sha256=hashlib.sha256(library.read_bytes()).hexdigest())))
            tapes = []
            for index in range(2):
                path = root / (str(index) + '.tape')
                path.write_bytes(b'RIRNG001')
                tapes.append(dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), calls=0, bytes=0))
            cases = [dict(name='empty-entropy', entropy_tapes=tapes)]
            selected, paths = comparison.entropy_inputs(qualification, cases)
            self.assertEqual(selected, library)
            self.assertEqual(len(paths), 4)
            tapes[0]['calls'] = True
            with self.assertRaisesRegex(RuntimeError, 'invalid entropy calls'):
                comparison.entropy_inputs(qualification, cases)
            tapes[0]['calls'] = 0
            Path(tapes[0]['path']).write_bytes(b'changed-tape')
            with self.assertRaisesRegex(RuntimeError, 'entropy tape changed'):
                comparison.entropy_inputs(qualification, cases)
            library.write_bytes(b'changed-library')
            with self.assertRaisesRegex(RuntimeError, 'entropy library changed'):
                comparison.entropy_inputs(qualification, cases)

    def test_entropy_tapes_cannot_be_silently_ignored(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps([dict(name='case', entropy_tapes=[])]))
            result = subprocess.run([sys.executable, str(RUNNER), '--baseline', str(root / 'absent-baseline'),
                '--candidate', str(root / 'absent-candidate'), '--manifest', str(manifest),
                '--output', str(root / 'output'), '--lock', str(root / 'lock')],
                capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 2)
            self.assertIn('entropy tapes require an explicit qualified replay library', result.stderr)
            self.assertFalse((root / 'output').exists())

    def test_invalid_limits_fail_before_opening_binaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / 'manifest.json'
            for field, value in [('allocation_limit', None), ('allocation_limit', -1),
                                 ('instruction_limit', 0), ('instruction_limit', True)]:
                with self.subTest(field=field, value=value):
                    manifest.write_text(json.dumps([dict(name='original-case', artifact=str(root / 'absent.rbc'),
                        stdout='0\n', **{field: value})]))
                    result = subprocess.run([sys.executable, str(RUNNER), '--baseline', str(root / 'absent-baseline'),
                        '--candidate', str(root / 'absent-candidate'), '--manifest', str(manifest),
                        '--output', str(root / 'output'), '--lock', str(root / 'lock')],
                        capture_output=True, text=True, timeout=5)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(field + ' must be an explicit integer', result.stderr)
                    self.assertFalse((root / 'output').exists())
                    self.assertFalse((root / 'lock').exists())

    def test_mismatched_artifact_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / 'program.rbc'
            artifact.write_bytes(b'changed artifact')
            # These files are intentionally not executable. Reaching Popen
            # would fail differently, proving the provenance guard ran first.
            for mode in ['baseline', 'candidate']:
                (root / mode).write_bytes(b'not an executable')
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps([dict(name='original-case', artifact=str(artifact),
                artifact_sha256='0' * 64, stdout='0\n')]))
            output = root / 'output'
            result = subprocess.run([sys.executable, str(RUNNER), '--baseline', str(root / 'baseline'),
                '--candidate', str(root / 'candidate'), '--manifest', str(manifest), '--output', str(output),
                '--lock', str(root / 'lock'), '--lock-wait-seconds', '0'], capture_output=True, text=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('artifact differs from declared provenance', result.stderr)
            self.assertNotIn('PermissionError', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
