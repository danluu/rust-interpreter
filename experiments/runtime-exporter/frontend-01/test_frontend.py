"""Exercise expected-error receipt handling without constructing a live stage."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import frontend as f


class FrontendCommandControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='runtime-exporter-frontend-control-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.executor = self.root / 'inert-executor'; self.executor.write_bytes(b'not executable')
        self.environment = {'LANG': 'C'}
        self.argv = [str(self.executor), '--negative-control']
        self.stage = f.Frontend.__new__(f.Frontend)
        self.stage.data = dict(environment=self.environment, records={})
        self.stage.outputs = {str(self.executor): {'sha256': f.sha(self.executor)}}
        self.stage.build_plan = dict(children=[dict(argv=self.argv, cwd=str(f.OWNER),
            environment=self.environment, expected=[1, 2])])
        self.stage.record = {'commands': []}
        self.stage.sources = lambda: None
        self.stage.barrier = lambda: None
        self.stage.save = lambda: None
        self.status = 1
        self.change_executor = False
        self.expected_seen = None
        self.addCleanup(patch.stopall)
        patch.object(f, 'WORK', self.root).start()
        patch.object(f.m.owned, 'disk', return_value=100 * 2**30).start()
        self.run_mock = patch.object(f.m.owned, 'run', side_effect=self.saved_child).start()

    def saved_child(self, command, *, cwd, env, out, capacity_root, expected):
        self.expected_seen = expected
        out.mkdir(parents=True)
        (out / 'stdout').write_bytes(b'')
        (out / 'stderr').write_bytes(b'expected compiler diagnostic\n')
        result = dict(command=command, pid=123, returncode=self.status)
        (out / 'receipt.json').write_text(json.dumps(result))
        if self.change_executor:
            self.executor.write_bytes(b'changed executor')
        f.require(self.status in expected, 'owned command failed: saved outcome')
        return result

    def test_negative_exit_tuple_reaches_owned_runner(self):
        result = self.stage.command(self.argv, expected=(1, 2))
        self.assertEqual(self.expected_seen, (1, 2))
        self.assertEqual(result['receipt']['returncode'], 1)
        self.assertEqual(len(self.stage.record['commands']), 1)

    def test_wrong_exit_code_is_retained_and_rejected(self):
        self.status = 9
        with self.assertRaisesRegex(RuntimeError, 'owned command failed'):
            self.stage.command(self.argv, expected=(1, 2))
        self.assertEqual(self.expected_seen, (1, 2))
        self.assertEqual(self.stage.record['commands'][0]['returncode'], 9)
        self.assertTrue((self.root / 'commands/000/stderr').is_file())

    def test_unplanned_exit_policy_is_rejected_before_runner(self):
        with self.assertRaisesRegex(RuntimeError, 'unreviewed frontend child'):
            self.stage.command(self.argv, expected=(0,))
        self.run_mock.assert_not_called()
        self.assertEqual(self.stage.record['commands'], [])

    def test_executor_mutation_during_negative_child_is_rejected(self):
        self.change_executor = True
        with self.assertRaisesRegex(RuntimeError, 'executor changed during frontend child'):
            self.stage.command(self.argv, expected=(1, 2))
        self.assertEqual(self.stage.record['commands'][0]['returncode'], 1)


if __name__ == '__main__':
    unittest.main()
