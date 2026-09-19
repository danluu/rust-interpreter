"""Read-only reconciliation of the one actual bounded ten-directory-fixture child."""
import hashlib,json,re,time
from pathlib import Path
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918');A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
H=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/old-compiler-directory-modes-01');C=O/'experiments/old-compiler-directory-mode-controls-01';W=O/'.work/old-compiler-directory-mode-controls-01';E=O/'.work/experiments/old-compiler-directory-mode-controls-supervisor-01'
def read(p):return json.loads(p.read_bytes())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
f=read(C/'inputs.json');l=read(C/'launch.json');t=read(W/'receipt.json');c=read(W/'command/receipt.json');e=read(E/'status.json');v=read(W/'result.json')
assert sha(C/'launch.json')=='f0a736eaf855990597c3023034c6d976ccae3f644b48d381bb985922898dcae1'
assert sha(C/'inputs.json')==l['inputs_sha256']==t['inputs_sha256']=='d86fd34c8b543160af801fd378c789b5eb0ad43e3cfe22469f4ed015279da9d6'
total=0
for n,r in f['files'].items():
 p=Path(n);s=p.lstat();assert p.resolve()==p and [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]==r['stamp'] and sha(p)==r['sha256'];total+=s.st_size
for n,resolved in f['routes'].items():assert str(Path(n).resolve(strict=True))==resolved
assert e['status']=='finished' and e['returncode']==0 and e['child_pid']==t['pid']==c['supervisor_pid'] and e['supervisor_pid']==t['parent_pid']==c['parent_pid']
assert e['command']==l['command'][6:] and e['cwd']==str(O)
assert e['started_at']<=e['child_started_at']<=t['started_at']<=t['admitted_at']<=c['started_at']<=c['finished_at']<=t['finished_at']<=e['finished_at']
assert t['status']=='passed' and t['controls_passed']==10 and t['commands']==[dict(path=str(W/'command/receipt.json'),sha256=sha(W/'command/receipt.json'),pid=c['pid'])]
assert c['status']=='finished' and c['returncode']==0 and c['command']==f['command'] and c['cwd']==str(H) and c['environment']==f['environment']
ps=c['identity']['ps'].split();assert ps[:3]==[str(c['pid']),str(t['pid']),str(c['pid'])] and ps[9:]==c['command']
assert c['identity']['cwd']=='p'+str(c['pid'])+'\nfcwd\nn'+str(H)+'\n' and c['identity']['ps_returncode']==c['identity']['cwd_returncode']==0
for stream in ['stdout','stderr']:assert sha(W/'command'/stream)==c[stream+'_sha256']
assert not (W/'command/stdout').read_bytes()
s=(W/'command/stderr').read_text();assert sorted(re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$',s,re.M))==f['expected_names'];assert re.search(r'Ran 10 tests in [0-9.]+s\n\nOK\n$',s)
assert v['status']=='passed' and v['tests_run']==10 and v['expected_names']==f['expected_names'] and sha(W/'result.json')==t['result_sha256']
assert all(v[k]==0 for k in ['failures','errors','skipped','expected_failures','unexpected_successes','child_processes','compiler_calls','provider_probes','network_calls','signal_calls']) and not list((W/'tmp').iterdir())
assert v['writable_names']==34 and v['directories']==52 and v['maximum_writable_names']==256 and v['maximum_directory_names']==2048
assert v['local_reads']==sorted([str(H/'directory_modes.py'),str(H/'test_directory_modes.py'),str(H.parent/'old-compiler-partial-retirement-01/fd_remove.py')])
launch_record=O/'.work/old-compiler-directory-mode-controls-launch-01.actual.json';a=read(launch_record)
assert a['command']==l['command'] and a['environment']==l['environment'] and a['cwd']==str(O) and a['launcher_returncode']==0
assert a['launch_sha256']==sha(C/'launch.json') and a['started_at']<=a['launcher_finished_at']<=e['finished_at'] and a['started_at']<=e['started_at']
raw_launcher={}
for kind in ['stdout','stderr']:
 p=O/('.work/old-compiler-directory-mode-controls-launch-01.'+kind);assert sha(p)==a[kind+'_sha256'];raw_launcher[kind]=dict(path=str(p),sha256=sha(p))
assert a['status']=='terminal-observed' and a['outer_sha256']==sha(E/'status.json') and e['finished_at']<=a['terminal_observed_at']
handoff=read(O/'.work/old-compiler-directory-mode-controls-launch-01.stdout');assert handoff['supervisor_pid']==e['supervisor_pid'] and handoff['directory']==str(E)
assert a['launcher_sha256']==sha(O/'.work/launch_directory_mode_controls_01.py')
outer_plan=read(E/'plan.json');assert outer_plan['command']==e['command'] and sha(E/'plan.json')==e['plan_sha256'] and sha(E/'command.log')==e['log_sha256']
report=dict(status='verified',controls=10,children=1,checked_at=time.time(),receipt_sha256=sha(W/'receipt.json'),result_sha256=sha(W/'result.json'),outer_sha256=sha(E/'status.json'),child_sha256=sha(W/'command/receipt.json'),inputs_sha256=sha(C/'inputs.json'),frozen_files=len(f['files']),frozen_bytes=total,actual_compiler_calls=0,actual_filesystem_fixtures=10,actual_production_prefix_mutations=0,actual_nested_processes=0,actual_network_calls=0,actual_signal_calls=0,verifier_sha256=sha(Path(__file__)),launcher_sha256=sha(launch_record),launcher_raw=raw_launcher,admitted_at=t['admitted_at'],released_at=e['finished_at'],exact_argv_environment_cwd_parentage_raw_and_times=True,limitation='Detached supervisor launcher return is distinct from later terminal closure; both histories retained.')
p=O/'.work/old-compiler-directory-mode-controls-independent-verification-01.json';assert not p.exists();p.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,indent=2));print(sha(p))
