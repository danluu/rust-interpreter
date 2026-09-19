"""One bounded saved-failure audit; explicit wait, no signals or workloads."""
import hashlib, importlib.util, json, os, shutil, subprocess, sys, time
from pathlib import Path
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
P=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
AUDITOR=R/'experiments/hir-options-hash-driver-failure-audit-01/verify.py'
E=R/'.work/hash-driver-failure-verification-execution-01'
RESULT=R/'.work/hir-options-hash-driver-failure-verification-01.json'
H=R/'experiments/hir-options-hash-driver-stage-02'
OWNED=X/'experiments/stable-cgu/owned_stage.py'
CORRECTED=R/'experiments/hir-options-hash-driver-audit-02/verify.py'
QUALIFICATION=R/'.work/hash-inherited-record-controls-independent-verification-01.json'
EXPECTED={CORRECTED:'9e3e3291d168f3ac69d4bba4bf047212d53eb2eb485218df4b5f819f1601daf0',
 QUALIFICATION:'127b8d0845d34927cdad84429c8be4841f5f7c1d61a954722c8acf3cb3951fbc',
 AUDITOR:'be727d8f49f9b6af22792f0ebefa2172b3f36032792974baf3d8bb13ede60fff',
 H/'verify.py':'cbff690675b8697855bb87b0e09d9b77495fc0b8968855301e1a88612ec62a3f',
 OWNED:'7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e',
 H/'launch.json':'e315c703101fb5d8e9f732a10db9b07883792057c0f833b71979cf54efcbfc43',
 H/'inputs.json':'5accd23a86a3d7df8d19e8e294fcc96a4bc4f707ecd590b999c88ae092ed6dae'}
FAILED=R/'.work/hir-options-hash-driver-01'
OUTER=R/'.work/experiments/hir-options-hash-driver-supervisor-01'
LAUNCHER=R/'.work/hash-driver-launch-execution-01'
EXPECTED.update({FAILED/'receipt.json':'f53967e90c81144be6f10a00395ee86a427daaa67957d0eba1dd9bcdc0f44d2c',
 FAILED/'compile/receipt.json':'99571256179760fade951e5f0cdea31cffb8345ec5dccdd3d20ab113dade3cd4',
 FAILED/'compile/stderr':'789be46bc0f46a221859863de9fa28103a928ba8c4d5b51bd83e101dde06698f',
 OUTER/'status.json':'1d31d47f800316c712d401d58ec6fcf48c3549d8dfac0575aa299b185fcffb8c',
 LAUNCHER/'record.json':'7e003f2288530af91abd4887a87677c548ca63fdcca977df75bd91ac64c9b65e',
 O/'.work/hash-driver-packet-verification-05.json':'feb02068147f9f4b4d85a17cd9f984fd938e7d788438c7c4e144061053fb1f5e'})
def require(ok,message):
 if not ok:raise RuntimeError(message)
def sha(path):
 path=Path(path);before=path.stat();require(path.resolve(strict=True)==path and path.is_file() and before.st_size<=64*2**20,'bounded ordinary wrapper input')
 with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
 after=path.stat();require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'wrapper input changed')
 return digest
def sources():
 for path,digest in EXPECTED.items():require(sha(path)==digest,'reviewed exact wrapper input: '+str(path))
require(Path.cwd()==R and sys.dont_write_bytecode and not sys.flags.optimize and Path(sys.executable).resolve()==P,'fixed Python/owner')
require(not E.exists() and not E.is_symlink() and not RESULT.exists() and not RESULT.is_symlink(),'fresh audit evidence/result')
sources();entry=shutil.disk_usage(R).free;require(entry>=16*2**30,'fresh16GiB before audit evidence/child')
spec=importlib.util.spec_from_file_location('_failed_driver01_owned',OWNED);owned=importlib.util.module_from_spec(spec);spec.loader.exec_module(owned)
E.mkdir(mode=0o700);(E/'source').mkdir(mode=0o700)
for source,name in [(AUDITOR,'audit.py'),(CORRECTED,'corrected-verify.py'),(QUALIFICATION,'inherited22-audit.json'),(H/'verify.py','qualified-verify.py'),(OWNED,'owned_stage.py'),(Path(__file__).resolve(),'execution.py'),(FAILED/'receipt.json','failed-terminal.json'),(FAILED/'compile/receipt.json','failed-compile.json'),(FAILED/'compile/stderr','failed-stderr'),(OUTER/'status.json','outer.json'),(LAUNCHER/'record.json','launcher.json'),(O/'.work/hash-driver-packet-verification-05.json','packet05-audit.json')]:
 before=sha(source);data=source.read_bytes();require(hashlib.sha256(data).hexdigest()==before,'retained wrapper source differs')
 with (E/'source'/name).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
 require(sha(source)==before==sha(E/'source'/name),'stable exact retained source')
env=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
r=dict(status='waiting',started_at=time.time(),parent_pid=os.getpid(),parent_parent_pid=os.getppid(),cwd=str(R),environment=env,
 canonical_lock=str(owned.CANONICAL_LOCK),wait_seconds=600,capacity=dict(entry_gib=16,stop_gib=9,floor_gib=8),
 maximum_child_cpu_seconds=900,maximum_child_read_seconds=1200,maximum_observation_seconds=1250,maximum_file_bytes=4*2**20,
 source_hashes={str(k):v for k,v in EXPECTED.items()},execution_source_sha256=sha(__file__),entry_free_bytes=entry,disk_samples=[],
 scope='One saved failed-compiler audit; zero new compiler/provider/controller/workload calls.',
 identity_limitation='In-process parent identity plus Popen PID/argv/environment/cwd/times; no external ps/cwd probes and no signals.')
def save():owned.write(E/'record.json',r)
save()
try:
 with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
  sources();r.update(admitted_at=time.time(),free_bytes_before=owned.disk(R,16));save()
  command=[str(P),'-B',str(AUDITOR),'--launch-sha256',EXPECTED[H/'launch.json'],'--launcher-record',str(LAUNCHER/'record.json'),'--canonical-fd',str(fd)];r['command']=command;save()
  with (E/'stdout').open('xb') as stdout,(E/'stderr').open('xb') as stderr:
   child=subprocess.Popen(command,cwd=R,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,pass_fds=(fd,))
   r.update(status='running',pid=child.pid,child_started_at=time.time());deadline=time.monotonic()+1250
   try:
    try:save()
    except BaseException as error:r['initial_child_publication_error']=repr(error)
    while True:
     try:code=child.wait(timeout=min(5,max(.001,deadline-time.monotonic())));break
     except subprocess.TimeoutExpired:
      r['disk_samples'].append(dict(time=time.time(),free_bytes=shutil.disk_usage(R).free))
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
  require(code==0,'actual saved-failure audit failed; preserve evidence')
  require(not (E/'stderr').read_bytes(),'audit emitted stderr')
  require('initial_child_publication_error' not in r,'audit initial record publication failed')
  sources();report=json.loads(RESULT.read_bytes())
  require(report['status']=='verified-retained-failure' and report['receipt_sha256']==EXPECTED[FAILED/'receipt.json']
   and report['compile_receipt_sha256']==EXPECTED[FAILED/'compile/receipt.json']
   and report['actual_compiler_children']==1 and report['actual_driver_processes']==0
   and report['qualified_hash_driver_processes']==0 and report['hash_driver_qualified'] is False
   and report['full_frozen_byte_rehash'] is report['full_snapshot_selection'] is True
   and report['verifier_sha256']==EXPECTED[AUDITOR], 'complete saved-failure report association')
  r.update(result_sha256=sha(RESULT),free_bytes_after=owned.disk(R,9));save()
  require(all(row['free_bytes']>=9*2**30 for row in r['disk_samples']),'observed live-floor violation')
 r['canonical_released_at']=time.time();save()
 print(json.dumps(dict(record=str(E/'record.json'),record_sha256=sha(E/'record.json'),result=str(RESULT),result_sha256=r['result_sha256'],pid=r['pid'],returncode=0)),flush=True)
except BaseException as error:
 r['execution_error']=repr(error);save();raise
