#!/usr/bin/env python3
"""Produce a source-only packed-sidecar patch from exact immutable Git blobs."""
import difflib,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
C=Path('/Users/danluu/dev/rustc-hir-capture-check-20260913')
BASE='7efc0d9484da82cd327deb3b48616f8ec81eaf8d';OLD_IDENTITY='a6cf8a739f3c7a29707bacb4f12ecb575700f72bc41004260f99951f85ecf13b'
IDENTITY='compiler/rustc_ast_lowering/src/body_cache/source_identity.rs'
BODY='compiler/rustc_ast_lowering/src/body_cache/mod.rs';REPLAY='compiler/rustc_ast_lowering/src/body_cache/prepared_replay.rs'
STORAGE='compiler/rustc_ast_lowering/src/body_cache/storage.rs';SESSION='compiler/rustc_session/src/session.rs';LIB='compiler/rustc_session/src/lib.rs';FS='compiler/rustc_incremental/src/persist/fs.rs';PACK='compiler/rustc_session/src/hir_body_cache.rs';RMAKE='tests/run-make/hir-body-cache-capture/rmake.rs'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(root,*args):return subprocess.check_output(['/usr/bin/git','--no-optional-locks','-C',str(root),*args])
def replace(text,old,new,n=1):
 assert text.count(old)==n,old[:100];return text.replace(old,new)
def write(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def transform(before):
 out=dict(before)
 b=before[BODY].decode();b=replace(b,'use std::path::PathBuf;\n','use rustc_session::hir_body_cache::Policy;\n');b=replace(b,'    path: PathBuf,','    cache_policy: Policy,\n    cache_owner: String,');b=replace(b,'    let session = tcx.incr_comp_session?;','    tcx.incr_comp_session?;')
 b=replace(b,'        path: session.session_directory.join(format!("{policy}-{}.json", hex(probe.input.owner.0))),','        cache_policy: if tcx.sess.opts.unstable_opts.hir_body_cache_reuse { Policy::Reuse } else { Policy::Capture },\n        cache_owner: hex(probe.input.owner.0),')
 b=replace(b,'    let Some(frame) = effects::Frame::enter(lctx, &candidate) else {','    let Some(session) = lctx.tcx.incr_comp_session else { return lctx.lower_block_expr(body); };\n    let Some(frame) = effects::Frame::enter(lctx, &candidate) else {')
 b=replace(b,'storage::read(&candidate.path, &record_key)','storage::read_record(session, candidate.cache_policy, &candidate.cache_owner, &record_key)')
 b=replace(b,'    // A record is written only after stock lowering, cold materialization/\n    // recapture and exact exit checks, in the selected policy\'s own namespace.\n    let stored = storage::write(&candidate.path, &record_key, &payload);','    // Queue only after stock lowering, cold materialization/recapture and exact\n    // exit checks. The policy-specific pack is published at successful session\n    // finalization; this per-body report describes accepted evidence, not IO.\n    let stored = storage::queue_record(session, candidate.cache_policy, &candidate.cache_owner, &record_key, &payload);')
 out[BODY]=b.encode()
 out[REPLAY]=replace(before[REPLAY].decode(),'storage::read(&candidate.path, key)?','storage::read_record(lctx.tcx.incr_comp_session?, candidate.cache_policy, &candidate.cache_owner, key)?').encode()
 out[STORAGE]=(HERE/'templates/storage.rs').read_bytes();out[PACK]=(HERE/'templates/hir_body_cache.rs').read_bytes()
 out[LIB]=replace(before[LIB].decode(),'pub mod filesearch;','pub mod filesearch;\npub mod hir_body_cache;').encode()
 out[SESSION]=replace(before[SESSION].decode(),'pub struct IncrCompSession {','pub struct IncrCompSession {\n    /// Opaque HIR record bytes bound to this exact session directory. No HIR\n    /// proof survives a lookup; publication occurs only during finalization.\n    pub hir_body_cache: crate::hir_body_cache::HirBodyCache,').encode()
 f=before[FS].decode();f=replace(f,'IncrCompSession { session_directory: session_dir, _lock_file: directory_lock }','IncrCompSession {\n                hir_body_cache: rustc_session::hir_body_cache::HirBodyCache::new(session_dir.clone()),\n                session_directory: session_dir, _lock_file: directory_lock,\n            }',n=2)
 f=replace(f,'    let incr_comp_session_dir = incr_comp_session.session_directory.clone();','    // GlobalCtxt is no longer running queries. Publish pending opaque HIR\n    // records into fresh inodes before this successful session is renamed.\n    // Error/early-Stop/Drop paths never invoke this publication operation.\n    let outcomes = sess.time("incr_comp_publish_hir_body_cache", || incr_comp_session.hir_body_cache.finalize());\n    if sess.opts.unstable_opts.incremental_info {\n        for (policy, published) in outcomes {\n            eprintln!("[hir-body-storage] pack={} publication={}", policy.filename(),\n                if published { "published" } else { "unavailable" });\n        }\n    }\n\n    let incr_comp_session_dir = incr_comp_session.session_directory.clone();')
 out[FS]=f.encode()
 r=replace(before[RMAKE].decode(),'&& path.extension().is_some_and(|ext| ext == "json")','&& path.extension().is_some_and(|ext| ext == "pack")')
 r=replace(r,'fn records(root: &Path, prefix: &str, output: &mut Vec<PathBuf>) {','// Discover policy-specific packs; corruption still reaches the actual stored\n// records. A truncated pack must cause ordinary cold lowering, never a hit.\nfn records(root: &Path, prefix: &str, output: &mut Vec<PathBuf>) {')
 out[RMAKE]=r.encode();return out

def main():
 assert sys.dont_write_bytecode and not sys.flags.optimize
 dest=HERE/'artifacts-01';assert not dest.exists()
 assert git(C,'rev-parse','HEAD').decode().strip()==BASE and not git(C,'diff','HEAD','--')
 prior=json.loads(git(ROOT,'show','HEAD:experiments/hir-arena-identity-upgrade/inputs/patch.json'))
 assert prior['source_identity']==OLD_IDENTITY and len(prior['files'])==25
 before={}
 for name,row in prior['files'].items():
  data=git(C,'show',BASE+':'+name);assert sha(data)==row['after_sha256'];assert (C/name).read_bytes()==data;before[name]=data
 closure={name:sha(data) for name,data in before.items() if name!=IDENTITY}
 assert sha(json.dumps(closure,sort_keys=True,separators=(',',':')).encode())==OLD_IDENTITY
 for name in [SESSION,LIB,FS]:before[name]=git(C,'show',BASE+':'+name)
 assert not (C/PACK).exists()
 after=transform(before);identity_closure={name:sha(data) for name,data in after.items() if name!=IDENTITY};identity=sha(json.dumps(identity_closure,sort_keys=True,separators=(',',':')).encode());after[IDENTITY]=f'pub(super) const SOURCE_IDENTITY: &str = "{identity}";\n'.encode()
 changed=sorted(name for name in after if before.get(name)!=after[name]);expected=sorted([BODY,REPLAY,STORAGE,SESSION,LIB,FS,PACK,RMAKE,IDENTITY]);assert changed==expected
 pieces=[]
 for name in changed:
  pieces.append(f'diff --git a/{name} b/{name}\n')
  if name not in before:pieces.append('new file mode 100644\n')
  pieces.extend(difflib.unified_diff(before.get(name,b'').decode().splitlines(keepends=True),after[name].decode().splitlines(keepends=True),fromfile='a/'+name if name in before else '/dev/null',tofile='b/'+name,n=5))
 patch=''.join(pieces).encode();dest.mkdir()
 for name,data in before.items():write(dest/'base'/name,data)
 for name in changed:write(dest/'candidate'/name,after[name])
 write(dest/'candidate.patch',patch)
 manifest=dict(schema_version=1,status='source-only-uncompiled-unrun',base_commit=BASE,compiler_source_read_only=str(C),owner_checkpoint=git(ROOT,'rev-parse','HEAD').decode().strip(),previous_identity=OLD_IDENTITY,source_identity=identity,complete_closure_files=identity_closure,identity_file_sha256=sha(after[IDENTITY]),base_files={name:dict(bytes=len(data),sha256=sha(data)) for name,data in before.items()},candidate_files={name:dict(bytes=len(after[name]),sha256=sha(after[name])) for name in changed},patch_sha256=sha(patch),patch_bytes=len(patch),changed_files=changed,compiler_source_modified=False,compiler_builds=0,rust_controls_run=False,benchmarks_run=False,templates={p.name:sha(p.read_bytes()) for p in (HERE/'templates').glob('*.rs')},prepare_sha256=sha(Path(__file__).read_bytes()),scope='Packed opaque record storage only. No options-hash or single-Walk changes.')
 write(dest/'manifest.json',(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode());print(json.dumps(dict(source_identity=identity,patch_sha256=sha(patch),patch_bytes=len(patch),files=changed),indent=2))
if __name__=='__main__':main()
