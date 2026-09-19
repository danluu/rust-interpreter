"""Unbound one-shot preparation/recovery dispatcher with explicit bounded wait.

Each phase has a different fresh evidence directory. This never launches the
retirement wrapper, test fixtures, compiler or provider processes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import stat
import subprocess
import sys
import time
import types

HERE=Path(__file__).resolve().parent
OWNER=HERE.parents[1]
PYTHON=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
OWNED=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/stable-cgu/owned_stage.py')
OWNED_SHA='7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e'
SOURCE_BINDINGS={'recovery.py': '572907bc8ebd093b33cbe82906e8ed5c1409eadd9de3adbe27bf8c3604009474', 'prepare_recovery.py': 'f85dc1191c86edceba17051c53217ddb86edf478ba067fbf0f84b159911c3269', 'recover.py': '54cc6dc6982bafced123e145fd4ea79733d724f0607ceb16d7c4900c6abcb9bf'}  # Exact final source bytes after independent review.
ACTUAL_PACKET_SHA='f27de3771873cf07b2206e9a1add3c99c1d6bcc70cd94d2e95df1a2d93090de9'  # Only recovery needs the actual prepared packet digest.
ENV=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',
    PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')

def require(ok,message):
    if not ok:raise RuntimeError(message)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def sources():
    require(type(SOURCE_BINDINGS) is dict and set(SOURCE_BINDINGS)=={'recovery.py','prepare_recovery.py','recover.py'},'unbound reviewed source set')
    for name,sha in SOURCE_BINDINGS.items():
        path=HERE/name;require(path.resolve(strict=True)==path and stat.S_ISREG(path.lstat().st_mode)
            and digest(path)==sha,'exact reviewed source changed')
def main(phase):
    require(phase in ['prepare','recovery'] and Path.cwd()==OWNER and Path(sys.executable).resolve()==PYTHON
            and sys.dont_write_bytecode and not sys.flags.optimize,'fixed dispatcher route')
    sources()
    if phase=='recovery':require(type(ACTUAL_PACKET_SHA) is str and len(ACTUAL_PACKET_SHA)==64,'actual recovery packet digest remains unbound')
    evidence=OWNER/('.work/retained-proof-copy-'+('recovery-preparation' if phase=='prepare' else 'recovery')+'-execution-01')
    require(not evidence.exists() and not evidence.is_symlink(),'fresh one-shot execution evidence')
    require(shutil.disk_usage(OWNER).free>=16*2**30,'fresh read-only 16GiB entry before evidence')
    require(digest(OWNED)==OWNED_SHA,'qualified admission helper source')
    owned=types.ModuleType('_copy_recovery_owned');owned.__file__=str(OWNED)
    exec(compile(OWNED.read_bytes(),str(OWNED),'exec'),owned.__dict__)
    require(owned.CANONICAL_LOCK==Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock'),'fixed canonical lock')
    evidence.mkdir(mode=0o700);(evidence/'source').mkdir(mode=0o700)
    for name in SOURCE_BINDINGS:(evidence/'source'/name).write_bytes((HERE/name).read_bytes())
    (evidence/'source/execute_recovery.py').write_bytes(Path(__file__).read_bytes())
    (evidence/'source/owned_stage.py').write_bytes(OWNED.read_bytes())
    command=[str(PYTHON),'-B',str(HERE/('prepare_recovery.py' if phase=='prepare' else 'recover.py'))]
    if phase=='recovery':command+=['--inputs-sha256',ACTUAL_PACKET_SHA]
    record=dict(status='waiting',phase=phase,started_at=time.time(),parent_pid=os.getpid(),parent_parent_pid=os.getppid(),
        command=command,cwd=str(OWNER),environment=ENV,source_sha256=SOURCE_BINDINGS,
        wrapper_sha256=digest(__file__),owned_sha256=OWNED_SHA,canonical_lock=str(owned.CANONICAL_LOCK),
        wait_seconds=600,capacity=dict(entry_gib=16,live_gib=9,floor_gib=8),signals=[],workload_children=0,
        identity_limitation='Exact Popen child PID and in-process parent observation; no separate ps/cwd child probes and no signals.',disk_samples=[])
    def save():owned.write(evidence/'record.json',record)
    save()
    child=None
    try:
        with owned.workload_lock(owned.CANONICAL_LOCK,600) as lockfd:
            record.update(admitted_at=time.time(),free_bytes_before=owned.disk(OWNER,16));save();sources()
            resource.setrlimit(resource.RLIMIT_CPU,(300,300));resource.setrlimit(resource.RLIMIT_FSIZE,(16*2**20,16*2**20))
            if phase=='recovery':require(digest(HERE/'recovery-plan-01.json')==ACTUAL_PACKET_SHA,'actual packet changed before child')
            with (evidence/'stdout').open('xb') as stdout,(evidence/'stderr').open('xb') as stderr:
                child=subprocess.Popen(command,cwd=OWNER,env=ENV,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,pass_fds=(lockfd,))
                record.update(status='running',pid=child.pid,child_started_at=time.time())
                publication_error=None
                try:save()
                except BaseException as error:publication_error=repr(error)
                deadline=time.monotonic()+650
                while True:
                    try:code=child.wait(timeout=min(1,max(.001,deadline-time.monotonic())));break
                    except subprocess.TimeoutExpired:
                        free=shutil.disk_usage(OWNER).free;record['disk_samples'].append(dict(time=time.time(),free_bytes=free))
                        if free<9*2**30:record['capacity_violation']=True
                        try:save()
                        except BaseException as error:publication_error=repr(error)
                        if time.monotonic()>=deadline:
                            record.update(status='unresolved-live-child-not-signaled',observation_finished_at=time.time());save();raise
            record.update(status='finished',returncode=code,finished_at=time.time(),stdout_sha256=digest(evidence/'stdout'),stderr_sha256=digest(evidence/'stderr'))
            if publication_error is not None:record['publication_error']=publication_error
            save();require(code==0 and not (evidence/'stderr').read_bytes() and publication_error is None
                and not record.get('capacity_violation'),'read-only child failed; no retry')
            answer=json.loads((evidence/'stdout').read_bytes())
            if phase=='prepare':
                require(answer['status']=='prepared-unrun-read-only-recovery' and answer['sha256']==digest(HERE/'recovery-plan-01.json'),'actual preparation packet binding')
                record['prepared_packet']=answer
            else:
                require(answer['status']=='verified-read-only-exact-copy-recovery' and answer['result']==str(OWNER/'.work/retained-proof-copy-recovery-01.json')
                    and answer['result_sha256']==digest(answer['result']),'actual recovery result binding')
                record['result_sha256']=answer['result_sha256'];record['result_path']=answer['result']
            sources();record['free_bytes_after']=owned.disk(OWNER,9);save()
        record['canonical_released_at']=time.time();save();print(json.dumps(record,sort_keys=True))
    except BaseException as error:
        record['error']=repr(error)
        if child is not None and record.get('status')!='finished':record['child_may_remain_live']=child.poll() is None
        save();raise

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['prepare','recovery'],required=True)
    main(parser.parse_args().phase)
