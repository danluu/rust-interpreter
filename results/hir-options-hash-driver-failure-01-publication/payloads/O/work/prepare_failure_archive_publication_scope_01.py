"""Bounded metadata/byte census for the closed archive publication capsule."""
import hashlib
import json
from pathlib import Path
import stat
import time

R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
W=R/'.work'; OW=O/'.work'; D=R/'results/hir-options-hash-driver-failure-01'
rows={}
def identity(p):
 s=p.lstat();return {k:getattr(s,'st_'+k) for k in ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def add(p,role):
 p=Path(p);before=identity(p);assert p.resolve(strict=True)==p and stat.S_ISREG(before['mode']) and before['size']<=2*2**20
 digest=sha(p);assert identity(p)==before
 if str(p) in rows:
  assert rows[str(p)]['identity']==before and rows[str(p)]['sha256']==digest
  rows[str(p)]['roles']=sorted(set(rows[str(p)]['roles']+[role]));return
 for name,root in [('ROOT',R),('O',O),('X',X)]:
  if p.is_relative_to(root):
   destination='payloads/'+name+'/'+'/'.join('work' if n=='.work' else n for n in p.relative_to(root).parts);break
 else:raise AssertionError('outside three explicit source owners')
 rows[str(p)]=dict(source=str(p),destination=destination,size=before['size'],sha256=digest,identity=before,roles=[role])
 assert len(rows)<=128 and sum(r['size'] for r in rows.values())<=4*2**20
def tree(root,role):
 assert root.resolve(strict=True)==root and root.is_dir()
 for p in sorted(root.rglob('*')):
  assert not p.is_symlink()
  if p.is_file():add(p,role)
  else:assert p.is_dir()

for n in ['01','02']:tree(R/('experiments/hash-driver-failure-evidence-'+n),'immutable archive/auditor source and narrow successor history')
for n in ['01','02']:tree(W/('hash-driver-failure-retention-execution-'+n),'closed archive processing attempt source/raw/record')
tree(W/'hash-driver-failure-archive-auditor-before-bounded-gzip-01','preserved unexecuted bounded-reader draft and correction')
tree(OW/'hash-driver-failure-retention-audit-execution-02','closed independent archive audit source/raw/record')
tree(W/'hash-driver-failure-evidence-01','actual passed archive receipt')
for n in ['hash-driver-failure-archive-environment-probe-01.json','hash-driver-failure-archive-root-completed-review-01.json',
          'hash-driver-failure-archive-audit-root-source-review-01.json','hash-driver-failure-archive02-audit-root-source-review-01.json',
          'hash-driver-failure-archive-root-source-review-01.json','hash-driver-failure-archive02-root-source-review-01.json']:
 add(W/n,'root independent source/current-byte review or pure startup diagnostic')
for n in ['hash-driver-failure-retention-proposal-01.json','hash-driver-failure-archive-source-handoff-01.json',
          'hash-driver-failure-archive-verifier-source-handoff-01.json','hash-driver-failure-archive-verifier-source-handoff-02.json',
          'hash-driver-failure-archive-source02-handoff-01.json','hash-driver-failure-retention-audit02-binding-review-01.json',
          'hash-driver-failure-retention-independent-verification-02.json']:
 add(OW/n,'exact selection/source history and passed independent archive audit')
for p in [OW/'propose_hash_driver_failure_retention_01.py',W/'execute_hash_driver_failure_audit_01.py',
          OW/'execute_hash_driver_packet_review_05.py',R/'experiments/old-compiler-published-retirement-evidence-01/archive.py',
          X/'experiments/stable-cgu/owned_stage.py']:
 add(p,'source census or exact previously passed wrapper/engine comparison')
add(W/'hir-options-hash-driver-independent-verification-02.json','separate successful driver02 qualification reference')
add(Path(__file__).resolve(),'publication census source')

audit_path=OW/'hash-driver-failure-retention-independent-verification-02.json'
audit=json.loads(audit_path.read_bytes());assert sha(audit_path)=='b08b4dcaf82f09267f8a05aa09218b2fb952781881665008259415b642a0f3f0'
assert audit['status']=='verified' and audit['original_status']=='failed' and audit['selected_files']==168 and audit['workload_children']==0
driver_path=W/'hir-options-hash-driver-independent-verification-02.json';driver=json.loads(driver_path.read_bytes())
assert sha(driver_path)=='9540ad45b5423f793e323bac31d593f1c1b030fe0e1dd5fc3665565277885ebb'
assert driver['status']=='verified' and driver['hash_driver_qualified'] is True and driver['application_qualified'] is False
protected=[]
assert sorted(p.name for p in D.iterdir())==['evidence.tar.gz','manifest.json','previous-attempt.json','proposal.json','summary.json']
for p in sorted(D.iterdir()):
 before=identity(p);assert p.resolve(strict=True)==p and stat.S_ISREG(before['mode']) and before['size']<=32*2**20
 digest=sha(p);assert identity(p)==before
 protected.append(dict(source=str(p),sha256=digest,size=before['size'],identity=before))
assert next(r['sha256'] for r in protected if r['source'].endswith('/evidence.tar.gz'))==audit['archive']['sha256']=='ff7870ea202cd33b7c91e2afe8b3784780fee1d9239a7df6394eaf0560417216'
summary=dict(status='passed-and-independently-verified-retention',original_driver_status='failed',original_compiler_children=1,
 original_driver_processes=0,archive_attempts=dict(first='failed before WORK/result creation on exact startup environment check',second='passed'),
 archive_workload_children=0,archive=dict(directory=str(D),sha256=audit['archive']['sha256'],bytes=audit['archive']['bytes'],
   members=168,logical_bytes=40467639,expanded_bytes=audit['archive']['expanded_bytes']),
 archive_audit=dict(path=str(audit_path),sha256=sha(audit_path)),
 separate_driver02=dict(status='independently-qualified',audit=dict(path=str(driver_path),sha256=sha(driver_path)),application_qualified=False),
 scope='Small publication capsule for closed failure01 archive02, both archive attempts and explicit startup diagnostic, immutable source/diffs, actual independent full member/EOF audit. The original driver01 failure remains failed; driver02 qualification is separate.',
 original_archive_directory_preserved=True,originals_preserved=True,git_mutations=False)
readme='''# Failed driver01 archive and retention history

The original driver01 compiler invocation failed and neither planned driver
process ran. Its full selected proof was retained by archive02 and independently
audited: 168 members, 40,467,639 logical bytes, and 13,134,758 compressed bytes.
The adjacent hir-options-hash-driver-failure-01 directory contains the five
unchanged archive/proof files. This capsule supplies the archive sources,
bounded execution and audit receipts/raw, source reviews and preserved drafts.

The first archive attempt refused the macOS startup environment before making
WORK or output. Source02 requires the exact passed environment plus the one
observed CF startup variable, and records both separately. Its retained prior
capsule preserves the failure and separate read-only diagnostic. The failed
attempt and source01 were not overwritten or retried unchanged.

The 34 reused gzip blobs and native03 base remain explicit references to two
published archives, including exact member aliases, SHA-256 and Git object IDs.
The new archive contains all 65 newly stored gzip blobs. Complete transitive
recovery requires those referenced prior archives.

Driver02 subsequently passed a separate three-command workload and independent
audit9540; that separate success does not relabel driver01. No application or
performance qualification is claimed here. STATUS.md and summary.json record
these outcomes; prepared source READMEs retain their historical wording.
'''
status='''# Status

- Driver01: one failed compiler invocation; zero driver processes; retained unchanged.
- Archive01: startup-environment refusal before WORK/result creation; retained unchanged.
- Archive02: passed once; all 168 members and gzip EOF independently verified (audit b08b4dca).
- Driver02: independently qualified by separate audit 9540ad45 (three commands, two driver processes).
- This capsule: exact ordinary evidence copies only; no compiler/provider workload, cleanup or Git mutation.

The original five archive result files remain byte- and identity-identical.
'''
files=sorted(rows.values(),key=lambda r:r['destination']);assert len(files)==len({r['destination'] for r in files})
proposal=dict(status='proposed-unpublished',created_at=time.time(),destination=str(R/'results/hir-options-hash-driver-failure-01-publication'),
 files=files,file_count=len(files),source_bytes=sum(r['size'] for r in files),maximum_files=128,maximum_source_bytes=4*2**20,
 maximum_file_bytes=2*2**20,maximum_publication_bytes=6*2**20,generated_files=['README.md','STATUS.md','summary.json','manifest.json','publication-proposal.json'],
 protected_result_directory=str(D),protected_results=protected,protected_result_files=5,
 required_evidence=sorted(str(p) for p in [audit_path,W/'hash-driver-failure-evidence-01/receipt.json',
     W/'hash-driver-failure-retention-execution-01/record.json',W/'hash-driver-failure-retention-execution-02/record.json',
     OW/'hash-driver-failure-retention-audit-execution-02/record.json',W/'hash-driver-failure-archive-environment-probe-01.json']),
 summary=summary,readme=readme,status_document=status,copy_contract='Exact fresh ordinary copies only after review. Complete source and output byte/identity readback; all five adjacent original archive files untouched; no original or Git mutation.')
out=OW/'hash-driver-failure-retention-publication-proposal-01.json'
with out.open('x') as f:json.dump(proposal,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha(out),files=len(files),source_bytes=proposal['source_bytes'])))
