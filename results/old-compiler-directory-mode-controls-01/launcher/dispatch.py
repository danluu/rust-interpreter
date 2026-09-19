"""One exact approved pure-control launch, with explicit launcher and terminal waits."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918');H=O/'experiments/old-compiler-directory-mode-controls-01'
P=O/'.work/old-compiler-directory-mode-controls-launch-01'
def sha(p):
 with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
assert sha(H/'launch.json')=='f0a736eaf855990597c3023034c6d976ccae3f644b48d381bb985922898dcae1'
assert sha(H/'inputs.json')=='d86fd34c8b543160af801fd378c789b5eb0ad43e3cfe22469f4ed015279da9d6'
launch=read(H/'launch.json')
assert launch['command'][3]=='--run-id'
E=O/'.work/experiments'/launch['command'][4]
for name,row in read(H/'inputs.json')['files'].items():
 p=Path(name);s=p.lstat();assert p.resolve()==p and [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]==row['stamp'] and sha(p)==row['sha256']
for name,resolved in read(H/'inputs.json')['routes'].items():assert str(Path(name).resolve(strict=True))==resolved
assert shutil.disk_usage(O).free>=16*2**30
for p in [E,O/'.work/old-compiler-directory-mode-controls-01']:
 assert not p.exists() and not p.is_symlink()
record=dict(status='starting',command=launch['command'],cwd=launch['owner'],environment=launch['environment'],pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),launch_sha256=sha(H/'launch.json'),launcher_sha256=sha(Path(__file__)))
actual=Path(str(P)+'.actual.json');assert not actual.exists()
def save():
 tmp=Path(str(actual)+'.tmp')
 with tmp.open('w') as out:json.dump(record,out,indent=2,sort_keys=True);out.write('\n');out.flush();os.fsync(out.fileno())
 tmp.replace(actual)
save()
with Path(str(P)+'.stdout').open('xb') as out,Path(str(P)+'.stderr').open('xb') as err:
 child=subprocess.Popen(launch['command'],cwd=launch['owner'],env=launch['environment'],stdout=out,stderr=err)
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
