"""Finite metadata/build evidence capsule; no targets or provider payloads copied."""
import hashlib,json,os,stat,time
from pathlib import Path
Q=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913');X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
OUT=Q/'results/host-wrapper-exporter-metadata-build-01';PLAN=X/'.work/host-wrapper-exporter-metadata-build-publication-plan-01.json'
REPORT=X/'.work/host-wrapper-exporter-metadata-build-independent-readback-01.json'
REPORT_SHA='fed3686ba4ea03166ac9a4d4269af5d8d735c7afb7681d97f256c6659665fa8b'
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
extras=[REPORT,X/'.work/read_host_wrapper_exporter_metadata_build_01.py',X/'.work/read_host_wrapper_exporter_metadata_build_01.before-controller-argv.py',X/'.work/read_host_wrapper_exporter_metadata_build_01.controller-argv.diff',X/'.work/host-wrapper-exporter-metadata-build-reader-development-01.json']
for p in extras:files[str(p)]=read(p)[1]
F=Q/'experiments/host-wrapper-exporter-01';references={}
for name,row in report['checked_files'].items():
 if name in files:continue
 p=Path(name)
 if p.is_relative_to(F) or name in json.loads((F/'build-sources.json').read_bytes())['files'] or p==X/'scripts/supervise_experiment.py':references[name]=row
payloads={}
for name,row in files.items():
 raw,current=read(name);assert current==row
 base=Q if Path(name).is_relative_to(Q) else X;tag='ROOT' if base==Q else 'X';relative='retained/'+tag+'/'+str(Path(name).relative_to(base));payloads[relative]=(name,raw,row)
for name,row in references.items():assert read(name)[1]==row
scope=dict(status='finite-closed-metadata-build-capsule-plan',output=str(OUT),files=files,references=references,closed_trees=report['closed_trees'],payload_files=len(payloads),payload_bytes=sum(len(x[1]) for x in payloads.values()),binary_payload_copies=0,source238_payload_copies=0,compiler_calls=0,provider_calls=0)
assert len(payloads)<200 and scope['payload_bytes']<8*2**20 and not OUT.exists() and not PLAN.exists();write(PLAN,encoded(scope));OUT.mkdir(mode=0o700)
copies=[]
for rel,(name,data,row) in payloads.items():
 write(OUT/rel,data);dst=read(OUT/rel)[1];assert dst['identity'][1]!=row['identity'][1];copies.append(dict(original=name,relative=rel,source=row,destination=dst))
write(OUT/'scope.json',encoded(scope));write(OUT/'publisher.py',read(Path(__file__).absolute())[0])
status='''# Host wrapper exporter: metadata and build

Metadata passed all 36 declared commands, then build passed all seven commands. Both normal parent/supervisor/controller chains closed with exit zero. The ordinary Cargo recipe remained release, locked, offline, jobs=2. It built fresh exporter and wrapper binaries for the recorded D2/B3/runtime07 composition; no compiler or VM was rebuilt.

The independent saved readback checked 418 named files, all 238 materialized source SHA/identity rows, exact argv/environment/raw/closure associations, the 30-package dependency graph, and 44 actual compiler rows. Both built binary hashes and the generated role binding match. The exporter capability records host-codegen-opt-v1 (O3, MIR level 1, LTO off, checks preserved). The ordinary runtime wrapper binding adds the captured wrapper SHA and compiler-role association to the raw exporter capabilities.

Saved otool nodes and resolved-library hashes match the frozen packet. Each of the build compiler, runtime compiler and exporter streams reconstructs 705 dyld events, 548 images, 391 final loaded and 157 delayed images; its selected driver ends active. Current provider payloads and live loader resolution were not reprobed. Four build-script role identity probes are bound through the authenticated build script, Cargo and generated output; they do not have four separate supervisor receipts. Short-lived process identity observations may lack cwd; exact saved spawn cwd and normal closure remain retained.

This capsule contains complete closed metadata/build raw evidence and the independent reader/report. The 5.4 MB packet and held source manifests stay referenced in place. No provider, binary, target or materialized 238-source payload is duplicated. The source reader's initial sys.argv/environment schema assumption failed before report creation; its original source, correction and development note are retained. No workload was rerun. Frontend, publication, application correctness and performance are outside this capsule's qualification scope; later phases are retained separately.
'''
write(OUT/'README.md',status.encode())
for name,row in files.items():assert read(name)[1]==row
for name,row in references.items():assert read(name)[1]==row
assert all(tree(root)==rows for root,rows in report['closed_trees'].items())
manifest=dict(status='published-closed-metadata-build-evidence',pid=os.getpid(),parent_pid=os.getppid(),started_at=start,finished_at=time.time(),copies=copies,references=references,metadata={n:read(OUT/n)[1] for n in ('scope.json','publisher.py','README.md')},payload_files=len(copies),payload_bytes=scope['payload_bytes'],originals_unchanged=True,closed_trees=report['closed_trees'],binary_payload_copies=0,provider_payload_copies=0)
write(OUT/'manifest.json',encoded(manifest))
for r in copies:assert read(OUT/r['relative'])[1]==r['destination'] and read(r['original'])[1]==r['source']
stage=sorted(str(p.relative_to(Q)) for p in OUT.rglob('*') if p.is_file())+[str((OUT/n).relative_to(Q)) for n in ('STAGE.json','READBACK.json')]
write(OUT/'STAGE.json',encoded(dict(status='exact-paths-not-staged',paths=sorted(stage))))
readback=dict(status='verified',manifest=read(OUT/'manifest.json')[1],files={str(p.relative_to(OUT)):read(p)[1] for p in OUT.rglob('*') if p.is_file()},payload_files=len(copies),payload_bytes=scope['payload_bytes'],full_EOF_SHA_and_current_stamp=True,originals_unchanged=True)
write(OUT/'READBACK.json',encoded(readback))
assert sorted(str(p.relative_to(Q)) for p in OUT.rglob('*') if p.is_file())==sorted(stage)
print(json.dumps(dict(output=str(OUT),manifest=read(OUT/'manifest.json')[1]['sha256'],readback=read(OUT/'READBACK.json')[1]['sha256'],stage=read(OUT/'STAGE.json')[1]['sha256'],files=len(stage),payload_bytes=scope['payload_bytes'])))
