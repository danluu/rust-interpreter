"""Reversible exact evidence copies; no workload or Git mutation."""
from pathlib import Path
import hashlib,json,os,stat,time
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913');OUT=R/'results/old-compiler-published-retirement-01';EX=OUT/'archive-execution';assert EX.is_dir() and not EX.is_symlink()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def identity(p):
 s=p.lstat();return {k:getattr(s,'st_'+k) for k in ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']}
def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
manifest={}
def copy(source,relative):
 source=Path(source);before=identity(source);assert source.resolve(strict=True)==source and stat.S_ISREG(before['mode']) and before['size']<=96*2**20
 data=source.read_bytes();assert identity(source)==before
 target=EX/relative;target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():assert target.is_file() and not target.is_symlink() and target.read_bytes()==data
 else:
  with target.open('xb') as f:assert f.write(data)==len(data);f.flush();os.fsync(f.fileno())
 assert target.read_bytes()==data
 manifest[relative]=dict(source=str(source),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
items={
 'receipt.json':'.work/old-compiler-published-retirement-evidence-01/receipt.json',
 'independent-verification.json':'.work/old-compiler-published-retirement-evidence-verification-02.json',
 'packet-review.json':'.work/e48-retention-packet-independent-review-01.json',
 'packet-verifier.py':'.work/verify_e48_retention_packet_01.py',
 'launch.py':'.work/launch_old_compiler_published_retirement_evidence_01.py',
 'launch-from-qualified.diff':'.work/launch_old_compiler_published_retirement_evidence_01.from-qualified.diff',
 'verify.py':'.work/verify_old_compiler_published_retirement_evidence_02.py',
 'verify-from-01.diff':'.work/verify_old_compiler_published_retirement_evidence_02.from-01.diff',
 'original-audit-attempt/verify.py':'.work/verify_old_compiler_published_retirement_evidence_01.py',
 'original-audit-attempt/observation.json':'.work/e48-archive-verifier-preflight-observation-01.json',
 'publication-copy/preflight-failure.json':'.work/e48-publication-packing-failure-01.json',
 'publication-copy/package.py':'.work/package_e48_evidence_02.py',
}
for relative,source in items.items():copy(R/source,relative)
for suffix in ['actual.json','stdout','stderr']:copy(R/('.work/old-compiler-published-retirement-evidence-launch-01.'+suffix),'launcher/'+suffix)
for dirname,relative in [('.work/experiments/old-compiler-published-retirement-evidence-supervisor-01','outer'),('.work/old-compiler-published-retirement-evidence-preparation-01','preparation'),('.work/e48-archive-verification-execution-02','verification-execution')]:
 base=R/dirname
 for path in sorted(base.rglob('*')):
  assert not path.is_symlink()
  if path.is_file():copy(path,relative+'/'+str(path.relative_to(base)))
assert {str(p.relative_to(EX)) for p in EX.rglob('*') if p.is_file()}==set(manifest)
write(EX/'manifest.json',manifest)
audit=json.loads((EX/'independent-verification.json').read_bytes())
summary=dict(status='passed',scope='Retained completed e48 published compiler-prefix retirement evidence; zero new compiler, provider or deletion children.',
 closed_retirement=dict(retired_entries=8389,retired_files=6983,retired_directories=1406,deletion_events=25167,directory_mode_changes=1405,mode_events=4215,changed_files=0,changed_root=False,readonly_probes=2,remover_fixture_controls=12,directory_mode_fixture_controls=10,original_history_members=52),
 archive=dict(path='evidence.tar.gz',sha256=sha(OUT/'evidence.tar.gz'),bytes=(OUT/'evidence.tar.gz').stat().st_size,members=164,logical_bytes=368657707,expanded_bytes=368936960,full_member_and_gzip_eof_verified=True,manifest_sha256=sha(OUT/'manifest.json')),
 actual_archive=dict(receipt_sha256=sha(EX/'receipt.json'),audit_sha256=sha(EX/'independent-verification.json'),workload_children=0,actual_deletions=0,**audit['actual']),
 packet=dict(launch_sha256=sha(R/'experiments/old-compiler-published-retirement-evidence-01/launch.json'),inputs_sha256=sha(R/'experiments/old-compiler-published-retirement-evidence-01/inputs.json'),members=164,frozen_files=165,entry_free_bytes=9*2**30+128*2**20,live_free_gib=9),
 archive_execution_manifest_sha256=sha(EX/'manifest.json'),
 preservation=dict(original_retirement_and_comparison_failures_preserved=True,historical_absences_kept_historical=True,live_provider_payloads_included=False,original_audit_attempt='Original read-only verifier source and unknown-completion observation retained; corrected read-only successor passed. No archive rerun.'),created_at=time.time())
write(OUT/'summary.json',summary)
with (OUT/'README.md').open('x') as f:
 f.write('''# Closed e48 compiler-prefix retirement evidence

This preserves the completed removal of one superseded compiler installation: 8,389 entries, 25,167 deletion events and 4,215 events for 1,405 directory-only mode changes. The unique ready metadata, complete original/writable inventories, two read-only probes, successful 12+10 helper controls, original failed comparisons and 52-member historical archive remain recoverable. Current compiler/provider payloads are excluded.

The evidence-only archive ran once with zero workload children and zero deletions. All 164 members (368,657,707 logical bytes) and the full 368,936,960-byte gzip expansion were independently read back. The compressed archive is 42,439,437 bytes. Admission used 9 GiB plus 128 MiB reservation, with 9 GiB live checks.

`archive-execution` retains the actual dispatcher/outer/controller records, read-only preparation, full packet review and successful independent readback. An initial read-only verifier retained a predecessor launcher basename and produced no retained completion; its source and limitation are preserved. The successor corrects that path and passes against the same original archive. No cleanup or archive was repeated. Historical failures and past absence observations retain their original meaning.
''');f.flush();os.fsync(f.fileno())
roots=[R/'experiments/old-compiler-published-retirement-01',R/'experiments/old-compiler-published-retirement-evidence-01',OUT]
files={}
for base in roots:
 for p in sorted(base.rglob('*')):
  assert not p.is_symlink()
  if p.is_file():files[str(p.relative_to(R))]=dict(sha256=sha(p),bytes=p.stat().st_size)
proposal=dict(status='ready-for-root-direct-exact-path-commit',paths=sorted(files),files=files,root=str(R),unchanged_source_worktree=True,
 archive_audit_sha256=sha(EX/'independent-verification.json'),scope='Only completed e48 controller/evidence sources and retained result; excludes raw-profile/intermediate/hash/runtime drafts.',git_mutations=0,created_at=time.time())
write(R/'.work/e48-retirement-evidence-publication-01.json',proposal)
with (R/'.work/e48-retirement-evidence-publication-paths-01.txt').open('x') as f:f.write('\n'.join(sorted(files))+'\n')
print(json.dumps(dict(files=len(files),bytes=sum(row['bytes'] for row in files.values()),proposal_sha256=sha(R/'.work/e48-retirement-evidence-publication-01.json'),path_list_sha256=sha(R/'.work/e48-retirement-evidence-publication-paths-01.txt'),summary_sha256=sha(OUT/'summary.json')),indent=2))
