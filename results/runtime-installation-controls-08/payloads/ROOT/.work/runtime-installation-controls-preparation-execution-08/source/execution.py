"""One authorized bounded read-only packet preparation; no test or provider calls."""
import hashlib, importlib.util, json, os, resource, shutil, subprocess, sys, time
from pathlib import Path
O = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
H = O/'experiments/runtime-installation-controls-08'
E = O/'.work/runtime-installation-controls-preparation-execution-08'
P = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
EXPECTED = {'run.py': '0d24b27053d99a7c1826f1ea157dafd1428e81787a678da12fa946811f32fad9', 'child.py': '2f010210e41817b8f0a152f908c4a5ea777cd7ae890f33b40cfd6639dd1d2869', 'prepare.py': '2ea3a3c8afa12cd0c33df4ac20424e678998d4312209d462ac194b31948258aa'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
TESTED = {'/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/entry.py': '31bfb9cfd59bbbc45648ce7d6b5e72ddf5efdee62991df1e9414ae3d9ffdf736', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/controller.py': 'ba41563fed996c39c4f082e157c10845ddfca8bbde627ac22a22920c3f0ef642', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/audit_owner.py': '7a5fb8804372a42cc01e7890ec1be4e4a24cceb5dbe800a7dad67940efc212d5', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/routes.json': 'd339e74a11edb948f3cf4bcc0afbbba76887cc61aed125c8bb8bf62b1633723a', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/prepare.py': '8ca8b3371176b34c18b8e086e719f832ff86c4edbc1e2eab38c6a8ec04209722', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/prepare_once.py': 'ab0609d297302262feb418a240d0ec4a0c88d511f73e381c0a5c5b4245473c68', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/launch.py': '21560018724dd9439648acbf68e61a05b9899c8e8fb66e2f1e605bf747e8da06', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/imports.py': 'abfec7fa64337072613e2d707989c8a0724c758d3e412d85072af14570c2b460', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/test_installation.py': 'cee84852f61d4ecbb9c16c96521dc205b7090a2783333bb076fe08475630361d', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/test_imports.py': '78b8d7ecaa981c751206714bf282f6ce5cce108fbb86b1af163e3692ba81401d', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/runtime_compiler.py': '9591f94735c5b7d8333292c7ce3baf2cde7cf556eb4e75354fd19536f33b6f5b', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/producer_recipe.py': '38ccb1d5ac03f0ce80eca0e397de507b3aa9534fae5da8f3102f1b902adcdb50', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/audit_recipe.py': 'a464993d8200f43fe30f365215a07383a76e9be08c63e1ee844c27e8aaf985b2', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/test_native_loader.py': 'fa84b34a52e9f6b0eeb29bf727f718528891570e2dc274bdf2a594690ec70659', '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/runtime_compiler.py': 'f38cdfd9e9c719185d9e002abf76a8883ad718b3771c62a9788f6feedd52a61b', '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/custom_compiler.py': 'c6a44c3d271664de2c97bf6c3af3ea6426eba6dd3730ac0612411230a02b7449', '/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/hir-options-hash/runtime-installation-01/recipe.py': '0fad2d783d750bc2ffd3a1694e52505bb7fa7c4b983f1e8b1edb3691dc455e3e', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/installation-plan-01/specification.json': '96c228e2b561de69c2d56a8e1364ac349437418a47a5c1935f6e4f14e67ab6b9', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime04-environment-adapter-01/environment.py': 'fbc563accfeebe2650902263ed9972031d37c84bc8c21986a3545ae4020d314d', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05/routes.json': '893d6102741b5206a829e2f5e130614667140b1eacc09d0c55616f7311f82e6a', '/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/stable-cgu/owned_stage.py': '7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation07-test-development-02/child.py': 'e92801395c8f2871abaab4bad236a35230f35a6150028f88b89dbf4d7278844d', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation07-test-development-02/record.json': '216932c3e9a0688aaa76ad75d276fa613d49fb137df2972952c4cd9014a2df3b', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation07-test-development-02/result.json': '728e78190e4e1b93713ba54c615778c6dfaa4957b44ca873dddd19b2c520fcaf', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation07-test-development-02/run_once.py': '53025fa12ef0ce4e27e81c6da72337c9a8dfd593feaa1f94895cef8f0aae62e8', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation07-test-development-02/source-after.json': '735a75d865120a005fe2de6bbc1b97db55d3e8c9e01e0bd308c67f70824d74fa', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation07-test-development-02/source-before.json': '735a75d865120a005fe2de6bbc1b97db55d3e8c9e01e0bd308c67f70824d74fa', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation07-test-development-02/started.json': 'c219c187fd8431cb73da3fa2053a1d3972a4e8a0dabdb41a080528e39dc34530', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation07-test-development-02/stderr': '88f4d0dd4227ecbac14e5f06959fb847237bdc66c712b380fca16e905a678095', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation07-test-development-02/stdout': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation07-test-development-02/manifest.json': '32714faef9db089fe00fa8c3abafdd3770f0b69e4846bf4b0f76b6f00b2c9079', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-native-loader-development-01/child.py': '8a4e0f3dc2076b023b638ad0de734ed0899525028d714e155d0dbb9c3b2dceb3', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-native-loader-development-01/record.json': '6e9ba64778ca1e60e5e253cf02a9fea8be9d0f3a27be563fd1b1082b205c45d7', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-native-loader-development-01/result.json': '2484b106fa630791bf5f6d8d68a7f9c7b08a01e1bec742409de7623e5d257ac3', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-native-loader-development-01/run_once.py': 'a70853e3c70a88b6f91ac9ac43a1c77e956ee254a0ca62338296460958cb397e', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-native-loader-development-01/source-after.json': 'a48a43bc8a3523da92d3d590d0819162e2ff1f9f1ac5ba085c6e691e49574d8a', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-native-loader-development-01/source-before.json': 'a48a43bc8a3523da92d3d590d0819162e2ff1f9f1ac5ba085c6e691e49574d8a', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-native-loader-development-01/started.json': '6bbe5d5bab1737394c7a416411545ab107328faac7d230c4bcfdb6c6aa49d82c', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-native-loader-development-01/stderr': 'c6947e311925d67f86a1a56b187870642f52cb9d45ad7d4da0875d2b7f731215', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-native-loader-development-01/stdout': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-native-loader-development-01/manifest.json': '8a27d91ac6b6cb6286161c53f3b324992050b7e1343982cd766c98d38065dc69'}
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
spec = importlib.util.spec_from_file_location('installation48_prepare_owned', owned_path)
owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
E.mkdir(mode=0o700); (E/'source').mkdir(mode=0o700)
for name in EXPECTED: (E/'source'/name).write_bytes((H/name).read_bytes())
(E/'source'/'execution.py').write_bytes(Path(__file__).read_bytes())
(E/'source'/'owned_stage.py').write_bytes(owned_path.read_bytes())
env = dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR=str(O/'.work/runtime-installation-controls-08/tmp'))
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
