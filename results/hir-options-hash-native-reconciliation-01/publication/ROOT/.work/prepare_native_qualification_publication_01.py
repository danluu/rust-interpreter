"""One read-only exact publication preparation; canonical exclusion, no signals/retry."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
HERE=ROOT/'experiments/native-qualification-publication-01'
WORK=ROOT/'.work/native-qualification-publication-preparation-01'
LOCK=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
SCOPE=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/.work/native-qualification-publication-scope-02.json')
SCOPE_SHA='ba41bc923eded61ac0d1c044aeaec2c80466d9d4af3b255009d1c4ecffd8d308'
SOURCES={'retain.py':'0020c7ae6aa710c7013a4f9d98765fdb5e1aa9e01ed6ce4cbe3a9247c10eeae1',
'history.py':'2c75faf29e0322ca29f764900c1f7af2b5c3b9603c2945c2aeafa62f5210bc38',
'prepare.py':'4515e2d235573cfc5e27cbe0ad4c4ceb6de8afe2fbc5092bca11e6facdfb5354',
'README.md':'82e6ed5064cc79f17c7a0f69fbf9a8ad9a488a7815d24c101b9d344387b04e7b',
'engine-from-B308.diff':'41577f07fa59b85d82d008c5e15585a93385bc4505bec284716221f702e40020'}

def require(ok,message):
    if not ok:raise RuntimeError(message)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def save(record):
    staged=WORK/'record.staged'
    with staged.open('x') as stream:
        json.dump(record,stream,sort_keys=True,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    staged.replace(WORK/'record.json')

def main():
    require(Path.cwd()==ROOT and sys.dont_write_bytecode and not sys.flags.optimize,'exact owner/unoptimized -B')
    require(not WORK.exists() and not WORK.is_symlink(),'fresh preparation execution required')
    for name,digest in SOURCES.items():require(sha(HERE/name)==digest,'approved source differs: '+name)
    require(sha(SCOPE)==SCOPE_SHA,'reviewed scope differs')
    absent=[HERE/'inputs.json',HERE/'launch.json',ROOT/'.work/native-qualification-publication-01',
        ROOT/'results/hir-options-hash-native-reconciliation-01',ROOT/'experiments/native-qualification-source-01']
    require(all(not path.exists() and not path.is_symlink() for path in absent),'fresh proposal/archive/source-copy routes required')
    entry=shutil.disk_usage(ROOT).free;require(entry>=16*2**30,'fresh16GiB read-only admission required')
    command=[str(Path('/opt/homebrew/bin/python3').resolve(strict=True)),'-B',str(HERE/'prepare.py')]
    env=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',
        PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR='/tmp')
    WORK.mkdir();(WORK/'source').mkdir()
    for name,digest in SOURCES.items():
        data=(HERE/name).read_bytes();require(hashlib.sha256(data).hexdigest()==digest,'source snapshot changed')
        with (WORK/'source'/name).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    record=dict(status='waiting',parent_pid=os.getpid(),started_at=time.time(),command=command,cwd=str(ROOT),environment=env,
        entry_free_bytes=entry,canonical_lock=str(LOCK),wait_seconds=600,maximum_observation_seconds=1800,
        runner_source=str(Path(__file__).resolve()),runner_sha256=sha(__file__),sources_sha256=SOURCES,
        scope_path=str(SCOPE),scope_sha256=SCOPE_SHA,workload_children=0,
        identity_limitation='Exact Popen PID, parent, command, cwd and times recorded; no separate process probes.',
        runner_identity=dict(pid=os.getpid(),parent_pid=os.getppid(),pgid=os.getpgrp(),cwd=os.getcwd(),argv=sys.argv))
    save(record)
    try:
        require(LOCK.resolve(strict=True)==LOCK and stat.S_ISREG(LOCK.lstat().st_mode),'ordinary canonical lock required')
        with LOCK.open('r+') as lock:
            require((os.fstat(lock.fileno()).st_dev,os.fstat(lock.fileno()).st_ino)==(LOCK.stat().st_dev,LOCK.stat().st_ino),'lock route changed')
            deadline=time.monotonic()+600
            while True:
                try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                except BlockingIOError:
                    require(time.monotonic()<deadline,'bounded canonical admission expired');time.sleep(.25)
            free=shutil.disk_usage(ROOT).free;require(free>=16*2**30,'fresh16GiB admission after canonical wait required')
            record.update(status='admitted',admitted_at=time.time(),admission_free_bytes=free);save(record)
            for name,digest in SOURCES.items():require(sha(HERE/name)==digest,'source changed while waiting')
            require(sha(SCOPE)==SCOPE_SHA,'scope changed while waiting')
            with (WORK/'stdout').open('xb') as out,(WORK/'stderr').open('xb') as err:
                child=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                    start_new_session=True,pass_fds=(lock.fileno(),))
                record.update(status='running',pid=child.pid,child_started_at=time.time(),inherited_canonical_fd=lock.fileno())
                try:
                    try:save(record)
                    except BaseException as error:record['initial_child_publication_error']=repr(error)
                    try:child.wait(timeout=1800)
                    except subprocess.TimeoutExpired:record.update(status='unclosed-task-not-signaled',may_be_live=True)
                finally:
                    record.update(returncode=child.returncode,observation_finished_at=time.time(),
                        stdout_sha256=sha(WORK/'stdout'),stderr_sha256=sha(WORK/'stderr'))
                    if child.returncode is not None:record.update(status='finished',finished_at=time.time())
                    else:record.update(status='unclosed-task-not-signaled',may_be_live=True)
                    save(record)
                require(child.returncode is not None,'preparation may remain live; inherited lock retained by child, no signal/retry')
                require(child.returncode==0,'read-only preparation failed; preserve partial proposal')
            for name,digest in SOURCES.items():require(sha(HERE/name)==digest,'approved source changed during preparation')
            require(all(not path.exists() and not path.is_symlink() for path in absent[2:]),'preparation created archive/work/source copies')
        record['released_at']=time.time();save(record)
    except BaseException as error:
        record.update(error=repr(error))
        if 'pid' not in record:record.update(status='not-launched',finished_at=time.time())
        save(record);raise
    require('initial_child_publication_error' not in record,'initial child publication failed; inspect retained evidence')
    print(json.dumps(dict(path=str(WORK/'record.json'),sha256=sha(WORK/'record.json'),pid=record['pid'],returncode=record['returncode'],released_at=record['released_at'])))

if __name__=='__main__':main()
