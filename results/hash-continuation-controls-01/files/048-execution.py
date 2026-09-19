"""One authorized bounded read-only packet preparation; no test or provider calls."""
import hashlib, importlib.util, json, os, resource, shutil, subprocess, sys, time
from pathlib import Path
O = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
H = O/'experiments/hash-continuation-controls-01'
E = O/'.work/hash-continuation-controls-preparation-execution-01'
P = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
EXPECTED = {'run.py': '640625c82c310b56a763fdcfeb96a4d147bf6f6bdabffd87da77e9b28f6a8be3', 'child.py': '0b9e943a252d0c461ed99ab4985fb02c9a40533f3502e2717c74f6b72f4a811a', 'prepare.py': '5db2c820056e33af6ccc904623655e64351220f7d6fed381ad96ea795fc3812b', 'README.md': 'd49fcd41cb074692f7231ee647c05c117b8e1672d8ec28472bc411fde624eb92'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
TESTED = {'/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/completed-proof-snapshot-catalog-02/catalog.py': 'fafdc63b0bfc7f017db760ec1cb776a0822eca5ca4390840c2a9eed75ed2bf30', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/completed-proof-snapshot-catalog-02/test_catalog.py': '5d32ca0f19ff7aa2a4d720a24a59071a1dd882d5e99adf2958e2a19ac3c22f41', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/completed-proof-snapshot-catalog-02/test_failed_catalog.py': '18cf310a04d07b3282b48b81ec07b31f5e0f331f17555f867cd17ca6c06cd581', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/completed-proof-snapshot-catalog-02/README.md': '4edd7e7a6a643029bc39247767d3c1d2eceabef86a11f1122eddf80122baf16e', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/hir-options-hash-driver-stage-03/plan_reference.py': '3a620730fa0de469f85ca2e6336534b594249cc67a8363b2334a0d6748b767fe', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/hir-options-hash-driver-stage-03/test_plan_reference.py': '7d4742520627ae1de3eea2315cbd57dfdc935faafea7861e2b43159ceb4ff887', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/completed-proof-snapshot-catalog-controls-01/inputs.json': 'a7d63a7514ad0af7b46557a7e4cceff7c266077cdab4c311b7d061f66e6360dd', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/completed-proof-snapshot-catalog-controls-independent-verification-01.json': 'aab6a8376e93f8abb181950236afb95eb5fa6c89c5c68df6a2e95fabf6d122bd'}
def validate_sources():
 for name,digest in EXPECTED.items(): assert sha(H/name)==digest
 for path,digest in TESTED.items(): assert sha(Path(path))==digest
assert Path.cwd() == O and sys.dont_write_bytecode and not sys.flags.optimize
assert Path(sys.executable).resolve() == P
assert not E.exists() and not E.is_symlink()
assert not any((H/name).exists() for name in ['inputs.json','launch.json'])
validate_sources()
owned_path = X/'experiments/stable-cgu/owned_stage.py'
old_freeze = json.loads((ROOT/'experiments/frozen-file-table-delta-controls-01/inputs.json').read_bytes())
assert sha(owned_path) == old_freeze['files'][str(owned_path)]['sha256']
spec = importlib.util.spec_from_file_location('hash_continuation70_prepare_owned', owned_path)
owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
E.mkdir(mode=0o700); (E/'source').mkdir(mode=0o700)
for name in EXPECTED: (E/'source'/name).write_bytes((H/name).read_bytes())
(E/'source'/'execution.py').write_bytes(Path(__file__).read_bytes())
(E/'source'/'owned_stage.py').write_bytes(owned_path.read_bytes())
env = dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR=str(O/'.work/hash-continuation-controls-01/tmp'))
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
   r.update(status='running',pid=child.pid,child_started_at=time.time()); save()
   deadline=time.monotonic()+120
   while True:
    try:
     code=child.wait(timeout=min(1,max(.001,deadline-time.monotonic()))); break
    except subprocess.TimeoutExpired:
     free=shutil.disk_usage(O).free
     r['disk_samples'].append(dict(time=time.time(),free_bytes=free)); save()
     if time.monotonic()>=deadline:
      r.update(status='unresolved-live-child-not-signaled',observation_finished_at=time.time()); save(); raise
  r.update(status='finished',returncode=code,finished_at=time.time(),stdout_sha256=sha(E/'stdout'),stderr_sha256=sha(E/'stderr'),free_bytes_after=shutil.disk_usage(O).free); save()
  assert code==0 and not (E/'stderr').read_bytes()
  assert r['free_bytes_after']>=9*2**30 and all(row['free_bytes']>=9*2**30 for row in r['disk_samples'])
  for name,digest in EXPECTED.items(): assert sha(H/name)==digest
  r['prepared_packet']=json.loads((E/'stdout').read_bytes()); save()
 r['canonical_released_at']=time.time(); save()
 print(json.dumps(r,sort_keys=True))
except BaseException as error:
 r['execution_error']=repr(error); save(); raise
