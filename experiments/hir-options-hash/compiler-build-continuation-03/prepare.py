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

def retirement():
 """Bind the completed 1+4645 transition without relabeling old snapshots."""
 owner=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
 source=owner/'experiments/hir-options-hash-intermediate-retirement'
 packet=source/'plan-02';work=owner/'.work/hir-options-hash-intermediate-retirement-02'
 audit_path=owner/'.work/hir-options-hash-intermediate-retirement-verification-02.json'
 assert c.sha(audit_path)=='11eaae6c7c74d60036e193af13b7fd82b51492748cbeecc4e10a4dc151a090e6'
 assert c.sha(packet/'inputs.json')=='bf3ce3c879cda62d396f112f262437338a4a144a366cf6005e2d15ff866c7340'
 assert c.sha(packet/'launch.json')=='77afdcff5679d34a2a1719a1f57274f651a4847ba3d2660f1e525be73ad26ccf'
 audit=c.read(audit_path);terminal=c.read(work/'receipt.json');assessment=c.read(packet/'assessment.json')
 assert audit['status']=='verified' and c.sha(work/'receipt.json')==audit['terminal_sha256']
 assert terminal['status']=='passed' and terminal['retired_files']==audit['successor_retired_files']==4645
 assert terminal['prior_partial_retired_files']==audit['prior_partial_retired_files']==1
 assert terminal['combined_retired_files']==audit['combined_retired_files']==4646
 assert terminal['removed_directories']==audit['removed_directories']==0 and audit['ledger_rows']==13935
 assert audit['all_remaining_membership_bytes_and_identities_match_ledger'] and audit['all_protected_bytes_and_identities_unchanged']
 assert terminal['validated_deletions']==4645 and not terminal['uncertain_unlink_intents'] and 'ledger_readback_error' not in terminal
 for name,key in [('remaining-inventory.json','remaining_inventory_sha256'),('transition.json','transition_sha256'),('deleted.jsonl','deleted_ledger_sha256')]:
  assert c.sha(work/name)==audit[key]==terminal[key]
 transition=c.read(work/'transition.json');remaining=c.read(work/'remaining-inventory.json')['entries']
 assert transition==assessment['transition'] and terminal['prior_partial']==audit['prior_partial']==assessment['prior_partial']==transition['prior_partial']
 assert c.read(work/'admitted-inventory.json')['entries']==assessment['entries']
 root=c.S/'build'/c.m.HOST/'stage1-rustc';assert assessment['root']==str(root)
 original=c.read(source/'plan-01/assessment.json');partial=assessment['prior_partial']
 removed={str(root/name) for name in original['selected']}
 assert set(terminal['deleted'])|{partial['removed_path']}==removed and len(terminal['deleted'])==len(set(terminal['deleted']))==4645
 assert set(assessment['entries'])-set(remaining)==set(assessment['selected']) and not set(remaining)-set(assessment['entries'])
 for name in removed:assert not Path(name).exists() and not Path(name).is_symlink()
 preserved=source/'preserved-consumer-03/manifest.json'
 assert c.sha(preserved)=='e242c58b85a8341229c29d16c2cfb3bb9f632664b5a98e7d436a0897efac7b02'
 retained=c.read(preserved)['files'];consumer=transition['consumer']['files']
 assert set(retained)==set(consumer)
 paths={audit_path,packet/'inputs.json',packet/'launch.json',preserved,owner/'.work/verify_intermediate_retirement_02.py',
  c.OWNER/'.work/hir-options-hash-compiler-continuation-03-prepare-before-retirement.py',
  c.OWNER/'.work/launch_hir_options_compiler_continuation_03.py'}
 old_freeze=c.read(packet/'inputs.json')
 historical_sources={}
 for name,row in old_freeze['files'].items():
  path=Path(name)
  if name==str(HERE/'prepare.py'):
   path=Path(retained[name]['retained_path']);historical_sources[name]=str(path)
  actual=c.m.file(path)
  assert actual['sha256']==row['sha256'] and actual['stamp'][3]==row['identity']['size']
  if name!=str(HERE/'prepare.py'):
   assert dict(zip(['dev','ino','mode','size','mtime_ns','ctime_ns','nlink'],actual['stamp'],strict=True))==row['identity']
  paths.add(path)
 for name,row in retained.items():
  path=Path(row['retained_path']);assert c.sha(path)==row['sha256']==consumer[name] and path.stat().st_size==row['bytes'];paths.add(path)
  if name!=str(HERE/'prepare.py'):assert c.sha(Path(name))==row['sha256']
 before=c.OWNER/'.work/hir-options-hash-compiler-continuation-03-prepare-before-retirement.py'
 assert c.sha(before)==consumer[str(HERE/'prepare.py')]=='17c9845bfafb77c4838a37c0edfd912702e928f7c97cab9b1f0ab0e6ef7bc38d'
 outer=owner/'.work/experiments/hir-options-hash-intermediate-retirement-supervisor-02'
 status=c.read(outer/'status.json');assert status['status']=='finished' and status['returncode']==0
 assert status['child_pid']==terminal['pid'] and status['supervisor_pid']==terminal['parent_pid'] and terminal['finished_at']<=status['finished_at']
 for directory in [work,outer]:
  for member in c.members(directory):paths.add(directory/member)
 for suffix in ['actual.json','stdout','stderr']:paths.add(owner/('.work/hir-options-hash-intermediate-retirement-launch-02.'+suffix))
 paths.add(owner/'.work/launch_intermediate_retirement_02.py')
 for key in ['terminal','audit','inventory','original_plan','original_freeze']:
  ref=partial[key];path=Path(ref['path']);assert c.sha(path)==ref['sha256'];paths.add(path)
 proof=dict(policy='completed-intermediate-retirement-v2',terminal=dict(path=str(work/'receipt.json'),sha256=c.sha(work/'receipt.json')),
  audit=dict(path=str(audit_path),sha256=c.sha(audit_path)),prior_partial=partial,
  before_catalog=str(work/'admitted-inventory.json'),after_catalog=str(work/'remaining-inventory.json'),
  transition=dict(path=str(work/'transition.json'),sha256=c.sha(work/'transition.json')),
  historical_sources=historical_sources,combined_retired_files=4646,successor_retired_files=4645,prior_partial_retired_files=1,
  proofs=[dict(path=str(path),sha256=c.sha(path)) for path in sorted(paths)])
 return proof,paths,root,remaining

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
 control_source=HERE.with_name('compiler-build-continuation-02')/'support-controls-03'
 controls=c.OWNER/'.work/hir-options-hash-support-controls-03'
 control_outer=c.OWNER/'.work/experiments/hir-options-hash-support-controls-supervisor-03'
 control_audit=c.OWNER/'.work/hir-options-hash-support-controls-verification-03.json'
 assert c.sha(control_audit)=='fbbe3d010e41bec89cb483dbc79397ea4f56941ba931adbf63d9f2e97493e37b'
 plan['support_controls']=dict(schema='bounded-seven-support-controls-v1',source=str(control_source),
  inputs_sha256=c.sha(control_source/'inputs.json'),launch_sha256=c.sha(control_source/'launch.json'),
  audit=dict(path=str(control_audit),sha256=c.sha(control_audit)),
  root=str(controls),outer=str(control_outer),receipt_sha256=c.sha(controls/'receipt.json'),
  membership={str(root):c.members(root) for root in [controls,control_outer]})
 c.support_controls_guard(plan)
 assert len(plan['remaining_children'])==3 and plan['suffix_children']==old['suffix_children']
 c.recent_guard(plan);c.b.extracted(plan)
 assert not (c.N/'beta-sysroot').exists()
 retirement_proof,retirement_paths,retired_root,remaining=retirement()
 plan['retirement_transition']=retirement_proof
 roots=[c.S/'build',c.N/'cargo-home/registry/src']
 assert all(root.is_dir() and root.resolve(strict=True)==root for root in roots)
 # Only current post-history state is bound for new admission. Historical
 # snapshots stay immutable in their original plans and keep their old meaning.
 plan['continued_outputs']={str(root):c.b.output_files(root) for root in roots}
 prefix=str(retired_root.relative_to(c.S/'build'))+'/'
 actual={name[len(prefix):]:row for name,row in plan['continued_outputs'][str(c.S/'build')].items() if name.startswith(prefix)}
 expected={}
 for name,row in remaining.items():
  if row['kind']=='directory':continue
  identity=row['identity'];entry=dict(kind=row['kind'],stamp=[identity[key] for key in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']])
  if row['kind']=='file':entry['sha256']=row['sha256']
  else:entry.update(target=row['target'],resolved=row['resolved'])
  expected[name]=entry
 assert actual==expected,'new snapshot differs from completed retirement remaining catalog'
 files={}
 def add(path):
  path=Path(path);row=c.m.file(path)
  assert str(path) not in files or files[str(path)]==row
  files[str(path)]=row
 for path in sorted(retirement_paths):add(path)
 for name,row in oldfreeze['files'].items():
  add(name);assert files[name]==row
 for name,membership in plan['previous_continuation']['membership'].items():
  for member in membership:add(Path(name)/member)
 for name,membership in plan['support_controls']['membership'].items():
  for member in membership:add(Path(name)/member)
 for name,row in c.read(control_source/'inputs.json')['files'].items():
  add(name);assert files[name]['sha256']==row['sha256'] and files[name]['stamp'][3]==row['stamp'][3]
 for path in [control_source/'inputs.json',control_source/'launch.json',control_audit,
  c.OWNER/'.work/verify_hir_options_support_controls_03.py',c.OWNER/'.work/verify_hir_options_support_controls_03-preflight-01.py',
  c.OWNER/'.work/hir-options-hash-support-controls-review-03.json']:add(path)
 for suffix in ['actual.json','stdout','stderr']:
  add(c.OWNER/('.work/hir-options-hash-support-controls-launch-03.'+suffix))
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
  command=[str(python),'-B',str(c.OWNER/'scripts/supervise_experiment.py'),'--run-id','hir-options-hash-compiler-build-continuation-supervisor-03',
   '--',str(python),'-B',str(HERE/'continue.py'),'--inputs-sha256',c.sha(HERE/'inputs.json')],
  plan_sha256=c.sha(HERE/'plan.json'),inputs_sha256=c.sha(HERE/'inputs.json'),helper_sha256=c.sha(HERE/'continue.py'),
  expected_children=3,saved_children=22,saved_actual_children=23,compiler_stages=8,new_compiler_stages=1,capacity=plan['capacity'])
 write(HERE/'launch.json',launch)
 print(json.dumps(dict(launch_sha256=c.sha(HERE/'launch.json'),inputs_sha256=launch['inputs_sha256'],plan_sha256=launch['plan_sha256'],
  files=len(files),bytes=sum(row['stamp'][3] for row in files.values()),saved_children=22,new_children=3,
  current_output_files=sum(len(rows) for rows in plan['continued_outputs'].values()),
  current_output_bytes=sum(row['stamp'][3] for rows in plan['continued_outputs'].values() for row in rows.values() if row['kind']=='file')),indent=2))

if __name__=='__main__':main()
