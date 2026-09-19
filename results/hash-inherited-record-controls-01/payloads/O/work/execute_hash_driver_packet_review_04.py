"""One bounded read-only packet audit; explicit wait, no signals or workloads."""
import hashlib, importlib.util, json, os, shutil, subprocess, sys, time
from pathlib import Path
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
P=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
AUDITOR=O/'.work/verify_hash_driver_packet_04.py'
E=O/'.work/hash-driver-packet-review-execution-04'
RESULT=O/'.work/hash-driver-packet-verification-04.json'
H=R/'experiments/hir-options-hash-driver-stage-02'
OWNED=X/'experiments/stable-cgu/owned_stage.py'
EXPECTED={AUDITOR:'120d344ed17291327c8b0efa32ac853cb5b9a1ca7c0a7731bf0f725120ca1698',
 H/'verify.py':'cbff690675b8697855bb87b0e09d9b77495fc0b8968855301e1a88612ec62a3f',
 OWNED:'7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e',
 H/'launch.json':'e315c703101fb5d8e9f732a10db9b07883792057c0f833b71979cf54efcbfc43',
 H/'inputs.json':'5accd23a86a3d7df8d19e8e294fcc96a4bc4f707ecd590b999c88ae092ed6dae'}
def require(ok,message):
 if not ok:raise RuntimeError(message)
def sha(path):
 path=Path(path);before=path.stat();require(path.resolve(strict=True)==path and path.is_file() and before.st_size<=64*2**20,'bounded ordinary wrapper input')
 with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
 after=path.stat();require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'wrapper input changed')
 return digest
def sources():
 for path,digest in EXPECTED.items():require(sha(path)==digest,'reviewed exact wrapper input: '+str(path))
require(Path.cwd()==O and sys.dont_write_bytecode and not sys.flags.optimize and Path(sys.executable).resolve()==P,'fixed Python/owner')
require(not E.exists() and not E.is_symlink() and not RESULT.exists() and not RESULT.is_symlink(),'fresh audit evidence/result')
sources();entry=shutil.disk_usage(O).free;require(entry>=16*2**30,'fresh16GiB before audit evidence/child')
spec=importlib.util.spec_from_file_location('_packet04_owned',OWNED);owned=importlib.util.module_from_spec(spec);spec.loader.exec_module(owned)
E.mkdir(mode=0o700);(E/'source').mkdir(mode=0o700)
for source,name in [(AUDITOR,'audit.py'),(H/'verify.py','qualified-verify.py'),(OWNED,'owned_stage.py'),(Path(__file__).resolve(),'execution.py')]:
 before=sha(source);data=source.read_bytes();require(hashlib.sha256(data).hexdigest()==before,'retained wrapper source differs')
 with (E/'source'/name).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
 require(sha(source)==before==sha(E/'source'/name),'stable exact retained source')
env=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
r=dict(status='waiting',started_at=time.time(),parent_pid=os.getpid(),parent_parent_pid=os.getppid(),cwd=str(O),environment=env,
 canonical_lock=str(owned.CANONICAL_LOCK),wait_seconds=600,capacity=dict(entry_gib=16,stop_gib=9,floor_gib=8),
 maximum_child_cpu_seconds=900,maximum_child_read_seconds=1200,maximum_observation_seconds=1250,maximum_file_bytes=4*2**20,
 source_hashes={str(k):v for k,v in EXPECTED.items()},execution_source_sha256=sha(__file__),entry_free_bytes=entry,disk_samples=[],
 scope='One read-only prepared packet review; zero compiler/provider/controller/workload calls.',
 identity_limitation='In-process parent identity plus Popen PID/argv/environment/cwd/times; no external ps/cwd probes and no signals.')
def save():owned.write(E/'record.json',r)
save()
try:
 with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
  sources();r.update(admitted_at=time.time(),free_bytes_before=owned.disk(O,16));save()
  command=[str(P),'-B',str(AUDITOR),'--canonical-fd',str(fd)];r['command']=command;save()
  with (E/'stdout').open('xb') as stdout,(E/'stderr').open('xb') as stderr:
   child=subprocess.Popen(command,cwd=O,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,pass_fds=(fd,))
   r.update(status='running',pid=child.pid,child_started_at=time.time());deadline=time.monotonic()+1250
   try:
    try:save()
    except BaseException as error:r['initial_child_publication_error']=repr(error)
    while True:
     try:code=child.wait(timeout=min(5,max(.001,deadline-time.monotonic())));break
     except subprocess.TimeoutExpired:
      r['disk_samples'].append(dict(time=time.time(),free_bytes=shutil.disk_usage(O).free))
      if time.monotonic()>=deadline:
       r.update(status='observation-expired-task-not-signaled',may_be_live=True);code=None;break
   finally:
    r.update(returncode=child.returncode,observation_finished_at=time.time(),stdout_sha256=sha(E/'stdout'),stderr_sha256=sha(E/'stderr'))
    if child.returncode is not None:r.update(status='finished',finished_at=time.time())
    else:r.update(status='unclosed-task-not-signaled',may_be_live=True)
    try:save()
    except BaseException as error:
     print(json.dumps(dict(status='publication-failed',error=repr(error),observed_record=r)),flush=True);raise
  require(code is not None,'audit may still be live; no signal or retry')
  require(code==0,'actual packet audit failed; preserve evidence')
  require(not (E/'stderr').read_bytes(),'audit emitted stderr')
  require('initial_child_publication_error' not in r,'audit initial record publication failed')
  sources();r.update(result_sha256=sha(RESULT),free_bytes_after=owned.disk(O,9));save()
  require(all(row['free_bytes']>=9*2**30 for row in r['disk_samples']),'observed live-floor violation')
 r['canonical_released_at']=time.time();save()
 print(json.dumps(dict(record=str(E/'record.json'),record_sha256=sha(E/'record.json'),result=str(RESULT),result_sha256=r['result_sha256'],pid=r['pid'],returncode=0)),flush=True)
except BaseException as error:
 r['execution_error']=repr(error);save();raise
