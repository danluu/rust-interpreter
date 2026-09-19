import hashlib,json,os,subprocess,time,shutil
from pathlib import Path
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
LAUNCH=ROOT/'experiments/hir-options-hash-prerequisite-controls-02/launch.json'
EXPECTED='14d79b37f5ef7f36d68e4cc3ec92ba89ead79ab94b8978fecb09df1660610f61'
assert hashlib.sha256(LAUNCH.read_bytes()).hexdigest()==EXPECTED
plan=json.loads(LAUNCH.read_bytes())
assert hashlib.sha256((LAUNCH.parent/'inputs.json').read_bytes()).hexdigest()==plan['inputs_sha256']
assert hashlib.sha256((LAUNCH.parent/'run.py').read_bytes()).hexdigest()==plan['helper_sha256']
assert Path.cwd()==ROOT and shutil.disk_usage(ROOT).free>=16*2**30
WORK=ROOT/'.work/hir-options-hash-prerequisite-controls-launch-execution-02';WORK.mkdir()
def identity(pid):
 return dict(ps=subprocess.run(['/bin/ps','-p',str(pid),'-o','pid=,ppid=,pgid=,lstart=,tty=,command='],capture_output=True,text=True).stdout,
 cwd=subprocess.run(['/usr/sbin/lsof','-a','-p',str(pid),'-d','cwd','-Fn'],capture_output=True,text=True).stdout)
record=dict(launcher_source_path=str(Path(__file__).resolve()),launcher_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),status='starting',launch_path=str(LAUNCH),launch_sha256=EXPECTED,launcher_pid=os.getpid(),launcher_parent_pid=os.getppid(),launcher_identity=identity(os.getpid()),started_at=time.time(),command=plan['command'],cwd=plan['owner'],environment=plan['environment'])
def write():
 temp=WORK/'record.staged';temp.write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');temp.replace(WORK/'record.json')
write()
with (WORK/'stdout').open('xb') as stdout,(WORK/'stderr').open('xb') as stderr:
 child=subprocess.Popen(plan['command'],cwd=plan['owner'],env=plan['environment'],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
 try:
  record.update(status='running',pid=child.pid,child_identity=identity(child.pid));write()
 finally:
  code=child.wait();record.update(status='finished',returncode=code,finished_at=time.time(),stdout_sha256=hashlib.sha256((WORK/'stdout').read_bytes()).hexdigest(),stderr_sha256=hashlib.sha256((WORK/'stderr').read_bytes()).hexdigest());write()
print(json.dumps(dict(path=str(WORK/'record.json'),returncode=code,launcher_pid=os.getpid(),pid=child.pid)))
assert code==0
# Wrapper completion is distinct from the detached supervisor's terminal.
outer=ROOT/'.work/experiments/hir-options-hash-prerequisite-controls-supervisor-02/status.json'
deadline=time.monotonic()+900
while time.monotonic()<deadline:
 if outer.exists():
  terminal=json.loads(outer.read_bytes())
  if terminal['status']=='finished':
   print(json.dumps(dict(outer_status=terminal['status'],outer_returncode=terminal['returncode'],outer_finished_at=terminal['finished_at'])))
   assert terminal['returncode']==0
   break
 time.sleep(2)
else:raise RuntimeError('outer terminal unobserved within finite wait; no signal or retry')
