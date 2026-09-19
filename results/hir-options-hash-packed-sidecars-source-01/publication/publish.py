from pathlib import Path
import hashlib,json,os,stat,time
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918'); R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
scopepath=X/'.work/options-hash-packed-source-publication-scope-01.json'; scopebytes=scopepath.read_bytes();assert hashlib.sha256(scopebytes).hexdigest()=='304f06537f06a855943b896616f7e22f8aec94150ca43b07e16f6779160781ab';scope=json.loads(scopebytes)
S=R/'experiments/hir-options-hash-packed-sidecars';Q=Path(scope['result_namespace']);audit=X/'.work/options-hash-packed-source-publication-verification-01.json';assert not Q.exists() and not (S/'STATUS.md').exists() and not audit.exists()
start=time.time();pid=os.getpid();fields=['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']
def ident(p):
 s=p.lstat();return {k:getattr(s,'st_'+k) for k in fields}
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def check(row):
 p=Path(row['source']);assert p.resolve(strict=True)==p and stat.S_ISREG(p.lstat().st_mode) and ident(p)==row['identity'] and digest(p)==row['sha256'] and p.stat().st_size==row['size'];return p
def syncdir(p):
 fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)
def put(p,data):
 with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 assert p.read_bytes()==data and p.stat().st_nlink==1
 return {'path':str(p.relative_to(R)),'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'identity':ident(p)}
def encoded(j):return (json.dumps(j,indent=2,sort_keys=True)+'\n').encode()
for row in scope['existing_files']:check(row)
Q.mkdir();syncdir(Q.parent);copies=[]
for row in scope['existing_files']:
 dest=R/row['destination'];source=check(row)
 if source==dest:continue
 dest.parent.mkdir(parents=True,exist_ok=True)
 data=source.read_bytes();assert hashlib.sha256(data).hexdigest()==row['sha256']
 copied=put(dest,data);check(row);assert copied['identity']['ino']!=row['identity']['ino'] or copied['identity']['dev']!=row['identity']['dev'];copies.append(copied)
assert len(copies)==16
source_status='''# Combined source composition verified\n\nThe options-hash plus packed-sidecars source artifacts were generated and independently verified on 2026-09-18. The source identity is `e4d112c506f7b091c0e471c56ce25a1a8f62725ffa5676f7c977e105a1e450c0`, derived from 29 identity inputs and a complete 30-file closure on the exact options-hash base `4de35bdacef0e3cd18a66bc30b5459c19e09b118`. The combined patch SHA-256 is `8994a0af4060a5753bb0fb5410dc17e9d1ab5dd3a04c5e649c2642c6551652b9`.\n\nBoth source programs returned zero. Each revalidated the 79 pinned inputs; independent readback verified all 82 artifact files. The current options-hash context and cached-hash accessor were preserved. No combined compiler checkout, compiler build, Rust tests, native/private-metadata qualification, installation or application timing has occurred.\n\nThe six generator-source files, including README.md and QUALIFICATION.md, retain their exact historical pre-execution bytes. This status records the later actual source result without rewriting those frozen documents. Execution and review evidence is in `../../results/hir-options-hash-packed-sidecars-source-01/`.\n\nOne qualification wording limitation remains explicit: `Vec::try_reserve_exact` handles its own reservation failure, while decoding and queueing still allocate through `Arc::from` and `BTreeMap::insert`. General out-of-memory recovery is not established. The two 256 MiB policy maps and a temporary 256 MiB input buffer bound serialized payload, not total RSS. Future compiler and lifecycle qualification must retain that distinction.\n\nThe nine new session tests, existing compiler/run-make suites, real error and callback/finalization histories, metadata/runtime roles, exporter behavior, and strict Ruff measurement remain future work. Profile spans overlap; this source result establishes no speedup or sub-0.5-second bound.\n'''
readme='''# Verified options-hash plus packed-sidecars source\n\nThis publication retains the source composition and independent byte verification for candidate identity `e4d112c506f7b091c0e471c56ce25a1a8f62725ffa5676f7c977e105a1e450c0`. The exact generated patch, 29 base files, 30 candidate files, provenance, and six historical generator sources are under `../../experiments/hir-options-hash-packed-sidecars/`. Read that directory's STATUS.md for the current qualification boundary.\n\n`execution/` preserves the two actual source-program histories, dispatcher and independent source readback; `reviews/` retains the two independent source reviews. `manifest.json` maps each published source/evidence byte to its original path and SHA-256. The original source and all prior compiler evidence remain unchanged.\n\nNo compiler, test, provider probe, benchmark, installation or combined-source checkout was executed as part of generation or this publication. The source processes recorded Popen child/parent identities, argv, cwd, environment, times, exit statuses and kernel session/group IDs. No separate ps or cwd probe was run. The historical allocation-failure statement is limited by infallible Arc and BTreeMap allocation, as STATUS.md records.\n'''
statusrec=put(S/'STATUS.md',source_status.encode());readmerec=put(Q/'README.md',readme.encode())
actual=json.loads((Q/'execution/independent-source-readback.json').read_bytes())
summary=dict(status='source-composition-verified-no-compiler-qualification',source_identity=scope['source_identity'],source_base=scope['source_base'],patch_sha256='8994a0af4060a5753bb0fb5410dc17e9d1ab5dd3a04c5e649c2642c6551652b9',artifact_manifest_sha256='359bd389a77de318afbe0026d5ecabd93957eb7aa2a6065c39dfa12b095be568',source_verification_sha256='67285a3fe6be0681c79741513e96f8a1dabf5ed42d82b0231085f17fd9c6b850',identity_inputs=29,source_closure_files=30,artifacts=82,artifact_bytes=4496592,pinned_inputs=79,generator_returncode=0,verifier_returncode=0,source_namespace=str(S),original_execution_owner=str(X),source_audit_sha256=digest(Q/'execution/independent-source-readback.json'),publication_scope_sha256=hashlib.sha256(scopebytes).hexdigest(),original_scope_files=105,original_scope_bytes=4764442,evidence_copies=16,compiler_built=False,tests_run=False,performance_measured=False,allocation_limitation='Only the explicit Vec reservation failure is handled; Arc::from and BTreeMap insertion remain infallible allocation points. No general OOM recovery or RSS guarantee.',historical_document_policy='All six original generator-source bytes preserved, including their pre-execution README and QUALIFICATION; fresh STATUS carries current result.')
summaryrec=put(Q/'summary.json',encoded(summary))
for row in scope['existing_files']:check(row)
entries=[]
for row in scope['existing_files']:
 p=R/row['destination'];assert digest(p)==row['sha256'] and p.stat().st_size==row['size'];entries.append(dict(path=row['destination'],source=row['source'],source_identity=row['identity'],identity=ident(p),size=row['size'],sha256=row['sha256']))
for row in [statusrec,readmerec,summaryrec]:entries.append(dict(row,source='fresh-publication-document'))
assert len(entries)==108
manifest=dict(status='complete-exact-source-publication',scope=dict(path=str(scopepath),sha256=hashlib.sha256(scopebytes).hexdigest()),files=sorted(entries,key=lambda r:r['path']),files_excluding_this_manifest=108,original_files=105,ordinary_evidence_copies=16,fresh_documents=['experiments/hir-options-hash-packed-sidecars/STATUS.md',str((Q/'README.md').relative_to(R)),str((Q/'summary.json').relative_to(R))],no_provider_payload_copies=True,no_original_deletion_or_overwrite=True)
manifestrec=put(Q/'manifest.json',encoded(manifest))
for p in sorted([p for p in Q.rglob('*') if p.is_dir()],key=lambda p:len(p.parts),reverse=True):syncdir(p)
syncdir(Q);syncdir(Q.parent);syncdir(S)
expected={r['path'] for r in entries}|{manifestrec['path']}
actual_paths={str(p.relative_to(R)) for root in [S,Q] for p in root.rglob('*') if p.is_file()}
assert actual_paths==expected and len(expected)==109
final=[]
for rel in sorted(expected):
 p=R/rel;final.append(dict(path=rel,sha256=digest(p),size=p.stat().st_size,identity=ident(p)))
for row in scope['existing_files']:check(row)
report=dict(status='verified-exact-publication-ready-for-parent-git-review',pid=pid,parent_pid=os.getppid(),started_at=start,finished_at=time.time(),scope_sha256=hashlib.sha256(scopebytes).hexdigest(),files=final,file_count=len(final),logical_bytes=sum(r['size'] for r in final),copied_files=16,original105_files_unchanged=True,exact_membership=True,ordinary_single_link_copies=True,complete_output_readback=True,git_actions=0,compiler_test_provider_benchmark_calls=0)
put(audit,encoded(report))
print(json.dumps(dict(path=str(audit),sha256=digest(audit),file_count=len(final),bytes=report['logical_bytes'],manifest_sha256=manifestrec['sha256']),indent=2))
