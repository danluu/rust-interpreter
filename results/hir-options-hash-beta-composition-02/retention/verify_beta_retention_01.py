import gzip,hashlib,json,stat,tarfile,time
from pathlib import Path
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
H=A/'experiments/hir-options-hash-beta-retention-01';W=A/'.work/hir-options-hash-beta-retention-01';R=A/'results/hir-options-hash-beta-composition-02'
O=A/'.work/experiments/hir-options-hash-beta-retention-supervisor-01';L=A/'.work/beta-retention-launch-execution-01'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp(p):
 s=p.lstat();return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]
f=read(H/'inputs.json');launch=read(H/'launch.json');outer=read(L/'record.json');saved=read(L/'stdout');status=read(O/'status.json');plan=read(O/'plan.json');terminal=read(W/'receipt.json');m=read(R/'manifest.json')
assert sha(H/'launch.json')==outer['launch_sha256']=='23e13ad8423bfe5b36915e6f48dd8ec2a69382d80059a5a3148d9997988f46bf'
assert sha(H/'inputs.json')==launch['inputs_sha256']==terminal['inputs_sha256']=='87a4e1683479aa277985aa83874007de19037bba6bc4a9b92baa73ab2b846992'
assert sha(Path(outer['launcher_source_path']))==outer['launcher_source_sha256']
assert outer['status']=='finished' and outer['returncode']==0 and outer['command']==launch['command'] and outer['cwd']==launch['owner']==str(A) and outer['environment']==launch['environment']==f['environment']
assert sha(L/'stdout')==outer['stdout_sha256'] and sha(L/'stderr')==outer['stderr_sha256'] and not (L/'stderr').read_bytes()
assert saved['supervisor_pid']==status['supervisor_pid'] and saved['directory']==str(O)
line=saved['identity'].splitlines()[1].split();assert list(map(int,line[:2]))==[status['supervisor_pid'],outer['pid']]
assert status['status']=='finished' and status['returncode']==0 and status['owner']==status['cwd']==str(A)
assert sha(O/'plan.json')==status['plan_sha256'] and sha(O/'command.log')==status['log_sha256']
assert plan['command']==status['command']==launch['command'][launch['command'].index('--')+1:] and plan['owner']==str(A)
assert sha(A/'scripts/supervise_experiment.py')==plan['supervisor_sha256']
assert terminal['status']=='passed' and terminal['workload_children']==terminal['compiler_calls']==0 and not terminal['benchmark']
assert status['child_pid']==terminal['pid'] and status['supervisor_pid']==terminal['parent_pid']
assert outer['started_at']<=status['started_at']<=status['child_started_at']<=terminal['started_at']<=terminal['admitted_at']<=terminal['finished_at']<=status['finished_at']
for name,row in f['files'].items():
 p=Path(name);assert p.resolve(strict=True)==p and stat.S_ISREG(p.lstat().st_mode) and stamp(p)==row['stamp'] and sha(p)==row['sha256'] and stamp(p)==row['stamp'],name
for name,resolved in f['routes'].items():assert str(Path(name).resolve(strict=True))==resolved,name
for name,members in f['membership'].items():
 root=Path(name);actual=[]
 for p in root.rglob('*'):
  assert not p.is_symlink()
  if p.is_file():actual.append(str(p.relative_to(root)))
  else:assert p.is_dir()
 assert sorted(actual)==members,name
assert sha(R/'evidence.tar.gz')==m['archive_sha256']==terminal['archive_sha256']
assert sha(R/'manifest.json')==terminal['manifest_sha256']
expected_sources=set(f['archive_sources'])|{str(H/'inputs.json')}
assert {v['source'] for v in m['members'].values()}==expected_sources
assert m['logical_members']==len(m['members'])==82 and m['physical_members']==74
seen=set(); physical=logical=0
with tarfile.open(R/'evidence.tar.gz','r:gz') as t:
 entries=t.getmembers();assert len(entries)==len(m['members'])
 for e in entries:
  assert e.name not in seen and e.name in m['members'];r=m['members'][e.name]
  if e.islnk():assert e.linkname==r['linkname'] and e.linkname in seen and e.size==0
  else:assert e.isfile() and e.size==r['size'] and 'linkname' not in r;physical+=1
  h=hashlib.sha256();size=0
  with t.extractfile(e) as inp:
   while b:=inp.read(1024*1024):h.update(b);size+=len(b)
  assert size==r['size'] and h.hexdigest()==r['sha256']==sha(Path(r['source']))
  logical+=size;seen.add(e.name)
assert physical==m['physical_members'] and logical==m['logical_file_bytes']
expanded=0
with gzip.open(R/'evidence.tar.gz','rb') as stream:
 while b:=stream.read(1024*1024):expanded+=len(b)
assert expanded==m['gzip_expanded_bytes'] and m['gzip_full_eof_crc_verified']
report=dict(status='verified',receipt_sha256=sha(W/'receipt.json'),archive_sha256=sha(R/'evidence.tar.gz'),manifest_sha256=sha(R/'manifest.json'),inputs=len(f['files']),logical_members=len(seen),physical_members=physical,logical_bytes=logical,expanded_bytes=expanded,full_gzip_eof_crc=True,outer_process_raw_association=True,workload_children=0,controls_retained=49,verifier_sha256=sha(Path(__file__)),finished_at=time.time())
out=A/'.work/beta-retention-independent-verification-01.json';assert not out.exists();out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(report))
