"""Finite exclusive copies of closed overlay evidence; no compiler or project imports."""
from pathlib import Path
import hashlib,json,os,stat,time
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
S=R/'experiments/proc-macro-arena-n-overlay-01'
E=R/'results/proc-macro-arena-n-overlay-01'
D=R/'results/proc-macro-arena-n-overlay-01-publication'
REPORT=A/'.work/proc-macro-arena-n-overlay01-publication-verification-01.json'
READBACK=A/'.work/proc-macro-arena-n-overlay01-independent-readback-01.json'
assert not D.exists() and not REPORT.exists()
def stamp(p):
 s=p.lstat();return {k:getattr(s,'st_'+k) for k in ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']}
def read(p):
 p=Path(p);before=stamp(p)
 assert p.resolve(strict=True)==p and stat.S_ISREG(before['mode']) and before['size']<=4*2**20,p
 with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW),'rb') as f:
  assert {k:getattr(os.fstat(f.fileno()),'st_'+k) for k in before}==before
  data=f.read(4*2**20+1)
  assert {k:getattr(os.fstat(f.fileno()),'st_'+k) for k in before}==before
 assert stamp(p)==before and len(data)==before['size']
 return data,dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),identity=before)
def doc(p):return json.loads(read(p)[0])
def tree(p):return {'.':stamp(p),**{str(q.relative_to(p)):stamp(q) for q in sorted(p.rglob('*'))}}
def relative(p):
 for label,root in [('ROOT',R),('A',A),('X',X)]:
  if p.is_relative_to(root):return 'payloads/'+label+'/'+str(p.relative_to(root))
 raise AssertionError(p)
rb=doc(READBACK);assert read(READBACK)[1]['sha256']=='433379113642b537b47532a048f889433d3c0309dc4c5062053437783f89800c' and rb['status']=='verified'
assert rb['command_count']==20 and rb['stable_caller_pairs']==9
for root in [S,E]:assert tree(root)==rb['closed_trees'][str(root)]
selection={p for root in [S,E] for p in root.rglob('*') if p.is_file()}
selection.update(map(Path,doc(E/'inputs-before.json')))
prerequisite=doc(E/'prerequisite.json')
selection.update(Path(v['path']) for v in prerequisite['proofs'].values())
selection.update(map(Path,rb['depinfo']))
selection.update([READBACK,Path(rb['verifier']['path']),Path(__file__),Path(rb['prerequisite']['path']),
 R/'.work/proc-macro-arena-n-overlay-root-source-review-01.json',
 X/'.work/n-overlay-N04-prerequisite-binding-01.json',X/'.work/proc-macro-arena-n-overlay-source-handoff-01.json',
 R/'results/proc-macro-arena-n-client-04-publication/manifest.json',
 R/'results/proc-macro-arena-n-client-04-publication/STATUS.md',
 A/'.work/proc-macro-arena-n-client04-publication-verification-01.json'])
rows={}
for p in sorted(selection):
 data,row=read(p)
 if str(p) in rb['checked_files']:assert row==rb['checked_files'][str(p)],p
 rows[str(p)]={**row,'relative':relative(p)}
assert len(rows)<=256 and sum(v['bytes'] for v in rows.values())<=8*2**20
assert len({v['relative'] for v in rows.values()})==len(rows)
D.mkdir()
for name,row in rows.items():
 data,now=read(name);assert now=={k:row[k] for k in ['bytes','sha256','identity']}
 target=D/row['relative'];target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(data)
 copied=read(target)[1]
 assert copied['bytes']==row['bytes'] and copied['sha256']==row['sha256'] and copied['identity']['nlink']==1
 assert (copied['identity']['dev'],copied['identity']['ino'])!=(row['identity']['dev'],row['identity']['ino'])
 assert read(name)[1]==now
def write(name,value):
 data=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode() if not isinstance(value,str) else value.encode()
 assert len(data)<=2*2**20
 with (D/name).open('xb') as f:f.write(data)
 return read(D/name)[1]
external=dict(policy='verified-external-artifacts-not-copied-v1',runtime=rb['runtime'],runtime_entries=doc(E/'runtime-before.json'),
 overlays=rb['overlays'],built_artifacts=rb['built_artifacts'],work_files=rb['work_files'],work_links=rb['work_links'],
 prerequisite_artifacts=prerequisite['selected_artifacts'],prerequisite_proofs=prerequisite['proofs'],
 previous_publication=dict(path=str(R/'results/proc-macro-arena-n-client-04-publication'),manifest_sha256=read(R/'results/proc-macro-arena-n-client-04-publication/manifest.json')[1]['sha256']),
 portable_binary_reconstruction_claimed=False,original_paths_preserved=True)
generated={'external-artifacts.json':write('external-artifacts.json',external)}
status='''# Status

The N overlay01 default-discovery correctness phase passed once: two macro dylib builds and eighteen real caller commands, with all 20 children closed at their expected return codes. All nine stock/candidate caller pairs matched the required stable diagnostics, including success, error, panic, stale-handle and recovery cases.

Actual result SHA: 129e8818d8a2505139a147fb0f3c2d6593a049c0e8c7cfc9989798caf10a3a42. Execution SHA: fb525fb1ee530f706e2eef523c9db351db925e40222fd78cd0431981ec012893. Parent 24718 released its canonical lock at 1789824581.7055528. No retries, explicit signals or observation errors occurred.

Independent saved readback SHA: 433379113642b537b47532a048f889433d3c0309dc4c5062053437783f89800c. It reconstructed all 20 commands and raw diagnostic results, rehashed all 33 frozen input rows and the actual N04 prerequisite, and checked full unchanged N runtime membership and bytes (63 files, two declared links, 564,106,543 logical file bytes). Both overlays retained exactly eight owned files, 104 declared links and fourteen directories in total. The original 94 result files, source tree and complete 34-file WORK tree remained unchanged; all six built artifacts were rehashed.

Each macro build used its matching explicit overlay sysroot while omitting direct proc_macro and literal extern selections and dependency search overrides. Its actual dep-info selected all four matching overlay proc_macro/literal metadata and library files. Opposite-arm and original client/literal artifacts were excluded. Successful callers selected the matching newly built macro dylib. The N compiler server itself remained unchanged.

The prerequisite is the independently verified N04 correctness run: its candidate executed 13 native Arena/Interner tests, while stock had zero tests and only compiler/loader smoke. Overlay01 did not rerun those tests. All binary and source associations remain explicit in prerequisite.json and its before/after observations.

This capsule contains the full source tree, all actual result/raw files, every current source input, prerequisite proof records, successful dep-info, reviews and the independent readback. Large N runtime and WORK binary payloads are recorded by original path, identity and verified SHA-256 in external-artifacts.json. No portable reconstruction of those binaries is claimed. Prior N04 source/proof publication is referenced by its exact manifest SHA. Every copied payload has a fresh independent destination identity, and original files remain untouched.

This qualifies the tested external N clients and finite default-discovery cases. It does not qualify a full compiler distribution, runtime composition, builtin quote optimization, application holdouts or performance. The existing 16/9/8 resource policy was used unchanged; RSS/swap allowance is unmeasured and the aggregate output limit is sampled. The readback and publication ran no compiler or test commands. manifest.json has no self-row.
'''
generated['STATUS.md']=write('STATUS.md',status)
manifest=dict(status='passed-evidence-published',files=rows,generated=generated,closed_source_trees={str(root):rb['closed_trees'][str(root)] for root in [S,E]},
 result_sha256=rb['result']['sha256'],execution_sha256=rb['execution']['sha256'],independent_readback_sha256=read(READBACK)[1]['sha256'],
 command_count=20,paired_caller_cases=9,default_discovery_qualified=True,real_N_external_client_integration=True,
 large_runtime_payloads_copied=False,work_binary_payloads_copied=False,compiler_distribution_qualified=False,runtime_composition_qualified=False,holdout_qualified=False,benchmark=False)
manifest_row=write('manifest.json',manifest)
outputs=[]
for p in sorted(D.rglob('*')):
 if p.is_file():outputs.append(dict(relative=str(p.relative_to(D)),**read(p)[1]))
assert {v['relative'] for v in outputs}=={v['relative'] for v in rows.values()}|set(generated)|{'manifest.json'}
assert len(outputs)<=260 and sum(v['bytes'] for v in outputs)<=10*2**20
for name,row in rows.items():assert read(name)[1]=={k:row[k] for k in ['bytes','sha256','identity']}
for root in [S,E]:assert tree(root)==rb['closed_trees'][str(root)]
value=dict(status='verified',destination=str(D),finished_at=time.time(),publication_source=read(Path(__file__))[1],
 source_files=len(rows),source_bytes=sum(v['bytes'] for v in rows.values()),original_source_and_results_unchanged=True,
 manifest_sha256=manifest_row['sha256'],output_files=len(outputs),output_bytes=sum(v['bytes'] for v in outputs),outputs=outputs,no_git=True)
with REPORT.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(dict(report=str(REPORT),sha256=read(REPORT)[1]['sha256'],manifest=manifest_row['sha256'],outputs=len(outputs),bytes=value['output_bytes'])))
