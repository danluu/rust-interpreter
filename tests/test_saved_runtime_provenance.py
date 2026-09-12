"""A declared artifact mismatch must fail before creating or executing a run."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / 'scripts/compare_saved_runtime.py'


class SavedRuntimeProvenance(unittest.TestCase):
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
