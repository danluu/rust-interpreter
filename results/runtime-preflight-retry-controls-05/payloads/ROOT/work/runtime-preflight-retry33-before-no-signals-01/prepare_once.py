"""One authorized bounded read-only packet preparation; no test or provider calls."""
import hashlib, importlib.util, json, os, resource, shutil, subprocess, sys, time
from pathlib import Path
O = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
H = O/'experiments/runtime-preflight-retry-controls-05'
E = O/'.work/runtime-preflight-retry-controls-preparation-execution-05'
P = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
EXPECTED = {'run.py': '66cf2a2c4ff855d0cebcf18d60520e2455a33f58f4def1d1d28e502493fdcb42', 'child.py': '34dfcaea24a5ceeb8486d32b53164db3af9e79f871cf975e540ed30b7b030e29', 'prepare.py': '7e87dbec85332dd090cce5b4b3cb2eadd5dfb059d7ead26320372e9cdea457fb'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
TESTED = {'/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05/entry.py': '7d5f11d5a96c61608a84494be23c2fafa3d8e1ad6cb034949a7ddb749b70c28a', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05/controller.py': '5a3b5f2f18ac055611217265e3e800ba0389ae65f734f4b97400df1051872a0b', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05/audit_owner.py': '6c15a87bb0f56ef2f4fd8f7d47d88ee47db3fd076e8f207199d237e389ef5dce', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05/routes.json': '893d6102741b5206a829e2f5e130614667140b1eacc09d0c55616f7311f82e6a', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05/prepare.py': '8573e64303bc516131777281510067baaeae35cde61d0c78579cc434b60ec45d', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05/prepare_once.py': 'eab84cb51566a127a18b7d0f07361fdf51bcdc093d3f02cbe051dafaa966ae8c', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05/launch.py': 'e5dc2d5901ff52df0c7b94896a411a0be6b5274854317bbed40f5a7e79152971', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05/test_retry.py': '8af7ea13feaea3c20ae601d9903dedfd4c27b545ff917b5ca2b3796763e9a143', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime04-environment-adapter-01/environment.py': 'fbc563accfeebe2650902263ed9972031d37c84bc8c21986a3545ae4020d314d', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/hir-options-hash-runtime-audit-05/reader.py': 'da1f151cdc6defaad5b572dc87c3e770b057322b7f2789140b160fb755a07e2c', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/hir-options-hash-runtime-audit-05/test_reader.py': '43ef97a798997a30b3f4b8bd56c4d99ffb60e0ed00f942d2798ba30aed4a7bf6', '/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/stable-cgu/owned_stage.py': '7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e'}
def validate_sources():
 for name,digest in EXPECTED.items(): assert sha(H/name)==digest
 for path,digest in TESTED.items(): assert sha(Path(path))==digest
assert Path.cwd() == O and sys.dont_write_bytecode and not sys.flags.optimize
assert Path(sys.executable).resolve() == P
assert not E.exists() and not E.is_symlink()
assert not any((H/name).exists() for name in ['inputs.json','launch.json'])
validate_sources()
owned_path = X/'experiments/stable-cgu/owned_stage.py'
old_freeze = json.loads((ROOT/'experiments/runtime-startup-environment-controls-01/inputs.json').read_bytes())
assert sha(owned_path) == old_freeze['files'][str(owned_path)]['sha256']
spec = importlib.util.spec_from_file_location('retry33_prepare_owned', owned_path)
owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
E.mkdir(mode=0o700); (E/'source').mkdir(mode=0o700)
for name in EXPECTED: (E/'source'/name).write_bytes((H/name).read_bytes())
(E/'source'/'execution.py').write_bytes(Path(__file__).read_bytes())
(E/'source'/'owned_stage.py').write_bytes(owned_path.read_bytes())
env = dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR=str(O/'.work/runtime-preflight-retry-controls-05/tmp'))
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
  r.update(status='finished',returncode=code,finished_at=time.time())
  for key,callback in [('stdout_sha256',lambda:sha(E/'stdout')),('stderr_sha256',lambda:sha(E/'stderr')),('free_bytes_after',lambda:shutil.disk_usage(O).free)]:
   try: r[key]=callback()
   except BaseException as error: r['observation_errors'].append(dict(stage=key,error=repr(error),time=time.time()))
  observe_save()
  assert not r['observation_errors'], 'observation/publication error; child closed and evidence preserved'
  assert code==0 and not (E/'stderr').read_bytes()
  assert r['free_bytes_after']>=9*2**30 and all(row['free_bytes']>=9*2**30 for row in r['disk_samples'])
  for name,digest in EXPECTED.items(): assert sha(H/name)==digest
  r['prepared_packet']=json.loads((E/'stdout').read_bytes()); save()
 r['canonical_released_at']=time.time(); save()
 print(json.dumps(r,sort_keys=True))
except BaseException as error:
 r['execution_error']=repr(error); save(); raise
