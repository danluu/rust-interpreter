import hashlib,json,re,time
from pathlib import Path
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
D=A/'experiments/bounded-proof-snapshot-controls-v2-01'
W=A/'.work/bounded-proof-snapshot-controls-v2-01'
S=A/'.work/experiments/bounded-proof-snapshot-controls-v2-supervisor-01'
L=A/'.work/proof-snapshot-controls-v2-launch-execution-01'
def read(p):return json.loads(p.read_bytes())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def stamp(p):
 s=p.lstat();return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]
assert sha(D/'launch.json')=='8c3b162a55ee17468d4f722d2c9d9d970babc3ba09c4c4f53ad7078a081258f1'
assert sha(D/'inputs.json')=='0880defb3dfe6e37491856badd700748b868dbf255331fe3429bdb5e2438048c'
f=read(D/'inputs.json');launch=read(D/'launch.json');r=read(W/'receipt.json');c=read(W/'command/receipt.json');o=read(S/'status.json');l=read(L/'record.json');t=read(W/'result.json')
for n,v in f['files'].items():
 p=Path(n);assert p.resolve(strict=True)==p and stamp(p)==v['stamp'] and sha(p)==v['sha256'] and stamp(p)==v['stamp'],n
for n,v in f['routes'].items():assert str(Path(n).resolve(strict=True))==v,n
assert l['launch_path']==str(D/'launch.json') and l['launch_sha256']==sha(D/'launch.json')
assert Path(l['launcher_source_path'])==A/'.work/launch_proof_snapshot_controls_v2_01.py' and l['launcher_source_sha256']==sha(Path(l['launcher_source_path']))
assert l['status']=='terminal-observed' and l['returncode']==0 and l['command']==launch['command'] and l['environment']==launch['environment'] and l['cwd']==str(A)
assert l['launcher_source_sha256']=='33220be13feea7d316c2eb523b48f85afa878fb4d502abf1e847eaf54ff22cd2'
assert l['launcher_returncode']==0 and l['outer_status']=='finished' and l['outer_sha256']==sha(S/'status.json')
assert l['supervisor_pid']==o['supervisor_pid'] and l['controller_pid']==r['pid']
assert o['finished_at']<=l['terminal_observed_at']==l['finished_at'] and l['started_at']<=l['launcher_finished_at']<=l['finished_at']
assert l['maximum_wrapper_seconds']==30 and l['maximum_observation_seconds']==1800 and l['entry_free_bytes']>=16*2**30
assert l['launcher_identity']['source']=='in-process observation' and l['launcher_identity']['pid']==l['launcher_pid']
assert l['launcher_identity']['parent_pid']==l['launcher_parent_pid'] and l['launcher_identity']['cwd']==str(A)
assert l['wrapper_identity_limitation']=='Popen PID retained; no separate contemporaneous wrapper ps/cwd probe.'
for stream in ['stdout','stderr']:assert l[stream+'_sha256']==sha(L/stream)
hand=read(L/'stdout');assert hand==l['supervisor_handoff'];assert hand['supervisor_pid']==o['supervisor_pid'] and hand['directory']==str(S)
assert o['status']=='finished' and o['returncode']==0 and o['command']==launch['command'][6:] and o['cwd']==str(A)
assert o['plan_sha256']==sha(S/'plan.json') and o['log_sha256']==sha(S/'command.log')
assert r['status']=='passed' and r['controls_passed']==22 and r['pid']==o['child_pid'] and r['parent_pid']==o['supervisor_pid']
assert r['inputs_sha256']==sha(D/'inputs.json') and r['result_sha256']==sha(W/'result.json')
assert len(r['commands'])==1 and r['commands'][0]==dict(path=str(W/'command/receipt.json'),pid=c['pid'],sha256=sha(W/'command/receipt.json'))
assert c['status']=='finished' and c['returncode']==0 and c['command']==f['command'] and c['cwd']==str(A/'experiments/bounded-proof-snapshots-v2') and c['environment']==f['environment']
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
for stream in ['stdout','stderr']:assert c[stream+'_sha256']==sha(W/'command'/stream)
raw=(W/'command/stderr').read_text();names=re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$',raw,re.M)
assert sorted(names)==f['expected_names']==t['expected_names'] and len(names)==22
assert re.search(r'^Ran 22 tests in [0-9.]+s\n\nOK\n$',raw,re.M) and not (W/'command/stdout').read_bytes()
assert t['status']=='passed' and t['tests_run']==22 and all(t[k]==0 for k in ['failures','errors','skipped','expected_failures','unexpected_successes','child_processes','compiler_calls'])
assert all(r[k]==0 for k in ['compiler_calls','provider_probes','B3_compositions']) and not list((W/'tmp').iterdir())
assert r['free_bytes_before']>=16*2**30 and r['free_bytes_after']>=9*2**30
proof=dict(status='verified',finished_at=time.time(),controls=22,input_files=len(f['files']),input_bytes=sum(v['stamp'][3] for v in f['files'].values()),receipt_sha256=sha(W/'receipt.json'),result_sha256=sha(W/'result.json'),raw_sha256={s:sha(W/'command'/s) for s in ['stdout','stderr']},supervisor_pid=o['supervisor_pid'],helper_pid=r['pid'],test_pid=c['pid'],exact_names=names,compiler_calls=0,provider_probes=0,process_signals=0,unavailable_contemporaneous_cwd=missing_cwd,observed_context='twenty-two tiny lossless snapshot and reference-reuse fixtures; no actual provider/compiler/process calls',wrapper_identity_limitation=l['wrapper_identity_limitation'],verifier_sha256=sha(Path(__file__)))
out=A/'.work/proof-snapshot-controls-v2-independent-verification-01.json'
with out.open('x') as f:json.dump(proof,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha(out),receipt_sha256=proof['receipt_sha256'])))
