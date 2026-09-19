#!/opt/homebrew/bin/python3 -B
"""Only this experiment's Cargo child; retain exact received and forwarded maps."""
from pathlib import Path
import hashlib,json,os,sys,time
HERE=Path(__file__).absolute().parent
COMMON_SHA='67ffc35ad943aab6cc8cf2050a337a6129ef55d9df12466eb43795e747732548'  # Bound when all sources are reviewed; no unbound execution.
ATTEMPTS=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-ruff-screen-02/wrapper-attempts')
ATTEMPT=None
ATTEMPT_PATH=None

def save_attempt():
    payload=(json.dumps(ATTEMPT,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    assert len(payload)<=2**20
    temporary=ATTEMPT_PATH.with_suffix('.tmp')
    with temporary.open('xb') as stream:stream.write(payload);stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,ATTEMPT_PATH)

def begin_attempt():
    global ATTEMPT,ATTEMPT_PATH
    assert ATTEMPTS.resolve(strict=True)==ATTEMPTS and ATTEMPTS.is_dir()
    assert len(list(ATTEMPTS.iterdir()))<4096
    key=str(os.getpid())+'-'+str(time.time_ns());ATTEMPT_PATH=ATTEMPTS/(key+'.json')
    assert not os.path.lexists(ATTEMPT_PATH)
    ATTEMPT=dict(id=key,status='entered',wrapper_pid=os.getpid(),wrapper_parent_pid=os.getppid(),started_at=time.time(),
        argv=list(sys.argv),cwd=os.getcwd(),received_environment=dict(os.environ))
    save_attempt()


def main():
    global c
    assert isinstance(COMMON_SHA,str) and hashlib.sha256((HERE/'common.py').read_bytes()).hexdigest()==COMMON_SHA
    sys.path.insert(0,str(HERE));import common as c
    received=dict(os.environ);keys={'ARENA_SCREEN_CONTEXT','ARENA_SCREEN_CONTEXT_SHA','ARENA_SCREEN_LOCK_FD'}
    c.require(keys<=set(received),'explicit wrapper transport')
    context_path=Path(received['ARENA_SCREEN_CONTEXT']);c.require(context_path.parent==c.WORK/'contexts','owned context')
    context=c.read(context_path,received['ARENA_SCREEN_CONTEXT_SHA']);arm=context['arm']
    c.require(arm in ['stock','candidate'] and context['common_sha256']==COMMON_SHA,'bound source/arm')
    c.require(c.file(Path(__file__))['sha256']==context['wrapper_sha256'],'wrapper source changed')
    fd=int(received['ARENA_SCREEN_LOCK_FD']);c.inherited_lock(fd)
    base=c.OUT/'capture'/arm
    count=len(list(base.iterdir()));c.require(count<1024,'finite Cargo rustc calls')
    call=base/ATTEMPT['id'];c.require(not call.exists(),'one fresh wrapper invocation')
    original=list(sys.argv[1:]);c.require(c.option(original,'--sysroot') is None,'Cargo attempted own sysroot')
    c.require(not any(x.startswith(('proc_macro=','rustc_literal_escaper=')) for x in original),'explicit proc-macro client override')
    c.require(not any(x.startswith('incremental=') or x.startswith('-Cincremental=') for x in original),'incremental disabled')
    environment={k:v for k,v in received.items() if k not in keys}
    # Observe advertised pipe descriptors before opening any log could reuse a
    # stale descriptor number. Do not read or manufacture jobserver tokens.
    jobserver=c.jobserver_observation(environment)
    c.require(environment.get('RUSTC')==str(Path(__file__)) and not environment.get('RUSTC_WRAPPER') and not environment.get('RUSTC_WORKSPACE_WRAPPER'),'exact compiler route')
    c.require(not any(k in environment for k in ['RUSTC_BOOTSTRAP','RUSTC_OVERRIDE_VERSION_STRING','RUSTC_OVERRIDE_VERSION_HASH']),'no injected compiler policy')
    c.require(not environment.get('RUSTFLAGS') and not environment.get('CARGO_ENCODED_RUSTFLAGS'),'no injected Rust flags; preserve any observed empty fields')
    compiler=context['compiler'];c.require(c.file(compiler)==context['compiler_row'],'matched N compiler current')
    forwarded=[compiler,*original,'--sysroot',context['sysroot']]
    classification=c.classify_rustc(original,environment,os.getcwd(),c.WORK/'target'/arm,context['probe_sources'])
    unstable=[]
    for i,arg in enumerate(original):
        if arg=='-Z':
            c.require(i+1<len(original),'missing Cargo unstable option value');unstable.append(original[i+1])
        elif arg.startswith('-Z'):unstable.append(arg[2:])
    c.require(unstable in [[],['embed-metadata=no']],'unexpected Cargo unstable flag')
    if unstable:
        c.require(classification['kind']=='cargo-crate' and {'metadata','link'}<=set((c.option(original,'--emit') or '').split(',')),
            'split-metadata flag only for actual Cargo metadata/link crate output')
    is_compile=classification['kind']=='cargo-crate'
    if is_compile:forwarded.append('-Zbinary-dep-depinfo')
    c.require(c.option(forwarded,'--sysroot')==context['sysroot'],'all host and target calls select overlay')
    route=dict(arm=arm,wrapper_pid=os.getpid(),wrapper_parent_pid=os.getppid(),attempt=str(ATTEMPT_PATH),call_directory=str(call),started_at=time.time(),
        original_arguments=original,forwarded_arguments=forwarded,cwd=os.getcwd(),received_environment=received,
        forwarded_environment=environment,transport_removed=sorted(keys),jobserver_transport=jobserver,is_compile=is_compile,classification=classification,context_sha256=received['ARENA_SCREEN_CONTEXT_SHA'])
    # c.run creates the unique call directory before any child and records exact closure.
    stdin_bytes=None
    if '-' in original:
        stdin_bytes=sys.stdin.buffer.read(2**20+1);c.require(len(stdin_bytes)<=2**20,'bounded compiler query/probe stdin')
    record=c.run(forwarded,os.getcwd(),environment,call,fd=fd,seconds=180,cpu=180,inherit_stdin=stdin_bytes is None,stdin_bytes=stdin_bytes,until=context['absolute_deadline_monotonic'])
    if classification['kind']=='proc-macro2-probe':
        c.require(c.file(classification['probe_source'])==classification['source_row'],'probe source changed during compile')
    c.require(record['returncode'] in classification.get('expected_exit_set',[0]),'unexpected actual compiler/probe exit')
    route.update(record=dict(path=str(call/'record.json'),**c.file(call/'record.json')),finished_at=time.time())
    c.write(call/'route.json',route)
    for name,stream in [('stdout',sys.stdout.buffer),('stderr',sys.stderr.buffer)]:
        stream.write((call/name).read_bytes());stream.flush()
    c.require(record['returncode']>=0,'signal-terminated compiler is failed setup')
    return record['returncode']

if __name__=='__main__':
    try:
        begin_attempt();code=main()
        ATTEMPT.update(status='returned-native-exit',returned_code=code,finished_at=time.time());save_attempt()
    except BaseException as error:
        if ATTEMPT is not None:
            ATTEMPT.update(status='wrapper-refused',error=repr(error),finished_at=time.time())
            try:save_attempt()
            except BaseException as publication_error:print('attempt publication failed: '+repr(publication_error),file=sys.stderr)
        print('arena screen wrapper failed: '+repr(error),file=sys.stderr);code=1
    raise SystemExit(code)
