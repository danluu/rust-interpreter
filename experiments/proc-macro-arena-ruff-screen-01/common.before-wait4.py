"""Finite process and file operations for this one Ruff screen."""
from pathlib import Path
import fcntl, hashlib, json, os, resource, shutil, stat, subprocess, threading, time
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
SOURCE=ROOT/'experiments/proc-macro-arena-ruff-screen-01'
WORK=ROOT/'.work/proc-macro-arena-ruff-screen-01'
OUT=ROOT/'results/proc-macro-arena-ruff-screen-01'
LOCK=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')

def require(ok, message):
    if not ok: raise RuntimeError(message)

def stamp(p):
    s=Path(p).lstat();return {n:getattr(s,'st_'+n) for n in FIELDS}

def digest(b):return hashlib.sha256(b).hexdigest()

def file(p):
    p=Path(p);require(p.is_absolute() and p.resolve(strict=True)==p,'ordinary absolute file')
    before=stamp(p);require(stat.S_ISREG(before['mode']) and before['size']<=512*2**20,'bounded ordinary file')
    h=hashlib.sha256();n=0
    with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW),'rb') as f:
        require({k:getattr(os.fstat(f.fileno()),'st_'+k) for k in FIELDS}==before,'opened file identity')
        while b:=f.read(2**20):h.update(b);n+=len(b);require(n<=512*2**20,'file bound')
        require({k:getattr(os.fstat(f.fileno()),'st_'+k) for k in FIELDS}==before,'file changed during EOF read')
    require(stamp(p)==before and n==before['size'],'file replaced')
    return dict(bytes=n,sha256=h.hexdigest(),identity=before)

def read(p,sha=None):
    r=file(p);require(r['bytes']<=8*2**20 and (sha is None or r['sha256']==sha),'bounded authenticated JSON')
    d=json.loads(Path(p).read_bytes());require(file(p)==r,'JSON changed');return d

def write(p,d):
    p=Path(p);b=(json.dumps(d,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();require(len(b)<=8*2**20,'record bound')
    t=p.with_name(p.name+'.tmp')
    with t.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
    os.replace(t,p);require(p.read_bytes()==b,'record readback')

def disk(entry=False):
    n=shutil.disk_usage(ROOT).free;require(n>=(16 if entry else 9)*2**30,'screen disk gate');return n

def budget():
    n=0;total=0
    for base in [WORK,OUT]:
        for root,dirs,files in os.walk(base,followlinks=False):
            for name in dirs+files:
                p=Path(root)/name;s=p.lstat();n+=1;require(n<=70000,'owned membership bound')
                require(stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode) or stat.S_ISLNK(s.st_mode),'ordinary owned output kind')
                if not stat.S_ISDIR(s.st_mode):total+=s.st_size
    require(total<=4*2**30,'owned screen bytes exceed4GiB');return dict(entries=n,bytes=total)

def inherited_lock(fd):
    require(type(fd) is int and fd>2,'inherited canonical fd required')
    named=LOCK.stat();held=os.fstat(fd)
    require((named.st_dev,named.st_ino,named.st_nlink)==(held.st_dev,held.st_ino,1),'canonical descriptor identity')
    with LOCK.open('r+') as other:
        try:fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:pass
        else:raise RuntimeError('canonical lock was not already held')
    fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)

def limits(cpu):
    resource.setrlimit(resource.RLIMIT_CPU,(cpu,cpu));resource.setrlimit(resource.RLIMIT_FSIZE,(512*2**20,512*2**20));resource.setrlimit(resource.RLIMIT_CORE,(0,0))

def run(argv,cwd,env,directory,*,fd,seconds,cpu,inherit_stdin=False):
    """Bounded wait continues after observation errors; no process is signalled."""
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False);inherited_lock(fd);disk()
    record=dict(status='starting',command=list(argv),cwd=str(cwd),environment=dict(env),parent_pid=os.getpid(),parent_parent_pid=os.getppid(),started_at=time.time(),may_be_live=False,observation_errors=[])
    write(directory/'record.json',record);before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.monotonic()
    with (directory/'stdout').open('xb') as stdout,(directory/'stderr').open('xb') as stderr:
        try:
            child=subprocess.Popen(argv,cwd=cwd,env=env,stdin=None if inherit_stdin else subprocess.DEVNULL,stdout=stdout,stderr=stderr,close_fds=False,preexec_fn=lambda:limits(cpu))
        except BaseException as error:
            record.update(status='spawn-failed',error=repr(error),observation_finished_at=time.time(),may_be_live=False)
            write(directory/'record.json',record);raise
        deadline=time.monotonic()+seconds;record.update(pid=child.pid,spawned_at=time.time(),status='running',may_be_live=True)
        def observed_write():
            try:write(directory/'record.json',record)
            except BaseException as error:
                if len(record['observation_errors'])<16:record['observation_errors'].append(repr(error))
        try:
            observed_write()
            while time.monotonic()<deadline:
                try:child.wait(timeout=min(1,max(.001,deadline-time.monotonic())));break
                except subprocess.TimeoutExpired:
                    try:disk()
                    except BaseException as error:
                        if len(record['observation_errors'])<16:record['observation_errors'].append(repr(error))
                    observed_write()
                except BaseException as error:
                    if len(record['observation_errors'])<16:record['observation_errors'].append(repr(error))
                    time.sleep(min(.1,max(0,deadline-time.monotonic())))
        finally:
            end=time.monotonic();after=resource.getrusage(resource.RUSAGE_CHILDREN)
            record.update(returncode=child.returncode,observation_finished_at=time.time(),elapsed_seconds=end-start,
                cpu_user_seconds=after.ru_utime-before.ru_utime,cpu_system_seconds=after.ru_stime-before.ru_stime,
                observer_children_maxrss=after.ru_maxrss,maxrss_is_cumulative_observer_highwater=True,
                status='closed' if child.returncode is not None else 'unclosed-not-signalled',may_be_live=child.returncode is None)
            if child.returncode is not None:record['finished_at']=time.time()
            observed_write()
    require(child.returncode is not None,'child may remain live; no restoration/retry/further call')
    for name in ['stdout','stderr']:
        record[name]=file(directory/name);require(record[name]['bytes']<=8*2**20,'raw stream bound')
    write(directory/'record.json',record);require(not record['observation_errors'],'observation failed after bounded wait')
    return record

def exact_table(rows,full):
    for name,row in rows.items():
        require(stamp(name)==row['identity'],'recorded input identity changed')
        if full:require(file(name)==row,'recorded input bytes changed')

def overlay_guard(invocation,full=False):
    prior=invocation['overlay_data'];runtime=prior['runtime-after.json'];overlays=prior['overlays-after.json']
    runtime_root=Path(invocation['runtime_root']);overlay_work=Path(invocation['overlay_work'])
    for relative,row in runtime['entries'].items():
        p=runtime_root/relative;require(stamp(p)==row['identity'],'N member changed')
        if row['kind']=='file' and full:require(file(p)=={k:row[k] for k in ['bytes','sha256','identity']},'N bytes changed')
        if row['kind']=='link':require(os.readlink(p)==row['target'] and str(p.resolve(strict=True))==row['resolved'],'N source link changed')
    for name,row in overlays['entries'].items():
        p=Path(name);require(p.is_relative_to(overlay_work) and stamp(p)==row['identity'],'overlay member changed')
        if row['kind']=='file' and full:require(file(p)=={k:row[k] for k in ['bytes','sha256','identity']},'owned client changed')
        if row['kind']=='link':require(os.readlink(p)==row['target'] and str(p.resolve(strict=True))==row['resolved'],'overlay alias changed')
    for name,row in overlays['directories'].items():require(stamp(name)==row,'overlay directory membership changed')
    for relative,row in runtime['directories'].items():require(stamp(runtime_root/relative)==row,'N directory membership changed')

def option(args,name):
    values=[]
    for i,arg in enumerate(args):
        if arg==name:require(i+1<len(args),'missing option value');values.append(args[i+1])
        elif arg.startswith(name+'='):values.append(arg.split('=',1)[1])
    require(len(values)<=1,'duplicate '+name);return values[0] if values else None

def change_option(args,name,value):
    require(option(args,name) is not None,'expected replay option '+name)
    result=[];i=0
    while i<len(args):
        arg=args[i]
        if arg==name:result.extend([name,value]);i+=2
        elif arg.startswith(name+'='):result.append(name+'='+value);i+=1
        else:result.append(arg);i+=1
    return result
