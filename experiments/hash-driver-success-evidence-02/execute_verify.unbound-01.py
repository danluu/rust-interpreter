"""One bounded independent archive audit; explicit wait, no signals or workloads."""
import hashlib, importlib.util, json, os, shutil, subprocess, sys, time
from pathlib import Path
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
P=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
AUDITOR=R/'experiments/hash-driver-success-evidence-02/verify.py'
E=A/'.work/hash-driver-success-retention-audit-execution-02'
RESULT=A/'.work/hash-driver-success-retention-independent-verification-02.json'
H=R/'experiments/hash-driver-success-evidence-02'
W=R/'.work/hash-driver-success-evidence-01'
D=R/'results/hir-options-hash-driver-02'
CLOSED=R/'.work/hash-driver-success-retention-execution-02'
OWNED=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/stable-cgu/owned_stage.py')
PROPOSAL=A/'.work/hash-driver02-lossless-publication-scope-02.json'
ACTUAL=None  # Bind only after passed archive02 and explicit wrapper closure; preserve this draft.
EXPECTED={AUDITOR:'83091dcd44a00ef1294eaf177bf49146d61d98883b566fb7a107aa8607fe2bde',
 H/'archive.py':'c14818c16d8d3863bc9135203749f9ab75b46fe6b32b288e5357609627d4a39e',
 H/'execute.py':'8987c2eb72a52b2deb5c6304901d6c419c19d46f87132bdca89b9958a9d97de0',
 OWNED:'7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e',
 PROPOSAL:'f6ea57ce5485de96bcc00aa6bb872cf2560ba023df48affea533806e3fac7264'}
def require(ok,message):
 if not ok:raise RuntimeError(message)
def sha(path):
 path=Path(path);before=path.stat();require(path.resolve(strict=True)==path and path.is_file() and before.st_size<=64*2**20,'bounded ordinary wrapper input')
 with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
 after=path.stat();require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'wrapper input changed')
 return digest
def sources():
 require(type(ACTUAL) is dict and set(ACTUAL)=={'receipt','execution_record','summary'} and all(type(v) is str and len(v)==64 and all(c in '0123456789abcdef' for c in v) for v in ACTUAL.values()),'unbound actual closed archive')
 for path,digest in EXPECTED.items():require(sha(path)==digest,'reviewed exact wrapper input: '+str(path))
 for key,path in [('receipt',W/'receipt.json'),('execution_record',CLOSED/'record.json'),('summary',D/'summary.json')]:require(sha(path)==ACTUAL[key],'exact actual closure binding')
require(Path.cwd()==A and sys.dont_write_bytecode and not sys.flags.optimize and Path(sys.executable).resolve()==P,'fixed Python/owner')
require(not E.exists() and not E.is_symlink() and not RESULT.exists() and not RESULT.is_symlink(),'fresh audit evidence/result')
sources();entry=shutil.disk_usage(A).free;require(entry>=16*2**30,'fresh16GiB before audit evidence/child')
spec=importlib.util.spec_from_file_location('_success_archive_audit02_owned',OWNED);owned=importlib.util.module_from_spec(spec);spec.loader.exec_module(owned)
E.mkdir(mode=0o700);(E/'source').mkdir(mode=0o700)
for source,name in [(AUDITOR,'audit.py'),(H/'archive.py','archive.py'),(H/'execute.py','archive-execution.py'),(PROPOSAL,'proposal.json'),(OWNED,'owned_stage.py'),(Path(__file__).resolve(),'execution.py')]:
 before=sha(source);data=source.read_bytes();require(hashlib.sha256(data).hexdigest()==before,'retained wrapper source differs')
 with (E/'source'/name).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
 require(sha(source)==before==sha(E/'source'/name),'stable exact retained source')
env=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
r=dict(status='waiting',started_at=time.time(),parent_pid=os.getpid(),parent_parent_pid=os.getppid(),cwd=str(A),environment=env,
 canonical_lock=str(owned.CANONICAL_LOCK),wait_seconds=600,capacity=dict(entry_gib=16,stop_gib=9,floor_gib=8),
 maximum_child_cpu_seconds=180,maximum_child_read_seconds=300,maximum_observation_seconds=350,maximum_file_bytes=2*2**20,
 source_hashes={str(k):v for k,v in EXPECTED.items()},execution_source_sha256=sha(__file__),entry_free_bytes=entry,disk_samples=[],
 scope='One independent saved archive audit; exact241 sources/member hashes/EOF and closed owner, zero compiler/provider/workload calls.',
 identity_limitation='In-process parent identity plus Popen PID/argv/environment/cwd/times; no external ps/cwd probes and no signals.')
def save():owned.write(E/'record.json',r)
save()
try:
 with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
  sources();r.update(admitted_at=time.time(),free_bytes_before=owned.disk(A,16));save()
  command=[str(P),'-B',str(AUDITOR),'--receipt-sha256',ACTUAL['receipt'],'--execution-record-sha256',ACTUAL['execution_record'],'--summary-sha256',ACTUAL['summary'],'--canonical-fd',str(fd)];r['command']=command;save()
  with (E/'stdout').open('xb') as stdout,(E/'stderr').open('xb') as stderr:
   child=subprocess.Popen(command,cwd=A,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,pass_fds=(fd,))
   r.update(status='running',pid=child.pid,child_started_at=time.time());deadline=time.monotonic()+350
   try:
    try:save()
    except BaseException as error:r['initial_child_publication_error']=repr(error)
    while True:
     try:code=child.wait(timeout=min(5,max(.001,deadline-time.monotonic())));break
     except subprocess.TimeoutExpired:
      r['disk_samples'].append(dict(time=time.time(),free_bytes=shutil.disk_usage(A).free))
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
  require(code==0,'actual archive audit failed; preserve evidence')
  require(not (E/'stderr').read_bytes(),'audit emitted stderr')
  require('initial_child_publication_error' not in r,'audit initial record publication failed')
  sources();report=json.loads(RESULT.read_bytes())
  require(report['status']=='verified' and report['pid']==r['pid'] and report['parent_pid']==r['parent_pid']
   and report['receipt_sha256']==ACTUAL['receipt'] and report['execution_record_sha256']==ACTUAL['execution_record']
   and report['summary_sha256']==ACTUAL['summary'] and report['verifier_sha256']==EXPECTED[AUDITOR]
   and report['selected_files']==241 and report['logical_bytes']==13880266 and report['workload_children']==0
   and report['original_status']=='passed-awaiting-independent-audit' and report['hash_driver_qualified'] is True
   and report['retained_current_qualified_children']==3 and report['retained_historical_failed_compiler_children']==1
   and report['retained_total_actual_hash_children']==4 and report['complete_tree_stamps']==10
   and report['external_references']['reused_blobs']==93 and report['new_gzip_blobs']==54
   and all(report[k] is False for k in ['application_qualified','performance_measurement','runtime_installation']),'exact independent archive audit association')
  r.update(result_sha256=sha(RESULT),free_bytes_after=owned.disk(A,9));save()
  require(all(row['free_bytes']>=9*2**30 for row in r['disk_samples']),'observed live-floor violation')
 r['canonical_released_at']=time.time();save()
 print(json.dumps(dict(record=str(E/'record.json'),record_sha256=sha(E/'record.json'),result=str(RESULT),result_sha256=r['result_sha256'],pid=r['pid'],returncode=0)),flush=True)
except BaseException as error:
 r['execution_error']=repr(error);save();raise
