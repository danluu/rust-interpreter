import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import native_suite
from test_suite_reports import libtest


class NativeSuiteTests(unittest.TestCase):
    def test_parallel_processes_are_bounded_ordered_and_have_distinct_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'target';target.mkdir()
            executable=target/'unit-tests';executable.write_bytes(b'fixture')
            build=json.dumps(dict(reason='compiler-artifact',profile=dict(test=True),target=dict(kind=['lib']),executable=str(executable)))
            barrier=threading.Barrier(2);lock=threading.Lock();receipts=[];active=0;peak=0
            def capture(command, **kwargs):
                nonlocal active,peak
                if '--no-run' in command:return SimpleNamespace(returncode=0),build,'Compiling fixture\n'
                name=command[command.index('--exact')+1]
                with lock:
                    active+=1;peak=max(active,peak);receipts.append(kwargs['receipt_path'])
                barrier.wait(timeout=5)
                with lock:active-=1
                if name=='case-0':return SimpleNamespace(returncode=101),libtest(name,status='FAILED',passed=0,failed=1),''
                return SimpleNamespace(returncode=0),libtest(name),''
            args=argparse.Namespace(manifest_path=root/'Cargo.toml',package='fixture',target_dir=target,
                jobs=2,timings=False,suite_report=root/'report.json',entry=[f'case-{n}' for n in range(6)],suite_workers=2)
            report=dict(tests=[])
            with patch.object(native_suite,'capture',capture),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(native_suite.execute(args,report),1)
            self.assertEqual(peak,2);self.assertEqual(active,0)
            self.assertEqual(len(set(receipts)),6)
            self.assertTrue(all(p.parent==root/'report.workers' for p in receipts))
            self.assertEqual([t['name'] for t in report['tests']],args.entry)
            self.assertEqual((report['passed'],report['failed'],report['workers']),(5,1,2))

    def test_invalid_parallel_worker_limits_fail_before_cargo(self):
        for workers in ['0','65','-1','1.5']:
            arguments=['native_suite.py','--manifest-path','Cargo.toml','--package','fixture','--target-dir','unused',
                       '--jobs','2','--entry','first','--suite-workers',workers,'--suite-report','unused.json']
            with patch.object(sys,'argv',arguments),patch.object(native_suite,'execute') as execute,contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as failure:
                native_suite.main()
            self.assertEqual(failure.exception.code,2);execute.assert_not_called()

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
