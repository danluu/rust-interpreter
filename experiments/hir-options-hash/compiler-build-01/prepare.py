#!/usr/bin/env python3
"""Freeze the compiler build only after actual metadata admission succeeds."""
import ast
import json
from pathlib import Path
import sys
import build as b

def write(p,value):
 with p.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')
def main():
 assert sys.dont_write_bytecode and not sys.flags.optimize
 assert not b.W.exists()
 meta=b.m.WORK
 terminal=b.read(meta/'receipt.json');assert terminal['status']=='passed' and terminal['compiler_builds']==0
 metadata=b.read(meta/'metadata.json');assert metadata['status']=='metadata-qualified-not-built'
 assert b.sha(meta/'metadata.json')==terminal['metadata_sha256']
 mplan=b.read(b.MHERE/'plan.json');mfreeze=b.read(b.MHERE/'inputs.json')
 assert b.sha(b.MHERE/'plan.json')==mfreeze['plan_sha256']
 assert len(terminal['commands'])==len(mplan['children'])
 tests=b.read(b.HERE/'expected-tests.json');assert tests['source_revision']==mplan['candidate_revision']
 for path,digest in tests['source_files'].items():assert b.sha(path)==digest
 environment=mplan['build_environment']
 assert environment['CARGO_NET_OFFLINE']=='true' and environment['PATH'].split(':')[0]==str(b.MHERE/'offline-bin')
 stages=[]
 def stage(argv):
  row=dict(argv=list(map(str,argv)),cwd=str(b.S),environment=environment);stages.append(row);return row
 stage(['./x','check','--stage','1','compiler/rustc_ast_lowering','--jobs','2','-vv'])
 stage(['./x','test','--stage','1','compiler/rustc_ast_lowering','--jobs','2','-vv'])
 stage(['./x','build','--stage','1','compiler/rustc','library','--jobs','2','-vv'])
 e=b.S/'build'/b.m.HOST/'stage1/bin/rustc'
 stage([e,'-vV']);stage([e,'--print','sysroot']);stage([e,'-Zhelp'])
 stage(['./x','test','--stage','1','compiler/rustc_interface','--jobs','2','-vv'])
 stage(['./x','build','--stage','1','src/tools/run-make-support','--jobs','2','-vv'])
 def gitrow(*args,stdout):return dict(argv=['/usr/bin/git',*args],cwd=str(b.S),environment=environment,stdout=stdout,stderr='')
 prefix=[gitrow('rev-parse','HEAD',stdout=mplan['candidate_revision']+'\n'),gitrow('diff','HEAD','--',stdout='')]
 suffix=[dict(row) for row in prefix]
 children=[*prefix,stages[0]];newroots=[];identities={}
 def replace(value):return json.loads(json.dumps(value).replace(str(b.m.OLD),str(b.S)))
 for name,path in mplan['closure_roots']:
  if name not in ['stage0-rustc','stage0-cargo','llvm-config']:continue
  newpath=path.replace(str(b.m.OLD),str(b.S));newroots.append([name,newpath]);identities[name]=replace(mplan['closures'][name]['identity'])
  # Reuse the exact metadata traversal order, including repeated logical
  # aliases. The first bootstrap stage must reproduce these admitted bytes.
  requests=[]
  b.m.planned_closure(path,requests,environment)
  for request in requests:
   row=replace(request);row['cwd']=str(b.S);row.pop('expected');row['stderr']='';children.append(row)
 children.extend(stages[1:4])
 children.append(dict(argv=[str(e),'-vV'],cwd=str(b.S),environment=environment|{'DYLD_PRINT_LIBRARIES':'1'}))
 children.extend(stages[4:]);children.extend(suffix)
 initial=b.output_files(b.S/'build')
 expected_seed_paths={str(Path(row['destination']).relative_to(b.S/'build')) for row in b.read(b.m.ACQUIRED)['copies'] if Path(row['destination']).is_relative_to(b.S/'build')}
 assert set(initial)==expected_seed_paths and len(initial)==6,'initial build tree contains unadmitted artifacts'
 assert not (b.N/'cargo-home/registry/src').exists()
 plan=dict(status='prepared-unrun',owner=str(b.OWNER),candidate_revision=mplan['candidate_revision'],source_identity=metadata['source_identity'],
  metadata_inputs_sha256=b.sha(b.MHERE/'inputs.json'),metadata_plan=mplan,metadata_receipt=dict(path=str(meta/'receipt.json'),sha256=b.sha(meta/'receipt.json')),
  tests=tests,llvm_version=metadata['llvm_version'],stages=stages,prefix_children=prefix,suffix_children=suffix,children=children,new_closure_roots=newroots,new_closure_identities=identities,
  initial_build_files=initial,environment=environment,capacity=mplan['capacity'],canonical_lock=str(b.owned.CANONICAL_LOCK),wait_seconds=600,
  native_recipe_qualified=False,hash_driver_qualified=False,application_qualified=False)
 write(b.HERE/'plan.json',plan)
 files={}
 def add(p):
  p=Path(p);record=b.m.file(p);assert str(p) not in files or files[str(p)]==record;files[str(p)]=record
 for p in [*b.HERE.glob('*'),*b.MHERE.glob('*.json'),b.MHERE/'metadata.py',b.MHERE/'offline-bin/curl',b.OWNER/'scripts/supervise_experiment.py',b.OWNER/'experiments/stable-cgu/owned_stage.py']:
  if p.is_file():add(p)
  if p.suffix=='.py':ast.parse(p.read_text())
 for p in meta.rglob('*'):
  if p.is_file():add(p)
 for p in [b.OWNER/'.work/hir-options-hash-build-budget-controls-02/receipt.json',b.OWNER/'.work/hir-options-hash-build-budget-controls-verification-02.json']:
  add(p)
 python=Path(sys.executable).resolve(strict=True);add(python)
 freeze=dict(files=files,python=str(python),plan_sha256=b.sha(b.HERE/'plan.json'),metadata_inputs_sha256=plan['metadata_inputs_sha256'],launch_environment=environment)
 write(b.HERE/'inputs.json',freeze)
 launch=dict(status='prepared-unrun-awaiting-review',owner=str(b.OWNER),environment=environment,
  command=[str(python),'-B',str(b.OWNER/'scripts/supervise_experiment.py'),'--run-id','hir-options-hash-compiler-build-supervisor-01','--',str(python),'-B',str(b.HERE/'build.py'),'--inputs-sha256',b.sha(b.HERE/'inputs.json')],
  plan_sha256=b.sha(b.HERE/'plan.json'),inputs_sha256=b.sha(b.HERE/'inputs.json'),helper_sha256=b.sha(b.HERE/'build.py'),expected_children=len(children),compiler_stages=8,capacity=plan['capacity'])
 write(b.HERE/'launch.json',launch)
 print(json.dumps(dict(launch_sha256=b.sha(b.HERE/'launch.json'),inputs_sha256=launch['inputs_sha256'],plan_sha256=launch['plan_sha256'],files=len(files),children=len(children),compiler_stages=8),indent=2))
if __name__=='__main__':main()
