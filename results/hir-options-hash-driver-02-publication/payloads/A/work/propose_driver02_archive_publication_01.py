"""Bounded read-only lossless publication census; no copies, archives or Git writes."""
import hashlib,json,stat,time
from pathlib import Path
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913');A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918');O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918');X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918');D=R/'results/hir-options-hash-driver-02';F=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
rows={};trees={}
def identity(p):return {k:getattr(p.lstat(),'st_'+k) for k in F}
def read(p,limit=2*2**20):
 before=identity(p);assert p.resolve(strict=True)==p and stat.S_ISREG(before['mode']) and before['size']<=limit
 b=p.read_bytes();assert identity(p)==before and len(b)==before['size'];return b,before
def sha(p):return hashlib.sha256(read(p,16*2**20)[0]).hexdigest()
def add(p,role):
 p=Path(p);b,i=read(p);digest=hashlib.sha256(b).hexdigest()
 if str(p) in rows:
  assert rows[str(p)]['identity']==i and rows[str(p)]['sha256']==digest;rows[str(p)]['roles']=sorted(set(rows[str(p)]['roles']+[role]));return
 for name,root in [('ROOT',R),('A',A),('O',O),('X',X)]:
  if p.is_relative_to(root):destination='payloads/'+name+'/'+'/'.join('work' if part=='.work' else part for part in p.relative_to(root).parts);break
 else:raise AssertionError('source outside four explicit owners')
 rows[str(p)]=dict(source=str(p),destination=destination,size=len(b),sha256=digest,identity=i,roles=[role])
 assert len(rows)<=256 and sum(r['size'] for r in rows.values())<=8*2**20

def tree(p,role):
 assert p.resolve()==p and p.is_dir();members={'.':dict(kind='directory',identity=identity(p))}
 for q in sorted(p.rglob('*')):
  i=identity(q);assert q.resolve()==q and (stat.S_ISDIR(i['mode']) or stat.S_ISREG(i['mode']))
  members[str(q.relative_to(p))]=dict(kind='directory' if stat.S_ISDIR(i['mode']) else 'file',identity=i)
  if q.is_file():add(q,role)
 trees[str(p)]=members

for n in ['01','02','03']:tree(R/('experiments/hash-driver-success-evidence-'+n),'archive/auditor exact source and preserved prior drafts/diffs')
for n in ['01','02']:tree(R/'.work'/('hash-driver-success-retention-execution-'+n),'archive processing attempt full source/record/raw; failed01 distinct from passed02')
for n in ['02','03']:tree(A/'.work'/('hash-driver-success-retention-audit-execution-'+n),'independent readback attempt full source/record/raw; failed02 distinct from passed03')
tree(R/'.work/hash-driver-success-evidence-01','passed actual archive02 terminal')
tree(R/'.work/published-failure-archive-git-proof-01','actual Git recovery proof complete44 payload files plus report')
add(R/'.work/verify_published_failure_archive_git_01.py','exact executed Git proof source')
for name in ['hash-driver-success-archive-root-source-review-01.json','hash-driver-success-archive02-root-source-review-01.json','hash-driver-success-archive02-audit-root-source-review-01.json','hash-driver-success-archive03-root-source-review-01.json']:
 add(R/'.work'/name,'ROOT independent source/scope/readback reviews')
for name in ['hash-driver02-lossless-publication-scope-01.json','hash-driver02-lossless-publication-scope-02.json','hash-driver02-archive-source-self-review-01.json','hash-driver-success-archive02-schema-census-01.json','inspect_driver02_archive_metadata_02.py','hash-driver-success-archive-auditor-source-review-02.json','hash-driver-success-archive-audit02-failure-source-map-01.json','hash-driver-success-archive-audit03-source-review-01.json','hash-driver-success-retention-independent-verification-03.json']:
 add(A/'.work'/name,'scope/evidence schema history and complete final independent archive audit')
for name in ['published-failure-git-proof-independent-source-review-01.json','published-failure-git-proof-independent-source-review-02.json','published-failure-git-proof-before-lifecycle-review-01.py']:
 add(O/'.work'/name,'independent Git proof source review and preserved source-only predecessor')
add(O/'.work/publish_failure_archive_capsule_01.py','previously executed publication copier comparison')
add(O/'.work/hash-driver-failure-retention-publication-verification-01.json','closed separate failed-driver archive publication reference')
add(Path(__file__).resolve(),'exact publication census source')

archive_audit=A/'.work/hash-driver-success-retention-independent-verification-03.json';audit=json.loads(read(archive_audit)[0]);assert sha(archive_audit)=='6473ffef9b51944ccc660e2e074769042b044290576d3732e09a526b94bd545b'
assert audit['status']=='verified' and audit['selected_files']==241 and audit['retained_current_qualified_children']==3 and audit['retained_historical_failed_compiler_children']==1 and audit['retained_total_actual_hash_children']==4 and audit['hash_driver_qualified'] is True
scope=A/'.work/hash-driver02-lossless-publication-scope-02.json';original=json.loads(read(scope)[0]);assert sha(scope)=='f6ea57ce5485de96bcc00aa6bb872cf2560ba023df48affea533806e3fac7264'
protected=[];assert sorted(p.name for p in D.iterdir())==['evidence.tar.gz','manifest.json','previous-attempt.json','proposal.json','summary.json']
for p in sorted(D.iterdir()):
 b,i=read(p,16*2**20);protected.append(dict(source=str(p),sha256=hashlib.sha256(b).hexdigest(),size=len(b),identity=i))
assert next(r['sha256'] for r in protected if r['source'].endswith('/evidence.tar.gz'))==audit['archive']['sha256']=='0ac226eb1a6c17d7db0c3e4a4140183b584cf5cf55180959ffb05b0c86ba5dcd'
assert audit['archive']['members']==241 and audit['archive']['logical_bytes']==13880266 and audit['archive']['bytes']==2559860
summary=dict(status='driver02-and-lossless-retention-independently-verified',driver=dict(current_qualified_children=3,compilations=1,driver_processes=2,contexts_per_process=8,records_per_process=9,historical_failed_compiler_children=1,total_actual_hash_children=4,audit=original['history']['audit']),
 archive=dict(directory=str(D),**audit['archive']),archive_audit=dict(path=str(archive_audit),sha256=sha(archive_audit)),
 archive_attempts={'01':'closed schema failure before WORK/result','02':'passed; original scope241 unchanged'},
 archive_audit_attempts={'02':'closed missing historical working-copy identity after sparse publication; original failure retained','03':'passed with explicit committed Git blob full-byte proof'},
 recovery=dict(new_gzip_blobs=54,reused_gzip_blobs=93,logical_snapshot_members=158,native_base=original['snapshots']['compact_base_archive_association'],metadata_plan=original['snapshots']['external_metadata_plan_recovery'],prior_archives=original['prior_archives'],failure_archive_git_transition=audit['git_publication_transition']['report']),
 original_archive_directory_preserved=True,originals_preserved=True,archive_payload_duplicated=False,git_mutations=False,
 application_qualified=False,performance_measurement=False,runtime_installation=False,
 scope='Adjacent exact closed evidence/source publication. All241 selected original source/proof payload bytes remain in the five-file archive directory; this capsule adds processing/audit failures, source/raw, full Git recovery proof and reviews. No live provider payload duplication.')
readme='''# Qualified driver02 and complete retention evidence

Driver02 passed its compile, serial and parallel commands and independent audit
9540ad45. Both driver processes reported eight contexts and nine records.
The earlier driver01 compiler failure remains separate: four actual top-level
children across both attempts, three qualified current children. No application,
performance measurement or runtime installation is claimed.

The adjacent `hir-options-hash-driver-02` directory contains the five unchanged
archive outputs. Its 241 ordinary members retain 13,880,266 logical bytes in a
2,559,860-byte gzip archive. Audit03 independently rehashed all241 original and
archived files, all ten closed source trees and full gzip EOF. Every logical
member has its exact original path, member name, SHA-256, length and historical
identity in the adjacent manifest; the scope is not rewritten by this capsule.

All54 newly stored gzip snapshot blobs are included in that archive. The93
reused blobs, original native03 file-table base and external raw metadata plan
retain explicit published archive/member/SHA aliases in that manifest. Recovery
requires the referenced beta, native and failure01 archives. The metadata plan
requires the recorded two-step outer archive member and inner-gzip readback.
No6.7GB live compiler/provider payload closure is duplicated here.

Archive01 failed before creating WORK/result because its reader assumed a
compile-style returncode in serial/parallel receipts. Corrected archive02
retains that source/raw failure and binds nested wait records to audit9540.
Independent audit02 then completed its own archive readback but refused the
now-absent failure01 archive working-copy inode after sparse Git publication.
Audit03 binds the exact committed Git blob's full13,134,758-byte SHA-256 proof,
all11 read-only Git command closures and before/after sparse omission. It does
not invent an old inode or restore the absent working-copy file. Both failed
audits/attempts remain raw evidence; no workload was rerun.

This capsule contains the immutable sources/diffs, complete processing/audit
execution directories, actual Git proof, selection scopes and reviews. Original
prepared READMEs keep their historical wording. STATUS.md records final state.
'''
status='''# Status

- Driver01: one failed compiler; zero driver processes; retained unchanged.
- Driver02: three successful independently qualified commands; two processes, eight contexts each.
- Archive01: closed pre-output schema failure; preserved.
- Archive02: passed once;241 members/2,559,860 compressed bytes.
- Archive audit02: closed sparse-working-copy identity refusal; preserved.
- Archive audit03: passed once, audit6473ffef; all own bytes/ten trees and recovery aliases verified.
- Historical failure archive: committed Git blob09c50202/fullSHAff7870ea proved without restoration.
- This publication: exact ordinary copies only; no compiler/provider/runtime/Git mutation.
'''
files=sorted(rows.values(),key=lambda r:r['destination']);assert len(files)==len({r['destination'] for r in files})
required=[archive_audit,R/'.work/hash-driver-success-evidence-01/receipt.json',R/'.work/hash-driver-success-retention-execution-01/record.json',R/'.work/hash-driver-success-retention-execution-02/record.json',A/'.work/hash-driver-success-retention-audit-execution-02/record.json',A/'.work/hash-driver-success-retention-audit-execution-03/record.json',R/'.work/published-failure-archive-git-proof-01/report.json']
proposal=dict(status='proposed-unpublished',created_at=time.time(),destination=str(R/'results/hir-options-hash-driver-02-publication'),
 files=files,file_count=len(files),source_bytes=sum(r['size'] for r in files),maximum_files=256,maximum_source_bytes=8*2**20,maximum_file_bytes=2*2**20,maximum_publication_bytes=12*2**20,
 generated_files=['README.md','STATUS.md','summary.json','manifest.json','publication-proposal.json','publication-copier.py'],
 complete_source_trees=trees,protected_result_directory=str(D),protected_results=protected,protected_result_files=5,
 required_evidence=sorted(map(str,required)),selected_archive_source_count=241,selected_archive_sources=original['files'],
 selected_archive_recovery=dict(archive_sha256=audit['archive']['sha256'],manifest_sha256=audit['manifest_sha256'],members_use_original_path_without_initial_slash=True),
 summary=summary,readme=readme,status_document=status,
 copy_contract='Exact fresh ordinary copies after review; selected241 payloads recovered from adjacent unchanged archive, processing/audit closure fully copied. Complete source/output readback and allfive archive bytes/identities preserved. No archive payload duplication, source mutation, Git operations or workloads.')
out=A/'.work/hash-driver-success-retention-publication-proposal-01.json'
with out.open('x') as f:json.dump(proposal,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha(out),files=len(files),source_bytes=proposal['source_bytes'],trees=len(trees),protected_archive_sha256=audit['archive']['sha256'])))
