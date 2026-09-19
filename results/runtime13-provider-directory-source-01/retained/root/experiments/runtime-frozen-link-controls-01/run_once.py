"""One bounded real-filesystem unittest child; no compiler-size admission."""
from pathlib import Path
import hashlib
import json
import os
import re
import resource
import shutil
import stat
import subprocess
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
HERE = ROOT/'experiments/runtime-frozen-link-controls-01'
SOURCE = ROOT/'experiments/runtime-frozen-link-reader-01'
OUT = ROOT/'results/runtime-frozen-link-controls-01'
PYTHON = '/opt/homebrew/bin/python3'
PLAN_SHA = '09426eaa20e39a4ab596242351cc4af3b37c7d8906653632a5a9b5d9c8c81d20'  # Bound only after the final exact source plan exists.
FIELDS = ('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')


def require(value,message):
    if not value:
        raise RuntimeError(message)


def identity(info):
    return {key:getattr(info,'st_'+key) for key in FIELDS}


def file(path):
    path = Path(path); before = identity(path.lstat())
    require(path.resolve(strict=True)==path and stat.S_ISREG(before['mode']) and before['size']<=64*2**20,
            'bounded ordinary exact file required')
    digest=hashlib.sha256();size=0
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(descriptor,'rb') as stream:
        require(identity(os.fstat(stream.fileno()))==before,'opened file changed')
        while block:=stream.read(2**20):
            digest.update(block);size+=len(block);require(size<=64*2**20,'bounded read')
        require(identity(os.fstat(stream.fileno()))==before,'file changed during read')
    require(identity(path.lstat())==before and size==before['size'],'named file changed')
    return dict(bytes=size,sha256=digest.hexdigest(),identity=before)


def write(name,value,replace=False):
    data=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    require(len(data)<=256*1024,'bounded control record')
    destination=OUT/name;temporary=destination.with_name(destination.name+'.tmp') if replace else destination
    with temporary.open('xb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    if replace:os.replace(temporary,destination)
    require(destination.read_bytes()==data,'control record readback differs')


def owned_size():
    count=0;total=0
    for root,dirs,files in os.walk(OUT,followlinks=False):
        for name in dirs+files:
            p=Path(root)/name
            try:s=p.lstat()
            except FileNotFoundError:continue  # Owned fixtures may remove entries during observation.
            count+=1
            require(count<=512,'bounded control output membership')
            if stat.S_ISREG(s.st_mode):total+=s.st_size
            else:require(stat.S_ISDIR(s.st_mode) or stat.S_ISLNK(s.st_mode),'ordinary owned fixture entry')
    require(total<=8*2**20,'control namespace exceeded8MiB')
    return total


def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_FSIZE,(256*1024,256*1024))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def main():
    require(Path(__file__)==HERE/'run_once.py' and Path.cwd()==ROOT,'exact runner and cwd')
    require(type(PLAN_SHA) is str and re.fullmatch('[0-9a-f]{64}',PLAN_SHA),'plan must be bound')
    require(not os.path.lexists(OUT),'fresh control result namespace required')
    require(shutil.disk_usage(ROOT).free>=256*2**20,'small256MiB free-space admission')
    require(file(HERE/'plan.json')['sha256']==PLAN_SHA,'exact control plan')
    plan=json.loads((HERE/'plan.json').read_bytes())
    require(plan['tests']==24 and len(plan['test_names'])==24 and plan['actual_result'] is None,'exact24 unrun plan')
    python=Path(PYTHON).resolve(strict=True)
    require(str(python)==plan['python_resolved'],'exact declared interpreter route')
    paths=set(plan['sources'])|{str(HERE/'plan.json'),str(Path(__file__)),str(python)}
    before={name:file(name) for name in sorted(paths)}
    for name,row in plan['sources'].items():
        require(before[name]==row,'exact helper/test/child source before launch')
    OUT.mkdir();(OUT/'tmp').mkdir()
    for name in ['run_once.py','child.py','plan.json']:
        shutil.copyfile(HERE/name,OUT/name)
    write('source-before.json',before)
    command=[PYTHON,'-B',str(HERE/'child.py')]
    environment=dict(PATH='/usr/bin:/bin:/opt/homebrew/bin',LANG='C',LC_ALL='C',TMPDIR=str(OUT/'tmp'),
        PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHONHASHSEED='0')
    record=dict(status='starting',command=command,cwd=str(SOURCE),environment=environment,
        parent_pid=os.getpid(),parent_parent_pid=os.getppid(),started_at=time.time(),plan_sha256=PLAN_SHA,
        cpu_seconds=30,observer_seconds=60,file_bytes=256*1024,namespace_bytes=8*2**20,
        canonical_lock_access=False,compiler_calls=0,retries=0,signals=[],may_be_live=False,observation_errors=[],samples=[])
    write('started.json',record);child=None
    try:
        with (OUT/'stdout').open('xb') as stdout,(OUT/'stderr').open('xb') as stderr:
            child=subprocess.Popen(command,cwd=SOURCE,env=environment,stdin=subprocess.DEVNULL,
                stdout=stdout,stderr=stderr,preexec_fn=limits)
            record.update(pid=child.pid,spawned_at=time.time(),status='running',may_be_live=True)
            try:write('started.json',record,replace=True)
            except BaseException as error:record['observation_errors'].append(repr(error))
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                try:
                    child.wait(timeout=min(1,max(.001,deadline-time.monotonic())));break
                except subprocess.TimeoutExpired:
                    try:
                        free=shutil.disk_usage(ROOT).free;require(free>=128*2**20,'small control floor128MiB')
                        record['samples'].append(dict(time=time.time(),free_bytes=free,owned_bytes=owned_size()))
                    except BaseException as error:
                        if len(record['observation_errors'])<16:record['observation_errors'].append(repr(error))
                except BaseException as error:
                    if len(record['observation_errors'])<16:record['observation_errors'].append(repr(error))
                    time.sleep(min(.1,max(0,deadline-time.monotonic())))
    finally:
        code=None if child is None else child.returncode
        record.update(returncode=code,status='not-spawned' if child is None else 'closed' if code is not None else 'unclosed-not-signalled',
            may_be_live=child is not None and code is None,observation_finished_at=time.time())
        if code is not None:record['finished_at']=time.time()
        for name in ['stdout','stderr']:
            if (OUT/name).exists():
                try:record[name]=file(OUT/name)
                except BaseException as error:record['observation_errors'].append(repr(error))
        write('record.json',record)
    require(not record['may_be_live'],'child remains live; no signal/retry or further controls')
    after={name:file(name) for name in before};write('source-after.json',after)
    require(Path(PYTHON).resolve(strict=True)==python,'interpreter route changed')
    raw=(OUT/'stdout').read_text();stderr=(OUT/'stderr').read_bytes()
    footer=[line for line in raw.splitlines() if line.startswith('FROZEN_LINK_CONTROL_RESULT ')]
    proof=json.loads(footer[0].split(' ',1)[1]) if len(footer)==1 else None
    names=plan['test_names'];raw_tests=[line for line in raw.splitlines() if line.startswith('test_')]
    exact_lines=[name.rsplit('.',1)[1]+' ('+name+') ... ok' for name in names]
    passed=(record['status']=='closed' and record['returncode']==0 and not record['observation_errors']
        and before==after and stderr==b'' and raw_tests==exact_lines and proof is not None
        and proof['status']=='passed' and proof['tests']==24 and proof['test_names']==names
        and proof['child_pid']==record['pid'] and proof['parent_pid']==record['parent_pid']
        and proof['cwd']==str(SOURCE) and proof['test_sources']==plan['test_sources']
        and proof['skipped']==proof['failures']==proof['errors']==0
        and proof['io_policy']['denied_events']==[] and proof['io_policy']['temporary_members_after']==[]
        and not list((OUT/'tmp').iterdir()))
    result=dict(status='verified-frozen-link-controls' if passed else 'failed',tests=24 if passed else None,
        test_names=names,source_unchanged=before==after,sources=before,child_proof=proof,
        record=dict(path=str(OUT/'record.json'),sha256=file(OUT/'record.json')['sha256']),
        source_before=dict(path=str(OUT/'source-before.json'),sha256=file(OUT/'source-before.json')['sha256']),
        source_after=dict(path=str(OUT/'source-after.json'),sha256=file(OUT/'source-after.json')['sha256']),
        stdout=dict(path=str(OUT/'stdout'),sha256=file(OUT/'stdout')['sha256']),
        stderr=dict(path=str(OUT/'stderr'),sha256=file(OUT/'stderr')['sha256']),
        plan=dict(path=str(HERE/'plan.json'),sha256=PLAN_SHA),owned_bytes=owned_size(),
        compiler_calls=0,provider_writes=False,network=False,canonical_lock_access=False,
        scope='real temporary-filesystem frozen-link helper controls only',runtime_audit_qualified=False)
    write('result.json',result)
    write('manifest.json',{p.name:file(p) for p in sorted(OUT.iterdir()) if p.is_file()})
    print(json.dumps(dict(status=result['status'],result_sha256=file(OUT/'result.json')['sha256'])))
    require(passed,'actual frozen-link controls failed; retain this namespace')


if __name__=='__main__':
    main()
