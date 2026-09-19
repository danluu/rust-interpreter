#!/usr/bin/env python3
"""Reconcile exact source closure and patch; no compiler/test execution."""
import difflib,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;D=HERE/'artifacts-01';C=Path('/Users/danluu/dev/rustc-hir-capture-check-20260913')
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 assert sys.dont_write_bytecode and not sys.flags.optimize
 m=json.loads((D/'manifest.json').read_bytes());base={n:(D/'base'/n).read_bytes() for n in m['base_files']}
 for n,data in base.items():
  assert sha(data)==m['base_files'][n]['sha256'] and len(data)==m['base_files'][n]['bytes'];assert (C/n).read_bytes()==data
 after=dict(base)
 for n,r in m['candidate_files'].items():
  data=(D/'candidate'/n).read_bytes();assert sha(data)==r['sha256'] and len(data)==r['bytes'];after[n]=data
 identity='compiler/rustc_ast_lowering/src/body_cache/source_identity.rs';closure={n:sha(b) for n,b in after.items() if n!=identity}
 assert closure==m['complete_closure_files'] and sha(json.dumps(closure,sort_keys=True,separators=(',',':')).encode())==m['source_identity']
 assert after[identity]==f'pub(super) const SOURCE_IDENTITY: &str = "{m["source_identity"]}";\n'.encode()
 pieces=[]
 for n in m['changed_files']:
  pieces.append(f'diff --git a/{n} b/{n}\n')
  if n not in base:pieces.append('new file mode 100644\n')
  pieces.extend(difflib.unified_diff(base.get(n,b'').decode().splitlines(keepends=True),after[n].decode().splitlines(keepends=True),fromfile='a/'+n if n in base else '/dev/null',tofile='b/'+n,n=5))
 patch=''.join(pieces).encode();assert patch==(D/'candidate.patch').read_bytes() and sha(patch)==m['patch_sha256']
 # Proof-bearing tree, journal, entry, effects, gate and materialization sources
 # are exactly the inherited bytes. The replay change only selects raw storage.
 for n in ['input.rs','entry.rs','effects.rs','journal.rs','validate.rs','wire.rs','prepared.rs','prepared_audit.rs','capture.rs','kinds.rs']:
  p='compiler/rustc_ast_lowering/src/body_cache/'+n;assert after[p]==base[p]
 p='compiler/rustc_ast_lowering/src/body_cache/prepared_replay.rs';assert after[p].decode()==base[p].decode().replace('storage::read(&candidate.path, key)?','storage::read_record(lctx.tcx.incr_comp_session?, candidate.cache_policy, &candidate.cache_owner, key)?')
 body=after['compiler/rustc_ast_lowering/src/body_cache/mod.rs'].decode();assert 'tcx.sess.opts.dep_tracking_hash(false).as_u64().encode(&mut encoder);' in body and 'input::current_nodes(' in body
 r='tests/run-make/hir-body-cache-capture/rmake.rs';assert after[r].decode().replace('// Discover policy-specific packs; corruption still reaches the actual stored\n// records. A truncated pack must cause ordinary cold lowering, never a hit.\n','').replace('ext == "pack"','ext == "json"')==base[r].decode()
 command=['/usr/bin/git','--no-optional-locks','-C',str(C),'apply','--check',str(D/'candidate.patch')]
 check=subprocess.run(command,capture_output=True,text=True);assert check.returncode==0,(check.stdout,check.stderr)
 record=dict(status='source-only-verification-passed',manifest_sha256=sha((D/'manifest.json').read_bytes()),patch_sha256=sha(patch),source_identity=m['source_identity'],complete_closure_files=len(closure),changed_files=m['changed_files'],git_apply_check=dict(command=command,returncode=check.returncode,stdout=check.stdout,stderr=check.stderr),compiler_source_modified=False,compiler_builds=0,rust_controls_run=False,benchmarks_run=False,options_hash_candidate_applied=False,single_walk_candidate_applied=False)
 with (D/'source-verification.json').open('x') as f:f.write(json.dumps(record,indent=2,sort_keys=True)+'\n')
 print(json.dumps(record,indent=2))
if __name__=='__main__':main()
