"""One explicitly observed read-only preparation or rehearsal; no signals/retry."""
import argparse
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
HERE=ROOT/'experiments/runtime04-historical-copy-reader-rehearsal-01'
P=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
OWNED=X/'experiments/stable-cgu/owned_stage.py'
OWNED_SHA='7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e'
SOURCES={'README.md': 'bd103219aa88d1719b3db9d6db26d742bed412a6176f42632c20412c6df7a4a0', 'common.py': 'b523714f906b2ead5548a1e980637e0c6b02098198cac512b100d8ede534e43c', 'prepare.py': 'aacdb0d58d244bba8166eb5a89d9eec5e16c611a12d0f6dc9fec7dd589acc87c', 'rehearse.py': 'e36396dc035401eb361d07a64f42c0d98d90af2cef83afb810a6f5f61ff99491'}
EXPECTED_LAUNCH=None  # Rehearsal remains disabled until actual preparation review.


def require(ok,message):
    if not ok:raise RuntimeError(message)


def sha(path):
    path=Path(path);before=path.lstat()
    require(path.resolve(strict=True)==path and path.is_file() and before.st_size<=64*2**20,'bounded ordinary dispatcher input')
    with path.open('rb') as stream:answer=hashlib.file_digest(stream,'sha256').hexdigest()
    after=path.lstat()
    require(all(getattr(before,'st_'+key)==getattr(after,'st_'+key) for key in
        ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']),'dispatcher input changed')
    return answer


def read(path):return json.loads(Path(path).read_bytes())


def sources():
    require(type(SOURCES) is dict and set(SOURCES)=={'common.py','prepare.py','rehearse.py','README.md'},'reviewed rehearsal source map remains unbound')
    for name,digest in SOURCES.items():require(sha(HERE/name)==digest,'reviewed rehearsal source changed')
    require(sha(OWNED)==OWNED_SHA,'qualified admission source changed')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['prepare','rehearse'],required=True);args=parser.parse_args()
    require(Path.cwd()==ROOT and sys.dont_write_bytecode and not sys.flags.optimize
        and Path(sys.executable).resolve(strict=True)==P,'exact Python/owner required')
    sources()
    if args.mode=='prepare':
        E=ROOT/'.work/runtime04-historical-copy-reader-preparation-execution-01'
        result=HERE/'preparation.json';target=HERE/'prepare.py';extra=[]
        require(all(not (HERE/name).exists() and not (HERE/name).is_symlink() for name in
            ['inputs.json','plan.json','preparation.json','launch.json']),'fresh preparation output required')
    else:
        require(type(EXPECTED_LAUNCH) is str and len(EXPECTED_LAUNCH)==64
            and sha(HERE/'launch.json')==EXPECTED_LAUNCH,'actual reviewed rehearsal packet remains unbound')
        launch=read(HERE/'launch.json')
        require(launch['status']=='prepared-rehearsal-awaiting-review' and launch['cwd']==str(ROOT)
            and launch['reader_sha256']==SOURCES['rehearse.py'] and launch['common_sha256']==SOURCES['common.py']
            and sha(HERE/'inputs.json')==launch['inputs_sha256'] and sha(HERE/'plan.json')==launch['plan_sha256'],
            'actual prepared rehearsal source/packet changed')
        E=ROOT/'.work/runtime04-historical-copy-reader-rehearsal-execution-01'
        result=ROOT/'.work/runtime04-historical-copy-reader-rehearsal-01/result.json';target=HERE/'rehearse.py'
        extra=['--inputs-sha256',launch['inputs_sha256'],'--plan-sha256',launch['plan_sha256']]
        require(not result.parent.exists() and not result.parent.is_symlink(),'fresh rehearsal result WORK required')
    require(not E.exists() and not E.is_symlink() and not result.exists() and not result.is_symlink(),'fresh explicit execution evidence')
    free=shutil.disk_usage(ROOT).free;require(free>=16*2**30,'fresh16GiB before evidence or child')
    spec=importlib.util.spec_from_file_location('_runtime04_rehearsal_owned',OWNED)
    owned=importlib.util.module_from_spec(spec);spec.loader.exec_module(owned)
    E.mkdir(mode=0o700);(E/'source').mkdir(mode=0o700)
    for source,name in [(HERE/name,name) for name in SOURCES]+[(OWNED,'owned_stage.py'),(Path(__file__).resolve(),'execution.py')]:
        digest=sha(source);data=source.read_bytes();require(hashlib.sha256(data).hexdigest()==digest,'retained source changed')
        with (E/'source'/name).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        require(sha(source)==sha(E/'source'/name)==digest,'source copy readback differs')
    environment=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',
        PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
    record=dict(status='waiting',mode=args.mode,started_at=time.time(),parent_pid=os.getpid(),parent_parent_pid=os.getppid(),
        parent_pgid=os.getpgrp(),parent_argv=list(sys.argv),cwd=str(ROOT),environment=environment,
        source_sha256=SOURCES,execution_source_sha256=sha(__file__),owned_source_sha256=OWNED_SHA,
        canonical_lock=str(owned.CANONICAL_LOCK),wait_seconds=600,capacity=dict(entry_gib=16,live_gib=9,floor_gib=8),
        maximum_child_cpu_seconds=900,maximum_child_read_seconds=1200,maximum_observation_seconds=1250,
        maximum_child_file_bytes=(64 if args.mode=='prepare' else 4)*2**20,
        result=str(result),entry_free_bytes=free,disk_samples=[],
        identity_limitation='In-process parent identity and exact Popen PID/command/cwd/environment/times; no separate contemporaneous ps/cwd probe or signal.',
        runtime_admission=False,retirement_authorized=False,compiler_calls=0,provider_probes=0)
    def save():owned.write(E/'record.json',record)
    save()
    try:
        with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
            sources();record.update(admitted_at=time.time(),free_bytes_before=owned.disk(ROOT,16));save()
            command=[str(P),'-B',str(target),'--canonical-fd',str(fd),
                '--passed-environment-json',json.dumps(environment,sort_keys=True,separators=(',',':')),*extra]
            record['command']=command;save()
            with (E/'stdout').open('xb') as stdout,(E/'stderr').open('xb') as stderr:
                child=subprocess.Popen(command,cwd=ROOT,env=environment,stdin=subprocess.DEVNULL,
                    stdout=stdout,stderr=stderr,pass_fds=(fd,))
                record.update(status='running',pid=child.pid,child_started_at=time.time());deadline=time.monotonic()+1250
                try:
                    try:save()
                    except BaseException as error:record['initial_child_publication_error']=repr(error)
                    while True:
                        try:code=child.wait(timeout=min(5,max(.001,deadline-time.monotonic())));break
                        except subprocess.TimeoutExpired:
                            record['disk_samples'].append(dict(time=time.time(),free_bytes=shutil.disk_usage(ROOT).free))
                            if time.monotonic()>=deadline:
                                code=None;record.update(status='observation-expired-task-not-signaled',may_be_live=True);break
                finally:
                    record.update(returncode=child.returncode,observation_finished_at=time.time(),
                        stdout_sha256=sha(E/'stdout'),stderr_sha256=sha(E/'stderr'))
                    if child.returncode is not None:record.update(status='finished',finished_at=time.time())
                    else:record.update(status='unclosed-task-not-signaled',may_be_live=True)
                    try:save()
                    except BaseException as error:
                        print(json.dumps(dict(status='publication-failed',error=repr(error),observed_record=record)),flush=True);raise
            require(code is not None,'child may be live; no signal or retry')
            require(code==0,'actual read-only child failed; preserve evidence')
            require(not (E/'stderr').read_bytes() and 'initial_child_publication_error' not in record,'raw or publication failure')
            sources();record.update(result_sha256=sha(result),free_bytes_after=owned.disk(ROOT,9));save()
            require(all(row['free_bytes']>=9*2**30 for row in record['disk_samples']),'observed live floor violation')
        record['canonical_released_at']=time.time();save()
        print(json.dumps(dict(record=str(E/'record.json'),sha256=sha(E/'record.json'),result=str(result),
            result_sha256=record['result_sha256'],pid=record['pid'],returncode=0)),flush=True)
    except BaseException as error:record['execution_error']=repr(error);save();raise


if __name__=='__main__':main()
