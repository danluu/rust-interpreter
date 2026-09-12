import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_suite import selected_executable, test_status
from suite_reports import read_report, validate_report, validate_runtime_limits


def libtest(name='fixture', status='ok', passed=1, failed=0, ignored=0):
    return f'test {name} ... {status}\n\ntest result: {"FAILED" if failed else "ok"}. {passed} passed; {failed} failed; {ignored} ignored; 0 measured; 0 filtered out; finished in 0.00s\n'


class SuiteReportTests(unittest.TestCase):
    def test_omitted_reference_limit_cannot_match_an_effective_default_receipt(self):
        report = dict(runtime_limits=dict(instructions=100_000_000_000, allocations=100_000,
                                          memory_bytes=64*1024*1024, frames=4096),
                      jit_code_limit_bytes=16*1024*1024)
        with self.assertRaises(RuntimeError):
            validate_runtime_limits(report, 100_000_000_000, 150_000, required=True)
        report['runtime_limits']['allocations'] = 150_000
        validate_runtime_limits(report, 100_000_000_000, 150_000, required=True)
        validate_runtime_limits({}, 100_000_000_000, 150_000)
        with self.assertRaises(RuntimeError):
            validate_runtime_limits({}, 100_000_000_000, 150_000, required=True)
        report['runtime_limits']['instructions'] = True
        with self.assertRaises(RuntimeError):
            validate_runtime_limits(report, 1, 150_000, required=True)

    def test_native_control_requires_one_real_exact_test(self):
        self.assertEqual(test_status('fixture', 0, libtest()), 'passed')
        self.assertEqual(test_status('fixture', 101, libtest(status='FAILED', passed=0, failed=1)), 'failed')
        for code, text in [(0, libtest(name='other')), (0, libtest(passed=0)),
                           (0, libtest(status='ignored', passed=0, ignored=1)),
                           (0, libtest()+libtest()), (101, libtest()),
                           (1, 'compiler error'), (0, libtest(passed=2))]:
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                test_status('fixture', code, text)

    def test_cargo_executable_must_be_unique_and_inside_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'target'; target.mkdir()
            executable = target / 'unit-test'; executable.write_bytes(b'executable')
            event = dict(reason='compiler-artifact', profile=dict(test=True), target=dict(kind=['lib']), executable=str(executable))
            self.assertEqual(selected_executable(json.dumps(event), target), executable)
            bad = [dict(event, profile=dict(test=False)), dict(event, target=dict(kind=['bin']))]
            for row in bad:
                with self.assertRaises(RuntimeError): selected_executable(json.dumps(row), target)
            with self.assertRaises(RuntimeError): selected_executable(json.dumps(event)+'\n'+json.dumps(event), target)
            outside = Path(directory) / 'outside'; outside.write_bytes(b'outside')
            with self.assertRaises(RuntimeError): selected_executable(json.dumps(dict(event, executable=str(outside))), target)
            link = target / 'linked'; link.symlink_to(executable)
            with self.assertRaises(RuntimeError): selected_executable(json.dumps(dict(event, executable=str(link))), target)

    def test_wrong_edit_rejects_budget_or_unsupported_error_even_with_failure_count(self):
        report = dict(schema_version=1, mode='prepared', status='failed', passed=1, failed=1,
            tests=[dict(name='one', status='failed', error='guest trap: assertion failed: expected value in one'),
                   dict(name='two', status='passed')])
        self.assertEqual(validate_report(report, ['one','two'], 'prepared', False), [('one','failed'),('two','passed')])
        for error in ['instruction limit exceeded', 'guest trap: unsupported foreign call in one', 'allocation limit exceeded']:
            bad=copy.deepcopy(report);bad['tests'][0]['error']=error
            with self.subTest(error=error), self.assertRaises(RuntimeError): validate_report(bad,['one','two'],'prepared',False)
        for key, value in [('passed',2), ('mode','fresh'), ('status','passed')]:
            with self.subTest(key=key), self.assertRaises(RuntimeError): validate_report(dict(report,**{key:value}),['one','two'],'prepared',False)
        with self.assertRaises(RuntimeError): validate_report(report,['two','one'],'prepared',False)

    def test_changed_or_redirected_report_cannot_reuse_old_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'suite.json';path.write_text('{"status":"passed"}')
            report,digest=read_report(path)
            self.assertEqual(report['status'],'passed')
            path.write_text('{"status":"failed"}')
            with self.assertRaises(RuntimeError): read_report(path,digest)
            link=Path(directory)/'linked.json';link.symlink_to(path)
            with self.assertRaises(RuntimeError): read_report(link)


if __name__ == '__main__':
    unittest.main()
