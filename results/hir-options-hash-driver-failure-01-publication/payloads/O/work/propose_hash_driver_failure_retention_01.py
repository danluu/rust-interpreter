"""Bounded metadata/source census only; no archive, copy or workload creation."""
from pathlib import Path
import difflib,hashlib,json,os,stat,time
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918');R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913');X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918');A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918');N=X/'.work/hir-options-hash-compiler-01';W=R/'.work/hir-options-hash-driver-01'
OUT=O/'.work/hash-driver-failure-retention-proposal-01.json'
def require(ok,message):
 if not ok:raise RuntimeError(message)
def sha(data):return hashlib.sha256(data).hexdigest()
def identity(p):
 s=p.lstat();return {k:getattr(s,'st_'+k) for k in ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']}
def row(p):
 p=Path(p);i=identity(p);require(p.resolve(strict=True)==p and stat.S_ISREG(i['mode']) and i['size']<=64*2**20,'bounded ordinary census input')
 raw=p.read_bytes();require(identity(p)==i and len(raw)==i['size'],'stable source read');return dict(path=str(p),size=len(raw),sha256=sha(raw),identity=i)
selected={};groups={};roots={}
def add(p,group):
 p=Path(p);name=str(p);groups.setdefault(group,[]).append(name)
 if name not in selected:
  require(len(selected)<256,'selected source count bound');selected[name]=row(p)
  require(sum(r['size'] for r in selected.values())<=128*2**20,'selected logical source bound')
def tree(p,group):
 p=Path(p);require(p.resolve(strict=True)==p and p.is_dir(),'ordinary scoped source directory');members=[]
 for base,dirs,files in os.walk(p,followlinks=False):
  require(all(not (Path(base)/d).is_symlink() for d in dirs),'no linked census directories')
  for name in sorted(files):add(Path(base)/name,group);members.append(str((Path(base)/name).relative_to(p)))
 roots[str(p)]=sorted(members)
for p,group in [
 (R/'experiments/hir-options-hash-driver-stage-02','original_prepared_packet_and_source'),
 (R/'.work/hash-driver-preparation-execution-03','preparation03_actual_history'),
 (W,'failed01_complete_work'),
 (R/'.work/experiments/hir-options-hash-driver-supervisor-01','failed01_outer'),
 (R/'.work/hash-driver-launch-execution-01','failed01_launcher'),
 (R/'experiments/hir-options-hash-driver-failure-audit-01','failure_auditor_source'),
 (R/'.work/hash-driver-failure-verification-execution-01','failure_audit_actual_history')]:tree(p,group)
for p in [R/'.work/prepare_hash_driver_03.py',R/'.work/prepare_hash_driver_03_final_unbound.py',R/'.work/prepare_hash_driver_03_unbound_before_input_binding.py',R/'.work/prepare_hash_driver_03_actual_binding.diff',R/'.work/prepare_hash_driver_03_input_binding.diff',R/'.work/prepare_hash_driver_03_unbound.diff',R/'.work/hash-stage02-final-source-inventory-01.json',R/'.work/hash-driver-preparation-predecessors-03.json']:
 add(p,'preparation03_source_and_prior_history_references')
for p in [R/'.work/execute_hash_driver_failure_audit_01.py',R/'.work/execute_hash_driver_failure_audit_01.py.diff',R/'.work/hir-options-hash-driver-failure-verification-01.json',R/'.work/hash-driver-failure-audit-root-source-review-01.json',R/'.work/hash-driver-v2-root-source-review-01.json',O/'.work/hash-driver-first-compile-failure-assessment-01.json',O/'.work/hash-driver-packet-verification-05.json',R/'.work/hash-driver-packet05-root-source-review-01.json']:
 add(p,'independent_failure_and_packet_reviews')
old=X/'experiments/hir-options-hash/controls/driver.rs';new=old.with_name('driver-v2.rs');diff=O/'.work/hash-driver-v2-two-replacements.diff'
require(not diff.exists(),'fresh source diff')
diff.write_text(''.join(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),fromfile=str(old),tofile=str(new))))
for p in [old,new,old.with_name('fixture.rs'),diff,N/'hash-driver-01/fixture.rs',N/'source/compiler/rustc_data_structures/src/marker.rs',N/'source/compiler/rustc_data_structures/src/sync.rs',N/'source/compiler/rustc_data_structures/src/sync/parallel.rs']:
 add(p,'exact_source_diagnosis_and_uncompiled_successor')
manifest=json.loads((W/'source-snapshots.json').read_bytes());terminal=json.loads((W/'receipt.json').read_bytes());audit=json.loads((R/'.work/hir-options-hash-driver-failure-verification-01.json').read_bytes())
require(terminal['status']=='failed' and audit['status']=='verified-retained-failure' and audit['actual_compiler_children']==1 and audit['actual_driver_processes']==0,'honest failed workload accounting')
require(audit['receipt_sha256']==selected[str(W/'receipt.json')]['sha256'] and audit['source_snapshots_sha256']==selected[str(W/'source-snapshots.json')]['sha256'],'actual failure audit binding')
blobs=manifest['blobs'];stored={key:blob for key,blob in blobs.items() if manifest['storage'][key]['kind']=='stored'}
require(len(stored)==65 and len(manifest['reuse'])==34 and len(manifest['files'])==103,'complete retained failure snapshot scope')
for key,b in stored.items():
 r=selected[str(W/'source-snapshots'/b['filename'])];require(r['sha256']==b['sha256'] and r['size']==b['compressed_bytes'],'all actual newly stored blobs selected')
archive_inputs={
 'beta':dict(result=R/'results/hir-options-hash-beta-composition-08',git_blob='ed73e0afec13a7e1da3e46f6371aa03ff75df72c',audit=R/'results/hir-options-hash-beta-composition-08/actual-retention/001-beta-composition08-retention-independent-verification-01.json'),
 'native':dict(result=R/'results/hir-options-hash-native-reconciliation-01',git_blob='0b05a7333f7d47716d73623db2d9d7bc4f232ef6',audit=R/'.work/native-qualification-publication-independent-verification-01.json')}
archives={};archive_manifests={}
for kind,definition in archive_inputs.items():
 result=definition['result'];m=json.loads((result/'manifest.json').read_bytes());summary=json.loads((result/'summary.json').read_bytes());a=json.loads(definition['audit'].read_bytes())
 require(summary['manifest_sha256']==sha((result/'manifest.json').read_bytes()) and summary['archive']['sha256']==a['archive_sha256'] and a['status']=='verified','published archive manifest and independent audit')
 archives[kind]=dict(path=str(result/'evidence.tar.gz'),sha256=summary['archive']['sha256'],size=summary['archive']['bytes'],git_repository=str(R),git_blob=definition['git_blob'],ordinary_working_copy_present=(result/'evidence.tar.gz').exists(),manifest=row(result/'manifest.json'),summary=row(result/'summary.json'),independent_audit=row(definition['audit']),archive_payload_included=False,archive_payload_read_now=False)
 archive_manifests[kind]=m
 for p in [result/'manifest.json',result/'summary.json',definition['audit']]:add(p,'published_prior_archive_metadata')
def archive_member(kind,name,digest,size):
 m=archive_manifests[kind];key=name.lstrip('/');r=m[key];chain=[key]
 require(r['source']==name and r['sha256']==digest,'exact logical archived member')
 while 'linkname' in r:
  key=r['linkname'];require(key not in chain and len(chain)<256,'finite archive alias chain');chain.append(key);r=m[key]
 require(r['sha256']==digest and r['bytes']==size,'complete physical archived payload association')
 return dict(archive=kind,logical_member=chain[0],physical_member=chain[-1],alias_chain=chain,sha256=digest,size=size)
reused=[]
for key,r in sorted(manifest['reuse'].items()):
 kind='beta' if 'beta-composition-08' in r['evidence_root'] else 'native'
 require(r['path']==manifest['storage'][key]['path'] and r['blob']==blobs[key],'exact reused compressed descriptor')
 reused.append(dict(source=r,archived=archive_member(kind,r['path'],r['blob']['sha256'],r['blob']['compressed_bytes'])))
compact=json.loads((R/'experiments/hir-options-hash-driver-stage-02/inputs.json').read_bytes());base=compact['file_table_base'];base_row=compact['files'][base['path']]
base_reference=dict(reference=base,archived=archive_member('native',base['path'],base['sha256'],base_row['size']))
for p in [R/'results/hash-inherited-record-controls-01/manifest.json',R/'results/hash-inherited-record-controls-01/summary.json']:
 add(p,'previous_published_packet_audits_and_inherited22_reference')
require(len(selected)<=256 and sum(r['size'] for r in selected.values())<=128*2**20,'complete final bounded selection')
for r in selected.values():require(identity(Path(r['path']))==r['identity'],'selected originals remain stable')
report=dict(status='proposed-unpublished-uncompressed',created_at=time.time(),archive_source=str(R/'experiments/hash-driver-failure-evidence-01'),destination=str(R/'results/hir-options-hash-driver-failure-01'),work=str(R/'.work/hash-driver-failure-evidence-01'),files=[dict(r,member=Path(r['path']).as_posix().lstrip('/')) for r in sorted(selected.values(),key=lambda r:r['path'])],file_count=len(selected),logical_bytes=sum(r['size'] for r in selected.values()),groups=groups,complete_scoped_directories=roots,
 limits=dict(maximum_selected_files=256,maximum_file_bytes=64*2**20,maximum_logical_bytes=128*2**20,maximum_compressed_bytes=32*2**20,maximum_manifest_bytes=2*2**20,maximum_expanded_archive_bytes=132*2**20),
 archive_policy='Proposed deterministic bounded GNU tar plus gzip; ordinary full-byte source checks before/after, complete member/EOF readback. No archive engine or compressed measurement executed by this proposal.',
 history=dict(status='failed',actual_compiler_children=1,actual_driver_processes=0,hash_driver_qualified=False,application_qualified=False,performance_measurement=False,receipt_sha256=audit['receipt_sha256'],failure_audit_sha256=selected[str(R/'.work/hir-options-hash-driver-failure-verification-01.json')]['sha256'],exact_diagnostic_sha256=audit['failure']['diagnostic_sha256'],original_plan_children=3,new_driver_source_status='uncompiled source-only successor'),
 snapshots=dict(logical_files=103,unique_payloads=99,new_stored_blobs=65,new_stored_bytes=sum(b['compressed_bytes'] for b in stored.values()),reused_blobs=34,reused_bytes=sum(r['blob']['compressed_bytes'] for r in manifest['reuse'].values()),all_new_blobs_selected=True,all_reused_blobs_mapped_to_published_archives=True,reused_archive_associations=reused,compact_base_archive_association=base_reference),prior_archives=archives,
 exclusions=['Live compiler/B3/SDK/registry/provider payloads','The 34 reused gzip payloads and native03 file-table base already retained in the two explicitly referenced published archives','Active stage03 sources/workloads and future qualification'],
 prior_packet_audits=dict(result_directory=str(R/'results/hash-inherited-record-controls-01'),manifest_sha256=selected[str(R/'results/hash-inherited-record-controls-01/manifest.json')]['sha256']),
 proposal_only=True,archive_created=False,copies_created=False,originals_mutated=False,git_mutations=False,compressed_fit_measured=False)
with OUT.open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(dict(proposal=str(OUT),sha256=sha(OUT.read_bytes()),files=len(selected),logical_bytes=report['logical_bytes'],new_blobs=65,reused_archive_refs=34)))
