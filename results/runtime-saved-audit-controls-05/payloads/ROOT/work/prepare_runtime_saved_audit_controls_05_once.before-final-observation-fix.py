"""One authorized bounded read-only packet preparation; no test or provider calls."""
import hashlib, importlib.util, json, os, resource, shutil, subprocess, sys, time
from pathlib import Path
O = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
H = O/'experiments/runtime-saved-audit-controls-05'
E = O/'.work/runtime-saved-audit-controls-preparation-execution-05'
P = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
EXPECTED = {'run.py': '4bd1e3b4859e8fb06775b125b24fef9fc85b4bd1baadd6844acd779a798a03c8', 'child.py': 'c1caaeb871679c3be27f333344cfd469d8dd311942ec84e1aa4349c4c569ac9c', 'prepare.py': '5a2b247808ab3854e3b9032a65a6776e14e4045d9fb9403111364333fe7a9841'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
TESTED = {'reader.py': 'da1f151cdc6defaad5b572dc87c3e770b057322b7f2789140b160fb755a07e2c', 'test_reader.py': '43ef97a798997a30b3f4b8bd56c4d99ffb60e0ed00f942d2798ba30aed4a7bf6', 'audit_io.py': '7b7fa5108da4edce1096215d8974d7bff23e39e6f5123f23321a277199a15156', 'test_audit_io.py': '1ba98493025f1a8526b7484a96031e7856a76459e2ae2b6e11b16f336d738e35'}
def validate_sources():
 for name,digest in EXPECTED.items(): assert sha(H/name)==digest
 for name,digest in TESTED.items(): assert sha(ROOT/'experiments/hir-options-hash-runtime-audit-05'/name)==digest
assert Path.cwd() == O and sys.dont_write_bytecode and not sys.flags.optimize
assert Path(sys.executable).resolve() == P
assert not E.exists() and not E.is_symlink()
assert not any((H/name).exists() for name in ['inputs.json','launch.json'])
validate_sources()
owned_path = X/'experiments/stable-cgu/owned_stage.py'
old_freeze = json.loads((ROOT/'experiments/retained-proof-copy-controls-01/inputs.json').read_bytes())
assert sha(owned_path) == old_freeze['files'][str(owned_path)]['sha256']
spec = importlib.util.spec_from_file_location('runtime53_prepare_owned', owned_path)
owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
E.mkdir(mode=0o700); (E/'source').mkdir(mode=0o700)
for name in EXPECTED: (E/'source'/name).write_bytes((H/name).read_bytes())
(E/'source'/'execution.py').write_bytes(Path(__file__).read_bytes())
(E/'source'/'owned_stage.py').write_bytes(owned_path.read_bytes())
env = dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR=str(O/'.work/runtime-saved-audit-controls-05/tmp'))
command=[str(P),'-B',str(H/'prepare.py')]
r=dict(status='waiting',started_at=time.time(),parent_pid=os.getpid(),supervisor_parent_pid=os.getppid(),command=command,cwd=str(O),environment=env,source_sha256=EXPECTED,execution_source_sha256=sha(__file__),owned_source_sha256=sha(owned_path),canonical_lock=str(owned.CANONICAL_LOCK),wait_seconds=600,capacity=dict(entry_gib=16,stop_gib=9,floor_gib=8),mode='authorized one-shot read-only proposal preparation; no test or compiler workload',identity_limitation='Popen PID and in-process parent identity retained; no independent ps/cwd probes and no signals.',disk_samples=[])
def save(): owned.write(E/'record.json',r)
save()
try:
 with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
  r.update(admitted_at=time.time(),free_bytes_before=owned.disk(O,16)); save()
  validate_sources()
  resource.setrlimit(resource.RLIMIT_CPU,(60,60)); resource.setrlimit(resource.RLIMIT_FSIZE,(256*1024,256*1024))
  with (E/'stdout').open('xb') as stdout,(E/'stderr').open('xb') as stderr:
   child=subprocess.Popen(command,cwd=O,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,pass_fds=(fd,))
   deadline=time.monotonic()+120
   r.update(status='running',pid=child.pid,child_started_at=time.time(),observation_errors=[])
   def observe_save():
    try: save()
    except BaseException as error: r['observation_errors'].append(dict(stage='publication',error=repr(error),time=time.time()))
   observe_save()
   while True:
    try:
     code=child.wait(timeout=min(1,max(.001,deadline-time.monotonic()))); break
    except subprocess.TimeoutExpired:
     try: r['disk_samples'].append(dict(time=time.time(),free_bytes=shutil.disk_usage(O).free))
     except BaseException as error: r['observation_errors'].append(dict(stage='disk-sample',error=repr(error),time=time.time()))
     observe_save()
     if time.monotonic()>=deadline:
      code=None
      r.update(status='unresolved-live-child-not-signaled',observation_finished_at=time.time(),returncode=child.returncode,may_be_live=child.returncode is None)
      observe_save(); break
   if code is None: raise RuntimeError('bounded observation expired; child not signaled and closure not asserted')
  r.update(status='finished',returncode=code,finished_at=time.time(),stdout_sha256=sha(E/'stdout'),stderr_sha256=sha(E/'stderr'),free_bytes_after=shutil.disk_usage(O).free); save()
  assert not r['observation_errors'], 'observation/publication error; child closed and evidence preserved'
  assert code==0 and not (E/'stderr').read_bytes()
  assert r['free_bytes_after']>=9*2**30 and all(row['free_bytes']>=9*2**30 for row in r['disk_samples'])
  for name,digest in EXPECTED.items(): assert sha(H/name)==digest
  r['prepared_packet']=json.loads((E/'stdout').read_bytes()); save()
 r['canonical_released_at']=time.time(); save()
 print(json.dumps(r,sort_keys=True))
except BaseException as error:
 r['execution_error']=repr(error); save(); raise
