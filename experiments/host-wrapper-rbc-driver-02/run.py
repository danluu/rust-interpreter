"""Authenticate immutable inputs; normally wait one bounded-observation RBC suite."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    for name in ('binding','binding-sha256','tool-key'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();raw=Path(args.binding).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=args.binding_sha256:raise RuntimeError('reviewed binding differs')
    candidate=json.loads(raw)
    if not {str(Path(__file__).resolve()),str(HERE/'support.py')} <= set(candidate['sources']):
        raise RuntimeError('caller/support source authentication missing')
    for p,h in candidate['sources'].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:raise RuntimeError('pre-import source changed: '+p)
    spec=importlib.util.spec_from_file_location('_rbc_run_support',HERE/'support.py')
    s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
    binding=s.binding(args.binding,args.binding_sha256,args.tool_key)
    s.require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd()==s.R,'fixed parent -B/R cwd')
    s.require(not os.path.lexists(s.WORK) and not os.path.lexists(s.OUT),'fresh fixture output namespaces required')
    limits=dict(canonical_wait_seconds=600,suite_observed_seconds=600,child_observed_seconds=30,
                owned_bytes=2**30,owned_entries=65536,entry_gib=16,stop_gib=9,floor_gib=8)
    s.require(binding['limits']==limits and binding['tests']==list(s.TESTS),'fixed resource/test policy required')
    def no_signals(event,arguments):
        if event in ('os.kill','os.killpg'):raise RuntimeError('process signals forbidden')
    sys.addaudithook(no_signals)
    with s.LOCK.open('r') as lock:
        deadline=time.monotonic()+600
        while True:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                s.require(time.monotonic()<deadline,'canonical acquisition exceeded600s');time.sleep(.1)
        s.require(shutil.disk_usage(s.ROOT).free>=16*2**30,'entry requires16GiB free')
        s.configuration_absent()
        s.WORK.mkdir();s.OUT.mkdir();(s.WORK/'tmp').mkdir();(s.WORK/'artifacts').mkdir()
        record=dict(status='admitted',parent_pid=os.getpid(),parent_parent_pid=os.getppid(),
            started_at=time.time(),binding=s.file(Path(args.binding)),tool_key=args.tool_key,
            canonical_lock=str(s.LOCK),limits=limits,signals=0,retries=0,benchmark=False,child_may_be_live=False)
        s.write(s.OUT/'record.json',record)
        try:
            with s.environment(binding['environment']),s.readers(binding['sources']) as modules:
                before,compiler,std=s.authenticate(binding,modules);s.write(s.OUT/'inputs-before.json',before)
                tools=s.R/'.work/interpreter-tools'/args.tool_key
                env=dict(binding['environment'],RUST_INTERP_TEST_EXPORTER=str(tools/'rust-interp-mir-export'),
                    RUST_INTERP_TEST_WRAPPER=str(tools/'rust-interp-rustc-wrapper'),RUST_INTERP_TEST_RUSTC=str(compiler.rustc),
                    RUST_INTERP_TEST_CARGO=binding['cargo'],RUST_INTERP_TEST_STD_SYSROOT=str(std),
                    RUST_INTERP_TEST_VM=str(tools/'rust-interp-vm'),RUST_INTERP_TEST_ARTIFACT_DIR=str(s.WORK/'artifacts'))
                command=[sys.executable,'-B',str(HERE/'suite.py'),'--binding',args.binding,
                         '--binding-sha256',args.binding_sha256,'--tool-key',args.tool_key]
                record.update(command=command,cwd=str(s.R),environment=env,status='running');s.write(s.OUT/'record.json',record)
                errors=[];started=time.monotonic();peak=dict(logical_bytes=0,allocated_bytes=0,entries=0)
                with (s.OUT/'stdout').open('xb') as stdout,(s.OUT/'stderr').open('xb') as stderr:
                    child=subprocess.Popen(command,cwd=s.R,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
                    record.update(child_pid=child.pid,child_started_at=time.time(),child_may_be_live=True)
                    try:
                        s.write(s.OUT/'record.json',record)
                        while child.poll() is None:
                            try:
                                elapsed=time.monotonic()-started;free=shutil.disk_usage(s.ROOT).free;fp=s.footprint()
                                peak={k:max(peak[k],fp[k]) for k in peak}
                                s.require(elapsed<=600,'suite600s observed threshold exceeded')
                                s.require(free>=9*2**30,'stop9GiB free threshold exceeded')
                                s.require(max(fp['logical_bytes'],fp['allocated_bytes'])<=2**30,'owned1GiB threshold exceeded')
                                for p in (s.WORK/'artifacts').glob('*/commands/*/record.json'):
                                    with p.open('rb') as live:
                                        raw=live.read(1024*1024+1)
                                    s.require(len(raw)<=1024*1024,'live receipt bound')
                                    r=json.loads(raw)
                                    s.require(r['status']!='running' or time.time()-r['started_at']<=30,'child30s observed threshold exceeded: '+str(p))
                            except BaseException as error:
                                if repr(error) not in errors:errors.append(repr(error));s.write(s.OUT/'STOP.json',dict(errors=errors,at=time.time()))
                            time.sleep(.25)
                    finally:
                        code=child.wait()
                        record.update(status='closed',returncode=code,child_may_be_live=False,normal_wait_completed=True,
                            child_finished_at=time.time(),suite_seconds=time.monotonic()-started,observation_errors=errors,observed_peak=peak)
                        s.write(s.OUT/'record.json',record)
                # Always save the complete after readback, including on test failure.
                s.configuration_absent()
                after,_,_=s.authenticate(binding,modules);s.write(s.OUT/'inputs-after.json',after)
                s.require(before==after,'immutable source/tool/runtime/std input changed')
                result=s.read(s.OUT/'suite-result.json');ids=['_host_codegen_rbc_fixture.HostCodegenNativeTests.'+n for n in sorted(s.TESTS)]
                s.require(code==0 and not errors and result['status']=='passed' and result['tests_run']==5
                    and result['test_ids']==result['expected_test_ids']==ids
                    and all(result[n]==0 for n in ('skipped','expected_failures','unexpected_successes','failures','errors')),
                    'complete five-test actual suite success required')
                s.require(record['suite_seconds']<=600 and 0<len(result['commands'])<=256,'final suite/time/command bound')
                fp=s.footprint();s.require(max(fp['logical_bytes'],fp['allocated_bytes'])<=2**30,'final owned output bound')
                s.require(shutil.disk_usage(s.ROOT).free>=8*2**30,'final8GiB free floor')
                record.update(status='passed',result=s.file(s.OUT/'suite-result.json'),inputs_unchanged=True,
                    stdout=s.file(s.OUT/'stdout'),stderr=s.file(s.OUT/'stderr'),footprint=fp,application_fixture_qualified=True)
        except BaseException as error:
            record.update(status='failed',error=repr(error));raise
        finally:
            record.update(finished_at=time.time());s.write(s.OUT/'record.json',record)
    print(json.dumps(record,sort_keys=True))


if __name__=='__main__':main()
