import hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
LAUNCH=ROOT/'experiments/hir-options-hash-beta-retention-02/launch.json'
EXPECTED='3be7abd5605521640d84277be2c742f75993e796b9cac00866a94b487de4ff42'
assert hashlib.sha256(LAUNCH.read_bytes()).hexdigest()==EXPECTED
plan=json.loads(LAUNCH.read_bytes())
assert hashlib.sha256((LAUNCH.parent/'inputs.json').read_bytes()).hexdigest()==plan['inputs_sha256']
assert hashlib.sha256((LAUNCH.parent/'retain.py').read_bytes()).hexdigest()==plan['helper_sha256']
WORK=ROOT/'.work/beta-producer-retention-launch-execution-02';WORK.mkdir()
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
