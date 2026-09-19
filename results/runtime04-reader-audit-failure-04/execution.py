"""Explicit bounded independent saved-reader audit; no retries or signals."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
SOURCE=ROOT/'.work/verify_runtime04_historical_copy_reader_04.py'
EXPECTED='9e9aa4efd43fd5c770cde6147159c771d9f405b0e6896fb426dffe504887a34b'  # Four actual closed preparation/rehearsal pins bound after readback.
E=ROOT/'.work/runtime04-historical-copy-reader-verification-execution-04'
REPORT=ROOT/'.work/runtime04-historical-copy-reader-independent-verification-04.json'
HERE=ROOT/'experiments/runtime04-historical-copy-reader-rehearsal-03'
WORK=ROOT/'.work/runtime04-historical-copy-reader-rehearsal-03'
PREP=ROOT/'.work/runtime04-historical-copy-reader-preparation-execution-03'
EXEC=ROOT/'.work/runtime04-historical-copy-reader-rehearsal-execution-03'
P=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
OWNED=X/'experiments/stable-cgu/owned_stage.py'
OWNED_SHA='7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e'


def require(ok,message):
    if not ok:raise RuntimeError(message)


def sha(path):
    path=Path(path);before=path.lstat()
    require(path.resolve(strict=True)==path and path.is_file() and before.st_size<=64*2**20,'bounded ordinary saved auditor input')
    with path.open('rb') as stream:value=hashlib.file_digest(stream,'sha256').hexdigest()
    require(all(getattr(before,'st_'+key)==getattr(path.lstat(),'st_'+key) for key in
        ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']),'saved auditor input changed')
    return value


def read(path):return json.loads(Path(path).read_bytes())


def closure():
    require(sha(SOURCE)==EXPECTED and sha(OWNED)==OWNED_SHA,'exact reviewed independent source required')
    wanted={'EXPECTED_LAUNCH':HERE/'launch.json','EXPECTED_PREPARATION_RECORD':PREP/'record.json',
        'EXPECTED_EXECUTION_RECORD':EXEC/'record.json','EXPECTED_RESULT':WORK/'result.json'}
    constants={}
    for node in ast.parse(SOURCE.read_bytes()).body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in wanted:
            constants[node.targets[0].id]=ast.literal_eval(node.value)
    require(set(constants)==set(wanted) and all(type(constants[key]) is str and len(constants[key])==64
        and sha(path)==constants[key] for key,path in wanted.items()),'actual prepared and closed rehearsal pins remain unbound or changed')
    actual=read(EXEC/'record.json');preparation=read(PREP/'record.json');result=read(WORK/'result.json')
    require(actual['status']==preparation['status']=='finished' and actual['returncode']==preparation['returncode']==0
        and 'execution_error' not in actual and 'execution_error' not in preparation
        and preparation['canonical_released_at']<=actual['started_at']<=actual['canonical_released_at']
        and actual['result_sha256']==sha(WORK/'result.json')
        and result['status']=='passed-strict-callback-rehearsal-awaiting-independent-audit',
        'two explicitly observed successful closures required before audit')
    return constants


def main():
    require(Path.cwd()==ROOT and sys.dont_write_bytecode and not sys.flags.optimize
        and Path(sys.executable).resolve(strict=True)==P,'fixed independent execution owner/Python')
    pins=closure()
    require(not E.exists() and not E.is_symlink() and not REPORT.exists() and not REPORT.is_symlink(),'fresh audit execution and report')
    free=shutil.disk_usage(ROOT).free;require(free>=16*2**30,'fresh16GiB before audit evidence or child')
    spec=importlib.util.spec_from_file_location('_runtime04_reader_audit_owned',OWNED)
    owned=importlib.util.module_from_spec(spec);spec.loader.exec_module(owned)
    E.mkdir(mode=0o700)
    for source,name in [(SOURCE,'source.py'),(OWNED,'owned_stage.py'),(Path(__file__).resolve(),'execution.py')]:
        digest=sha(source);data=source.read_bytes();require(hashlib.sha256(data).hexdigest()==digest,'source changed during retention')
        with (E/name).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        require(sha(source)==sha(E/name)==digest,'exact retained source readback')
    environment=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',
        PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
    record=dict(status='waiting',started_at=time.time(),parent_pid=os.getpid(),parent_parent_pid=os.getppid(),
        parent_pgid=os.getpgrp(),parent_argv=list(sys.argv),cwd=str(ROOT),environment=environment,
        source_sha256=EXPECTED,execution_source_sha256=sha(__file__),owned_source_sha256=OWNED_SHA,
        actual_closure_pins=pins,canonical_lock=str(owned.CANONICAL_LOCK),wait_seconds=600,
        capacity=dict(entry_gib=16,live_gib=9,floor_gib=8),entry_free_bytes=free,disk_samples=[],
        maximum_child_cpu_seconds=900,maximum_child_read_seconds=1200,maximum_observation_seconds=1250,
        maximum_child_file_bytes=4*2**20,report=str(REPORT),runtime_admission=False,retirement_authorized=False,
        compiler_calls=0,provider_probes=0,
        identity_limitation='Exact in-process parent and Popen child PID/command/cwd/environment/times; no separate ps/cwd probe or signals.')
    def save():owned.write(E/'record.json',record)
    save()
    try:
        with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
            require(closure()==pins,'actual saved closure changed before admission')
            record.update(admitted_at=time.time(),free_bytes_before=owned.disk(ROOT,16));save()
            command=[str(P),'-B',str(SOURCE),'--canonical-fd',str(fd)];record['command']=command;save()
            with (E/'stdout').open('xb') as stdout,(E/'stderr').open('xb') as stderr:
                child=subprocess.Popen(command,cwd=ROOT,env=environment,stdin=subprocess.DEVNULL,
                    stdout=stdout,stderr=stderr,pass_fds=(fd,))
                deadline=time.monotonic()+1250
                record.update(status='running',pid=child.pid,child_started_at=time.time(),observation_errors=[])
                try:
                    try:save()
                    except BaseException as error:record['initial_child_publication_error']=repr(error)
                    while True:
                        try:code=child.wait(timeout=min(5,max(.001,deadline-time.monotonic())));break
                        except subprocess.TimeoutExpired:
                            try:record['disk_samples'].append(dict(time=time.time(),free_bytes=shutil.disk_usage(ROOT).free))
                            except BaseException as error:record['observation_errors'].append(dict(stage='disk-sample',error=repr(error),time=time.time()))
                            if time.monotonic()>=deadline:
                                code=None;record.update(status='observation-expired-task-not-signaled',may_be_live=True);break
                finally:
                    record.update(returncode=child.returncode,observation_finished_at=time.time())
                    if child.returncode is not None:record.update(status='finished',finished_at=time.time())
                    else:record.update(status='unclosed-task-not-signaled',may_be_live=True)
                    for key,path in [('stdout_sha256',E/'stdout'),('stderr_sha256',E/'stderr')]:
                        try:record[key]=sha(path)
                        except BaseException as error:record['observation_errors'].append(dict(stage=key,error=repr(error),time=time.time()))
                    try:save()
                    except BaseException as error:
                        print(json.dumps(dict(status='publication-failed',error=repr(error),observed_record=record)),flush=True);raise
            require(code is not None,'audit child may be live; no signal or retry')
            require(code==0 and not (E/'stderr').read_bytes() and 'initial_child_publication_error' not in record
                and not record['observation_errors'],
                'actual independent audit failed; preserve raw evidence')
            require(sha(SOURCE)==EXPECTED==sha(E/'source.py'),'auditor source changed')
            report=read(REPORT)
            require(report['status']=='verified-strict-callback-rehearsal' and report['pid']==child.pid
                and report['parent_pid']==os.getpid() and report['auditor_sha256']==EXPECTED
                and report['runtime_admission'] is report['retirement_authorized'] is False,
                'actual independent report source/process/scope association')
            record.update(report_sha256=sha(REPORT),free_bytes_after=owned.disk(ROOT,9));save()
            require(all(row['free_bytes']>=9*2**30 for row in record['disk_samples']),'observed live floor violation')
        record['canonical_released_at']=time.time();save()
        print(json.dumps(dict(record=str(E/'record.json'),sha256=sha(E/'record.json'),report=str(REPORT),
            report_sha256=record['report_sha256'],pid=record['pid'],returncode=0)),flush=True)
    except BaseException as error:record['execution_error']=repr(error);save();raise


if __name__=='__main__':main()
