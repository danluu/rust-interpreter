#!/usr/bin/env python3
import argparse, fcntl, hashlib, json, os, pathlib, resource, shutil, signal, subprocess, time

parser = argparse.ArgumentParser()
parser.add_argument('--source', default='/Users/danluu/dev/rustc-stable-cgu-20260913')
parser.add_argument('--receipt', required=True)
parser.add_argument('--projected-gib', type=float, required=True)
parser.add_argument('--artifact-dir', action='append', default=[])
parser.add_argument('--lock-wait-seconds', type=int, default=45)
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
assert 0 < args.lock_wait_seconds <= 600
source = pathlib.Path(args.source).resolve()
out = pathlib.Path(args.receipt).resolve()
out.mkdir(parents=True, exist_ok=False)
command = args.command[1:] if args.command[:1] == ['--'] else args.command
assert command and command[0] == './x'
lock_path = pathlib.Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
start = time.time()
admission = {'supervisor_pid': os.getpid(), 'started_at': start, 'source': str(source),
             'command': command, 'lock_path': str(lock_path), 'status': 'waiting',
             'lock_wait_limit_seconds': args.lock_wait_seconds,
             'runner_sha256': hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
def save_admission():
    (out/'admission.json').write_text(json.dumps(admission, indent=2)+'\n')
save_admission()
lock = lock_path.open('a+')
def admission_timeout(signum, frame):
    raise TimeoutError('shared resource admission deadline')
previous_alarm = signal.signal(signal.SIGALRM, admission_timeout)
signal.alarm(args.lock_wait_seconds)
print('Owned supervisor', os.getpid(), 'waiting up to', args.lock_wait_seconds,
      'seconds for the shared setup slot', flush=True)
try:
    fcntl.flock(lock, fcntl.LOCK_EX)
except TimeoutError:
    admission.update(status='lock admission timed out; no build started', finished_at=time.time())
    save_admission()
    raise SystemExit('shared resource lock unavailable; no build started')
finally:
    signal.alarm(0)
    signal.signal(signal.SIGALRM, previous_alarm)
free = shutil.disk_usage(source).free
admission.update(status='lock acquired', lock_acquired_at=time.time(), free_bytes=free,
                 projected_gib=args.projected_gib)
save_admission()
if free < (8 + args.projected_gib) * 2**30:
    admission.update(status='disk admission rejected; no build started', finished_at=time.time())
    save_admission()
assert free >= (8 + args.projected_gib) * 2**30, (free, args.projected_gib)
env = os.environ.copy()
removed = {}
for key in ['RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTDOCFLAGS', 'CARGO_ENCODED_RUSTDOCFLAGS', 'CARGO_TARGET_DIR', 'RUSTC_BOOTSTRAP', 'CARGO_PROFILE_DEV_DEBUG', 'CARGO_PROFILE_TEST_DEBUG', 'CARGO_PROFILE_RELEASE_DEBUG']:
    if key in env:
        removed[key] = 'removed'
        del env[key]
env.update(CARGO_BUILD_JOBS='2', CARGO_INCREMENTAL='0', RUST_TEST_THREADS='2')
tracked = subprocess.check_output(['git','ls-files','-z'],cwd=source).decode().split('\0')
hashes = {name: hashlib.sha256((source/name).read_bytes()).hexdigest() for name in tracked if name and (source/name).is_file()}
shutil.copy2(source/'bootstrap.toml', out/'bootstrap.toml')
r = {'schema_version':1,'supervisor_pid':os.getpid(),'source':str(source),'command':command,'started_at':start,'lock_path':str(lock_path),'lock_wait_seconds':time.time()-start,'projected_gib':args.projected_gib,'minimum_free_gib':8,'free_bytes_before':free,'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip(),'source_diff_sha256':hashlib.sha256(subprocess.check_output(['git','diff','HEAD','--'],cwd=source)).hexdigest(),'source_file_hashes':hashes,'config_sha256':hashlib.sha256((source/'bootstrap.toml').read_bytes()).hexdigest(),'environment_removed':removed,'environment':{k:env[k] for k in ['PATH','CARGO_HOME','CARGO_BUILD_JOBS','CARGO_INCREMENTAL','RUST_TEST_THREADS','CC','CXX','SDKROOT','DEVELOPER_DIR','MACOSX_DEPLOYMENT_TARGET'] if k in env},'disk_samples':[]}
def save():
    (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
save()
with (out/'command.log').open('w') as log:
    child = subprocess.Popen(command,cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        admission.update(status='build running', child_pid=child.pid)
        save_admission()
        r['pid']=child.pid
        r['child_start_time']=subprocess.check_output(['ps','-p',str(child.pid),'-o','lstart='],text=True).strip()
        r['process_identity']=subprocess.check_output(['ps','-p',str(child.pid),'-o','pid,ppid,pgid,lstart,command'],text=True).strip()
        save()
        print('Owned supervisor',os.getpid(),'child',child.pid,'command',command,flush=True)
        while child.poll() is None:
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                sample={'time':time.time(),'free_bytes':shutil.disk_usage(source).free}
                r['disk_samples'].append(sample)
                save()
                print('Owned build active; elapsed',round(time.time()-start),'seconds; free',round(sample['free_bytes']/2**30,2),'GiB',flush=True)
                if sample['free_bytes'] < 10*2**30:
                    print('CAPACITY ALERT: remaining free space below10GiB',flush=True)
                if sample['free_bytes'] < 9*2**30 and child.poll() is None:
                    current_start=subprocess.check_output(['ps','-p',str(child.pid),'-o','lstart='],text=True).strip()
                    assert current_start == r['child_start_time'] and os.getpgid(child.pid) == child.pid
                    group=[]
                    table=subprocess.check_output(['ps','-axo','pid=,ppid=,pgid='],text=True)
                    for line in table.splitlines():
                        pid,ppid,pgid=map(int,line.split())
                        if pgid == child.pid:
                            identity=subprocess.check_output(['ps','-p',str(pid),'-o','pid,ppid,pgid,lstart,tty,command'],text=True).strip()
                            cwd=subprocess.run(['lsof','-a','-p',str(pid),'-d','cwd','-Fn'],capture_output=True,text=True).stdout
                            group.append({'pid':pid,'ppid':ppid,'identity':identity,'cwd':cwd})
                    owned={entry['pid'] for entry in group}
                    assert child.pid in owned and all(entry['pid']==child.pid or entry['ppid'] in owned for entry in group)
                    r['capacity_stop']={'time':time.time(),'reason':'free disk below9GiB, preserving8GiB floor','revalidated_owned_group':group}
                    save()
                    os.killpg(child.pid,signal.SIGINT)
                    child.wait()
    finally:
        if child.poll() is None:
            child.wait()

r['returncode']=child.returncode
r['finished_at']=time.time()
admission.update(status='build finished', returncode=child.returncode, finished_at=r['finished_at'])
save_admission()
r['free_bytes_after']=shutil.disk_usage(source).free
r['log_sha256']=hashlib.sha256((out/'command.log').read_bytes()).hexdigest()
r['children_rusage']=list(resource.getrusage(resource.RUSAGE_CHILDREN))
if child.returncode == 0:
    r['artifact_inventories'] = {}
    r['artifact_capture_started_at'] = time.time()
    for name in args.artifact_dir:
        root = pathlib.Path(name).resolve()
        assert root.is_relative_to(source/'build') and root.is_dir()
        r['artifact_inventories'][str(root)] = {
            str(path.relative_to(root)): {'size': path.stat().st_size,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in sorted(root.rglob('*')) if path.is_file()}
    r['artifact_capture_finished_at'] = time.time()
save()
print((out/'command.log').read_text(errors='replace')[-6000:],flush=True)
raise SystemExit(child.returncode)
