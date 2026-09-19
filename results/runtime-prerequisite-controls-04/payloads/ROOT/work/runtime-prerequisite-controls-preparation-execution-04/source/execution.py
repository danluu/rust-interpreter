"""One authorized bounded read-only packet preparation; no test or provider calls."""
import hashlib, importlib.util, json, os, resource, shutil, subprocess, sys, time
from pathlib import Path
O = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
H = O/'experiments/runtime-prerequisite-controls-04'
E = O/'.work/runtime-prerequisite-controls-preparation-execution-04'
P = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
EXPECTED = {'run.py': '7da7394b7a542b75ea6630d32ca49eec310954032fa622c7967c9e410ff09af8', 'child.py': '1429c002b12383fd1f43e18179e0f1cc7a1c0f75eea650e4dbdb55bb55994230', 'prepare.py': 'f6734b25b00c2b84ec18ce3fcb0c44afc0ec38fd315475586d06a4387a725f85'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
TESTED = {'prerequisites.py': 'f0bec62bf5526c7ec3b3b28500cb304e98a35e0f89f3b45208b5fb086f0a888e', 'imports.py': '574196f8f73a422b225b73c5bad9b59634e674b7b23b1ee30daca4b830120451', 'copies.py': 'e81fe5230c239d370670af1907743eb2680b40eab0273622a775eb50259938fb', 'entry.py': 'ee8127d53f294b14aa5243c9ff008557ea0a3f148c91a413ab6cafdcb60881b8', 'test_prerequisite_successor.py': '7c90ec9507dba63be3694b1e20b1d3cb03e97ab99a97bd77a0fcd48cb53841ea', 'test_copy_references.py': '0dea2fc636e08932dc606c6531afa1cb1100e77df394f79204124ffec80c8985', 'README.md': '1bdc904b499c0e61235212160c49d297b0d424fca4fda40be290273c7dafe162', 'source-bindings.json': '9947b9cbaa1fbf1634c466abea4841ae25f2f4db567df00306f065d7c01fefcb'}
def validate_sources():
 for name,digest in EXPECTED.items(): assert sha(H/name)==digest
 for name,digest in TESTED.items(): assert sha(X/'experiments/hir-options-hash/runtime-installation-04'/name)==digest
assert Path.cwd() == O and sys.dont_write_bytecode and not sys.flags.optimize
assert Path(sys.executable).resolve() == P
assert not E.exists() and not E.is_symlink()
assert not any((H/name).exists() for name in ['inputs.json','launch.json'])
validate_sources()
owned_path = X/'experiments/stable-cgu/owned_stage.py'
old_freeze = json.loads((ROOT/'experiments/retained-proof-copy-controls-01/inputs.json').read_bytes())
assert sha(owned_path) == old_freeze['files'][str(owned_path)]['sha256']
spec = importlib.util.spec_from_file_location('runtime52_prepare_owned', owned_path)
owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
E.mkdir(mode=0o700); (E/'source').mkdir(mode=0o700)
for name in EXPECTED: (E/'source'/name).write_bytes((H/name).read_bytes())
(E/'source'/'execution.py').write_bytes(Path(__file__).read_bytes())
(E/'source'/'owned_stage.py').write_bytes(owned_path.read_bytes())
env = dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR=str(O/'.work/runtime-prerequisite-controls-04/tmp'))
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
