"""Finite source/control capsule; no compiler, provider payload or full-map copy."""
import hashlib,json,os,stat,time
from pathlib import Path
Q=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913');X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918');O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918');A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918');R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
OUT=Q/'results/host-wrapper-rbc-source-controls-01';START=time.time();MAX_FILES=150;MAX_BYTES=3*2**20
originals={};data={};placements={};memberships={};references={}
def identity(s):return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]
def read(p,sha=None,expected=None):
 p=Path(p);a=identity(p.lstat());assert p.resolve(strict=True)==p and stat.S_ISREG(a[2]) and a[3]<=4*2**20
 with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW),'rb') as f:
  assert identity(os.fstat(f.fileno()))==a;b=f.read(4*2**20+1);assert identity(os.fstat(f.fileno()))==a
 assert identity(p.lstat())==a and len(b)==a[3]
 row=dict(path=str(p),bytes=len(b),identity=a,sha256=hashlib.sha256(b).hexdigest())
 assert sha is None or row['sha256']==sha
 if expected:assert all(row[k]==v for k,v in expected.items())
 if str(p) in originals:assert originals[str(p)]==row
 originals[str(p)]=row;return b
def add(p,sha=None,expected=None,copy=False):
 p=Path(p);b=read(p,sha,expected);data[str(p)]=b
 if not copy and p.is_relative_to(Q/'experiments'):dest=p
 else:
  alias,base=next((alias,base) for alias,base in [('ROOT',Q),('X',X),('O',O),('A',A),('R',R)] if p.is_relative_to(base))
  dest=OUT/'files'/alias/p.relative_to(base)
 placements[str(p)]=str(dest);return b
def doc(p,sha=None,copy=False):return json.loads(add(p,sha,copy=copy))
def directory(p):
 p=Path(p);a=identity(p.lstat());assert stat.S_ISDIR(a[2]) and p.resolve(strict=True)==p
 memberships[str(p)]=dict(identity=a,names=sorted(os.listdir(p)))
# Review-held driver/fixture histories. Their concrete bindings are references only.
bindpins={'01':'391ff1126a4b47efced9323564220c382a94a5fc1a8be1c7e2f49ddfbeded6a4','02':'73c226bc231180d545578db551823a80fdee4c88a1d8689d0cd1f1807c8f6aac','03':'e267d7c25bfb941766dd96b1813f528547356e7430eb6ad2dce933e3fff022c3'}
bindings={}
for run in ('01','02','03'):
 root=Q/f'experiments/host-wrapper-rbc-driver-{run}';directory(root)
 for p in sorted(root.iterdir()):
  assert p.is_file() and not p.is_symlink()
  if p.name!='binding.json':add(p)
 manifest=doc(root/'sources.json');assert len(manifest['files'])==24
 for p,sha in manifest['files'].items():add(p,sha)
 b=read(root/'binding.json',bindpins[run]);bindings[run]=originals[str(root/'binding.json')];references[str(root/'binding.json')]=dict(original=bindings[run],scope='current bytes authenticated; omitted from this capsule and retained for the later full archive')
for run in ('01','02'):
 root=Q/f'experiments/host-wrapper-rbc-fixture-{run}';directory(root)
 for p in sorted(root.iterdir()):assert p.is_file() and not p.is_symlink();add(p)
# C's final finite local source/history/reviews packet, retaining its declared source124 map.
C=Q/'experiments/host-wrapper-ruff-correctness-01';cm=doc(C/'manifest.json','87b31897d8f6354b892785b52e4fa0be93e4fd924be3852dd84a2d4e09ae6b17');assert cm['payload_count']==38 and cm['payload_bytes']==361515
assert len(cm['files'])==38 and sum(r['bytes'] for r in cm['files'].values())==361515
for rel,row in cm['files'].items():assert '..' not in Path(rel).parts and not Path(rel).is_absolute();add(C/rel,expected=row)
actual=[]
for parent,dirs,files in os.walk(C,followlinks=False):
 directory(parent)
 for n in dirs:assert not (Path(parent)/n).is_symlink()
 for n in files:actual.append(str((Path(parent)/n).relative_to(C)))
assert set(actual)==set(cm['files'])|{'manifest.json'}
# Finite external reviews/handoffs are physically copied with exact origin mappings.
proofs=[
 (O/'.work/host-wrapper-rbc-driver-source-handoff-01.json',None),
 (O/'.work/host-wrapper-rbc-driver02-source-handoff-01.json',None),
 (O/'.work/host-wrapper-rbc-driver03-source-handoff-01.json','19bff93425de3e97e90b68898f75094ca4848275ce2afb69940dd994baa17d75'),
 (O/'.work/host-wrapper-rbc-fixture-independent-source-review-01.json',None),
 (O/'.work/host-wrapper-rbc-binding-independent-readback-01.json',None),
 (O/'.work/host-wrapper-rbc02-binding-independent-readback-01.json',None),
 (O/'.work/host-wrapper-rbc01-failure-independent-readback-01.json','fb65862461ee2ae1497298f69e482c3b37145780e81606a72eef8c4fc5cd6020'),
 (O/'.work/host-wrapper-rbc02-observer-diagnosis-01.json','6b0c5234577f02832a7d484ea0528107a44075d169df5163ef846a9d9e1f9871'),
 (O/'.work/host-wrapper-rbc-observer-tests-independent-readback-01.json','50693c01bd8437188c0640102bc42f007e3a426e6f9d6019d4e2cef3c595ec14'),
 (X/'.work/host-wrapper-rbc01-failure-scope-independent-readback-01.json','1c09ee910188dc67f361651b15d43ab54f9b2a747884d3bb992876738e3d09bf'),
 (X/'.work/host-wrapper-rbc02-failure-independent-readback-01.json','05ae83c86890458355c6d0d02580f0a67fb11f519bd81d4d2f317a9d8da16712'),
 (X/'.work/read_host_wrapper_rbc01_failure_scope_01.py',None),
 (X/'.work/read_host_wrapper_rbc02_failure_01.py',None),
 (A/'.work/host-wrapper-ruff-correctness-source-handoff-01.json','63ff80fd7be339260c67f2765a43d40ccce5d9a94c347c49e79c31ac898a1e16')]
for p,sha in proofs:add(p,sha,copy=True)
# Closed failed runtime terminals/raw summaries; no full command trees or full input maps.
failed={}
for run in ('01','02'):
 outer_root=Q/f'.work/host-wrapper-rbc-execution-{run}';result=Q/f'results/host-wrapper-rbc-fixture-{run}'
 directory(outer_root)
 for n in ('record.json','stdout','stderr'):add(outer_root/n,copy=True)
 outer=json.loads(data[str(outer_root/'record.json')]);driver=doc(result/'record.json',copy=True);suite=doc(result/'suite-result.json',copy=True)
 for n in ('stdout','stderr'):add(result/n,copy=True)
 assert outer['returncode']==driver['returncode']==1 and outer['normal_wait_completed'] is driver['normal_wait_completed'] is True
 assert outer['driver_may_be_live'] is driver['child_may_be_live'] is False and suite['tests_run']==5
 assert driver['binding']['sha256']==bindings[run]['sha256']
 assert (suite['failures'],suite['errors'],len(suite['commands']))==((1,0,180) if run=='01' else (0,5,11))
 if run=='02':doc(result/'STOP.json','c8ea624056b61fb4062d5e2c2925f0245942cbbd089f9bef7f7b2ab9b677bf60',copy=True)
 else:assert not (result/'STOP.json').exists()
 independent=json.loads(data[str(X/('.work/host-wrapper-rbc01-failure-scope-independent-readback-01.json' if run=='01' else '.work/host-wrapper-rbc02-failure-independent-readback-01.json'))])
 for name in ('inputs-before.json','inputs-after.json'):
  path=str(result/name);saved=independent.get('refs',{}).get(path)
  if saved is None:
   saved=next(row for row in independent.values() if isinstance(row,dict) and row.get('path')==path)
  assert identity(Path(path).lstat())==saved['identity']
  references[path]=dict(recorded=saved,current_stamp_checked=True,scope='full bytes were independently checked by the copied failure readback; not reread or copied here')
 failed[run]=dict(outer=originals[str(outer_root/'record.json')],driver=originals[str(result/'record.json')],suite=originals[str(result/'suite-result.json')],commands=len(suite['commands']),failures=suite['failures'],errors=suite['errors'])
# Actual ten pure tests: exact parent/child normal wait, complete raw names and stable two sources.
testroot=Q/'.work/host-wrapper-rbc-observer-tests-execution-01';directory(testroot)
test=doc(testroot/'record.json','05466425f2e8e7079a16de3a6b9aaf59df576d21b4b3578d0f01dcdb9c252880',copy=True)
for kind in ('stdout','stderr'):add(testroot/kind,test[kind]['sha256'],copy=True)
add(test['source']['path'],test['source']['sha256'],copy=True)
assert test['status']=='passed' and test['returncode']==0 and test['normal_wait_completed'] is True and test['child_may_be_live'] is False
assert test['tests_run']==10 and test['test_names']==test['expected_tests'] and test['inputs_unchanged'] is True
raw=data[str(testroot/'stderr')].decode();assert 'Ran 10 tests in ' in raw and raw.rstrip().endswith('OK') and data[str(testroot/'stdout')]==b''
for name in test['test_names']:assert raw.count(name+' (')==1
for p,row in test['sources'].items():add(p,expected=row)
assert sorted((testroot/'tmp').iterdir())==[]
absent=[Q/'results/host-wrapper-rbc-fixture-03',Q/'.work/host-wrapper-rbc-execution-03',Q/'.work/host-wrapper-rbc-fixture-03']
assert all(not p.exists() for p in absent)
add(Path(__file__).absolute(),copy=True)
assert len(placements)+4<=MAX_FILES and sum(len(b) for b in data.values())<MAX_BYTES
assert not OUT.exists();OUT.mkdir()
def write(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
 return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),identity=identity(p.lstat()))
copied={};staged={}
for p,dest in placements.items():
 dest=Path(dest)
 if str(dest)!=p:copied[p]=dict(original=originals[p],copy=write(dest,data[p]))
 else:staged[p]=originals[p]
manifest=dict(status='source-and-control-publication; no complete RBC qualification',created_at=time.time(),copied=copied,staged_originals=staged,references_only=references,source_directories=memberships,D_bindings=bindings,failed_runs=failed,pure_observer_tests=originals[str(testroot/'record.json')],C_source_manifest=originals[str(C/'manifest.json')],C_payload_count=38,C_payload_bytes=361515,D03_status='bound-unrun; blocked before invocation by fixed 16 GiB entry admission',D03_absent_paths=list(map(str,absent)),complete_RBC_pass=False,application_qualified=False,performance_claim=False,provider_payload_copies=0,native_or_Cargo_binary_copies=0,full_input_map_copies=0,binding_copies=0,limits=dict(max_stage_files=MAX_FILES,max_stage_bytes=MAX_BYTES),scope='Full command/input histories remain unchanged at their recorded original paths, reserved for the later complete combined archive. C source124 is retained as an authenticated map; this capsule includes its complete local38-file packet, not a second copy of all external source124 dependencies.')
write(OUT/'manifest.json',(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode())
readme='''# Host wrapper RBC sources and observer controls\n\nThis finite capsule retains driver01–03 and fixture01–02 source histories, the complete 38-file Ruff correctness source packet, actual ten-test observer proof, and closed RBC01/02 failure terminals and independent readbacks. ROOT experiment sources are staged in place; external proof/source files are copied with exact original SHA-256 and seven-field identities in manifest.json.\n\nRBC01 normally closed with 180 direct children: four test passes and one collector assertion. Cargo correctly rejected the generated E0308 case, but json-render-diagnostics omitted the compiler-message events expected by the collector. RBC02 changed only that presentation contract; it normally closed after eleven successful direct children and a parent observation STOP. Its five tests errored before further children were spawned. The saved ENOENT lacks the precise vanished pathname; no complete RBC pass is claimed.\n\nThe ten pure observer tests passed once with normal parent/child wait. Driver03 is bound but was not invoked: available disk was below its unchanged 16 GiB entry threshold. Its result/work/execution namespaces were absent at capture. The Ruff application correctness controller is source-only with future proof pins unset. There is no application qualification or performance result.\n\nThe three 3 MB binding files and four full input maps are recorded as references, not copied. Full failed command/raw/argv/source/RBC histories remain unchanged at their original task-owned paths and are reserved for the later combined archive. Provider and executable payloads are excluded. No tests, compilers, benchmark, cleanup or Git operations were run by this publication.\n'''
write(OUT/'README.md',readme.encode())
stage=sorted(set(staged)|{str(p) for p in OUT.rglob('*') if p.is_file()}|{str(OUT/'STAGE.txt'),str(OUT/'READBACK.json')})
assert len(stage)<=MAX_FILES
write(OUT/'STAGE.txt',(''.join(str(Path(p).relative_to(Q))+'\n' for p in stage)).encode())
# Full copied bytes and in-place originals checked to EOF; all source identities remain exact.
verified={}
for p,b in data.items():
 assert read(p,originals[p]['sha256'],originals[p])==b
 dest=Path(placements[p]);assert dest.read_bytes()==b
 verified[str(dest)]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
for p,row in memberships.items():assert identity(Path(p).lstat())==row['identity'] and sorted(os.listdir(p))==row['names']
assert all(not p.exists() for p in absent)
current_bytes=sum(Path(p).lstat().st_size for p in stage if Path(p).exists())
readback=dict(status='verified',created_at=time.time(),publisher_pid=os.getpid(),publisher_parent_pid=os.getppid(),started_at=START,finished_at=time.time(),manifest=dict(path=str(OUT/'manifest.json'),sha256=hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest()),stage=dict(path=str(OUT/'STAGE.txt'),sha256=hashlib.sha256((OUT/'STAGE.txt').read_bytes()).hexdigest()),staged_file_count=len(stage),selected_payload_count=len(data),copied_payload_count=len(copied),staged_original_count=len(staged),all_selected_original_EOF_SHA_and_seven_stamps_unchanged=True,copied_bytes_verified_to_EOF=True,exact_source_memberships_unchanged=True,D03_namespaces_absent=True,complete_RBC_pass=False,application_qualified=False,performance_claim=False,verified=verified)
rb=(json.dumps(readback,sort_keys=True,indent=2)+'\n').encode();assert current_bytes+len(rb)<=MAX_BYTES
write(OUT/'READBACK.json',rb)
expected={str(Path(p).relative_to(OUT)) for p in stage if Path(p).is_relative_to(OUT)}
assert {str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file()}==expected
assert len(stage)<=MAX_FILES and sum(Path(p).lstat().st_size for p in stage)<=MAX_BYTES
print(json.dumps(dict(output=str(OUT),manifest=readback['manifest'],READBACK=dict(path=str(OUT/'READBACK.json'),sha256=hashlib.sha256(rb).hexdigest()),stage=readback['stage'],stage_files=len(stage),stage_bytes=sum(Path(p).lstat().st_size for p in stage),copied=len(copied),originals=len(staged))))
