#!/usr/bin/env python3
"""Freeze a saved-sixteen/remaining-nine continuation, without any compiler call."""
import ast
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('compiler_continuation',HERE/'continue.py')
c=importlib.util.module_from_spec(spec);sys.modules[spec.name]=c;spec.loader.exec_module(c)

def write(path,value):
 with path.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')

def main():
 assert Path.cwd()==c.OWNER and sys.dont_write_bytecode and not sys.flags.optimize
 assert not c.W.exists() and not (HERE/'inputs.json').exists() and not (HERE/'launch.json').exists()
 old=c.read(c.OLDHERE/'plan.json');oldfreeze=c.read(c.OLDHERE/'inputs.json')
 assert c.sha(c.OLDHERE/'plan.json')==oldfreeze['plan_sha256']
 assert c.sha(c.OLDWORK/'receipt.json')=='2a2e9ef2b72ea10a08d78a16626b28b71904b5d3d34f070d27c900719636e1f8'
 qualified=c.test_source.derive(c.S,old['tests'])
 assert c.read(HERE/'expected-tests.json')==qualified['tests']
 plan=json.loads(json.dumps(old))
 plan.update(status='prepared-unrun',original_plan=old,test_source=qualified,tests=qualified['tests'],
  remaining_children=old['children'][16:],saved=dict(receipt_sha256=c.sha(c.OLDWORK/'receipt.json'),
   inputs_sha256=c.sha(c.OLDHERE/'inputs.json'),plan_sha256=c.sha(c.OLDHERE/'plan.json'),
   membership={str(root):c.members(root) for root in [c.OLDWORK,c.OLDOUTER]},
   unavailable_contemporaneous_cwd_children=[0,*range(3,15)],
   cwd_limitation='Thirteen fast Git/otool children have rc1/empty contemporaneous cwd probes; recorded Popen cwd and exact ps PID/parent/command are retained. No missing observation is inferred.'),
  continuation_semantics='Prior sixteen successful children and original name-validation failure remain immutable; only original final nine rows execute.',
  current_compiler_stages=2,new_compiler_stages=6,actual_children=9,prior_children=16)
 controls=c.OWNER/'.work/hir-options-hash-build-continuation-controls-02'
 control_outer=c.OWNER/'.work/experiments/hir-options-hash-build-continuation-controls-supervisor-02'
 plan['monitor_controls']=dict(root=str(controls),outer=str(control_outer),receipt_sha256=c.sha(controls/'receipt.json'),
  membership={str(root):c.members(root) for root in [controls,control_outer]})
 c.controls_guard(plan)
 assert len(plan['remaining_children'])==9 and plan['stages']==old['stages']
 assert not (c.S/'build'/c.m.HOST/'stage1').exists() and not (c.N/'beta-sysroot').exists()
 c.saved_guard(plan,replay_loaders=True)
 c.b.extracted(plan)
 # Existing mutable outputs are bound exactly once after admission. Later
 # changes are from the remaining owned bootstrap commands, under the original
 # namespace monitor and immutable source/archive/provider guards.
 roots=[c.S/'build',c.N/'cargo-home/registry/src']
 assert all(root.is_dir() and root.resolve(strict=True)==root for root in roots)
 plan['continued_outputs']={str(root):c.b.output_files(root) for root in roots}
 files={}
 def add(path):
  path=Path(path);row=c.m.file(path)
  assert str(path) not in files or files[str(path)]==row
  files[str(path)]=row
 # Preserve original inputs and failed histories; none of the mutable build
 # output snapshots is promoted into an immutable provider catalog.
 for name,row in oldfreeze['files'].items():
  add(name);assert files[name]==row
 for root_name,membership in plan['saved']['membership'].items():
  for name in membership:add(Path(root_name)/name)
 for name,row in c.read(HERE/'control-inputs-02.json')['files'].items():
  add(name);assert files[name]['sha256']==row['sha256'] and files[name]['stamp'][3]==row['bytes']
 for root_name,membership in plan['monitor_controls']['membership'].items():
  for name in membership:add(Path(root_name)/name)
 for suffix in ['actual.json','stdout','stderr']:
  add(c.OWNER/('.work/hir-options-hash-build-continuation-controls-launch-02.'+suffix))
 controls_audit=c.OWNER/'.work/hir-options-hash-build-continuation-controls-verification-02.json'
 assert c.sha(controls_audit)=='95c5a6a60469be7765b4214ac339bbd758598fae988aca60e88e64343e95f3dc'
 add(controls_audit);add(c.OWNER/'.work/verify_hir_options_continuation_controls_02.py')
 add(c.OWNER/'.work/hir-options-hash-continuation-capacity-observation-01.json')
 for path in [c.OLDHERE/'inputs.json',c.OLDHERE/'launch.json']:
  add(path)
 for suffix in ['actual.json','stdout','stderr']:
  add(c.OWNER/('.work/hir-options-hash-compiler-build-launch-02.'+suffix))
 for name in ['hir-options-hash-compiler-build-prelaunch-capacity-01.json','wait_hir_options_build_capacity_02.py','hir-options-hash-compiler-build-capacity-wait-02.json']:
  add(c.OWNER/'.work'/name)
 peer=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work')
 audit=peer/'options-hash-build02-failure-independent-verification.json'
 assert c.sha(audit)=='9c23190a065a187b4325202c81858aab9b04ae685255e59a46bd9ad89cf8776b'
 add(audit);add(peer/'verify-options-hash-build02-failure.py')
 root_audit=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/root-compiler-continuation-test-names-verification-01.json')
 assert c.sha(root_audit)=='41d4f0c36b9a4a0b8ef698ed9dd4c044c932eb2d9075dd6fc5869475ee31315e';add(root_audit)
 plan['saved']['independent_actual_audit']=dict(path=str(audit),sha256=c.sha(audit))
 for row in qualified['proof']['files']:add(row['path'])
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
  command=[str(python),'-B',str(c.OWNER/'scripts/supervise_experiment.py'),'--run-id','hir-options-hash-compiler-build-continuation-supervisor-01',
   '--',str(python),'-B',str(HERE/'continue.py'),'--inputs-sha256',c.sha(HERE/'inputs.json')],
  plan_sha256=c.sha(HERE/'plan.json'),inputs_sha256=c.sha(HERE/'inputs.json'),helper_sha256=c.sha(HERE/'continue.py'),
  expected_children=9,saved_children=16,compiler_stages=8,new_compiler_stages=6,capacity=plan['capacity'])
 write(HERE/'launch.json',launch)
 print(json.dumps(dict(launch_sha256=c.sha(HERE/'launch.json'),inputs_sha256=launch['inputs_sha256'],plan_sha256=launch['plan_sha256'],
  files=len(files),bytes=sum(row['stamp'][3] for row in files.values()),saved_children=16,new_children=9,
  current_output_files=sum(len(rows) for rows in plan['continued_outputs'].values()),
  current_output_bytes=sum(row['stamp'][3] for rows in plan['continued_outputs'].values() for row in rows.values() if row['kind']=='file')),indent=2))

if __name__=='__main__':main()
