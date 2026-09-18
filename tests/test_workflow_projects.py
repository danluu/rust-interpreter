"""Additional workflows remain opt-in and bound to independently pinned cases."""
import contextlib
import copy
import fcntl
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import bench_e2e_workflow
from workflow_case_file import checked, load
from workflow_projects import WORKFLOW_ONLY_PROJECTS, project_revision


class WorkflowProjectTests(unittest.TestCase):
    def test_oxc_case_is_pinned_without_changing_the_executable_corpus(self):
        corpus = json.loads((ROOT / 'benchmarks/corpus.json').read_text())
        self.assertNotIn('oxc', corpus['projects'])
        self.assertNotIn('oxc', bench_e2e_workflow.WORKFLOWS)
        for project, specification in corpus['projects'].items():
            self.assertEqual(project_revision(ROOT, project), specification['revision'])
        path = ROOT / 'experiments/oxc-plugin-normalization/case.json'
        revision = WORKFLOW_ONLY_PROJECTS['oxc']['revision']
        case, proof = load(path, 'oxc', revision)
        self.assertEqual(len(case['tests']), 3)
        self.assertEqual(len(case['edits']), 3)
        self.assertEqual(case['selections'], [[0, 1, 2]] * 3)
        data = json.loads(path.read_text())
        for key, wrong in [('project', 'ruff'), ('revision', '0' * 40)]:
            changed = copy.deepcopy(data)
            changed[key] = wrong
            with self.assertRaises(ValueError):
                checked(changed, 'oxc', revision)

    def test_oxc_without_case_fails_before_tool_preparation(self):
        with patch.object(sys, 'argv', ['bench_e2e_workflow.py', '--project', 'oxc']), \
                patch.object(bench_e2e_workflow, 'checked_tools') as tools, \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as failure:
            bench_e2e_workflow.main()
        self.assertEqual(failure.exception.code, 2)
        tools.assert_not_called()

    def test_conflicting_rustc_fails_before_tool_preparation_or_measurement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.work').mkdir()
            (root / '.work/benchmark.lock').touch()
            (root / 'benchmarks').mkdir()
            (root / 'benchmarks/corpus.json').write_bytes((ROOT / 'benchmarks/corpus.json').read_bytes())
            arguments = ['bench_e2e_workflow.py', '--project', 'fre', '--native-toolchain', '1.98.1', '--run-id', 'conflict']
            opened = []
            original_open = Path.open
            def track_open(path, *args, **kwargs):
                stream = original_open(path, *args, **kwargs)
                if path == root / '.work/benchmark.lock':
                    opened.append(stream)
                    self.addCleanup(stream.close)
                return stream
            with patch.object(bench_e2e_workflow, 'ROOT', root), patch.object(sys, 'argv', arguments), \
                    patch.object(Path, 'open', track_open), \
                    patch.dict(os.environ, {'RUSTC': '/another/compiler'}), \
                    patch.object(bench_e2e_workflow, 'checked_tools') as tools, \
                    patch.object(bench_e2e_workflow, 'capture') as capture, \
                    self.assertRaisesRegex(RuntimeError, 'conflicts with inherited RUSTC'):
                bench_e2e_workflow.main()
            tools.assert_not_called()
            capture.assert_not_called()
            self.assertEqual(len(opened), 1)
            self.assertTrue(opened[0].closed)
            with (root / '.work/benchmark.lock').open('a') as competing:
                fcntl.flock(competing, fcntl.LOCK_EX | fcntl.LOCK_NB)


if __name__ == '__main__':
    unittest.main()
