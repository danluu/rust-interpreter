"""Read-only actual39 audit. Execute only after passed terminal and outer release."""
import hashlib,json,re,time
from pathlib import Path
EXPECTED_LAUNCH = None  # Bind only to the actual reviewed preparation/dispatcher.
EXPECTED_INPUTS = None  # Bind only to the actual reviewed preparation/dispatcher.
EXPECTED_DISPATCHER = None  # Bind only to the actual reviewed preparation/dispatcher.
EXPECTED_INPUT_BYTES = None  # Bind only to the actual reviewed preparation/dispatcher.
EXPECTED_INPUT_FILES = None  # Bind only to the actual reviewed preparation/dispatcher.
A=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
D=A/'experiments/runtime-startup-environment-controls-01'
W=A/'.work/runtime-startup-environment-controls-01'
S=A/'.work/experiments/runtime-startup-environment-controls-supervisor-01'
L=A/'.work/runtime-startup-environment-controls-launch-execution-01'
def read(p):
 assert p.stat().st_size<=2*2**20,'bounded actual JSON required'
 return json.loads(p.read_bytes())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def stamp(p):
 s=p.lstat();return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]
assert all(type(value) is str and len(value)==64 for value in [EXPECTED_LAUNCH,EXPECTED_INPUTS,EXPECTED_DISPATCHER]), 'actual packet and dispatcher pins required'
assert type(EXPECTED_INPUT_BYTES) is int and type(EXPECTED_INPUT_FILES) is int, 'actual frozen membership pins required'
assert sha(D/'launch.json')==EXPECTED_LAUNCH
assert sha(D/'inputs.json')==EXPECTED_INPUTS
f=read(D/'inputs.json');launch=read(D/'launch.json');r=read(W/'receipt.json');c=read(W/'command/receipt.json');o=read(S/'status.json');l=read(L/'record.json');t=read(W/'result.json')
for n,v in f['files'].items():
 p=Path(n);assert p.resolve(strict=True)==p and stamp(p)==v['stamp'] and sha(p)==v['sha256'] and stamp(p)==v['stamp'],n
for n,v in f['routes'].items():assert str(Path(n).resolve(strict=True))==v,n
assert l['launch_path']==str(D/'launch.json') and l['launch_sha256']==sha(D/'launch.json')
assert Path(l['launcher_source_path'])==A/'.work/launch_runtime_startup_environment_controls_01_bounded.py' and l['launcher_source_sha256']==sha(Path(l['launcher_source_path']))
assert l['status']=='terminal-observed' and l['returncode']==0 and l['launcher_returncode']==0 and l['command']==launch['command'] and l['environment']==launch['environment'] and l['cwd']==str(A)
assert l['launcher_source_sha256']==EXPECTED_DISPATCHER
assert l['observation_errors']==[] and l['wrapper_may_be_live'] is False and l['actual_task_may_be_live'] is False
assert all(sample['free_bytes']>=9*2**30 for sample in l['disk_samples'])
assert l['outer_sha256']==sha(S/'status.json') and l['controller_pid']==r['pid'] and l['supervisor_pid']==o['supervisor_pid']
assert l['finished_at']==o['finished_at']<=l['terminal_observed_at'] and l['started_at']<=l['launcher_finished_at']<=l['terminal_observed_at']
assert l['started_at']<=o['started_at'] and l['launcher_identity']['method']=='in-process'
assert l['launcher_identity']['pid']==l['launcher_pid'] and l['launcher_identity']['parent_pid']==l['launcher_parent_pid'] and l['launcher_identity']['cwd']==str(A)
assert l['wrapper_identity_limitation']=='Popen PID retained; no separate contemporaneous wrapper ps/cwd probe.'
for stream in ['stdout','stderr']:assert l[stream+'_sha256']==sha(L/stream)
hand=read(L/'stdout');assert hand['supervisor_pid']==o['supervisor_pid'] and hand['directory']==str(S)
assert o['status']=='finished' and o['returncode']==0 and o['command']==launch['command'][6:] and o['cwd']==str(A)
assert o['plan_sha256']==sha(S/'plan.json') and o['log_sha256']==sha(S/'command.log')
assert r['status']=='passed' and r['controls_passed']==39 and r['pid']==o['child_pid'] and r['parent_pid']==o['supervisor_pid']
assert r['inputs_sha256']==sha(D/'inputs.json') and r['result_sha256']==sha(W/'result.json')
assert len(r['commands'])==1 and r['commands'][0]==dict(path=str(W/'command/receipt.json'),pid=c['pid'],sha256=sha(W/'command/receipt.json'))
assert c['status']=='finished' and c['returncode']==0 and c['command']==f['command'] and c['cwd']=='/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime04-environment-adapter-01' and c['environment']==f['environment']
assert c['supervisor_pid']==r['pid'] and c['parent_pid']==o['supervisor_pid']
assert c['identity']['ps_returncode']==0
ps=c['identity']['ps'].split();assert list(map(int,ps[:3]))==[c['pid'],r['pid'],c['pid']]
assert len(ps)>9 and ps[8]=='??' and c['identity']['ps'].endswith(' '.join(c['command']))
time.strptime(' '.join(ps[3:8]),'%a %b %d %H:%M:%S %Y')
missing_cwd=[]
if c['identity']['cwd_returncode']==0:
 assert c['identity']['cwd']=='p'+str(c['pid'])+'\nfcwd\nn'+c['cwd']+'\n'
else:
 assert c['identity']['cwd_returncode']==1 and c['identity']['cwd']==''
 missing_cwd.append(dict(pid=c['pid'],requested_cwd=c['cwd'],limitation='Fast-child contemporaneous cwd unavailable; saved process identity and requested/recorded cwd retained, no observed cwd inferred.'))
assert o['child_started_at']<=r['started_at']<=r['admitted_at']<=c['started_at']<=c['finished_at']<=r['finished_at']<=o['finished_at']
for stream in ['stdout','stderr']:
 assert (W/'command'/stream).stat().st_size<=256*1024
 assert c[stream+'_sha256']==sha(W/'command'/stream)
raw=(W/'command/stderr').read_text();names=re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$',raw,re.M)
assert sorted(names)==f['expected_names']==t['expected_names'] and len(names)==39
assert re.search(r'^Ran 39 tests in [0-9.]+s\n\nOK\n$',raw,re.M) and not (W/'command/stdout').read_bytes()
assert t['status']=='passed' and t['tests_run']==39 and all(t[k]==0 for k in ['failures','errors','skipped','expected_failures','unexpected_successes','child_processes','compiler_calls'])
assert all(r[k]==0 for k in ['compiler_calls','provider_probes','B3_compositions']) and not list((W/'tmp').iterdir())
assert r['free_bytes_before']>=16*2**30 and r['free_bytes_after']>=9*2**30
assert len(f['files'])==EXPECTED_INPUT_FILES and sum(v['stamp'][3] for v in f['files'].values())==EXPECTED_INPUT_BYTES
assert read(S/'plan.json')['command']==launch['command'][6:] and read(S/'plan.json')['supervisor_sha256']==sha(A/'scripts/supervise_experiment.py')
for rawpath in [W/'command/stdout',W/'command/stderr',W/'result.json']:
 assert rawpath.stat().st_size<=256*1024
retained=0
for path in W.rglob('*'):
 assert not path.is_symlink()
 if path.is_file():
  assert path.stat().st_size<=256*1024;retained+=path.stat().st_size
 else:assert path.is_dir()
assert retained<=2*2**20 and r['retained_file_bytes']<=retained
assert f['capacity']==launch['capacity']==dict(entry_gib=16,stop_gib=9,floor_gib=8)
prefix_counts={'test_environment.Environment.test_':20,'test_environment.Admission.test_':4,'test_audit_owner.Owner.test_':15}
assert all(name.startswith(tuple(prefix_counts)) for name in names) and len(set(names))==39
for prefix,count in prefix_counts.items():assert sum(name.startswith(prefix) for name in names)==count
proof=dict(status='verified',finished_at=time.time(),controls=39,input_files=len(f['files']),input_bytes=sum(v['stamp'][3] for v in f['files'].values()),receipt_sha256=sha(W/'receipt.json'),result_sha256=sha(W/'result.json'),raw_sha256={s:sha(W/'command'/s) for s in ['stdout','stderr']},supervisor_pid=o['supervisor_pid'],helper_pid=r['pid'],test_pid=c['pid'],exact_names=names,compiler_calls=0,provider_probes=0,process_signals=0,retained_file_bytes=retained,launcher_sha256=sha(L/'record.json'),outer_sha256=sha(S/'status.json'),wrapper_identity_limitation=l['wrapper_identity_limitation'],unavailable_contemporaneous_cwd=missing_cwd,observed_context='Thirty-nine explicit startup controls;20 pure policy fixtures,4 unchanged Controller early-admission sentinels,15 complete saved phase-owner metadata fixtures; no compiler/provider/nested process calls and no actual runtime qualification',verifier_sha256=sha(Path(__file__)))
out=A/'.work/runtime-startup-environment-controls-independent-verification-01.json'
with out.open('x') as f:json.dump(proof,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha(out),receipt_sha256=proof['receipt_sha256'])))
