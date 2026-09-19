"""Read-only full closed archive and actual launcher/controller reconciliation."""
import gzip,hashlib,json,tarfile,time
from pathlib import Path
O=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913');H=O/'experiments/old-compiler-published-retirement-evidence-01';W=O/'.work/old-compiler-published-retirement-evidence-01';R=O/'results/old-compiler-published-retirement-01';P=O/'.work/old-compiler-published-retirement-evidence-launch-01'
def read(p):return json.loads(p.read_bytes())
def sha(p):
 with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
plan=read(H/'plan.json');f=read(H/'inputs.json');l=read(H/'launch.json')
assert l['command'][3]=='--run-id'
E=O/'.work/experiments'/l['command'][4]
t=read(W/'receipt.json');e=read(E/'status.json');a=read(Path(str(P)+'.actual.json'))
assert sha(H/'launch.json')=='290f6aab9cb41f4222eb174a3cb78d19f49ee10755916a4fb7fdf0ed3d29489b'
assert sha(H/'inputs.json')=='824d1377e3b0cabf2f9beea39852aa98ef7c561caa8fffa92bd759dade3a0c95'
for name,row in f['files'].items():
 p=Path(name);s=p.lstat();assert p.resolve()==p and {k:getattr(s,'st_'+k) for k in row['identity']}==row['identity'] and sha(p)==row['sha256']
assert t['status']=='passed' and t['children']==[] and t['compiler_or_cleanup_execution'] is False
assert t['reservation_bytes']==plan['reservation_bytes']==128*2**20 and t['free_bytes_before']>=plan['entry_free_bytes']==9*2**30+128*2**20 and t['free_bytes_after']>=9*2**30
assert e['status']=='finished' and e['returncode']==0 and e['child_pid']==t['pid'] and e['supervisor_pid']==t['parent_pid']
assert e['command']==l['command'][6:] and e['cwd']==str(O)
assert e['started_at']<=e['child_started_at']<=t['started_at']<=t['admitted_at']<=t['finished_at']<=e['finished_at']<=a['terminal_observed_at']
assert a['command']==l['command'] and a['environment']==l['environment'] and a['cwd']==l['cwd'] and a['launcher_returncode']==0
assert a['status']=='terminal-observed' and a['outer_status']=='finished' and a['outer_returncode']==0 and a['outer_sha256']==sha(E/'status.json')
assert a['started_at']<=a['launcher_finished_at']<=a['terminal_observed_at'] and a['started_at']<=e['started_at']
for kind in ['stdout','stderr']:assert sha(Path(str(P)+'.'+kind))==a[kind+'_sha256']
assert read(E/'plan.json')['command']==e['command'] and sha(E/'plan.json')==e['plan_sha256'] and sha(E/'command.log')==e['log_sha256']
for name,checks in plan['receipt_checks'].items():
 actual=read(Path(name));assert all(actual[k]==v for k,v in checks.items())
manifest=read(R/'manifest.json');expected={name:{key:row[key] for key in ['bytes','sha256']} for name,row in plan['members'].items()}
assert manifest['members']==expected and manifest['historical_source_substitutions']==plan['historical_source_substitutions'] and manifest['historical_freezes']==plan['historical_freezes']
assert t['archive_sha256']==sha(R/'evidence.tar.gz') and t['manifest_sha256']==sha(R/'manifest.json')
with tarfile.open(R/'evidence.tar.gz','r:gz') as tar:
 members=tar.getmembers();assert len(members)==len(expected)==plan['member_count']==t['members']==164
 assert len({member.name for member in members})==len(members) and {member.name for member in members}==set(expected)
 logical=0
 for member in members:
  row=expected[member.name];assert member.isfile() and member.size==row['bytes'];source=tar.extractfile(member);digest=hashlib.sha256();count=0
  while data:=source.read(2**20):digest.update(data);count+=len(data)
  assert count==row['bytes'] and digest.hexdigest()==row['sha256'];logical+=count
 while tar.fileobj.read(2**20):pass
assert logical==plan['logical_bytes']==t['logical_bytes']==368657707
assert (R/'evidence.tar.gz').stat().st_size<=plan['archive_limit_bytes']==64*2**20
expanded=0
with gzip.open(R/'evidence.tar.gz','rb') as stream:
 while data:=stream.read(2**20):
  expanded+=len(data);assert expanded<=384*2**20+2**20
assert expanded>=logical and len(f['files'])==165
assert manifest['scope']==plan['scope']
assert sum(row['identity']['size'] for row in f['files'].values())==368724386
assert t['full_member_bytes_and_gzip_trailer_verified'] is True
closed=read(O/'.work/old-compiler-published-retirement-independent-verification-01.json')
assert closed['retired_entries']==8389 and closed['ledger_events']==25167 and closed['mode_ledger_events']==4215
assert closed['unique_ready_sha256']=='ff93b6ae55e28406d6c88d0c1bc680f46ecae7f14014f54b83e84a8b34edaeda'
for name in ['deleted.jsonl','directory-modes.jsonl','writable-inventory.json','preserved-ready.json']:
 path=O/'.work/old-compiler-published-retirement-01'/name
 assert str(path).lstrip('/') in expected and expected[str(path).lstrip('/')]['sha256']==sha(path)
assert read(Path(str(P)+'.stdout'))['supervisor_pid']==e['supervisor_pid']
assert a['launcher_sha256']==sha(O/'.work/launch_old_compiler_partial_retirement_evidence_01.py')
assert str(t['pid']) in e['child_identity'] and str(t['parent_pid']) in e['child_identity']
assert e['command'][2] in e['child_identity'] and str(e['supervisor_pid']) in e['supervisor_identity']
report=dict(status='verified',checked_at=time.time(),members=164,logical_bytes=logical,expanded_bytes=expanded,archive_bytes=(R/'evidence.tar.gz').stat().st_size,all_member_hashes_and_full_gzip_trailer_verified=True,frozen_files=len(f['files']),closed_retired_entries=8389,retained_durable_events=25167,retained_mode_events=4215,retained_directory_mode_controls=10,retained_readonly_probes=2,retained_remover_controls=12,original_history_members=52,archive_sha256=sha(R/'evidence.tar.gz'),manifest_sha256=sha(R/'manifest.json'),receipt_sha256=sha(W/'receipt.json'),outer_sha256=sha(E/'status.json'),launcher_sha256=sha(Path(str(P)+'.actual.json')),verifier_sha256=sha(Path(__file__)),actual_workload_children=0,actual_deletions=0,compiler_or_provider_payloads_archived=False,actual=dict(supervisor_pid=e['supervisor_pid'],helper_pid=t['pid'],admitted_at=t['admitted_at'],finished_at=t['finished_at'],released_at=e['finished_at'],free_bytes_after=t['free_bytes_after']),limitation='This execution only retained already closed evidence. Historical failures stay failed; original published-prefix cleanup and its quiescence are retained observations, not repeated actions.')
out=O/'.work/old-compiler-published-retirement-evidence-verification-01.json';assert not out.exists();out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,indent=2));print(sha(out))
