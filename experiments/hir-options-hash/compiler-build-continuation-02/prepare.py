#!/usr/bin/env python3
"""Prepare source-correct support route and final guards; never execute a tool."""
import ast
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('compiler_support_continuation',HERE/'continue.py')
c=importlib.util.module_from_spec(spec);sys.modules[spec.name]=c;spec.loader.exec_module(c)

def write(path,value):
 with path.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')

def main():
 assert Path.cwd()==c.OWNER and sys.dont_write_bytecode and not sys.flags.optimize
 assert not c.W.exists() and not (HERE/'inputs.json').exists() and not (HERE/'launch.json').exists()
 old=c.read(c.PREVIOUS/'plan.json');oldfreeze=c.read(c.PREVIOUS/'inputs.json')
 assert c.sha(c.PREVIOUS/'plan.json')==oldfreeze['plan_sha256']
 assert c.sha(c.PREVIOUS_WORK/'receipt.json')=='def5d63da6b618efcacfaf64f605ffe37dba552f0dfd712717168b620ae4d9be'
 plan=json.loads(json.dumps(old))
 # The exact historical plan is frozen once and read through its hash binding.
 # Avoid embedding a second copy of its old mutable admission observation.
 for key in ['original_plan','initial_build_files','continued_outputs']:plan.pop(key,None)
 support=json.loads(json.dumps(old['children'][22]));assert support['argv'][1]=='build';support['argv'][1]='test'
 plan['children'][22]=support;plan['stages'][7]=support
 plan.update(status='prepared-unrun',remaining_children=plan['children'][22:],
  support_route=c.support_source.derive(c.S),
  previous_continuation=dict(receipt_sha256=c.sha(c.PREVIOUS_WORK/'receipt.json'),
   inputs_sha256=c.sha(c.PREVIOUS/'inputs.json'),plan_sha256=c.sha(c.PREVIOUS/'plan.json'),
   membership={str(root):c.members(root) for root in [c.PREVIOUS_WORK,c.PREVIOUS_OUTER]},
   unavailable_contemporaneous_cwd_children=[1],
   cwd_limitation='Original thirteen fast Git/otool children and previous-continuation -vV child001 have rc1/empty contemporaneous cwd probes. Exact recorded Popen cwd and ps identities remain retained; no unavailable observation is inferred.'),
  continuation_semantics='Retain 22 successful commands plus failed unsupported build route. Execute registered support-library test route and two remaining Git guards only. Successful logical history has25 rows; complete actual history has26 rows and three owning controllers.',
  current_compiler_stages=7,new_compiler_stages=1,actual_children=3,prior_children=22,prior_actual_children=23)
 controls=c.OWNER/'.work/hir-options-hash-support-controls-01'
 control_outer=c.OWNER/'.work/experiments/hir-options-hash-support-controls-supervisor-01'
 plan['support_controls']=dict(root=str(controls),outer=str(control_outer),receipt_sha256=c.sha(controls/'receipt.json'),
  membership={str(root):c.members(root) for root in [controls,control_outer]})
 c.support_controls_guard(plan)
 assert len(plan['remaining_children'])==3 and plan['suffix_children']==old['suffix_children']
 c.recent_guard(plan);c.b.extracted(plan)
 assert not (c.N/'beta-sysroot').exists()
 roots=[c.S/'build',c.N/'cargo-home/registry/src']
 assert all(root.is_dir() and root.resolve(strict=True)==root for root in roots)
 # Only current post-history state is bound for new admission. Historical
 # snapshots stay immutable in their original plans and keep their old meaning.
 plan['continued_outputs']={str(root):c.b.output_files(root) for root in roots}
 files={}
 def add(path):
  path=Path(path);row=c.m.file(path)
  assert str(path) not in files or files[str(path)]==row
  files[str(path)]=row
 for name,row in oldfreeze['files'].items():
  add(name);assert files[name]==row
 for name,membership in plan['previous_continuation']['membership'].items():
  for member in membership:add(Path(name)/member)
 for name,membership in plan['support_controls']['membership'].items():
  for member in membership:add(Path(name)/member)
 for name,row in c.read(HERE/'control-inputs.json')['files'].items():
  add(name);assert files[name]['sha256']==row['sha256'] and files[name]['stamp'][3]==row['bytes']
 for suffix in ['actual.json','stdout','stderr']:
  add(c.OWNER/('.work/hir-options-hash-support-controls-launch-01.'+suffix))
 for path in [c.PREVIOUS/'inputs.json',c.PREVIOUS/'launch.json']:add(path)
 for suffix in ['actual.json','stdout','stderr']:
  add(c.OWNER/('.work/hir-options-hash-compiler-continuation-launch-01.'+suffix))
 for name in ['wait_hir_options_continuation_capacity_01.py','hir-options-hash-compiler-continuation-capacity-wait-01.json','hir-options-hash-compiler-continuation-prelaunch-capacity-01.json']:
  add(c.OWNER/'.work'/name)
 audit=c.OWNER/'.work/hir-options-hash-compiler-continuation-failure-verification-01.json'
 assert c.sha(audit)=='a98409c4f39f7d28e7132d04a216278f326596e0804357f4652fcfd0c5ba263c'
 assert c.read(audit)['status']=='verified-retained-failure' and c.read(audit)['receipt_sha256']==plan['previous_continuation']['receipt_sha256']
 add(audit);add(c.OWNER/'.work/verify_hir_options_compiler_continuation_failure_01.py')
 plan['previous_continuation']['independent_actual_audit']=dict(path=str(audit),sha256=c.sha(audit))
 for name in plan['support_route']['files']:add(c.S/name)
 write(HERE/'plan.json',plan)
 for path in sorted(HERE.iterdir()):
  if path.is_file():
   add(path)
   if path.suffix=='.py':ast.parse(path.read_bytes())
 python=Path(sys.executable).resolve(strict=True);add(python)
 freeze=dict(files=files,python=str(python),plan_sha256=c.sha(HERE/'plan.json'),
  metadata_inputs_sha256=plan['metadata_inputs_sha256'],launch_environment=plan['environment'])
 write(HERE/'inputs.json',freeze)
 launch=dict(status='prepared-unrun-awaiting-review',owner=str(c.OWNER),environment=plan['environment'],
  command=[str(python),'-B',str(c.OWNER/'scripts/supervise_experiment.py'),'--run-id','hir-options-hash-compiler-build-continuation-supervisor-02',
   '--',str(python),'-B',str(HERE/'continue.py'),'--inputs-sha256',c.sha(HERE/'inputs.json')],
  plan_sha256=c.sha(HERE/'plan.json'),inputs_sha256=c.sha(HERE/'inputs.json'),helper_sha256=c.sha(HERE/'continue.py'),
  expected_children=3,saved_children=22,saved_actual_children=23,compiler_stages=8,new_compiler_stages=1,capacity=plan['capacity'])
 write(HERE/'launch.json',launch)
 print(json.dumps(dict(launch_sha256=c.sha(HERE/'launch.json'),inputs_sha256=launch['inputs_sha256'],plan_sha256=launch['plan_sha256'],
  files=len(files),bytes=sum(row['stamp'][3] for row in files.values()),saved_children=22,new_children=3,
  current_output_files=sum(len(rows) for rows in plan['continued_outputs'].values()),
  current_output_bytes=sum(row['stamp'][3] for rows in plan['continued_outputs'].values() for row in rows.values() if row['kind']=='file')),indent=2))

if __name__=='__main__':main()
