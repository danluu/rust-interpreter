"""Independent full closed-history archive readback, run only after actual retention."""
import gzip,hashlib,importlib.util,json,stat,sys,time,tarfile
from pathlib import Path
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
D=A/'experiments/beta-composition08-retention-01';W=A/'.work/beta-composition08-retention-01'
O=A/'.work/experiments/beta-composition08-retention-supervisor-01';L=A/'.work/beta-composition08-retention-launch-execution-01'
RESULT=A/'results/hir-options-hash-beta-composition-08';OUT=A/'.work/beta-composition08-retention-independent-verification-01.json'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):
 with Path(p).open('rb') as s:return hashlib.file_digest(s,'sha256').hexdigest()
def stamp(p):
 s=Path(p).lstat();return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]
def check(p,r):
 p=Path(p);before=stamp(p)
 assert p.resolve(strict=True)==p and stat.S_ISREG(before[2]) and before==r['stamp'] and before[3]==r['bytes']
 assert sha(p)==r['sha256'] and stamp(p)==before
assert not OUT.exists()
assert sha(D/'launch.json')=='acc9ce1365d583512f9c43ac472b73de65634572fb26ce19ec787dd24af289ce'
assert sha(D/'inputs.json')=='00479a33411160d5e7a50cbf1495062e5b4c231da8062df05d5ba8e3236bb1aa'
f,launch,r,o,l=[read(p) for p in [D/'inputs.json',D/'launch.json',W/'receipt.json',O/'status.json',L/'record.json']]
assert l['status']=='finished' and l['returncode']==0 and l['command']==launch['command'] and l['environment']==launch['environment'] and l['cwd']==str(A)
assert l['launch_sha256']==sha(D/'launch.json') and sha(l['launcher_source_path'])==l['launcher_source_sha256']
for name in ['stdout','stderr']:assert l[name+'_sha256']==sha(L/name)
hand=read(L/'stdout');assert hand['supervisor_pid']==o['supervisor_pid'] and hand['directory']==str(O)
assert o['status']=='finished' and o['returncode']==0 and o['command']==launch['command'][6:] and o['cwd']==str(A)
assert o['plan_sha256']==sha(O/'plan.json') and o['log_sha256']==sha(O/'command.log')
assert r['status']=='passed' and r['pid']==o['child_pid'] and r['parent_pid']==o['supervisor_pid']
assert r['inputs_sha256']==launch['inputs_sha256']==sha(D/'inputs.json')
assert o['child_started_at']<=r['started_at']<=r['admitted_at']<=r['finished_at']<=o['finished_at']
assert all(r[k]==0 for k in ['workload_children','compiler_calls','B3_compositions'])
assert r['free_bytes_before']>=9*2**30+416*2**20 and r['free_bytes_after']>=9*2**30
for path,row in f['files'].items():check(path,row)
for path,resolved in f['routes'].items():assert str(Path(path).resolve(strict=True))==resolved
for path in f['absent_paths']:assert not Path(path).exists() and not Path(path).is_symlink()
for path,row in f['directories'].items():
 root=Path(path);assert root.resolve(strict=True)==root
 found=[]
 for p in root.rglob('*'):
  assert not p.is_symlink() and (p.is_file() or p.is_dir())
  if p.is_file() and str(p) not in row['excluded_future_outputs']:found.append(str(p))
 assert sorted(found)==row['members']
spec=importlib.util.spec_from_file_location('closed_beta_history_audit',D/'history.py');history=importlib.util.module_from_spec(spec);sys.modules[spec.name]=history;spec.loader.exec_module(history)
assert history.validate_all()==f['history']
summary,manifest=read(RESULT/'summary.json'),read(RESULT/'manifest.json')
assert summary['status']=='passed' and summary['history']==f['history'] and summary['inputs_sha256']==sha(D/'inputs.json')
assert summary['manifest_sha256']==sha(RESULT/'manifest.json') and r['summary_sha256']==sha(RESULT/'summary.json')
assert r['archive']==summary['archive'] and sha(RESULT/'evidence.tar.gz')==summary['archive']['sha256']
assert (RESULT/'evidence.tar.gz').stat().st_size==summary['archive']['bytes']<=192*2**20
expected={p.lstrip('/'):f['files'][p] for p in f['archive_sources']}
expected[str(D/'inputs.json').lstrip('/')]=dict(bytes=(D/'inputs.json').stat().st_size,sha256=sha(D/'inputs.json'))
assert set(expected)==set(manifest) and len(expected)==summary['archive']['logical_members']==428
seen=set();physical=0;logical=0
with tarfile.open(RESULT/'evidence.tar.gz','r:gz') as tar:
 for member in tar:
  assert member.name in manifest and member.name not in seen
  row=manifest[member.name];want=expected[member.name]
  assert row['source']=='/'+member.name and row['sha256']==want['sha256'] and row['bytes']==want['bytes']
  if 'linkname' in row:assert member.islnk() and member.linkname==row['linkname'] and member.linkname in seen and member.size==0
  else:assert member.isfile() and member.size==row['bytes'];physical+=1
  count=0;h=hashlib.sha256()
  with tar.extractfile(member) as s:
   while b:=s.read(2**20):count+=len(b);h.update(b);assert count<=64*2**20
  assert count==row['bytes'] and h.hexdigest()==row['sha256'];logical+=count;seen.add(member.name)
assert seen==set(expected) and physical==summary['archive']['physical_members']
expanded=0
with gzip.open(RESULT/'evidence.tar.gz','rb') as s:
 while b:=s.read(2**20):expanded+=len(b);assert expanded<=416*2**20
assert expanded==summary['archive']['expanded_bytes'] and summary['archive']['full_member_hashes_verified'] and summary['archive']['full_gzip_eof_crc_verified']
for path,row in f['files'].items():check(path,row)
proof=dict(status='verified',finished_at=time.time(),receipt_sha256=sha(W/'receipt.json'),summary_sha256=sha(RESULT/'summary.json'),manifest_sha256=sha(RESULT/'manifest.json'),archive_sha256=sha(RESULT/'evidence.tar.gz'),logical_members=len(expected),physical_members=physical,logical_bytes=logical,expanded_bytes=expanded,full_gzip_eof_crc=True,full_member_readback=True,history=f['history'],retention_workload_children=0,inputs=len(f['files']),verifier_sha256=sha(Path(__file__).resolve()))
with OUT.open('x') as s:json.dump(proof,s,sort_keys=True,indent=2);s.write('\n')
print(json.dumps(dict(path=str(OUT),sha256=sha(OUT),logical_members=len(expected),physical_members=physical)))
