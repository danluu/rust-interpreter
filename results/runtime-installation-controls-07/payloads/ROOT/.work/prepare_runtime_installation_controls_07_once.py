"""One authorized bounded read-only packet preparation; no test or provider calls."""
import hashlib, importlib.util, json, os, resource, shutil, subprocess, sys, time
from pathlib import Path
O = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
H = O/'experiments/runtime-installation-controls-07'
E = O/'.work/runtime-installation-controls-preparation-execution-07'
P = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
EXPECTED = {'run.py': 'f1bda8dacfebcc57dc1568c8f08ee68d1b1b3beb26ccc0e2e6a1eb6880e13971', 'child.py': '694795c2a77b18359b89a41eee9eb4b628bf28700f02009c9263bd2bdac0b3b7', 'prepare.py': 'fc50c04d8cad08f16451e0a9ff37456c7d7afcc64046b73828c33cb61691013e'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
TESTED = {'/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/entry.py': '6e98a34a72b756fd38c48e8f98dbdd535321d555d4332f66cacc876e0d487467', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/controller.py': 'cf44c7b7fae1964af472d6f3cffe6f5c9d2d1d782d83dc123f65dbd64de259c8', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/audit_owner.py': '4ce531a592d99046f0936a43d2b31c6a1f3ecbca7da809b70da79b20f45a97b8', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/routes.json': 'ef75ddf2057ebd395a159623d387b01051ee1479363bf9c878f7641b99ec0dd2', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/prepare.py': '9414b82645bbd96e491f2d348439bdfafd0fe54430ca427c3808bc8d8a68e855', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/prepare_once.py': 'b5210818a1321d802987ed5e234d0d4f1b65fc2dee823974f0bfbbe6f7429a43', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/launch.py': '27734a6ae2fa8f13ca62afdccfa3fe400f1b5e42666629fa81c9fce5dc1e8fdc', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/test_installation.py': 'cee84852f61d4ecbb9c16c96521dc205b7090a2783333bb076fe08475630361d', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime04-environment-adapter-01/environment.py': 'fbc563accfeebe2650902263ed9972031d37c84bc8c21986a3545ae4020d314d', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05/routes.json': '893d6102741b5206a829e2f5e130614667140b1eacc09d0c55616f7311f82e6a', '/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/stable-cgu/owned_stage.py': '7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation06-test-development-01/child.py': 'ad9430854a5a4075eb8d70400271d48890e1be44ded180c44635f678fd5723b8', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation06-test-development-01/child.py.from-development25.diff': 'b405781fa1ec836e462536475c3ed696e5eb6273d4850bed713c2af3bb1aa89b', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation06-test-development-01/record.json': '0e05c3a8914e1862ac0130644590fa11f3b10671bbe638c5e1d8bfb7c104d64d', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation06-test-development-01/result.json': '74b58e3a85112026889d8a123b154bbaf9daa756b98b0fc45eccc4153f19e26f', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation06-test-development-01/run_once.py': '5c3989a026f5764dac150608db59b250ed4dc5e0cfe7316988d152e298af132b', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation06-test-development-01/run_once.py.from-development25.diff': '4a68a505716867c00a9eae4472149cf80e05e73501d6f4f30355143a12ae96bf', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation06-test-development-01/source-after.json': '423d11fab306a99ecf416f5842e6aa42b502d190beddd34f42fec154f9d5ba3b', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation06-test-development-01/source-before.json': '423d11fab306a99ecf416f5842e6aa42b502d190beddd34f42fec154f9d5ba3b', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation06-test-development-01/source-review-provenance.json': '82fc52a4d551a6c50c91ab01b037281b2ec4b97495ba855552cf13f24eb32ed0', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation06-test-development-01/started.json': '63c54bf8a9f498092d736edcf6c9509ffc42cbf9be9c56834c946ec4c45a9253', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation06-test-development-01/stderr': 'c385c5d2bf5a8ed0c7e351110262792200c6476df0fdff7e00d97edc06aa8e5c', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation06-test-development-01/stdout': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation06-test-development-01/manifest.json': 'cfb87bc70ee8d39ab72d37555ff6a8f3c678e0e432497af81507803ac6eaa505'}
def validate_sources():
 for name,digest in EXPECTED.items(): assert sha(H/name)==digest
 for path,digest in TESTED.items(): assert sha(Path(path))==digest
assert Path.cwd() == O and sys.dont_write_bytecode and not sys.flags.optimize
assert Path(sys.executable).resolve() == P
assert not E.exists() and not E.is_symlink()
assert not any((H/name).exists() for name in ['inputs.json','launch.json'])
validate_sources()
owned_path = X/'experiments/stable-cgu/owned_stage.py'
old_freeze_path = ROOT/'experiments/runtime-installation-controls-05/inputs.json'
assert sha(old_freeze_path) == 'ff8029766174a10f3e60f0927098f6e723e69fdfbf5840629e7dea68d86cdc4f'
old_freeze = json.loads(old_freeze_path.read_bytes())
assert sha(owned_path) == old_freeze['files'][str(owned_path)]['sha256']
spec = importlib.util.spec_from_file_location('installation25_prepare_owned', owned_path)
owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
E.mkdir(mode=0o700); (E/'source').mkdir(mode=0o700)
for name in EXPECTED: (E/'source'/name).write_bytes((H/name).read_bytes())
(E/'source'/'execution.py').write_bytes(Path(__file__).read_bytes())
(E/'source'/'owned_stage.py').write_bytes(owned_path.read_bytes())
env = dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR=str(O/'.work/runtime-installation-controls-07/tmp'))
command=[str(P),'-B',str(H/'prepare.py')]
r=dict(status='waiting',started_at=time.time(),parent_pid=os.getpid(),supervisor_parent_pid=os.getppid(),command=command,cwd=str(O),environment=env,source_sha256=EXPECTED,execution_source_sha256=sha(__file__),owned_source_sha256=sha(owned_path),canonical_lock=str(owned.CANONICAL_LOCK),wait_seconds=600,capacity=dict(entry_gib=10,stop_gib=9,floor_gib=8),mode='authorized one-shot read-only proposal preparation; no test or compiler workload',identity_limitation='Popen PID and in-process parent identity retained; no independent ps/cwd probes and no signals.',disk_samples=[])
def save(): owned.write(E/'record.json',r)
save()
try:
 with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
  r.update(admitted_at=time.time(),free_bytes_before=owned.disk(O,10)); save()
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
