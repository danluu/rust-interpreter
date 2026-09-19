"""Read-only actual33 audit. Execute only after passed terminal and outer release."""
import hashlib,json,re,time
from pathlib import Path
EXPECTED_LAUNCH = 'c636947988515064dd9a3d7032cf1a696dcde9ae924e8e1d52ab26fc1b951918'  # Exact actual preparation/source binding.
EXPECTED_INPUTS = '671e7d0c7625bf576315a971ed165f92e3cdbf993918d0655a79639a0a0ff40f'  # Exact actual preparation/source binding.
EXPECTED_DISPATCHER = '301e71a7e1869d45f34d83f5b3dee0942443ccbaa8d1da5da0941bc7d6f89c06'  # Exact actual preparation/source binding.
EXPECTED_INPUT_BYTES = 1018181  # Exact actual preparation/source binding.
EXPECTED_INPUT_FILES = 19  # Exact actual preparation/source binding.
A=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
D=A/'experiments/runtime-preflight-retry-controls-05'
W=A/'.work/runtime-preflight-retry-controls-05'
S=A/'.work/experiments/runtime-preflight-retry-controls-supervisor-05'
L=A/'.work/runtime-preflight-retry-controls-launcher-05'
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
assert Path(l['launcher_source_path'])==A/'.work/launch_runtime_preflight_retry_controls_05_bounded.py' and l['launcher_source_sha256']==sha(Path(l['launcher_source_path']))
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
assert r['status']=='passed' and r['controls_passed']==33 and r['pid']==o['child_pid'] and r['parent_pid']==o['supervisor_pid']
assert r['inputs_sha256']==sha(D/'inputs.json') and r['result_sha256']==sha(W/'result.json')
assert len(r['commands'])==1 and r['commands'][0]==dict(path=str(W/'command/receipt.json'),pid=c['pid'],sha256=sha(W/'command/receipt.json'))
assert c['status']=='finished' and c['returncode']==0 and c['command']==f['command'] and c['cwd']=='/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05' and c['environment']==f['environment']
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
assert sorted(names)==f['expected_names']==t['expected_names'] and len(names)==33
assert re.search(r'^Ran 33 tests in [0-9.]+s\n\nOK\n$',raw,re.M) and not (W/'command/stdout').read_bytes()
assert t['status']=='passed' and t['tests_run']==33 and all(t[k]==0 for k in ['failures','errors','skipped','expected_failures','unexpected_successes','child_processes','compiler_calls'])
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
prefix_counts={'test_retry.Owner.test_':19,'test_retry.InheritedLock.test_':7,'test_retry.ControllerAdmission.test_':7}
assert all(name.startswith(tuple(prefix_counts)) for name in names) and len(set(names))==33
for prefix,count in prefix_counts.items():assert sum(name.startswith(prefix) for name in names)==count
proof=dict(status='verified',finished_at=time.time(),controls=33,input_files=len(f['files']),input_bytes=sum(v['stamp'][3] for v in f['files'].values()),receipt_sha256=sha(W/'receipt.json'),result_sha256=sha(W/'result.json'),raw_sha256={s:sha(W/'command'/s) for s in ['stdout','stderr']},supervisor_pid=o['supervisor_pid'],helper_pid=r['pid'],test_pid=c['pid'],exact_names=names,compiler_calls=0,provider_probes=0,process_signals=0,retained_file_bytes=retained,launcher_sha256=sha(L/'record.json'),outer_sha256=sha(S/'status.json'),wrapper_identity_limitation=l['wrapper_identity_limitation'],unavailable_contemporaneous_cwd=missing_cwd,observed_context='Thirty-three explicit retry controls;19 saved owner fixtures,7 real owned temporary-file inherited-lock fixtures,7 early Controller admission guards; observed preheld exclusion checks, not atomic concurrent ownership proof; no compiler/provider/nested process calls and no actual runtime qualification',verifier_sha256=sha(Path(__file__)))
out=A/'.work/runtime-preflight-retry-controls-independent-verification-05.json'
with out.open('x') as f:json.dump(proof,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha(out),receipt_sha256=proof['receipt_sha256'])))
