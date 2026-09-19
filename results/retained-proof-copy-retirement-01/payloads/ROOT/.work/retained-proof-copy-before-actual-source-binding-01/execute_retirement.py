"""Unbound one-shot prepare/retire/audit wrapper; never retry or signal.

Preparation and audit hold canonical for their read-only child. Retirement's
controller owns canonical itself, so its outer observer never takes that lock.
Every phase has separate evidence; no successful parent launch implies success.
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
ROOT=HERE.parents[1]
WORK=ROOT/'.work/retained-proof-copy-retirement-01'
PACKET=HERE/'plan-01.json'
AUDIT=ROOT/'.work/retained-proof-copy-retirement-independent-verification-01.json'
PYTHON=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
OWNED=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/stable-cgu/owned_stage.py')
OWNED_SHA='7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e'
SOURCE_BINDINGS=None  # Reviewed exact sources; set before preparation.
ACTUAL_PACKET_SHA=None  # Set only after distinct preparation and complete packet review.
ACTUAL_CLOSURE=None  # Exact receipt/execution hashes, set only after passed retirement closure.
ENV=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',
    PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
LIMIT=16*2**20


def require(ok,message):
    if not ok:raise RuntimeError(message)


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sources():
    require(type(SOURCE_BINDINGS) is dict and set(SOURCE_BINDINGS)==
        {'recovery.py','retire.py','no_consumer.py','prepare_retirement.py','verify_retirement.py'},
        'reviewed source bindings remain unset')
    for name,sha in SOURCE_BINDINGS.items():
        p=HERE/name;s=p.lstat();require(p.resolve(strict=True)==p and stat.S_ISREG(s.st_mode)
            and s.st_size<=2**20 and digest(p)==sha,'exact ordinary reviewed source changed')


def aggregate(evidence,phase):
    paths=[]
    for root in [evidence,*([WORK] if phase=='retire' else [])]:
        if root.exists():
            require(root.is_dir() and not root.is_symlink(),'ordinary exact execution root')
            paths.extend(root.rglob('*'))
    require(len(paths)<=256 and all(not p.is_symlink() for p in paths),'bounded evidence membership')
    require(sum(p.stat().st_size for p in paths if p.is_file())<=LIMIT,'aggregate execution evidence cap')


def main(phase):
    require(phase in ['prepare','retire','audit'] and Path.cwd()==ROOT
        and Path(sys.executable).resolve()==PYTHON and sys.dont_write_bytecode and not sys.flags.optimize,
        'fixed phase/route/interpreter')
    sources()
    if phase!='prepare':
        require(type(ACTUAL_PACKET_SHA) is str and len(ACTUAL_PACKET_SHA)==64
            and digest(PACKET)==ACTUAL_PACKET_SHA,'prepared retirement packet is unbound or changed')
    if phase=='audit':
        require(type(ACTUAL_CLOSURE) is dict and set(ACTUAL_CLOSURE)=={'receipt_sha256','execution_sha256'},
            'actual closed retirement bindings remain unset')
        require(digest(WORK/'receipt.json')==ACTUAL_CLOSURE['receipt_sha256']
            and digest(ROOT/'.work/retained-proof-copy-retirement-execution-01/record.json')==ACTUAL_CLOSURE['execution_sha256'],
            'actual retirement closure changed')
    suffix={'prepare':'retirement-preparation','retire':'retirement','audit':'retirement-audit'}[phase]
    evidence=ROOT/('.work/retained-proof-copy-'+suffix+'-execution-01')
    require(not evidence.exists() and not evidence.is_symlink(),'distinct fresh one-shot execution required')
    required=9*2**30+LIMIT if phase=='retire' else 16*2**30
    require(shutil.disk_usage(ROOT).free>=required,'fresh phase entry before evidence')
    require(digest(OWNED)==OWNED_SHA,'qualified lock helper changed')
    owned=types.ModuleType('_retirement_outer_owned');owned.__file__=str(OWNED)
    exec(compile(OWNED.read_bytes(),str(OWNED),'exec'),owned.__dict__)
    require(owned.CANONICAL_LOCK==Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock'),'exact canonical lock')
    evidence.mkdir(mode=0o700);(evidence/'source').mkdir(mode=0o700)
    for name in SOURCE_BINDINGS:(evidence/'source'/name).write_bytes((HERE/name).read_bytes())
    (evidence/'source/execute_retirement.py').write_bytes(Path(__file__).read_bytes())
    (evidence/'source/owned_stage.py').write_bytes(OWNED.read_bytes())
    script={'prepare':'prepare_retirement.py','retire':'retire.py','audit':'verify_retirement.py'}[phase]
    command=[str(PYTHON),'-B',str(HERE/script)]
    if phase!='prepare':command+=['--inputs-sha256',ACTUAL_PACKET_SHA]
    if phase=='audit':command+=['--receipt-sha256',ACTUAL_CLOSURE['receipt_sha256'],
        '--execution-sha256',ACTUAL_CLOSURE['execution_sha256']]
    record=dict(status='waiting',phase=phase,started_at=time.time(),parent_pid=os.getpid(),parent_parent_pid=os.getppid(),
        command=command,cwd=str(ROOT),environment=ENV,source_sha256=SOURCE_BINDINGS,
        wrapper_sha256=digest(__file__),owned_sha256=OWNED_SHA,signals=[],compiler_calls=0,
        canonical_lock=str(owned.CANONICAL_LOCK),canonical_owner='child' if phase=='retire' else 'wrapper',
        wait_seconds=600,observation_seconds=1250 if phase=='retire' else 650,
        capacity=dict(entry_gib=9 if phase=='retire' else 16,live_gib=9,floor_gib=8,
            entry_reserve_bytes=LIMIT if phase=='retire' else 0),disk_samples=[],
        identity_limitation='Exact Popen PID, parent and requested argv/cwd; no extra identity child and no signals.')
    def save():aggregate(evidence,phase);owned.write(evidence/'record.json',record)
    save();child=None
    def run(lockfd=None):
        nonlocal child
        sources();require(shutil.disk_usage(ROOT).free>=required,'fresh phase admission')
        if phase=='retire':require(not WORK.exists() and not WORK.is_symlink(),'retirement already attempted')
        elif phase=='prepare':require(not PACKET.exists() and not PACKET.is_symlink(),'preparation already attempted')
        else:require(not AUDIT.exists() and not AUDIT.is_symlink(),'independent audit already attempted')
        resource.setrlimit(resource.RLIMIT_CPU,(300,300));resource.setrlimit(resource.RLIMIT_FSIZE,(LIMIT,LIMIT))
        record.update(admitted_at=time.time(),free_bytes_before=shutil.disk_usage(ROOT).free);save()
        with (evidence/'stdout').open('xb') as out,(evidence/'stderr').open('xb') as err:
            record['launch_requested_at']=time.time();save()
            child=subprocess.Popen(command,cwd=ROOT,env=ENV,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                pass_fds=() if lockfd is None else (lockfd,))
            deadline=time.monotonic()+record['observation_seconds']
            record.update(status='running',pid=child.pid,child_started_at=time.time(),observation_errors=[])
            publication_error=None
            try:save()
            except BaseException as error:publication_error=repr(error)
            try:
                while True:
                    try:code=child.wait(timeout=min(1,max(.001,deadline-time.monotonic())));break
                    except subprocess.TimeoutExpired:
                        try:
                            free=shutil.disk_usage(ROOT).free;record['disk_samples'].append(dict(time=time.time(),free_bytes=free))
                            if free<9*2**30:record['capacity_violation']=True
                        except BaseException as error:
                            record['observation_errors'].append(dict(stage='disk-sample',error=repr(error),time=time.time()))
                        try:save()
                        except BaseException as error:publication_error=repr(error)
                        if time.monotonic()>=deadline:
                            code=None;break
            finally:
                record.update(returncode=child.returncode,observation_finished_at=time.time())
                if child.returncode is not None:record.update(status='finished',finished_at=time.time())
                else:record.update(status='unresolved-live-child-not-signalled',child_may_remain_live=True)
                for name in ['stdout','stderr']:
                    try:record[name+'_sha256']=digest(evidence/name)
                    except BaseException as error:
                        record['observation_errors'].append(dict(stage=name+'-hash',error=repr(error),time=time.time()))
                if publication_error is not None:record['publication_error']=publication_error
                try:save()
                except BaseException as error:
                    print(json.dumps(dict(status='publication-failed',error=repr(error),observed_record=record)),flush=True);raise
        require(code is not None,'observation expired; child not signaled or retried')
        require(code==0 and not (evidence/'stderr').read_bytes() and publication_error is None
            and not record['observation_errors'] and not record.get('capacity_violation'),
            'phase failed after explicit child closure; no retry')
        if phase=='prepare':
            answer=json.loads((evidence/'stdout').read_bytes())
            require(answer['status']=='prepared-unrun-exact-copy-retirement'
                and answer['sha256']==digest(PACKET),'actual prepared packet binding')
            record['prepared_packet']=answer
        elif phase=='retire':
            receipt=json.loads((WORK/'receipt.json').read_bytes())
            require(not (evidence/'stdout').read_bytes() and receipt['status']=='passed'
                and receipt['packet_sha256']==ACTUAL_PACKET_SHA and receipt['pid']==child.pid
                and receipt['parent_pid']==os.getpid()
                and record['launch_requested_at']<=receipt['started_at']<=receipt['admitted_at']
                    <=receipt['finished_at']<=receipt['canonical_released_at']<=record['finished_at'],
                'actual retirement terminal and canonical release required')
            record.update(receipt_sha256=digest(WORK/'receipt.json'),actual_canonical_released_at=receipt['canonical_released_at'])
        else:
            answer=json.loads((evidence/'stdout').read_bytes())
            require(answer['status']=='verified-exact-proof-copy-retirement' and answer['report']==str(AUDIT)
                and answer['sha256']==digest(AUDIT),'actual independent report binding')
            record.update(result_path=str(AUDIT),result_sha256=answer['sha256'])
        sources();record['free_bytes_after']=owned.disk(ROOT,9);save()
    try:
        if phase=='retire':run()
        else:
            with owned.workload_lock(owned.CANONICAL_LOCK,600) as lockfd:run(lockfd)
            record['canonical_released_at']=time.time()
        record['observation_closed_at']=time.time();save();print(json.dumps(record,sort_keys=True))
    except BaseException as error:
        record['error']=repr(error)
        if child is not None and record.get('status')!='finished':record['child_may_remain_live']=child.poll() is None
        save();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['prepare','retire','audit'],required=True)
    main(parser.parse_args().phase)
