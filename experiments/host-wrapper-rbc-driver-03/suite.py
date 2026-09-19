"""One exact five-test child with observed per-command gates and retained raw IO."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time
import unittest

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    for name in ('binding','binding-sha256','tool-key'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();data=Path(args.binding).read_bytes()
    if hashlib.sha256(data).hexdigest()!=args.binding_sha256:raise RuntimeError('binding changed')
    draft=json.loads(data)
    if not {str(Path(__file__).resolve()),str(HERE/'support.py')} <= set(draft['sources']):
        raise RuntimeError('caller/support source authentication missing')
    for p,h in draft['sources'].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:raise RuntimeError('child source changed: '+p)
    spec=importlib.util.spec_from_file_location('_rbc_suite_support',HERE/'support.py')
    s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
    binding=s.binding(args.binding,args.binding_sha256,args.tool_key)
    s.require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd()==s.R,'fixed child -B/R cwd')
    def no_signals(event,arguments):
        if event in ('os.kill','os.killpg'):raise RuntimeError('fixture signals forbidden')
    sys.addaudithook(no_signals)
    sys.path.insert(0,str(s.R/'scripts'))
    io=s.load(s.R/'scripts/workflow_io.py','workflow_io')
    original_capture=io.capture;started=time.monotonic();violations=[];commands=[]
    def gate():
        s.configuration_absent()
        if (s.OUT/'STOP.json').exists():raise RuntimeError('parent observation requires no further child')
        if violations:raise RuntimeError('previous child observation failed')
        s.require(time.monotonic()-started<=600,'suite600s observed threshold exceeded')
        s.require(shutil.disk_usage(s.ROOT).free>=9*2**30,'stop9GiB free threshold')
        fp=s.footprint();s.require(max(fp['logical_bytes'],fp['allocated_bytes'])<=2**30,'owned1GiB threshold')
    def observed_capture(command,*,cwd,env,receipt_path,receipt):
        gate();s.require(len(commands)<256,'direct command limit256 reached');before=time.monotonic()
        result=original_capture(command,cwd=cwd,env=env,receipt_path=receipt_path,receipt=receipt)
        child,stdout,stderr=result;elapsed=time.monotonic()-before
        directory=Path(receipt_path).parent
        # Persist streams even if a subsequent boundary check refuses progress.
        # The held fixture rewrites identical raw bytes after capture returns, so
        # raw references bind bytes, not the earlier write's transient stamp.
        (directory/'stdout').write_text(stdout);(directory/'stderr').write_text(stderr)
        record=s.read(receipt_path)
        s.require(record['status']=='finished' and record['returncode']==child.returncode,'normal child closure required')
        observation=dict(seconds=elapsed,limit_seconds=30,passed=elapsed<=30,receipt=s.file(receipt_path),
                         stdout={k:v for k,v in s.file(directory/'stdout').items() if k!='identity'},
                         stderr={k:v for k,v in s.file(directory/'stderr').items() if k!='identity'})
        s.write(directory/'observation.json',observation);commands.append(observation)
        if elapsed>30:violations.append(dict(kind='child-seconds',receipt=str(receipt_path),seconds=elapsed))
        return result
    io.capture=observed_capture
    fixture=s.load(s.FIXTURE,'_host_codegen_rbc_fixture')
    names=unittest.defaultTestLoader.getTestCaseNames(fixture.HostCodegenNativeTests)
    s.require(names==sorted(s.TESTS),'exact five inherited fixture methods required')
    expected=['_host_codegen_rbc_fixture.HostCodegenNativeTests.'+n for n in sorted(s.TESTS)]
    class Result(unittest.TextTestResult):
        def __init__(self,*a,**k):super().__init__(*a,**k);self.identifiers=[]
        def startTest(self,test):self.identifiers.append(test.id());super().startTest(test)
    suite=unittest.TestSuite(fixture.HostCodegenNativeTests(n) for n in names)
    result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
    passed=(result.wasSuccessful() and result.testsRun==5 and result.identifiers==expected
        and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses
        and not violations and not (s.OUT/'STOP.json').exists())
    # Enumerate actual loaded project modules, including dynamic donor imports.
    loaded={}
    for module in list(sys.modules.values()):
        path=getattr(module,'__file__',None)
        if path and str(Path(path).resolve()).startswith('/Users/danluu/dev/'):
            p=str(Path(path).resolve())
            s.require(p in binding['sources'],'undeclared dynamic local import: '+p)
            loaded[p]=s.file(p,binding['sources'][p])
    s.write(s.OUT/'suite-result.json',dict(status='passed' if passed else 'failed',tests_run=result.testsRun,
        test_ids=result.identifiers,expected_test_ids=expected,skipped=len(result.skipped),
        expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses),
        failures=len(result.failures),errors=len(result.errors),commands=commands,violations=violations,
        loaded_sources=loaded,seconds=time.monotonic()-started,benchmark=False))
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
