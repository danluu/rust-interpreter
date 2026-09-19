"""Independent read-only review of the prepared, unlaunched hash03 packet.

No controller, constructor, workload, probe, signal or snapshot file is run.
Only pinned saved-evidence verifier definitions are loaded. New gzip descriptors
are checked with an in-memory counting sink; no compressed payload is retained.
"""
import ast, errno, fcntl, gzip, hashlib, json, os, re, resource, shutil, stat, sys, time
from pathlib import Path
from types import ModuleType

O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
H=R/'experiments/hir-options-hash-driver-stage-02'
E=O/'.work/hash-driver-packet-review-execution-04'
OUT=O/'.work/hash-driver-packet-verification-04.json'
PREP=R/'.work/hash-driver-preparation-execution-03'
EXPECTED={
 'launch.json':'e315c703101fb5d8e9f732a10db9b07883792057c0f833b71979cf54efcbfc43',
 'inputs.json':'5accd23a86a3d7df8d19e8e294fcc96a4bc4f707ecd590b999c88ae092ed6dae',
 'plan.json':'8ca27580b2e2435c34123c4eeaa8c7e90f6711871d7cb34e106ed9107ef92c5b',
 'snapshot-plan.json':'3082d235c8ff1c700b5a611aef8a488a4f4297f7607f0b8f37e6afbd22d0d7ad',
 'metadata-preflight.json':'6730faa41b9bbf7f35a328a4bfc16de0a9cf0900a4c0a195fb3325863a59c04f',
 'verify.py':'cbff690675b8697855bb87b0e09d9b77495fc0b8968855301e1a88612ec62a3f'}
PREP_SHA='d0530245c9edeb84309a27258f65d889679f8c38efcb21e2dae5bf6e50c588e9'
AUDITS={
 'compiler':'033ae3c870cf98ed36d0e17d5b02aaabff6f5bbb03353f2454426be3b9f49fc3',
 'beta':'9d23767296bfbf4147d170f8138711effcfda47eb744391edf52253a3da8891d',
 'native':'6e95c8845fd761757d6db80e375673e126208466fa54ed678a32d3a2a036685e',
 'run_make':'31ba70f239c69ecf47d0815c49d2551330ec1cf31019623dc3a6b97f728716c4'}
LIMITS=dict(maximum_files=1024,maximum_file_bytes=64*2**20,maximum_logical_bytes=512*2**20,
 maximum_compressed_bytes=128*2**20,maximum_manifest_bytes=4*2**20)
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
START=time.monotonic();SAMPLES=[];LAST_SAMPLE=0;V=None;READ_BYTES=0

def require(ok,message):
 if not ok:raise RuntimeError(message)
def guard():
 global LAST_SAMPLE
 require(time.monotonic()-START<=1200,'finite read-only audit wall bound')
 if time.monotonic()-LAST_SAMPLE>=1:
  free=shutil.disk_usage(O).free;require(free>=9*2**30,'live9GiB audit floor')
  SAMPLES.append(dict(time=time.time(),free_bytes=free));LAST_SAMPLE=time.monotonic()
def identity(path):
 s=Path(path).lstat();return {k:getattr(s,'st_'+k) for k in FIELDS}
def sha(path):
 global READ_BYTES
 guard();path=Path(path);before=identity(path)
 require(path.resolve(strict=True)==path and stat.S_ISREG(before['mode']) and before['size']<=2**30,'ordinary bounded audit input')
 digest=hashlib.sha256()
 with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
  require({k:getattr(os.fstat(stream.fileno()),'st_'+k) for k in FIELDS}==before,'opened audit input changed')
  while block:=stream.read(2**20):
   guard();READ_BYTES+=len(block);require(READ_BYTES<=24*2**30,'total audit byte-read bound');digest.update(block)
  require({k:getattr(os.fstat(stream.fileno()),'st_'+k) for k in FIELDS}==before,'read audit input changed')
 require(identity(path)==before,'audit input changed');return digest.hexdigest()
def write(path,value):
 data=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode();require(len(data)<=4*2**20,'bounded audit document')
 with Path(path).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
def load_verifier():
 require(sha(H/'verify.py')==EXPECTED['verify.py'],'exact actual22-qualified verifier')
 source=(H/'verify.py').read_bytes();tree=ast.parse(source,filename=str(H/'verify.py'))
 allowed=(ast.Import,ast.ImportFrom,ast.Assign,ast.FunctionDef)
 body=[]
 for node in tree.body:
  if isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):continue
  if isinstance(node,ast.If):
   require(ast.unparse(node.test)=="__name__ == '__main__'",'unexpected top-level verifier branch');continue
  require(isinstance(node,allowed),'unexpected verifier top-level executable')
  if isinstance(node,ast.FunctionDef) and node.name in {'main','import_parsers'}:continue
  body.append(node)
 value=ModuleType('hash_packet03_readonly_verifier');value.__file__=str(H/'verify.py')
 exec(compile(ast.Module(body=body,type_ignores=[]),str(H/'verify.py'),'exec'),value.__dict__)
 original_identity=value.identity
 def checked_identity(path):guard();return original_identity(path)
 value.identity=checked_identity
 def cached_sha(path):
  path=Path(path);before=checked_identity(path);old=value.CHECKED.get(str(path))
  if old is not None and old['identity']==before:return old['sha256']
  digest=sha(path);require(checked_identity(path)==before,'cached audit input changed')
  value.CHECKED[str(path)]=dict(identity=before,sha256=digest);return digest
 value.sha=cached_sha
 return value

def controls(namespace,count,audit_sha,required_sources,number='01'):
 source=R/('experiments/'+namespace+'-'+number);work=R/('.work/'+namespace+'-'+number)
 audit_path=R/('.work/'+namespace+'-independent-verification-'+number+'.json')
 require(V.sha(audit_path)==audit_sha,'pinned independent controls audit')
 inputs=V.read(source/'inputs.json');launch=V.read(source/'launch.json');terminal=V.read(work/'receipt.json')
 result=V.read(work/'result.json');audit=V.read(audit_path);child=V.read(work/'command/receipt.json')
 for name,row in inputs['files'].items():require(V.sha(name)==row['sha256'] and V.stamp(name)==row['stamp'],'complete controls inputs')
 for name,resolved in inputs['routes'].items():require(str(Path(name).resolve(strict=True))==resolved and resolved in inputs['files'],'controls routes')
 for original,current in required_sources:require(inputs['files'][str(original)]['sha256']==V.sha(current),'tested exact production source')
 names=inputs['expected_names'];require(len(names)==len(set(names))==count and sorted(audit['exact_names'])==names==result['expected_names'],'actual test identities')
 require(terminal['status']==result['status']=='passed' and audit['status']=='verified'
  and terminal['controls_passed']==result['tests_run']==audit['controls']==launch['controls']==count
  and terminal['inputs_sha256']==launch['inputs_sha256']==V.sha(source/'inputs.json')
  and terminal['result_sha256']==audit['result_sha256']==V.sha(work/'result.json')
  and audit['receipt_sha256']==V.sha(work/'receipt.json'),'control result/receipt/input associations')
 require(all(type(result[k]) is int and result[k]==0 for k in ['failures','errors','skipped','expected_failures','unexpected_successes','child_processes','compiler_calls']),'all test outcomes zero')
 require(terminal['commands']==[dict(path=str(work/'command/receipt.json'),pid=child['pid'],sha256=V.sha(work/'command/receipt.json'))]
  and child['status']=='finished' and child['returncode']==0 and child['command']==inputs['command']
  and child['environment']==inputs['environment'] and child['supervisor_pid']==terminal['pid']
  and child['parent_pid']==terminal['parent_pid']
  and terminal['admitted_at']<=child['started_at']<=child['finished_at']<=terminal['finished_at'],'actual controls child association')
 for stream in ['stdout','stderr']:require(V.sha(work/'command'/stream)==child[stream+'_sha256']==audit['raw_sha256'][stream],'controls raw')
 stderr=V.raw(work/'command/stderr').decode('utf-8');actual=re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$',stderr,re.M)
 require(not V.raw(work/'command/stdout') and sorted(actual)==names and re.search(r'^Ran '+str(count)+r' tests in [0-9.]+s\n\nOK\n$',stderr,re.M),'raw exact test outcomes')
 return dict(controls=count,audit_sha256=audit_sha,receipt_sha256=V.sha(work/'receipt.json'),result_sha256=V.sha(work/'result.json'))

PRIOR_FAILURE_FILES={'/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/verify_hash_driver_packet_03.py': '6d6d4914d5b1f309fb1873eb1696a7e4d2b958a0fa221913701adb67871e93fa', '/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/execute_hash_driver_packet_review_03.py': '8f93aec4fb11292f3715ca12888dc4a877cd9e7da861ba0a912acd072df93a6a', '/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/hash-driver-packet-review-execution-03/record.json': '5221715bc1ca9af59b12943ac7156ab0234d0786c10dab76f30f7d77e0a6a195', '/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/hash-driver-packet-review-execution-03/stdout': '7733a5872aa8042f67405a205f7915523d44e2a20b1e0c73637f1b3dc8f07fa6', '/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/hash-driver-packet-review-execution-03/stderr': '6682c3b354e4aeab88cc22b8b3fac96092c3b7a013196e0ad2a635717716cc49', '/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/hash-driver-packet-review-execution-03/source/audit.py': '6d6d4914d5b1f309fb1873eb1696a7e4d2b958a0fa221913701adb67871e93fa', '/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/hash-driver-packet-review-execution-03/source/execution.py': '8f93aec4fb11292f3715ca12888dc4a877cd9e7da861ba0a912acd072df93a6a', '/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/hash-driver-packet-review-execution-03/source/owned_stage.py': '7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e', '/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/hash-driver-packet-review-execution-03/source/qualified-verify.py': 'cbff690675b8697855bb87b0e09d9b77495fc0b8968855301e1a88612ec62a3f'}

def previous_audit_failure():
 refs=PRIOR_FAILURE_FILES
 for name,digest in refs.items():require(V.sha(name)==digest,'original failed audit bytes preserved')
 prior=V.read(O/'.work/hash-driver-packet-review-execution-03/record.json')
 raw=V.raw(O/'.work/hash-driver-packet-review-execution-03/stderr').decode('utf-8','strict')
 require(prior['status']=='finished' and prior['returncode']==1 and prior['pid']==88362 and prior['parent_pid']==87637
  and prior['execution_error']=="RuntimeError('actual packet audit failed; preserve evidence')"
  and raw.endswith("RuntimeError: ordinary SDK root\n") and "sdk_inventory(plan['sdk'])" in raw,
  'honest earlier SDK alias audit rejection')
 require(not (O/'.work/hash-driver-packet-verification-03.json').exists(), 'failed audit did not publish qualification')
 return dict(status='retained-failed-audit',files=refs,record_sha256=refs[str(O/'.work/hash-driver-packet-review-execution-03/record.json')],
  error='RuntimeError: ordinary SDK root',workload_children=0,
  correction='Inventory the exact canonical SDK route already pinned in both metadata routes and launch executor routes; preserve the versioned SDKROOT alias.')

def sdk_inventory(root):
 root=Path(root);require(root.resolve(strict=True)==root and root.is_dir(),'ordinary SDK root')
 result={'':dict(kind='directory',stamp=V.stamp(root))}
 for parent,dirs,files in os.walk(root,followlinks=False,onerror=lambda e:(_ for _ in ()).throw(e)):
  guard()
  for name in sorted(dirs+files):
   path=Path(parent)/name;info=path.lstat();key=str(path.relative_to(root));require(len(result)<180000,'finite SDK inventory')
   if stat.S_ISLNK(info.st_mode):
    target=path.resolve(strict=True);require(target.is_relative_to(root),'SDK link escapes')
    row=dict(kind='link',stamp=V.stamp(path),target=os.readlink(path),resolved=str(target))
   elif stat.S_ISREG(info.st_mode):row=dict(kind='file',sha256=V.sha(path),stamp=V.stamp(path))
   else:require(stat.S_ISDIR(info.st_mode),'special SDK entry');row=dict(kind='directory',stamp=V.stamp(path))
   result[key]=row
 return result

def allocation(plan):
 prefixes=('hir-options-hash-compiler-build-','hir-options-hash-beta-composition-',
  'hir-options-hash-native-controls-','hir-options-hash-run-make-','hir-options-hash-driver-')
 owners=(X,A,O,R);roots=list(map(Path,plan['evidence_roots']));found=set()
 require(list(map(str,roots))==sorted(set(map(str,roots))) and V.WORK in roots,'exact explicit aggregate roots')
 for owner in owners:
  for path in (owner/'.work').iterdir():
   if path.name.startswith(prefixes) and (path.is_dir() or path.is_symlink()):
    require(not path.is_symlink(),'candidate evidence symlink');found.add(path)
 require(found<=set(roots),'new unaccounted evidence root')
 samples={}
 for root in [V.N,*roots]:
  guard();require(root==V.N or root.parent in {o/'.work' for o in owners} and root.name.startswith(prefixes),'scoped allocation root')
  require(not root.is_symlink(),'allocation root symlink')
  if not root.exists():require(root==V.WORK,'unexpected missing evidence');samples[str(root)]=dict(bytes=0,absent=True);continue
  require(root.resolve(strict=True)==root and root.is_dir(),'ordinary allocation root')
  seen=set();total=0;entries=0
  def walk(fd):
   nonlocal total,entries
   guard();info=os.fstat(fd);inode=(info.st_dev,info.st_ino)
   if inode not in seen:seen.add(inode);total+=info.st_blocks*512
   with os.scandir(fd) as listing:
    for entry in listing:
     entries+=1;require(entries<=180000,'finite scoped allocation entries');info=entry.stat(follow_symlinks=False)
     require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode),'special allocation entry')
     inode=(info.st_dev,info.st_ino)
     if inode not in seen:seen.add(inode);total+=info.st_blocks*512
     if stat.S_ISDIR(info.st_mode):
      child=os.open(entry.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
      try:
       held=os.fstat(child);require((held.st_dev,held.st_ino,held.st_mode)==(info.st_dev,info.st_ino,info.st_mode),'allocation directory changed');walk(child)
      finally:os.close(child)
  fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
  try:walk(fd)
  finally:os.close(fd)
  samples[str(root)]=dict(bytes=total,entries=entries)
 aggregate=sum(samples[str(root)]['bytes'] for root in roots)
 require(samples[str(V.N)]['bytes']<=14*2**30 and aggregate<=256*2**20,'current namespace/evidence cap')
 return dict(time=time.time(),namespace_bytes=samples[str(V.N)]['bytes'],evidence_bytes=aggregate,roots=samples,
  limitation='Read-only non-atomic allocation sample; concurrent new files/size changes may occur. Any traversal disappearance or observed directory replacement refuses the audit.')

class Sink:
 def __init__(self):self.size=0;self.digest=hashlib.sha256()
 def write(self,data):
  guard();require(self.size+len(data)<=128*2**20,'finite new gzip projection')
  self.size+=len(data);self.digest.update(data);return len(data)
 def flush(self):pass
 def tell(self):return self.size

def projection(freeze,plan,document):
 p=document['projection'];require(document['limits']==p['limits']==LIMITS and p['policy']=='bounded-gzip-proof-snapshots-v2','snapshot policy')
 require(document['helper']==dict(path=str(A/'experiments/bounded-proof-snapshots-v2/proof_snapshots.py'),sha256='f695e2c154a11dec9abbe9e6d2186729ab06c6b5b5c2bd1f10f9009b165c5064'),'exact qualified gzip helper')
 names=freeze['snapshot_inputs'];require(names==sorted(set(names)) and str(H/'inputs.json') not in names,'full unique sorted current snapshot selection')
 files={n:dict(path=n,**freeze['files'][n]) for n in names}
 files[str(H/'inputs.json')]=dict(path=str(H/'inputs.json'),size=(H/'inputs.json').stat().st_size,sha256=EXPECTED['inputs.json'],identity=identity(H/'inputs.json'))
 require(p['files']==files and len(files)<=1024,'full current snapshot logical mapping')
 catalog=V.verify_snapshot_catalog(freeze,plan,LIMITS);sizes={};selected={};inodes=set();roots={}
 for row in files.values():
  require(row['size']<=64*2**20 and (row['sha256'] not in sizes or sizes[row['sha256']]==row['size']),'logical alias bound/size')
  sizes[row['sha256']]=row['size']
 for row in catalog['records']:
  key=row['blob']['logical_sha256']
  if key in sizes and key not in selected:
   inode=(row['identity']['dev'],row['identity']['ino']);require(inode not in inodes and row['blob']['logical_bytes']==sizes[key],'no duplicate reuse credit')
   selected[key]=row;inodes.add(inode);roots[row['evidence_root']]=catalog['evidence_roots'][row['evidence_root']]
 require(document['reuse_selection']==dict(records=[selected[k] for k in sorted(selected)],evidence_roots=roots)
  and p['reuse']==selected and p['evidence_roots']==roots,'complete deterministic old beta-first reuse selection')
 require(set(p['blobs'])==set(sizes) and p['storage']=={k:(dict(kind='reused',path=selected[k]['path']) if k in selected else dict(kind='stored')) for k in sizes},'complete stored/reused groups')
 compressed=allocated=new=new_allocated=0;new_rows=[]
 for key,blob in p['blobs'].items():
  guard();require(set(blob)=={'filename','logical_sha256','logical_bytes','sha256','compressed_bytes'} and blob['filename']==key+'.gz'
   and blob['logical_sha256']==key and blob['logical_bytes']==sizes[key] and type(blob['compressed_bytes']) is int and 0<blob['compressed_bytes']<=128*2**20,'bounded full blob descriptor')
  if key in selected:require(blob==selected[key]['blob'],'reused complete blob binding')
  else:
   row=next(r for r in files.values() if r['sha256']==key);path=Path(row['path']);require(identity(path)==row['identity'],'new selected input identity')
   sink=Sink();logical=hashlib.sha256();size=0
   with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as source:
    require({k:getattr(os.fstat(source.fileno()),'st_'+k) for k in FIELDS}==row['identity'],'opened new source')
    with gzip.GzipFile(filename='',mode='wb',fileobj=sink,mtime=0,compresslevel=6) as stream:
     while block:=source.read(2**20):
      guard();size+=len(block);require(size<=row['size'],'selected input grew');logical.update(block);stream.write(block)
    require({k:getattr(os.fstat(source.fileno()),'st_'+k) for k in FIELDS}==row['identity'],'read new source identity')
   require(identity(path)==row['identity'] and size==row['size'] and logical.hexdigest()==key
    and sink.size==blob['compressed_bytes'] and sink.digest.hexdigest()==blob['sha256'],'independent counted gzip6 projection differs')
   new+=sink.size;new_allocated+=(sink.size+4095)//4096*4096;new_rows.append(dict(logical_sha256=key,path=str(path),compressed_bytes=sink.size))
  compressed+=blob['compressed_bytes'];allocated+=(blob['compressed_bytes']+4095)//4096*4096
 logical=sum(r['size'] for r in files.values());reservation=new_allocated+4096*len(new_rows)+40*2**20
 require(logical==p['logical_bytes']<=512*2**20 and p['unique_logical_bytes']==sum(sizes.values())
  and compressed==p['compressed_bytes']<=128*2**20 and allocated==p['compressed_allocated_bytes']
  and new==p['new_compressed_bytes'] and new_allocated==p['new_compressed_allocated_bytes']
  and compressed-new==p['reused_compressed_bytes'] and p['manifest_reservation_bytes']==8*2**20,'all total/new accounting')
 require(document['remaining_evidence_reservation_bytes']==32*2**20 and document['evidence_cap_bytes']==256*2**20
  and reservation==document['projected_reservation_bytes']==51810304
  and document['measured_existing_evidence_bytes']==215441408
  and document['measured_existing_evidence_bytes']+reservation<=256*2**20,'full physical reservation under unchanged cap')
 return dict(logical_files=len(files),unique_blobs=len(sizes),reused_blobs=len(selected),new_blobs=len(new_rows),logical_bytes=logical,
  compressed_bytes=compressed,new_compressed_bytes=new,new_allocated_bytes=new_allocated,reservation_bytes=reservation,
  preparation_margin_bytes=256*2**20-document['measured_existing_evidence_bytes']-reservation,new_blob_counting_sink=new_rows,
  original_reused_gzip_full_eof_crc=True,all_aliases_retained=True,no_compressed_files_written=True)

def main():
 global V
 require(Path.cwd()==O and sys.dont_write_bytecode and not sys.flags.optimize and not OUT.exists(),'fixed fresh readonly audit')
 resource.setrlimit(resource.RLIMIT_CPU,(900,900));resource.setrlimit(resource.RLIMIT_FSIZE,(4*2**20,4*2**20))
 require(len(sys.argv)==3 and sys.argv[1]=='--canonical-fd' and sys.argv[2].isdigit(),'explicit inherited canonical descriptor')
 fd=int(sys.argv[2]);lock=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock');opened=os.fstat(fd);current=lock.stat()
 require((opened.st_dev,opened.st_ino)==(current.st_dev,current.st_ino) and lock.resolve(strict=True)==lock,'exact canonical descriptor')
 fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with lock.open('r+') as competing:
  try:fcntl.flock(competing,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:pass
  else:raise RuntimeError('inherited canonical lock is not held')
 started=time.time();guard();V=load_verifier();prior_failure=previous_audit_failure()
 for name,digest in EXPECTED.items():require(V.sha(H/name)==digest,'exact prepared '+name)
 require(V.sha(PREP/'record.json')==PREP_SHA,'exact successful preparation record')
 record=V.read(PREP/'record.json');launch=V.read(H/'launch.json');compact=V.read(H/'inputs.json');plan=V.read(H/'plan.json');preflight=V.read(H/'metadata-preflight.json');snapshot=V.read(H/'snapshot-plan.json')
 require(record['status']=='finished' and record['returncode']==0 and record['workload_children']==0 and record['pid']==25516 and record['parent_pid']==24799,'explicit successful zero-workload preparation')
 require(record['cwd']==str(R) and record['entry_free_bytes']>=16*2**30 and record['maximum_observation_seconds']==1800
  and record['started_at']<=preflight['started_at']<=preflight['finished_at']<=record['finished_at'],'actual preparation ownership/time')
 for stream in ['stdout','stderr']:require(V.sha(PREP/stream)==record[stream+'_sha256'],'preparation raw')
 require(not V.raw(PREP/'stderr') and V.read(PREP/'stdout')==dict(status='prepared-unrun',launch_sha256=EXPECTED['launch.json'],inputs_sha256=EXPECTED['inputs.json'],files=109196,bytes=6770927978),'actual prepared output')
 for name,digest in record['sources_sha256'].items():require(V.sha(H/name)==V.sha(PREP/'source'/name)==digest,'actual prepared source copy')
 require(V.sha(record['runner_source'])==record['runner_sha256']=='015e8dfaf25d6c9eefab0ae3253673a07ab0b70d3cac69fb88a235aa56153076','prepared source runner')
 require(V.sha(R/'.work/hash-driver-preparation-predecessors-03.json')=='0fd7de818ec1efa748078c9e9605c7849131a3751280cd2d0ddd7c7dbcc559a4','exact closed prior preparation history')
 predecessors=V.read(R/'.work/hash-driver-preparation-predecessors-03.json')
 previous=predecessors['previous_preparation'];require(V.sha(previous['record'])==previous['sha256'],'first failed preparation retained')
 for name,row in previous['partial_catalogs'].items():require(V.sha(name)==row['sha256'],'first partial catalog retained')
 previous=predecessors['previous_preparation02']
 for row in [previous[k] for k in ['record','stdout','stderr']]+previous['sources']+previous['partial_packet']:
  require(V.sha(row['path'])==row['sha256'] and identity(row['path'])['size']==row['size'],'second failed preparation retained')
 reader=controls('hash-file-table-reader-controls',22,'ea8ba76b848318affd0f2d76f4f5e4b6711731d15250e0eb17ec5d1362408b2b',[(H/name,H/name) for name in ['verify.py','test_file_table_audit.py']])
 generic=controls('hir-options-hash-prerequisite-controls',66,'7d17277c1551a40faa717ed06056184d156519cee4b2002a83e69f7d3424265a',
  [(R/'experiments/hir-options-hash-driver-stage'/name,H/name) for name in ['prerequisites.py','snapshot_bindings.py','test_native_wrapper.py','test_snapshot_bindings.py']],number='05')
 freeze=V.complete_file_table(compact,expected_base=dict(path=str(V.NATIVE_SOURCE/'inputs.json'),sha256='8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d'))
 require(len(freeze['files'])==109196 and sum(r['size'] for r in freeze['files'].values())==6770927978 and len(compact['files'])==2764,'exact complete frozen table')
 for index,name in enumerate(freeze['files']):
  V.frozen(name,freeze)
  if index%10000==0:print(json.dumps(dict(phase='frozen-inputs',completed=index,total=len(freeze['files']))),flush=True)
 for name,row in freeze['links'].items():
  path=Path(name);require(path.is_symlink() and V.stamp(path)==row['stamp'] and os.readlink(path)==row['target'] and str(path.resolve(strict=True))==row['resolved'],'complete symlink route')
 for name in freeze['absent_paths']:require(not Path(name).exists() and not Path(name).is_symlink(),'complete absence guard')
 for name,resolved in plan['executor_routes'].items():require(str(Path(name).resolve(strict=True))==resolved,'executor route')
 for path in [V.WORK,V.ARTIFACTS,V.OUTER]:require(not path.exists() and not path.is_symlink(),'no current hash workload/output')
 table_proof=V.file_table_helper_qualification(freeze);snapshot_proof=V.snapshot_helper_qualification(freeze)
 require(V.encoded(preflight['file_table_qualification'])==V.encoded(table_proof)
  and V.encoded(preflight['file_table_base'])==V.encoded(compact['file_table_base'])
  and V.encoded(preflight['file_table_integrity'])==V.encoded(compact['file_table_integrity']) and preflight['delta_files']==2764,'qualified complete reconstruction metadata')
 require(set(plan['immutable_trees'])==set(map(str,[V.D2,V.E2,V.B3])),'three exact provider roots')
 inventories={}
 for name,catalog in plan['immutable_trees'].items():
  guard();now=V.inventory(name);require(now==V.read(V.frozen(catalog,freeze)),'full current provider membership/bytes');inventories[name]=len(now)
 metadata=plan['metadata_plan'];sdk_alias=Path(plan['sdk'])
 sdk_root=Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
 require(metadata['routes'][str(sdk_alias)]==plan['executor_routes'][str(sdk_alias)]==str(sdk_root)
  and metadata['routes'][str(sdk_root)]==plan['executor_routes'][str(sdk_root)]==str(sdk_root)
  and sdk_alias.resolve(strict=True)==sdk_root,'exact admitted SDK alias and canonical metadata route')
 require(sdk_inventory(sdk_root)==metadata['sdk_inventory'] and sdk_alias.resolve(strict=True)==sdk_root,
  'full unchanged canonical SDK membership/bytes/stamps and alias route')
 for name,resolved in metadata['routes'].items():require(str(Path(name).resolve(strict=True))==resolved,'metadata executor route')
 for name,digest in metadata['configuration'].items():require(not Path(name).is_symlink() and (V.sha(name) if Path(name).is_file() else None)==digest,'metadata configuration guard')
 platform=os.uname();require(plan['platform']==dict(system=platform.sysname,release=platform.release,version=platform.version,machine=platform.machine),'same strict platform identity')
 prior={'compiler':(X/'experiments/hir-options-hash/compiler-build-continuation-03',X/'.work/hir-options-hash-compiler-build-continuation-03'),
  'beta':(A/'experiments/hir-options-hash-beta-composition-08',A/'.work/hir-options-hash-beta-composition-08'),
  'native':(V.RECON_SOURCE,V.RECON_WORK),'run_make':(O/'experiments/hir-options-hash-run-make-stage-02',O/'.work/hir-options-hash-run-make-01')}
 require(set(plan['independent_audits'])==set(prior),'four prerequisite audits')
 for role,(source,evidence) in prior.items():
  ref=plan['independent_audits'][role];audit=V.verified_reference(ref,freeze);terminal=V.read(V.frozen(evidence/'receipt.json',freeze))
  require(ref['sha256']==AUDITS[role] and audit['status']=='verified' and terminal['status']=='passed' and audit['receipt_sha256']==V.sha(evidence/'receipt.json'),'exact completed prerequisite audit')
  V.inherited_inputs(source,freeze)
 native=V.verified_native_reconciliation(freeze,plan)
 require(native['result']['qualified_native_children']==20 and native['result']['total_actual_native_children']==31,'native saved20/prior11/zero-new qualification')
 counts=dict(compiler_actual_children=26,compiler_successful_children=25,beta_commands=19,run_make_top_level_commands=2,run_make_nested_commands=230)
 require(all(preflight['prerequisites'][k]==v for k,v in counts.items()),'exact completed histories')
 for path,digest in V.SOURCE_HASHES.items():require(V.sha(V.frozen(path,freeze))==digest,'exact driver fixture source')
 core_source=V.raw(V.frozen(H/'controls.py',freeze));tree=ast.parse(core_source)
 fn=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='desired_commands'];require(len(fn)==1,'one source-derived command function')
 namespace=dict(V.__dict__,H=V.HOST);exec(compile(ast.Module(body=fn,type_ignores=[]),str(H/'controls.py'),'exec'),namespace)
 require(plan['children']==namespace['desired_commands'](plan)==V.commands(plan),'source-derived independent three commands/roles')
 capacity=dict(entry_gib=24,stop_gib=9,floor_gib=8,namespace_bytes=14*2**30,evidence_bytes=256*2**20)
 require(launch['status']=='prepared-unrun-awaiting-review' and launch['owner']==str(R) and launch['capacity']==plan['capacity']==capacity
  and launch['environment']==freeze['launch_environment']==plan['environment'] and launch['expected_children']==3 and launch['driver_processes']==2 and launch['contexts_per_process']==8,'unchanged concrete launch policy')
 wanted=[freeze['python'],'-B',str(R/'scripts/supervise_experiment.py'),'--run-id','hir-options-hash-driver-supervisor-01','--',freeze['python'],'-B',str(H/'stage.py'),'--inputs-sha256',EXPECTED['inputs.json'],'--snapshot-plan-sha256',EXPECTED['snapshot-plan.json']]
 require(launch['command']==wanted and launch['helper_sha256']==V.sha(H/'stage.py') and launch['inputs_sha256']==snapshot['inputs_sha256']==preflight['inputs_sha256']==EXPECTED['inputs.json']
  and launch['plan_sha256']==freeze['plan_sha256']==EXPECTED['plan.json'] and launch['snapshot_plan_sha256']==preflight['snapshot_plan_sha256']==EXPECTED['snapshot-plan.json'],'all final launch/preflight/plan/snapshot associations')
 require(preflight['status']=='passed' and preflight['workload_children']==0 and preflight['work_created'] is False and preflight['files']==109196 and preflight['input_bytes']==6770927978
  and preflight['discovery_entry_gib']==16 and preflight['discovery_live_floor_gib']==9 and preflight['free_bytes_before']>=16*2**30 and preflight['free_bytes_after']>=9*2**30,'actual read-only preflight')
 before=allocation(plan);proof=projection(freeze,plan,snapshot);after=allocation(plan)
 require(preflight['snapshot_reservation_bytes']==proof['reservation_bytes'] and preflight['budget']['evidence_allocated_bytes']==snapshot['measured_existing_evidence_bytes'],'preflight complete reservation binding')
 require(before['evidence_bytes']+proof['reservation_bytes']<=256*2**20 and after['evidence_bytes']+proof['reservation_bytes']<=256*2**20,'current aggregate plus complete future reservation')
 for name,row in freeze['files'].items():require(V.identity(name)==row['identity'],'final full file identities')
 for name,digest in EXPECTED.items():require(V.sha(H/name)==digest,'final prepared packet unchanged')
 for path in [V.WORK,V.ARTIFACTS,V.OUTER]:require(not path.exists() and not path.is_symlink(),'workload still absent')
 guard();report=dict(status='verified-prepared-unrun',pid=os.getpid(),parent_pid=os.getppid(),started_at=started,finished_at=time.time(),source_sha256=sha(__file__),
  launch_sha256=EXPECTED['launch.json'],inputs_sha256=EXPECTED['inputs.json'],plan_sha256=EXPECTED['plan.json'],snapshot_plan_sha256=EXPECTED['snapshot-plan.json'],
  preparation_record_sha256=PREP_SHA,prior_failed_audit=prior_failure,sdk_alias=str(sdk_alias),sdk_inventory_root=str(sdk_root),qualified_reader=reader,file_table_qualification=table_proof,snapshot_helper_qualification=snapshot_proof,
  files=len(freeze['files']),frozen_bytes=sum(r['size'] for r in freeze['files'].values()),delta_files=len(compact['files']),links=len(freeze['links']),absences=len(freeze['absent_paths']),provider_inventories=inventories,
  generic_controls=generic,sdk_entries=len(metadata['sdk_inventory']),prerequisites=preflight['prerequisites'],independent_audits=plan['independent_audits'],planned_children=plan['children'],capacity=capacity,
  projection=proof,allocation_before=before,allocation_after=after,disk_samples=SAMPLES,read_bytes=READ_BYTES,
  workload_children=0,work_created=False,artifacts_created=False,application_qualified=False,performance_measurement=False,
  limitation='Prepared packet only. No new compile/driver output or workload qualification; fresh24GiB and canonical admission remain required before any actual launch.')
 write(OUT,report);print(json.dumps(dict(status=report['status'],report=str(OUT),sha256=sha(OUT),files=report['files'],frozen_bytes=report['frozen_bytes'],margin_bytes=256*2**20-after['evidence_bytes']-proof['reservation_bytes'])),flush=True)

if __name__=='__main__':main()
