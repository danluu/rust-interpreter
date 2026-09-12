import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import native_suite
from test_suite_reports import libtest


class NativeSuiteTests(unittest.TestCase):
    def test_failed_test_does_not_skip_the_next_separate_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); target=root/'target';target.mkdir()
            executable=target/'unit-tests';executable.write_bytes(b'fixture')
            build=json.dumps(dict(reason='compiler-artifact',profile=dict(test=True),target=dict(kind=['lib']),executable=str(executable)))
            calls=[]
            def capture(command, **kwargs):
                calls.append(command)
                if len(calls)==1:return SimpleNamespace(returncode=0),build,'Compiling fixture\n'
                name=command[command.index('--exact')+1]
                if name=='first':return SimpleNamespace(returncode=101),libtest(name,status='FAILED',passed=0,failed=1),''
                return SimpleNamespace(returncode=0),libtest(name),''
            args=argparse.Namespace(manifest_path=root/'Cargo.toml',package='fixture',target_dir=target,
                jobs=2,timings=False,suite_report=root/'report.json',entry=['first','second'])
            report=dict(tests=[])
            with patch.object(native_suite,'capture',capture), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(native_suite.execute(args,report),1)
            self.assertEqual(len(calls),3)
            self.assertIn('--no-run',calls[0]);self.assertNotIn('--',calls[0])
            self.assertEqual(calls[1:],[ [str(executable),'--exact',name,'--test-threads=1'] for name in ['first','second'] ])
            self.assertEqual([t['status'] for t in report['tests']],['failed','passed'])
            self.assertEqual((report['passed'],report['failed']),(1,1))

    def test_report_is_preserved_and_no_build_starts_when_path_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            report=Path(directory)/'report.json';report.write_text('prior evidence')
            arguments=['native_suite.py','--manifest-path','Cargo.toml','--package','fixture','--target-dir',directory,
                       '--jobs','2','--entry','first','--suite-report',str(report)]
            with patch.object(sys,'argv',arguments),patch.object(native_suite,'execute') as execute,self.assertRaises(FileExistsError):
                native_suite.main()
            execute.assert_not_called();self.assertEqual(report.read_text(),'prior evidence')


if __name__ == '__main__':
    unittest.main()
