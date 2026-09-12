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

class FilteredSelectionControls(unittest.TestCase):
    def test_filtered_selection_binds_exact_names_skips_and_bytecode(self):
        import hashlib
        from test_discovery import read_selection
        with tempfile.TemporaryDirectory() as directory:
            artifact=Path(directory)/'program.rbc';artifact.write_bytes(b'checked fixture')
            path=Path(str(artifact)+'.selection.json')
            tests=[entry('case'),entry('nested::case'),entry('nested::ignored',ignored=True,should_panic=True)]
            for pattern,exact,names,skipped in [('case',False,['case','nested::case'],[]),
                    ('case',True,['case'],[]),('nested::',False,['nested::case'],['nested::ignored'])]:
                selection=dict(report(tests),kind='test-selection',filter=dict(pattern=pattern,exact=exact),
                    selected=names,skipped_ignored=skipped,artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest())
                path.write_text(json.dumps(selection))
                actual,digest=read_selection(path,artifact,pattern,exact)
                self.assertEqual(actual,selection);self.assertEqual(len(digest),64)

    def test_stale_filter_unsupported_semantics_and_changed_artifacts_are_rejected(self):
        import hashlib
        from test_discovery import read_selection
        with tempfile.TemporaryDirectory() as directory:
            artifact=Path(directory)/'program.rbc';artifact.write_bytes(b'checked fixture')
            path=Path(str(artifact)+'.selection.json')
            valid=dict(report([entry('case'),entry('ignored',ignored=True)]),kind='test-selection',
                filter=dict(pattern='',exact=False),selected=['case'],skipped_ignored=['ignored'],
                artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest())
            bad=[dict(valid,selected=[]),dict(valid,selected=['case','ignored']),dict(valid,skipped_ignored=[]),
                 dict(valid,artifact_sha256='0'*64),dict(valid,filter=dict(pattern='case',exact=False)),
                 dict(valid,filter=dict(pattern='',exact=0)),dict(valid,executed=True)]
            panic=copy.deepcopy(valid);panic['tests'][0]=entry('case',should_panic=True);bad.append(panic)
            empty=dict(valid,tests=[],count=0,selected=[],skipped_ignored=[]);bad.append(empty)
            large=dict(valid,tests=[entry(f'case_{i:03}') for i in range(257)],count=257,
                       selected=[f'case_{i:03}' for i in range(257)],skipped_ignored=[]);bad.append(large)
            for value in bad:
                path.write_text(json.dumps(value))
                with self.subTest(value=str(value)[:150]),self.assertRaises(RuntimeError):read_selection(path,artifact,'',False)
            path.write_text(json.dumps(valid));artifact.write_bytes(b'changed fixture')
            with self.assertRaises(RuntimeError):read_selection(path,artifact,'',False)

    def test_filter_requires_isolated_test_mode_and_bounded_pattern_before_tools(self):
        invalid=[['--test-filter','case'],['--test-filter','case','--test-body'],
                 ['--entry','case','--test-exact'],['--list-tests','--test-body','--test-exact'],
                 ['--test-filter','line\n','--test-body','--isolated-batch','prepared','--suite-report','unused.json'],
                 ['--test-filter','x'*4097,'--test-body','--isolated-batch','prepared','--suite-report','unused.json']]
        for extra in invalid:
            with self.subTest(extra=str(extra)[:120]),patch.object(sys,'argv',['interpreter.py','--package','fixture',*extra]), \
                    patch.object(interpreter,'checked_tools') as tools,contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as error:
                interpreter.main()
            self.assertEqual(error.exception.code,2);tools.assert_not_called()


if __name__=='__main__':unittest.main()
