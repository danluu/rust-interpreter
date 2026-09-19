"""Finite process and file operations for this one Ruff screen."""
from pathlib import Path
import fcntl, hashlib, json, os, re, resource, shutil, stat, subprocess, threading, time
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
SOURCE=ROOT/'experiments/proc-macro-arena-ruff-screen-03'
WORK=ROOT/'.work/proc-macro-arena-ruff-screen-03'
OUT=ROOT/'results/proc-macro-arena-ruff-screen-03'
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

def jobserver_pair(environment):
    pairs=set();present={}
    for name in ['CARGO_MAKEFLAGS','MAKEFLAGS','MFLAGS']:
        if name not in environment:continue
        value=environment[name];matches=list(re.finditer(r'--jobserver-(auth|fds)=([0-9]+),([0-9]+)',value))
        kinds=[m.group(1) for m in matches]
        require(len(matches)<=2 and len(kinds)==len(set(kinds)) and value.count('--jobserver-')==len(matches),'unrecognized jobserver flags')
        if matches:present[name]=value;pairs.update((int(m.group(2)),int(m.group(3))) for m in matches)
    require(len(pairs)<=1,'jobserver variables advertise inconsistent descriptors')
    return next(iter(pairs)) if pairs else None,present

def jobserver_observation(environment):
    pair,present=jobserver_pair(environment);observed={}
    if pair is not None:
        require(pair[0]>2 and pair[1]>2 and pair[0]!=pair[1],'distinct jobserver pipe endpoints')
        for fd,mode in zip(pair,[os.O_RDONLY,os.O_WRONLY]):
            s=os.fstat(fd);flags=fcntl.fcntl(fd,fcntl.F_GETFL)
            require(stat.S_ISFIFO(s.st_mode) and os.get_inheritable(fd) and flags&os.O_ACCMODE==mode,'live inheritable jobserver pipe endpoint')
            observed[str(fd)]=dict(identity={k:getattr(s,'st_'+k) for k in FIELDS},flags=flags,inheritable=True)
    return dict(advertised=present,pair=pair,observed_endpoints=observed)

def run(argv,cwd,env,directory,*,fd,seconds,cpu,inherit_stdin=False,stdin_bytes=None,until=None):
    """Blocking wait4 timestamps completion; bounded parent observation never signals."""
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False);inherited_lock(fd);disk();budget()
    require(os.get_inheritable(fd),'canonical FD must survive every actual exec')
    require(until is None or time.monotonic()<until,'overall observation deadline passed before spawn')
    record=dict(status='starting',command=list(argv),cwd=str(cwd),environment=dict(env),parent_pid=os.getpid(),parent_parent_pid=os.getppid(),observer_started_at=time.time(),may_be_live=False,observation_errors=[])
    source_input=None
    if stdin_bytes is not None:
        require(not inherit_stdin and type(stdin_bytes) is bytes and len(stdin_bytes)<=2**20,'finite explicitly captured stdin')
        with (directory/'stdin').open('xb') as f:f.write(stdin_bytes)
        record['stdin']=file(directory/'stdin');source_input=(directory/'stdin').open('rb')
    write(directory/'record.json',record)
    with (directory/'stdout').open('xb') as stdout,(directory/'stderr').open('xb') as stderr:
        start=time.monotonic();record['started_at']=time.time()
        try:
            child=subprocess.Popen(argv,cwd=cwd,env=env,stdin=source_input if source_input is not None else (None if inherit_stdin else subprocess.DEVNULL),stdout=stdout,stderr=stderr,close_fds=False,preexec_fn=lambda:limits(cpu))
        except BaseException as error:
            record.update(status='spawn-failed',error=repr(error),observation_finished_at=time.time(),may_be_live=False)
            write(directory/'record.json',record);raise
        finally:
            if source_input is not None:source_input.close()
        deadline=time.monotonic()+seconds
        if until is not None:deadline=min(deadline,until)
        record.update(pid=child.pid,spawned_at=time.time(),status='running',may_be_live=True,observation_deadline_monotonic=deadline)
        completed=threading.Event();waited={}
        def wait_owned_child():
            try:
                while True:
                    try:pid,status,usage=os.wait4(child.pid,0);break
                    except InterruptedError:continue
                end=time.monotonic();finished=time.time()
                require(pid==child.pid,'wait4 returned different owned child')
                waited.update(pid=pid,wait_status=status,returncode=os.waitstatus_to_exitcode(status),
                    finished_at=finished,elapsed_seconds=end-start,
                    cpu_user_seconds=usage.ru_utime,cpu_system_seconds=usage.ru_stime,
                    child_maxrss=usage.ru_maxrss,rusage_source='actual os.wait4 return for this child')
                child.returncode=waited['returncode']
            except BaseException as error:waited['wait_error']=repr(error)
            finally:completed.set()
        # Daemon waiter may remain blocked after the observation deadline. This
        # does not grant permission to signal the child or continue the screen.
        waiter=threading.Thread(target=wait_owned_child,daemon=True);waiter.start()
        def observed_write():
            try:write(directory/'record.json',record)
            except BaseException as error:
                if len(record['observation_errors'])<16:record['observation_errors'].append(repr(error))
        try:
            observed_write()
            while not completed.wait(timeout=min(.25,max(0,deadline-time.monotonic()))):
                if time.monotonic()>=deadline:break
                try:disk()
                except BaseException as error:
                    if len(record['observation_errors'])<16:record['observation_errors'].append(repr(error))
                observed_write()
        finally:
            if completed.is_set():
                waiter.join();record.update(waited)
            closed=completed.is_set() and 'returncode' in waited
            record.update(observation_finished_at=time.time(),status='closed' if closed else 'unclosed-not-signalled',may_be_live=not closed)
            observed_write()
    require(record['status']=='closed','child may remain live; no restoration/retry/further call')
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

def crate_types(args):
    values=[]
    for i,arg in enumerate(args):
        if arg=='--crate-type':
            require(i+1<len(args),'missing crate type');values.extend(args[i+1].split(','))
        elif arg.startswith('--crate-type='):values.extend(arg.split('=',1)[1].split(','))
    require(len(values)==len(set(values)) and set(values)<={'bin','lib','rlib','dylib','cdylib','staticlib','proc-macro'},'distinct actual crate types')
    return values


def cargo_depinfo_path(args,cwd):
    crate=option(args,'--crate-name');output=option(args,'--out-dir');extra=[]
    for i,arg in enumerate(args):
        if arg=='-C' and i+1<len(args) and args[i+1].startswith('extra-filename='):extra.append(args[i+1].split('=',1)[1])
        elif arg.startswith('-Cextra-filename='):extra.append(arg.split('=',1)[1])
    require(crate is not None and output is not None and len(extra)<=1,'captured Cargo dependency output key')
    if not extra:
        require(crate=='build_script_build' and crate_types(args)==['bin'] and option(args,'--emit')=='dep-info,link','only normal build-script binary omits suffix')
    return Path(output)/(crate+(extra[0] if extra else '')+'.d')


def classify_rustc(args,environment,cwd,target,probe_sources):
    """Only actual Cargo crates, version/print queries, or five source-read probe families."""
    if args in [['-vV'],['-V'],['--version'],['--version','--verbose'],['--verbose','--version']]:
        return dict(kind='query',query='version')
    if any(a=='--print' or a.startswith('--print=') for a in args):
        require(not any(a.endswith('.rs') for a in args),'print query cannot hide a Rust source compile')
        return dict(kind='query',query='print')
    crate=option(args,'--crate-name');output=option(args,'--out-dir')
    out=environment.get('OUT_DIR');base=Path(out) if out else None
    if crate is not None and re.fullmatch(r'autocfg_[0-9a-f]{16}_[0-9]+',crate):
        require(base is not None and base.is_relative_to(target) and Path(output).is_relative_to(base),'autocfg owns only its build output')
        expected=['--crate-name',crate,'--crate-type=lib','--out-dir',output,'--emit=llvm-ir']
        edition=option(args,'--edition')
        if edition is not None:require(edition in ['2015','2018','2021','2024'],'known probe edition');expected+=['--edition',edition]
        triple=option(args,'--target')
        if triple is not None:require(triple=='aarch64-apple-darwin','native probe target');expected+=['--target',triple]
        require(args==expected+['-'],'exact autocfg source-derived command')
        return dict(kind='autocfg-probe',probe_source='captured stdin',expected_exit_set=[0,1])
    if '--cfg=procmacro2_build_probe' in args:
        require(base is not None and base.is_relative_to(target) and output==str(base/'probe'),'proc-macro2 owned probe output')
        sources=[a for a in args if a.endswith('.rs')];require(len(sources)==1,'one proc-macro2 source probe')
        source=str((Path(cwd)/sources[0]).resolve(strict=True));require(source in probe_sources,'exact pinned proc-macro2 source')
        require(file(source)['sha256']==probe_sources[source]['sha256'],'proc-macro2 probe source current bytes')
        expected=['--cfg=procmacro2_build_probe','--edition=2021','--crate-name=proc_macro2','--crate-type=lib','--cap-lints=allow','--emit=dep-info,metadata','--out-dir',output,sources[0]]
        triple=option(args,'--target')
        if triple is not None:require(triple=='aarch64-apple-darwin','native probe target');expected+=['--target',triple]
        require(args==expected,'exact proc-macro2 source-derived command')
        return dict(kind='proc-macro2-probe',probe_source=source,source_row=file(source),expected_exit_set=[0,1])
    if crate in ['thiserror','anyhow'] and not any(a.startswith(('metadata=','-Cmetadata=')) for a in args):
        relative='build/probe.rs' if crate=='thiserror' else 'src/nightly.rs'
        source=str((Path(cwd)/relative).resolve(strict=True))
        require(source in probe_sources and file(source)['sha256']==probe_sources[source]['sha256'],'exact pinned capability probe source')
        require(environment.get('CARGO_PKG_NAME')==crate and environment.get('CARGO_MANIFEST_DIR')==str(Path(cwd)),'actual probe package ownership')
        require(base is not None and base.is_relative_to(target) and output==str(base/'probe'),'capability probe owns only declared output')
        expected=(['--cfg=anyhow_build_probe'] if crate=='anyhow' else [])+['--edition=2018','--crate-name='+crate,'--crate-type=lib','--cap-lints=allow','--emit=dep-info,metadata','--out-dir',output,relative]
        triple=option(args,'--target')
        if triple is not None:require(triple=='aarch64-apple-darwin','native probe target');expected+=['--target',triple]
        require(args==expected,'exact upstream capability command; no injected flags')
        return dict(kind=crate+'-probe',probe_source=source,source_row=file(source),expected_exit_set=[0,1])
    if environment.get('CARGO_PKG_NAME')=='rustix' and args and args[-1]=='-':
        source=str((Path(cwd)/'build.rs').resolve(strict=True))
        require(source in probe_sources and file(source)['sha256']==probe_sources[source]['sha256'],'pinned rustix stdin generator/call-site')
        require(environment.get('CARGO_MANIFEST_DIR')==str(Path(cwd)) and base is not None and base.is_relative_to(target),'rustix package/output ownership')
        expected=['--crate-type=rlib','--emit=metadata','--target','aarch64-apple-darwin','-o',str(base/'rustix_test_can_compile'),'-']
        require(args==expected,'exact source-derived rustix stdin probe')
        return dict(kind='rustix-probe',probe_source='captured stdin',callsite_source=dict(path=source,**file(source)),expected_exit_set=[0,1])
    extra=[a for a in args if a.startswith('extra-filename=') or a.startswith('-Cextra-filename=')]
    metadata=[a for a in args if a.startswith('metadata=') or a.startswith('-Cmetadata=')]
    require(crate is not None and output is not None and Path(output).is_relative_to(target) and len(metadata)==1 and len(extra)<=1,'actual Cargo crate metadata/output shape')
    require(len([a for a in args if a.endswith('.rs')])==1 and 'dep-info' in (option(args,'--emit') or '').split(','),'actual Cargo crate source and dep-info')
    if not extra:
        require(crate=='build_script_build' and crate_types(args)==['bin'] and option(args,'--emit')=='dep-info,link' and environment.get('CARGO_CRATE_NAME')==crate,'normal Cargo build-script binary without filename suffix')
        source=next(a for a in args if a.endswith('.rs'));manifest_dir=Path(environment['CARGO_MANIFEST_DIR'])
        require((Path(cwd)/source).resolve(strict=True).is_relative_to(manifest_dir.resolve(strict=True)),'build-script source belongs to actual package')
    crate_types(args);cargo_depinfo_path(args,cwd)
    return dict(kind='cargo-crate',expected_exit_set=[0])
