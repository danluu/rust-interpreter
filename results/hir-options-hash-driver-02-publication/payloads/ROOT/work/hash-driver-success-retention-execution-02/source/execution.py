"""One bounded qualified-driver archive; explicit wait, no signals or workload calls."""
import hashlib, importlib.util, json, os, shutil, subprocess, sys, time
from pathlib import Path
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
P=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
AUDITOR=R/'experiments/hash-driver-success-evidence-02/archive.py'
E=R/'.work/hash-driver-success-retention-execution-02'
RESULT=R/'results/hir-options-hash-driver-02/summary.json'
WORK=R/'.work/hash-driver-success-evidence-01'
PROPOSAL=A/'.work/hash-driver02-lossless-publication-scope-02.json'
OWNED=X/'experiments/stable-cgu/owned_stage.py'
RESERVATION=64*2**20
EXPECTED={AUDITOR:'c14818c16d8d3863bc9135203749f9ab75b46fe6b32b288e5357609627d4a39e',
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
 for path,digest in EXPECTED.items():require(sha(path)==digest,'reviewed exact wrapper input: '+str(path))
require(Path.cwd()==R and sys.dont_write_bytecode and not sys.flags.optimize and Path(sys.executable).resolve()==P,'fixed Python/owner')
require(all(not p.exists() and not p.is_symlink() for p in [E,WORK,RESULT.parent]),'fresh archive execution/work/result')
sources();entry=shutil.disk_usage(R).free;require(entry>=9*2**30+RESERVATION,'fresh9GiB plus64MiB reserve before archive evidence/child')
spec=importlib.util.spec_from_file_location('_qualified_driver_archive02_owned',OWNED);owned=importlib.util.module_from_spec(spec);spec.loader.exec_module(owned)
E.mkdir(mode=0o700);(E/'source').mkdir(mode=0o700)
for source,name in [(AUDITOR,'archive.py'),(PROPOSAL,'proposal.json'),(OWNED,'owned_stage.py'),(Path(__file__).resolve(),'execution.py')]:
 before=sha(source);data=source.read_bytes();require(hashlib.sha256(data).hexdigest()==before,'retained wrapper source differs')
 with (E/'source'/name).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
 require(sha(source)==before==sha(E/'source'/name),'stable exact retained source')
env=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
r=dict(status='waiting',started_at=time.time(),parent_pid=os.getpid(),parent_parent_pid=os.getppid(),cwd=str(R),environment=env,
 canonical_lock=str(owned.CANONICAL_LOCK),wait_seconds=600,capacity=dict(entry_bytes=9*2**30+RESERVATION,stop_gib=9,floor_gib=8,reservation_bytes=RESERVATION),
 maximum_child_cpu_seconds=300,maximum_child_read_seconds=600,maximum_observation_seconds=650,maximum_file_bytes=16*2**20,
 source_hashes={str(k):v for k,v in EXPECTED.items()},execution_source_sha256=sha(__file__),entry_free_bytes=entry,disk_samples=[],
 scope='One archive-processing child; exact241 files, no new compiler/provider/workload calls or original mutations.',
 identity_limitation='In-process parent identity plus Popen PID/argv/environment/cwd/times; no external ps/cwd probes and no signals.')
def save():owned.write(E/'record.json',r)
save()
try:
 with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
  sources();free=owned.disk(R,9);require(free>=9*2**30+RESERVATION,'canonical archive entry reservation');r.update(admitted_at=time.time(),free_bytes_before=free);save()
  command=[str(P),'-B',str(AUDITOR),'--canonical-fd',str(fd)];r['command']=command;save()
  with (E/'stdout').open('xb') as stdout,(E/'stderr').open('xb') as stderr:
   child=subprocess.Popen(command,cwd=R,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,pass_fds=(fd,))
   r.update(status='running',pid=child.pid,child_started_at=time.time());deadline=time.monotonic()+650
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
  require(code is not None,'archive may still be live; no signal or retry')
  require(code==0,'actual archive failed; preserve evidence')
  require(not (E/'stderr').read_bytes(),'archive emitted stderr')
  require('initial_child_publication_error' not in r,'archive initial record publication failed')
  sources();report=json.loads(RESULT.read_bytes())
  terminal=json.loads((WORK/'receipt.json').read_bytes())
  require(report['status']==terminal['status']=='passed'
   and report['original_status']==terminal['original_status']=='passed-awaiting-independent-audit'
   and report['original_independent_audit_status']==terminal['original_independent_audit_status']=='verified'
   and report['retained_current_qualified_children']==terminal['retained_current_qualified_children']==3
   and report['retained_compilation_count']==terminal['retained_compilation_count']==1
   and report['retained_driver_process_count']==terminal['retained_driver_process_count']==2
   and report['retained_contexts_per_process']==terminal['retained_contexts_per_process']==8
   and report['retained_historical_failed_compiler_children']==terminal['retained_historical_failed_compiler_children']==1
   and report['retained_total_actual_hash_children']==terminal['retained_total_actual_hash_children']==4
   and report['hash_driver_qualified'] is terminal['hash_driver_qualified'] is True
   and all(report[k] is terminal[k] is False for k in ['application_qualified','performance_measurement','runtime_installation'])
   and report['workload_children']==terminal['workload_children']==0 and terminal['children']==[]
   and terminal['pid']==r['pid'] and terminal['parent_pid']==r['parent_pid']
   and r['admitted_at']<=terminal['started_at']<=terminal['finished_at']<=r['finished_at']
   and terminal['passed_environment']==report['passed_environment']==env
   and terminal['startup_environment_additions']==report['startup_environment_additions']=={'__CF_USER_TEXT_ENCODING':'0x1F5:0x0:0x52'}
   and terminal['observed_environment']==report['observed_environment']=={**env,'__CF_USER_TEXT_ENCODING':'0x1F5:0x0:0x52'}
   and terminal['engine_sha256']==EXPECTED[AUDITOR] and terminal['proposal_sha256']==report['proposal_sha256']==EXPECTED[PROPOSAL]
   and terminal['previous_attempt_sha256']==report['previous_attempt_sha256']==sha(RESULT.parent/'previous-attempt.json')
   and terminal['previous_archive_schema_failure']==dict(record_sha256='f77467941c8b264b1a64904565bfff0151737e4ddcbf72f6cb8a3896884ac6c0',actual_archive_processing_children=1)
   and report['failure_archive_publication']['git_blob']=='09c50202c9b3241d7c620053cd47c3f283136c88'
   and terminal['summary_sha256']==sha(RESULT) and terminal['manifest_sha256']==report['manifest_sha256']==sha(RESULT.parent/'manifest.json')
   and terminal['archive_sha256']==report['archive']['sha256']==sha(RESULT.parent/'evidence.tar.gz')
   and report['archive']['members']==terminal['member_count']==241 and report['archive']['logical_bytes']==terminal['logical_bytes']==13880266
   and report['archive']['full_member_readback'] is report['archive']['full_gzip_eof_crc'] is True
   and report['external_references']['reused_blobs']==93 and report['external_references']['new_blobs']==54
   and report['external_references']['referenced_native_base'] is report['external_references']['referenced_external_metadata_plan'] is True,
   'complete archive/closed child/recovery association')
  output=json.loads((E/'stdout').read_bytes())
  require(output==dict(status='passed',receipt=str(WORK/'receipt.json'),receipt_sha256=sha(WORK/'receipt.json'),
   archive_sha256=terminal['archive_sha256'],workload_children=0),'exact closed engine stdout association')
  r.update(result_sha256=sha(RESULT),free_bytes_after=owned.disk(R,9));save()
  require(all(row['free_bytes']>=9*2**30 for row in r['disk_samples']),'observed live-floor violation')
 r['canonical_released_at']=time.time();save()
 print(json.dumps(dict(record=str(E/'record.json'),record_sha256=sha(E/'record.json'),result=str(RESULT),result_sha256=r['result_sha256'],pid=r['pid'],returncode=0)),flush=True)
except BaseException as error:
 r['execution_error']=repr(error);save();raise
