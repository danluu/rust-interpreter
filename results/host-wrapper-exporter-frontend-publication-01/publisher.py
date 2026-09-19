"""Finite frontend/publication evidence capsule; no executable or provider payloads copied."""
import hashlib,json,os,stat,time
from pathlib import Path
Q=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913');X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
OUT=Q/'results/host-wrapper-exporter-frontend-publication-01';PLAN=X/'.work/host-wrapper-exporter-frontend-publication-capsule-plan-01.json'
REPORT=X/'.work/host-wrapper-exporter-frontend-publication-independent-readback-01.json'
REPORT_SHA='2ca4e3d5a80d403e08e2bb26a9e8577c448751b861cc53b1cfc7d5239ab141dc'
def identity(s):return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]
def read(p):
 p=Path(p);a=identity(p.lstat());assert p.resolve(strict=True)==p and stat.S_ISREG(a[2]) and a[3]<=8*2**20
 with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as f:
  assert identity(os.fstat(f.fileno()))==a;b=f.read(8*2**20+1);assert identity(os.fstat(f.fileno()))==a
 assert identity(p.lstat())==a and len(b)==a[3]
 return b,dict(path=str(p),bytes=len(b),identity=a,sha256=hashlib.sha256(b).hexdigest())
def encoded(d):return (json.dumps(d,sort_keys=True,indent=2)+'\n').encode()
def write(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 assert read(p)[0]==b

def tree(root):
 rows=[]
 for parent,dirs,files in os.walk(root,followlinks=False):
  for n in dirs+files:
   p=Path(parent)/n;m=p.lstat().st_mode;assert stat.S_ISREG(m) or stat.S_ISDIR(m);rows.append([str(p.relative_to(root)),'d' if stat.S_ISDIR(m) else 'f'])
 assert len(rows)<=400;return sorted(rows)
start=time.time();raw,ref=read(REPORT);assert ref['sha256']==REPORT_SHA;report=json.loads(raw);assert report['status']=='verified'
files={}
for root,rows in report['closed_trees'].items():
 assert tree(root)==rows
 for rel,kind in rows:
  if kind=='f':files[str(Path(root)/rel)]=report['checked_files'][str(Path(root)/rel)]
extras=[REPORT,X/'.work/read_host_wrapper_exporter_frontend_publication_01.py']
for p in extras:files[str(p)]=read(p)[1]
installed=Path(report['directory'])
for n in ('compiler.json','ready.json','capabilities.json'):files[str(installed/n)]=report['checked_files'][str(installed/n)]
F=Q/'experiments/host-wrapper-exporter-01';references={}
for name,row in report['checked_files'].items():
 if name in files:continue
 p=Path(name)
 if p.is_relative_to(F) or name in json.loads((F/'publication-sources.json').read_bytes())['files'] or p==X/'scripts/supervise_experiment.py':references[name]=row
payloads={}
for name,row in files.items():
 raw,current=read(name);assert current==row
 R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918');base=Q if Path(name).is_relative_to(Q) else X if Path(name).is_relative_to(X) else R;tag='ROOT' if base==Q else 'X' if base==X else 'R';relative='retained/'+tag+'/'+str(Path(name).relative_to(base));payloads[relative]=(name,raw,row)
for name,row in references.items():assert read(name)[1]==row
scope=dict(status='finite-closed-frontend-publication-capsule-plan',output=str(OUT),files=files,references=references,closed_trees=report['closed_trees'],payload_files=len(payloads),payload_bytes=sum(len(x[1]) for x in payloads.values()),binary_payload_copies=0,source238_payload_copies=0,compiler_calls=0,provider_calls=0)
assert len(payloads)<200 and scope['payload_bytes']<8*2**20 and not OUT.exists() and not PLAN.exists();write(PLAN,encoded(scope));OUT.mkdir(mode=0o700)
copies=[]
for rel,(name,data,row) in payloads.items():
 write(OUT/rel,data);dst=read(OUT/rel)[1];assert dst['identity'][1]!=row['identity'][1];copies.append(dict(original=name,relative=rel,source=row,destination=dst))
write(OUT/'scope.json',encoded(scope));write(OUT/'publisher.py',read(Path(__file__).absolute())[0])
status='# Host wrapper exporter: frontend and publication\n\nThe full frontend phase closed normally after all 34 commands: 27 successes and seven expected failures, including 18 frontend controls and nine native/exporter comparison pairs. Publication then closed normally after four commands, installing tool key 16ad5d9a14ce7711f124a49f09e820eae8cd85b10be0ebf3aeb5eecfdd2602e2 for runtime f031d981666f450f760ccf303dccba986053ec6b9a143a60f3d26680f9ac7c70.\n\nThe independent saved readback checked 490 named files, exact commands/environments/raw output/normal parent closure, all 18 retained source states and final compiler argv, 17 complete stderr separations, and the deliberately plain wrong-role refusal. All nine raw compiler diagnostic pairs match. Explicit/default/wrapper/restored bytecode matches, test discovery identifies the declared test, and the two source fixtures are restored exactly. Whole stderr differs because exporter telemetry remains preserved; no diagnostic normalization or telemetry dropping was used.\n\nAll six installed files were read through EOF and checked by SHA and current identity: three distinct immutable binary copies and three metadata files. The composition digest, runtime/compiler roles, complete 238-source mapping, ordinary installed reader, wrapper identity and three-line host-codegen capability query agree. The published exporter dyld stream is retained losslessly and its runtime driver ends active. The original adopted VM was checked by its saved/current stamp and digest association, without rereading unrelated provider payloads.\n\nFrontend qualification used host-codegen mode off. Binding the new host-codegen capability does not qualify its use on an application. No guest application, host-on application correctness, or performance outcome is claimed here. This evidence does not change the previous allocator screening result or the fixed future benchmark protocol.\n\nThe capsule preserves complete six closed evidence trees, all small frontend artifacts and raw diagnostics, three installed metadata documents, and the independent reader/report. It references the prior metadata/build report, packet and held source manifests in place. It copies no executable/provider binaries or materialized source tree. The publisher performed bounded copies and full EOF/SHA/current-stamp readback; no target imports, probes, compiler calls or Git operations.\n'
write(OUT/'README.md',status.encode())
for name,row in files.items():assert read(name)[1]==row
for name,row in references.items():assert read(name)[1]==row
assert all(tree(root)==rows for root,rows in report['closed_trees'].items())
manifest=dict(status='published-closed-frontend-publication-evidence',pid=os.getpid(),parent_pid=os.getppid(),started_at=start,finished_at=time.time(),copies=copies,references=references,metadata={n:read(OUT/n)[1] for n in ('scope.json','publisher.py','README.md')},payload_files=len(copies),payload_bytes=scope['payload_bytes'],originals_unchanged=True,closed_trees=report['closed_trees'],binary_payload_copies=0,provider_payload_copies=0)
write(OUT/'manifest.json',encoded(manifest))
for r in copies:assert read(OUT/r['relative'])[1]==r['destination'] and read(r['original'])[1]==r['source']
stage=sorted(str(p.relative_to(Q)) for p in OUT.rglob('*') if p.is_file())+[str((OUT/n).relative_to(Q)) for n in ('STAGE.json','READBACK.json')]
write(OUT/'STAGE.json',encoded(dict(status='exact-paths-not-staged',paths=sorted(stage))))
readback=dict(status='verified',manifest=read(OUT/'manifest.json')[1],files={str(p.relative_to(OUT)):read(p)[1] for p in OUT.rglob('*') if p.is_file()},payload_files=len(copies),payload_bytes=scope['payload_bytes'],full_EOF_SHA_and_current_stamp=True,originals_unchanged=True)
write(OUT/'READBACK.json',encoded(readback))
assert sorted(str(p.relative_to(Q)) for p in OUT.rglob('*') if p.is_file())==sorted(stage)
print(json.dumps(dict(output=str(OUT),manifest=read(OUT/'manifest.json')[1]['sha256'],readback=read(OUT/'READBACK.json')[1]['sha256'],stage=read(OUT/'STAGE.json')[1]['sha256'],files=len(stage),payload_bytes=scope['payload_bytes'])))
