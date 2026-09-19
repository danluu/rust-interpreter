"""Independent full saved archive/actual evidence audit, no workloads."""
import gzip,hashlib,json,os,stat,tarfile,time
from pathlib import Path
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
W=X/'.work/hir-options-build-evidence-retention-02'
O=X/'.work/experiments/hir-options-build-evidence-supervisor-02'
R=X/'results/hir-options-hash-build-02'
F=X/'.work/hir-options-build-evidence-inputs-02.json'
L=X/'.work/hir-options-build-evidence-launch-02.json'
def read(p):return json.loads(p.read_bytes())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def stamp(p):
 s=p.lstat();return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]
f=read(F);l=read(L);r=read(W/'receipt.json');outer=read(O/'status.json');plan=read(O/'plan.json');m=read(R/'manifest.json')
a=read(X/'.work/hir-options-build-evidence-launch-02.actual.json')
assert sha(L)=='29bdb336a4ced1b03e4661b7157b353de768d6beb4b550f6ea26fa9293beafe5' and sha(F)==l['inputs_sha256']==r['inputs_sha256']
assert a['launch']==str(L) and a['launch_sha256']==sha(L) and a['command']==l['command'] and a['environment']==l['environment'] and a['cwd']==str(X)
assert not Path(a['stderr']).read_bytes()
announcement=read(Path(a['stdout']));assert announcement['directory']==str(O) and announcement['supervisor_pid']==outer['supervisor_pid']
assert announcement['identity'].splitlines()[1].split()[:2]==[str(outer['supervisor_pid']),str(a['supervisor_launcher_pid'])]
assert r['status']=='passed' and all(r[k]==0 for k in ['compiler_builds','metadata_probes_rerun','tests_rerun'])
assert outer['status']=='finished' and outer['returncode']==0 and outer['child_pid']==r['pid'] and outer['supervisor_pid']==r['parent_pid']
assert outer['command']==plan['command']==l['command'][l['command'].index('--')+1:] and outer['cwd']==plan['owner']==str(X)
assert sha(O/'plan.json')==outer['plan_sha256'] and sha(O/'command.log')==outer['log_sha256']
assert a['started_at']<=outer['started_at']<=r['started_at']<=r['admitted_at']<=r['finished_at']<=outer['finished_at']
assert r['free_bytes_before']>=9*2**30+192*2**20 and r['free_bytes_after']>=9*2**30
assert sha(R/'manifest.json')==r['manifest_sha256'] and sha(R/'evidence.tar.gz')==r['archive_sha256']==m['archive_sha256']
assert (R/'evidence.tar.gz').stat().st_size==r['archive_bytes']==m['archive_bytes']<=128*2**20
assert m['metadata_qualified'] and m['compiler_build_complete'] and not any(m[k] for k in ['compiler_qualified','native_recipe_qualified','hash_driver_qualified','application_qualified','performance_target_met','actual_workloads_rerun'])
assert m['metadata_failure_preserved'] and m['compiler_build_failure_preserved']
assert [x['children'] for x in m['stages']]==[16,1,7,1,3]
assert [x['status'] for x in m['stages']]==['failed','passed','failed','passed','passed']
for wanted,actual in zip(f['stages'],m['stages'],strict=True):
 assert wanted['kind']==actual['kind'] and wanted['children']==actual['children'] and wanted['status']==actual['status']
 assert sha(Path(wanted['work'])/'receipt.json')==actual['receipt_sha256']
expected={name.lstrip('/'):dict(source=name,sha256=row['sha256'],bytes=row['bytes']) for name,row in f['files'].items()}
expected[str(F).lstrip('/')]=dict(source=str(F),sha256=sha(F),bytes=F.stat().st_size)
assert expected==m['files'] and len(expected)==r['logical_members']==427
seen=set();physical=0;logical_bytes=0
with tarfile.open(R/'evidence.tar.gz','r:gz') as tar:
 for item in tar:
  assert item.name in expected and item.name not in seen and (item.isfile() or item.islnk())
  if item.islnk():assert item.linkname in seen
  else:physical+=1
  data=tar.extractfile(item).read();row=expected[item.name]
  assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
  seen.add(item.name);logical_bytes+=len(data)
assert seen==set(expected) and physical==m['physical_payloads'] and logical_bytes==m['logical_bytes']
expanded=0
with gzip.open(R/'evidence.tar.gz','rb') as fstream:
 while block:=fstream.read(2**20):expanded+=len(block);assert expanded<=288*2**20
assert expanded==m['expanded_bytes']
for name,row in f['files'].items():
 p=Path(name);assert p.resolve(strict=True)==p and stat.S_ISREG(p.lstat().st_mode) and stamp(p)==row['stamp'] and sha(p)==row['sha256'],name
for name,members in f['directories'].items():
 root=Path(name);assert root.resolve(strict=True)==root;actual=[]
 for parent,dirs,names in os.walk(root,followlinks=False):
  for name in dirs+names:
   p=Path(parent)/name;assert not p.is_symlink()
   if p.is_file():actual.append(str(p))
   else:assert p.is_dir()
 assert sorted(actual)==members
for name in f['absent_paths']:assert not Path(name).exists() and not Path(name).is_symlink()
prior=f['prior_archive'];assert sha(Path(prior['path']))==prior['sha256'] and stamp(Path(prior['path']))==prior['stamp']
report=dict(status='verified',time=time.time(),script_sha256=sha(Path(__file__)),terminal_sha256=sha(W/'receipt.json'),archive_sha256=sha(R/'evidence.tar.gz'),manifest_sha256=sha(R/'manifest.json'),logical_members=len(seen),physical_payloads=physical,logical_bytes=logical_bytes,expanded_bytes=expanded,full_tar_member_hashes=True,gzip_full_eof_crc=True,all_live_source_hashes_rechecked=True,actual_children_retained=28,actual_compiler_stage_children=26,successful_logical_compiler_stage_children=25,compiler_build_complete=True,compiler_qualified=False,application_qualified=False)
with (R/'verification.json').open('x') as fstream:json.dump(report,fstream,indent=2,sort_keys=True);fstream.write('\n')
with (R/'archive-execution.json').open('x') as fstream:json.dump(dict(terminal=r,supervisor=outer,outer_plan=plan,actual_launcher=a,launch=l,verification=report),fstream,indent=2,sort_keys=True);fstream.write('\n')
print(json.dumps(report,indent=2));print('verification_sha256',sha(R/'verification.json'))
