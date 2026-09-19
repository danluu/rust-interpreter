"""One exact reviewed evidence-only archive launch, with explicit launcher wait."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
L=X/'.work/hir-options-build-evidence-launch-02.json';F=X/'.work/hir-options-build-evidence-inputs-02.json'
P=X/'.work/hir-options-build-evidence-launch-02'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):
 temporary=Path(str(p)+'.tmp')
 with temporary.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(temporary,p)
assert Path.cwd()==X
assert sha(L)=='29bdb336a4ced1b03e4661b7157b353de768d6beb4b550f6ea26fa9293beafe5'
assert sha(F)=='85c84f5a16adb3ab2bf9c4fa346a7bcb77f1b5cdd3035425dd42e660342995ff'
l=json.loads(L.read_bytes());f=json.loads(F.read_bytes())
for name,row in f['files'].items():
 p=Path(name);s=p.lstat();assert [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]==row['stamp'] and sha(p)==row['sha256'],name
free=shutil.disk_usage(X).free;assert free>=9*2**30+192*2**20
for p in [X/'.work/hir-options-build-evidence-retention-02',X/'.work/experiments/hir-options-build-evidence-supervisor-02',X/'results/hir-options-hash-build-02',*[Path(str(P)+s) for s in ['.actual.json','.stdout','.stderr']]]:assert not p.exists() and not p.is_symlink()
a=dict(status='starting',launch=str(L),launch_sha256=sha(L),command=l['command'],environment=l['environment'],cwd=str(X),launcher_pid=os.getpid(),started_at=time.time(),stdout=str(P)+'.stdout',stderr=str(P)+'.stderr',prelaunch_free_bytes=free,prelaunch_frozen_files_verified=len(f['files']),dispatcher_sha256=sha(Path(__file__).resolve()))
r=Path(str(P)+'.actual.json')
with r.open('x') as output:json.dump(a,output,indent=2,sort_keys=True);output.write('\n')
with Path(a['stdout']).open('xb') as out,Path(a['stderr']).open('xb') as err:
 child=subprocess.Popen(l['command'],cwd=X,env=l['environment'],stdin=subprocess.DEVNULL,stdout=out,stderr=err)
 a.update(status='launcher-running',supervisor_launcher_pid=child.pid);write(r,a)
 try:a.update(status='launcher-finished',launcher_returncode=child.wait(timeout=30),launcher_finished_at=time.time())
 except subprocess.TimeoutExpired:a.update(status='launcher-wait-expired',launcher_wait_expired_at=time.time())
 finally:write(r,a)
print(json.dumps(a,indent=2))
assert a['status']=='launcher-finished' and a['launcher_returncode']==0
