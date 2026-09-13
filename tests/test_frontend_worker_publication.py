"""Worker public-build boundaries use archived bytes and never spawn tools."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from test_qualified_public_tools import archive
import qualified_public_tools as q
from frontend_worker_screen import public_build


class WorkerPublicationTests(unittest.TestCase):
    def test_worker_build_is_explicit_and_does_not_claim_worker_qualification(self):
        tool, key, data = archive(worker=True)
        read = lambda path: data[str(path.relative_to(tool))]
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('live input read')):
            result = public_build(tool, key, read)
            self.assertEqual(result['qualification_scope'], 'public-build-only')
            self.assertEqual(result['correctness']['results']['launcher-contracts']['passed'], 7)
            self.assertEqual(result['correctness']['results']['screen-contracts']['passed'], 8)
            with self.assertRaisesRegex(RuntimeError, 'qualification policy differs'):
                q.validate_public_tool(tool, key, read)
        tool, key, data = archive()
        with self.assertRaisesRegex(RuntimeError, 'qualification policy differs'):
            public_build(tool, key, lambda path: data[str(path.relative_to(tool))])

    def test_rekeyed_wrapper_probe_or_build_scope_cannot_replace_controls(self):
        def changed_wrapper(composition, data):
            name = 'provenance/logs/wrapper-capabilities.stdout'
            value = json.loads(data[name]); value['counts'] = [1]
            data[name] = json.dumps(value).encode()
        def false_scope(composition, data):
            name = 'provenance/correctness.json'
            value = json.loads(data[name]); value['qualification_scope'] = 'worker-qualified'
            data[name] = json.dumps(value).encode()
            composition['correctness_receipt_sha256'] = q.sha(data[name])
        for change, message in [(changed_wrapper, 'exporter/wrapper'), (false_scope, 'scope')]:
            tool, key, data = archive(change, worker=True)
            with self.subTest(change=change.__name__), self.assertRaisesRegex(RuntimeError, message):
                public_build(tool, key, lambda path: data[str(path.relative_to(tool))])


if __name__ == '__main__':
    unittest.main()
