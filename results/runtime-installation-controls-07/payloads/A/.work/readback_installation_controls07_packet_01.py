"""Read only the closed control preparation, exact frozen sources and raw packet."""
from pathlib import Path
import ast,hashlib,json,os,stat,time
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
H=R/'experiments/runtime-installation-controls-07'
S=R/'experiments/runtime-installation-after-preflight05-02'
E=R/'.work/runtime-installation-controls-preparation-execution-07'
D=R/'results/runtime-installation06-test-development-01'
OUT=A/'.work/runtime-installation-controls07-prepared-readback-01.json'
assert not OUT.exists()
checked={}
def identity(p):
 s=p.lstat();return {k:getattr(s,'st_'+k) for k in ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']}
def file(p):
 p=Path(p);before=identity(p)
 assert p.resolve(strict=True)==p and stat.S_ISREG(before['mode']) and before['size']<=2**20,p
 with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW),'rb') as f:
  assert {k:getattr(os.fstat(f.fileno()),'st_'+k) for k in before}==before
  data=f.read(2**20+1)
  assert {k:getattr(os.fstat(f.fileno()),'st_'+k) for k in before}==before
 assert identity(p)==before and len(data)==before['size']
 row=dict(sha256=hashlib.sha256(data).hexdigest(),size=len(data),identity=before)
 if str(p) in checked:assert checked[str(p)]==row
 checked[str(p)]=row;return data,row
def doc(p):return json.loads(file(p)[0])
def sha(p):return file(p)[1]['sha256']
r=doc(E/'record.json');f=doc(H/'inputs.json');launch=doc(H/'launch.json')
assert r['status']=='finished' and r['returncode']==0 and r['parent_pid']==68057
assert type(r['pid']) is int and r['pid']>0 and r['observation_errors']==[]
assert r['started_at']<=r['admitted_at']<=r['child_started_at']<=r['finished_at']<=r['canonical_released_at']
assert r['execution_source_sha256']==sha(R/'.work/prepare_runtime_installation_controls_07_once.py')==sha(E/'source/execution.py')=='09b98f1dcfb171b603288e6422e0673c92e02c34ff5b3713716bce867d143298'
assert r['owned_source_sha256']==sha(X/'experiments/stable-cgu/owned_stage.py')==sha(E/'source/owned_stage.py')
for n,digest in r['source_sha256'].items():assert sha(H/n)==digest==sha(E/'source'/n)
assert set(r['source_sha256'])=={'run.py','prepare.py','child.py'}
assert {p.name for p in H.iterdir()}=={'run.py','prepare.py','child.py','inputs.json','launch.json'}
assert {p.name for p in E.iterdir()}=={'source','record.json','stdout','stderr'}
assert {p.name for p in (E/'source').iterdir()}=={'run.py','prepare.py','child.py','execution.py','owned_stage.py'}
assert sha(E/'stdout')==r['stdout_sha256'] and sha(E/'stderr')==r['stderr_sha256'] and not file(E/'stderr')[0]
prepared=doc(E/'stdout');assert prepared==r['prepared_packet'] and prepared['status']=='prepared-unrun'
assert prepared['launch_sha256']==sha(H/'launch.json') and prepared['inputs_sha256']==sha(H/'inputs.json')==launch['inputs_sha256']
assert prepared['controls']==launch['controls']==25 and prepared['files']==len(f['files'])==31
assert prepared['bytes']==sum(row['stamp'][3] for row in f['files'].values())
for name,row in f['files'].items():
 value=file(name)[1]
 assert row['sha256']==value['sha256'] and row['stamp']==[value['identity'][k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']],name
for name,target in f['routes'].items():assert str(Path(name).resolve(strict=True))==target
expected={str((H/n).resolve(strict=True)) for n in ['run.py','prepare.py','child.py']}
expected|={str(S/n) for n in ['entry.py','controller.py','audit_owner.py','routes.json','prepare.py','prepare_once.py','launch.py','test_installation.py']}
expected|={str(R/'experiments/runtime04-environment-adapter-01/environment.py'),str(R/'experiments/runtime-preflight-retry-05/routes.json')}
expected|={str(D/n) for n in doc(D/'manifest.json')}|{str(D/'manifest.json')}
expected|={str(Path(p).resolve(strict=True)) for p in [f['python'],'/opt/homebrew/bin/python3','/bin/ps','/usr/sbin/lsof',R/'scripts/supervise_experiment.py',X/'experiments/stable-cgu/owned_stage.py']}
assert set(f['files'])==expected and len(f['routes'])==32
tree=ast.parse(file(S/'test_installation.py')[0]);names=sorted('test_installation.'+c.name+'.'+m.name for c in tree.body if isinstance(c,ast.ClassDef) for m in c.body if isinstance(m,ast.FunctionDef) and m.name.startswith('test_'))
assert len(names)==25 and f['expected_names']==names
assert r['cwd']==f['owner']==launch['owner']==str(R) and r['environment']==f['environment']==launch['environment']
assert r['command']==[f['python'],'-B',str(H/'prepare.py')] and f['command']==[f['python'],'-B',str(H/'child.py')]
assert launch['command']==[f['python'],'-B',str(R/'scripts/supervise_experiment.py'),'--run-id','runtime-installation-controls-supervisor-07','--',f['python'],'-B',str(H/'run.py'),'--inputs-sha256',sha(H/'inputs.json')]
assert launch['helper_sha256']==sha(H/'run.py') and launch['expected_children']==1
assert r['capacity']==f['capacity']==launch['capacity']==dict(entry_gib=10,stop_gib=9,floor_gib=8)
assert f['canonical_lock']==r['canonical_lock']=='/Users/danluu/dev/rust-interp/.work/benchmark.lock' and f['wait_seconds']==r['wait_seconds']==600
assert r['free_bytes_before']>=10*2**30 and r['free_bytes_after']>=9*2**30 and all(v['free_bytes']>=9*2**30 for v in r['disk_samples'])
assert f['bounds']==launch['bounds']==dict(child_alarm_seconds=120,child_cpu_seconds=60,maximum_file_bytes=256*1024,maximum_writable_names=256,maximum_directory_names=2048,maximum_cumulative_child_file_payload_bytes=258*256*1024,maximum_retained_stage_file_bytes=2*2**20)
assert all(f[k]==0 for k in ['compiler_calls','provider_probes','B3_compositions'])
for row in f['ordinary_development_reference'].values():assert sha(Path(row['path']))==row['sha256']
for name,row in checked.items():assert identity(Path(name))==row['identity']
report=dict(status='verified-prepared-unrun',finished_at=time.time(),verifier_sha256=sha(Path(__file__)),preparation_record=dict(path=str(E/'record.json'),sha256=sha(E/'record.json')),parent_pid=r['parent_pid'],child_pid=r['pid'],canonical_released_at=r['canonical_released_at'],launch_sha256=sha(H/'launch.json'),inputs_sha256=sha(H/'inputs.json'),input_files=len(f['files']),input_bytes=prepared['bytes'],routes=len(f['routes']),expected_names=names,ordinary_development_reference=f['ordinary_development_reference'],checked_files=checked,no_target_imports=True,compiler_calls=0)
with OUT.open('x') as stream:json.dump(report,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps(dict(path=str(OUT),sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),input_files=report['input_files'],input_bytes=report['input_bytes'],launch_sha256=report['launch_sha256'],inputs_sha256=report['inputs_sha256'])))
