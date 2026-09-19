"""One exact approved evidence-only archive launch, with explicit launcher and terminal waits."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
O=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913');H=O/'experiments/old-compiler-published-retirement-evidence-01'
P=O/'.work/old-compiler-published-retirement-evidence-launch-01'
def sha(p):
 with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
assert sha(H/'launch.json')=='290f6aab9cb41f4222eb174a3cb78d19f49ee10755916a4fb7fdf0ed3d29489b'
assert sha(H/'inputs.json')=='824d1377e3b0cabf2f9beea39852aa98ef7c561caa8fffa92bd759dade3a0c95'
launch=read(H/'launch.json')
assert launch['command'][3]=='--run-id'
E=O/'.work/experiments'/launch['command'][4]
for name,row in read(H/'inputs.json')['files'].items():
 p=Path(name);s=p.lstat();assert p.resolve()==p and {k:getattr(s,'st_'+k) for k in ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']}==row['identity'] and sha(p)==row['sha256']
plan=read(H/'plan.json');executor=plan['executor'];route=Path(executor['path']);s=route.lstat()
assert str(route.resolve(strict=True))==executor['resolved'] and {k:getattr(s,'st_'+k) for k in ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']}==executor['route_identity']
assert [v for i,v in enumerate(os.uname()) if i!=1]==plan['platform_identity']
assert plan['reservation_bytes']==128*2**20 and plan['entry_free_bytes']==9*2**30+plan['reservation_bytes']
assert shutil.disk_usage(O).free>=plan['entry_free_bytes']
assert sha(O/'.work/e48-retention-packet-independent-review-01.json')=='efd49e358f55c00fce05b9e89a23c5f4be14938752f426c75470a67e38a249d8'
for p in [E,O/'.work/old-compiler-published-retirement-evidence-01']:
 assert not p.exists() and not p.is_symlink()
record=dict(status='starting',command=launch['command'],cwd=launch['cwd'],environment=launch['environment'],pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),launch_sha256=sha(H/'launch.json'),launcher_sha256=sha(Path(__file__)))
actual=Path(str(P)+'.actual.json');assert not actual.exists()
def save():
 tmp=Path(str(actual)+'.tmp')
 with tmp.open('w') as out:json.dump(record,out,indent=2,sort_keys=True);out.write('\n');out.flush();os.fsync(out.fileno())
 tmp.replace(actual)
save()
with Path(str(P)+'.stdout').open('xb') as out,Path(str(P)+'.stderr').open('xb') as err:
 child=subprocess.Popen(launch['command'],cwd=launch['cwd'],env=launch['environment'],stdout=out,stderr=err)
 record['launcher_child_pid']=child.pid
 try:save()
 finally:
  try:code=child.wait(timeout=30)
  except subprocess.TimeoutExpired:
   record.update(status='wrapper-wait-expired-task-not-signaled',wrapper_may_be_live=True,finished_at=time.time());save();raise
record.update(status='launcher-finished',launcher_returncode=code,launcher_finished_at=time.time(),stdout_sha256=sha(Path(str(P)+'.stdout')),stderr_sha256=sha(Path(str(P)+'.stderr')));save();assert code==0
handoff=read(Path(str(P)+'.stdout'));assert handoff['directory']==str(E) and type(handoff['supervisor_pid']) is int
end=time.monotonic()+900
while time.monotonic()<end:
 if (E/'status.json').exists():
  state=read(E/'status.json');assert state['supervisor_pid']==handoff['supervisor_pid'] and state['command']==launch['command'][6:] and state['cwd']==str(O)
  if state['status'] in ['finished','supervisor failed']:
   record.update(status='terminal-observed',terminal_observed_at=time.time(),outer_sha256=sha(E/'status.json'),outer_status=state['status'],outer_returncode=state.get('returncode'));save();print(json.dumps(record,indent=2));assert state['status']=='finished' and state['returncode']==0;break
 time.sleep(1)
else:
 record.update(status='terminal-wait-bound-exhausted',finished_at=time.time());save();raise RuntimeError('preserved live/unresolved supervisor; no signaling')
