"""One authorized bounded read-only packet preparation; no test or provider calls."""
import hashlib, importlib.util, json, os, resource, shutil, subprocess, sys, time
from pathlib import Path
O = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
H = O/'experiments/hir-options-hash-runtime-audit-controls-04'
E = O/'.work/hir-options-hash-runtime-audit-controls-preparation-execution-04'
P = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
EXPECTED = {'run.py': '3c2580c41d9d0bdaab12b7c52f5cb358e4414cd3ad6912a464f69979d2199f32', 'child.py': '9a33b72671600138fb5cc5f8de70cd6b2a2e81cc156f7284e9fafa341eecd2dd', 'prepare.py': 'f1b1bbdb7b0e9a946eb37841869b9782d5d49329f128528504546a5218b6644a'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
TESTED = {'recipe.py': '9e93f91eb680e2dc1c0a134262e3d729897044c7adc31d7b58b11cc77c896a70', 'preflight.py': '6c713f48da1ea9a4b5cecddebab320a9e4f759aa9bdaa9014ee1784777e37024', 'final_runtime.py': '8ef23fd220b7f5a9cacce91c264ae697c26cd8ef9c968335a477e7e5bc1fe521', 'reader.py': 'da1f151cdc6defaad5b572dc87c3e770b057322b7f2789140b160fb755a07e2c', 'test_recipe.py': '68fe8cc81a075a7eee2446a0e0b43fb87d154862a7c14c62ddaf0e4de7f15cdb', 'test_preflight.py': '520b9d31c021f8580fef78cf452dbe227bd8547d946d73eae128b2038b8a36a7', 'test_final_runtime.py': '00cb032a4eb3182aa85e83c6f4830f25c6fcbec2a667cfed8313188d11a44cea', 'README.md': '59338e66c75d1ad93494a74fcdbbec1b2035f2b91d87d4827289ae04c013cd49'}
def validate_sources():
 for name,digest in EXPECTED.items(): assert sha(H/name)==digest
 for name,digest in TESTED.items(): assert sha(O/'experiments/hir-options-hash-runtime-audit-04'/name)==digest
assert Path.cwd() == O and sys.dont_write_bytecode and not sys.flags.optimize
assert Path(sys.executable).resolve() == P
assert not E.exists() and not E.is_symlink()
assert not any((H/name).exists() for name in ['inputs.json','launch.json'])
validate_sources()
owned_path = X/'experiments/stable-cgu/owned_stage.py'
old_freeze = json.loads((ROOT/'experiments/frozen-file-table-delta-controls-04/inputs.json').read_bytes())
assert sha(owned_path) == old_freeze['files'][str(owned_path)]['sha256']
spec = importlib.util.spec_from_file_location('runtime45_prepare_owned', owned_path)
owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
E.mkdir(mode=0o700); (E/'source').mkdir(mode=0o700)
for name in EXPECTED: (E/'source'/name).write_bytes((H/name).read_bytes())
(E/'source'/'execution.py').write_bytes(Path(__file__).read_bytes())
(E/'source'/'owned_stage.py').write_bytes(owned_path.read_bytes())
env = dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR=str(O/'.work/hir-options-hash-runtime-audit-controls-04/tmp'))
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
