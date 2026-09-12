import contextlib,copy,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import interpreter
from test_discovery import read_listing


def entry(name,ignored=False,should_panic=False):
    return dict(name=name,native_name=name,function=name,descriptor=name+'::descriptor',status='classified',harness='libtest',
                ignored=ignored,should_panic=should_panic,ordinary_test=not ignored and not should_panic,
                ignore_reason='deliberate' if ignored else None,panic_message='expected' if should_panic else None)


def report(tests):
    return dict(kind='test-discovery',schema_version=1,target='aarch64-apple-darwin',strict_frontend=True,
                executed=False,harness='libtest',count=len(tests),tests=tests)


class TestDiscoveryControls(unittest.TestCase):
    def test_listing_preserves_attributes_and_allows_empty_builtin_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'tests.json'
            for expected in [report([]),report([entry('ignored',ignored=True),entry('nested::same'),entry('panics',should_panic=True),entry('same')])]:
                path.write_text(json.dumps(expected))
                actual,digest=read_listing(path)
                self.assertEqual(actual,expected);self.assertEqual(len(digest),64)

    def test_execution_claims_mismatched_names_and_unclassified_tests_are_rejected(self):
        valid=report([entry('one'),entry('two')])
        bad=[dict(valid,executed=True),dict(valid,strict_frontend=False),dict(valid,harness='custom'),dict(valid,count=1),
             dict(valid,count=True),dict(valid,tests=list(reversed(valid['tests']))),dict(valid,tests=[entry('one'),entry('one')])]
        for field,value in [('native_name','other'),('ordinary_test',False),('status','unclassified'),('should_panic',1),('name','')]:
            altered=copy.deepcopy(valid);altered['tests'][0][field]=value;bad.append(altered)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'tests.json'
            for value in bad:
                path.write_text(json.dumps(value))
                with self.subTest(value=value),self.assertRaises(RuntimeError):read_listing(path)
            path.write_text('{')
            with self.assertRaises(RuntimeError):read_listing(path)
            path.write_text(json.dumps(valid));link=Path(directory)/'linked.json';link.symlink_to(path)
            with self.assertRaises(RuntimeError):read_listing(link)

    def test_discovery_rejects_execution_options_before_tools_or_cargo(self):
        for extra in [[],['--test-body','--engine','jit'],['--test-body','--instruction-limit','10'],
                      ['--test-body','--allocation-limit','150000'],['--test-body','--inline-leaves'],
                      ['--test-body','--trap-unsupported-calls'],['--test-body','--','7']]:
            with self.subTest(extra=extra),patch.object(sys,'argv',['interpreter.py','--package','fixture','--list-tests',*extra]), \
                    patch.object(interpreter,'checked_tools') as tools,contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as error:
                interpreter.main()
            self.assertEqual(error.exception.code,2);tools.assert_not_called()


if __name__=='__main__':unittest.main()
