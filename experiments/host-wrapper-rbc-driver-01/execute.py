"""Normal OS parent for the separately authenticated five-test RBC driver."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    for name in ('binding','binding-sha256','tool-key'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();raw=Path(args.binding).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=args.binding_sha256:raise RuntimeError('actual reviewed binding differs')
    value=json.loads(raw)
    if not {str(Path(__file__).resolve()),str(HERE/'support.py')} <= set(value['sources']):
        raise RuntimeError('parent/support source authentication missing')
    for p,h in value['sources'].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:raise RuntimeError('parent source changed: '+p)
    spec=importlib.util.spec_from_file_location('_rbc_execute_support',HERE/'support.py')
    s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
    binding=s.binding(args.binding,args.binding_sha256,args.tool_key)
    s.require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd()==s.R,'normal parent requires -B/R cwd')
    s.require(not any(os.path.lexists(p) for p in (s.EXECUTION,s.WORK,s.OUT)),'fresh execution/work/output required')
    def no_signals(event,arguments):
        if event in ('os.kill','os.killpg'):raise RuntimeError('process signals forbidden')
    sys.addaudithook(no_signals)
    s.EXECUTION.mkdir()
    command=[sys.executable,'-B',str(HERE/'run.py'),'--binding',args.binding,
             '--binding-sha256',args.binding_sha256,'--tool-key',args.tool_key]
    record=dict(status='starting',parent_pid=os.getpid(),parent_parent_pid=os.getppid(),started_at=time.time(),
        command=command,cwd=str(s.R),environment=binding['environment'],binding=s.file(args.binding),
        tool_key=args.tool_key,source=s.file(__file__),signals=0,retries=0,benchmark=False,
        driver_may_be_live=False,normal_wait_completed=False,
        resource_policy='Driver alone owns canonical600; observed suite600/direct-child30 seconds, owned1GiB, entry16/stop9/floor8GiB. Normal wait; no signals or hard CPU/memory/time quota.')
    s.write(s.EXECUTION/'record.json',record)
    try:
        with (s.EXECUTION/'stdout').open('xb') as stdout,(s.EXECUTION/'stderr').open('xb') as stderr:
            child=subprocess.Popen(command,cwd=s.R,env=binding['environment'],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
            try:
                record.update(status='running',pid=child.pid,child_started_at=time.time(),driver_may_be_live=True)
                s.write(s.EXECUTION/'record.json',record)
            finally:
                code=child.wait()
                record.update(status='closed',returncode=code,child_finished_at=time.time(),
                    driver_may_be_live=False,normal_wait_completed=True)
                # Publish known OS closure before parsing any driver result.
                s.write(s.EXECUTION/'record.json',record)
        record.update(stdout=s.file(s.EXECUTION/'stdout'),stderr=s.file(s.EXECUTION/'stderr'))
        driver=s.read(s.OUT/'record.json')
        s.require(driver['parent_pid']==child.pid and driver['parent_parent_pid']==os.getpid()
            and record['started_at']<=driver['started_at']<=driver['finished_at']<=record['child_finished_at'],
            'exact normally waited driver association required')
        record.update(driver_record=s.file(s.OUT/'record.json'),driver_status=driver['status'])
        s.require(code==0 and driver['status']=='passed' and driver['returncode']==0
            and driver['normal_wait_completed'] is True and driver['child_may_be_live'] is False
            and driver['inputs_unchanged'] is True,'complete closed driver success required')
        record.update(status='passed',result=driver['result'])
    except BaseException as error:
        record.update(status='failed',error=repr(error));raise
    finally:
        record.update(finished_at=time.time());s.write(s.EXECUTION/'record.json',record)
    print(json.dumps(record,sort_keys=True))


if __name__=='__main__':main()
