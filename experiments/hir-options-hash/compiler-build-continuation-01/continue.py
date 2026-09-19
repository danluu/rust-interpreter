#!/usr/bin/env python3
"""Replay sixteen saved commands; execute only the nine remaining build rows."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time

HERE=Path(__file__).resolve().parent
OWNER=HERE.parents[2]
OLDHERE=OWNER/'experiments/hir-options-hash/compiler-build-02'
OLDWORK=OWNER/'.work/hir-options-hash-compiler-build-02'
OLDOUTER=OWNER/'.work/experiments/hir-options-hash-compiler-build-supervisor-02'
W=OWNER/'.work/hir-options-hash-compiler-build-continuation-01'

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 result=importlib.util.module_from_spec(spec);sys.modules[name]=result;spec.loader.exec_module(result);return result

# Load the old source with its original monitor binding, then explicitly load
# the new monitor. Historical paths and records never change in place.
sys.path.insert(0,str(OLDHERE))
b=module('previous_compiler_build',OLDHERE/'build.py')
monitor=module('continued_compiler_monitor',HERE/'bounded_command_v2.py')
test_source=module('continued_test_source',HERE/'test_source.py')
m=b.m;owned=b.owned;S=b.S;N=b.N
sha=b.sha;read=b.read

def members(root):
 return sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file())

def controls_guard(plan):
 proof=plan['monitor_controls'];root=Path(proof['root']);outer=Path(proof['outer'])
 terminal=read(root/'receipt.json');status=read(outer/'status.json');child=read(root/'command/receipt.json')
 frozen=read(HERE/'control-inputs-02.json')
 assert sha(root/'receipt.json')==proof['receipt_sha256']
 assert terminal['status']=='passed' and terminal['controls_passed']==13
 assert terminal['commands']==[dict(path=str(root/'command/receipt.json'),sha256=sha(root/'command/receipt.json'),pid=child['pid'])]
 assert status['status']=='finished' and status['returncode']==0 and status['child_pid']==terminal['pid'] and status['supervisor_pid']==terminal['parent_pid']
 assert sha(outer/'plan.json')==status['plan_sha256'] and sha(outer/'command.log')==status['log_sha256']
 assert status['started_at']<=terminal['started_at']<=terminal['admitted_at']<=child['started_at']<=child['finished_at']<=terminal['finished_at']<=status['finished_at']
 assert child['status']=='finished' and child['returncode']==0 and child['supervisor_pid']==terminal['pid'] and child['parent_pid']==terminal['parent_pid']
 assert child['command']==frozen['command'] and child['cwd']==str(HERE) and child['environment']==dict(frozen['environment'],TMPDIR=str(root/'tmp'))
 for stream in ['stdout','stderr']:assert sha(root/'command'/stream)==child[stream+'_sha256']
 assert not (root/'command/stdout').read_bytes()
 stderr=(root/'command/stderr').read_text()
 assert re.search(r'^Ran 13 tests in [0-9.]+s\n\nOK\n$',stderr,re.M) and len(re.findall(r'^test_.* \.\.\. ok$',stderr,re.M))==13
 for name,expected in proof['membership'].items():assert members(Path(name))==expected

def saved_guard(plan,*,replay_loaders=False):
 oldplan=read(OLDHERE/'plan.json');oldfreeze=read(OLDHERE/'inputs.json')
 assert sha(OLDHERE/'plan.json')==oldfreeze['plan_sha256']==plan['saved']['plan_sha256']
 assert sha(OLDHERE/'inputs.json')==plan['saved']['inputs_sha256']
 assert oldplan==plan['original_plan']
 assert plan['children']==oldplan['children'] and plan['remaining_children']==oldplan['children'][16:]
 assert plan['test_source']==test_source.derive(S,oldplan['tests'])
 assert plan['tests']==plan['test_source']['tests']
 terminal=read(OLDWORK/'receipt.json');outer=read(OLDOUTER/'status.json')
 assert sha(OLDWORK/'receipt.json')==plan['saved']['receipt_sha256']
 assert terminal['status']=='failed' and terminal['compiler_stages_completed']==2 and len(terminal['commands'])==16
 assert not any(terminal[key] for key in ['native_recipe_qualified','hash_driver_qualified','application_qualified'])
 assert outer['status']=='finished' and outer['returncode']==1
 assert outer['child_pid']==terminal['pid'] and outer['supervisor_pid']==terminal['parent_pid']
 assert sha(OLDOUTER/'plan.json')==outer['plan_sha256'] and sha(OLDOUTER/'command.log')==outer['log_sha256']
 assert outer['started_at']<=terminal['started_at']<=terminal['admitted_at']<=terminal['finished_at']<=outer['finished_at']
 previous=terminal['admitted_at']
 missing_cwd=[]
 for index,(ref,row) in enumerate(zip(terminal['commands'],oldplan['children'][:16],strict=True)):
  directory=OLDWORK/'commands'/f'{index:03}';child=read(directory/'receipt.json')
  assert ref==dict(path=str(directory/'receipt.json'),sha256=sha(directory/'receipt.json'),pid=child['pid'],command=row['argv'])
  assert child['status']=='finished' and child['returncode']==0 and child['expected']==[0]
  assert child['command']==row['argv'] and child['cwd']==row['cwd'] and child['environment']==row['environment']
  assert child['supervisor_pid']==terminal['pid'] and child['parent_pid']==terminal['parent_pid']
  identity=child['identity'];ps=identity['ps'].splitlines()
  assert identity['ps_returncode']==0 and len(ps)==1
  assert ps[0].split()[:3]==[str(child['pid']),str(terminal['pid']),str(child['pid'])]
  assert ps[0].endswith(' '.join(row['argv']))
  if identity['cwd_returncode']!=0 or not identity['cwd']:
   assert identity['cwd_returncode']==1 and not identity['cwd'];missing_cwd.append(index)
  else:assert 'n'+str(S) in identity['cwd'].splitlines()
  assert previous<=child['started_at']<=child['finished_at']<=terminal['finished_at'];previous=child['finished_at']
  assert child['samples'] and not any((directory/name).exists() for name in ['owned-stop.json','budget-reason.json'])
  for sample in child['samples']:
   assert not sample['allocation_errors'] and sample['free_bytes']>=9*2**30
   assert sample['namespace_allocated_bytes']<=14*2**30 and sample['evidence_allocated_bytes']<=256*2**20
  for stream in ['stdout','stderr']:
   assert sha(directory/stream)==child[stream+'_sha256']
   if stream in row:assert (directory/stream).read_bytes()==row[stream].encode()
  raw=(directory/'stdout').read_bytes()+b'\n'+(directory/'stderr').read_bytes()
  assert not re.search(rb'(?im)^\s*(?:downloading https?://|Building LLVM(?:\s|$)|Building GCC(?:\s|$)|HIR compiler experiment: bootstrap network)',raw)
 check=(OLDWORK/'commands/002/stdout').read_bytes()+(OLDWORK/'commands/002/stderr').read_bytes()
 assert re.search(rb'(?m)^running: .*cargo.*\"check\".*rustc_ast_lowering',check)
 raw=(OLDWORK/'commands/015/stdout').read_bytes()+(OLDWORK/'commands/015/stderr').read_bytes()
 names=re.findall(r'^test ([A-Za-z0-9_:]+) \.\.\. ok$',raw.decode(),re.M)
 assert terminal['error']==repr(AssertionError((names,oldplan['tests']['lowering'])))
 b.check_tests(raw,plan['tests']['lowering'])
 assert missing_cwd==plan['saved']['unavailable_contemporaneous_cwd_children']==[0,*range(3,15)]
 for root,expected in plan['saved']['membership'].items():assert members(Path(root))==expected
 assert not (OLDWORK/'compiled.json').exists()
 if replay_loaders:
  cursor=3;closures={}
  for name,path in oldplan['new_closure_roots']:
   def inspect(argv,*,text):
    nonlocal cursor
    assert text is True and cursor<15 and argv==oldplan['children'][cursor]['argv']
    directory=OLDWORK/'commands'/f'{cursor:03}';cursor+=1
    assert not (directory/'stderr').read_bytes();return (directory/'stdout').read_text()
   identity,state=m.loaders.library_closure(Path(path),m.HOST,inspect=inspect)
   old=read(OLDWORK/'extracted-provider-closures.json')[name]
   assert identity==old['identity']==oldplan['new_closure_identities'][name]
   observation=b.owned_closure_guard(old)
   assert state==observation['state']
   closures[name]=dict(identity=identity,state=state,prior_alias_transition=observation['owned_alias_ctime_deltas'])
  assert cursor==15
  return closures

class Stage(b.Stage):
 def __init__(self,digest):
  assert sha(HERE/'inputs.json')==digest
  self.frozen=read(HERE/'inputs.json');assert sha(HERE/'plan.json')==self.frozen['plan_sha256']
  self.plan=read(HERE/'plan.json');self.mfreeze=read(b.MHERE/'inputs.json')
  assert Path.cwd()==OWNER and sys.dont_write_bytecode and not sys.flags.optimize
  assert str(Path(sys.executable).resolve(strict=True))==self.frozen['python']
  assert not W.exists();W.mkdir();(W/'commands').mkdir()
  self.record=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),commands=[],
   compiler_stages_completed=2,saved_children=16,new_compiler_stages_completed=0,
   saved_cwd_limitations=self.plan['saved']['cwd_limitation'],
   source=str(S),candidate_revision=self.plan['candidate_revision'],source_identity=self.plan['source_identity'],
   native_recipe_qualified=False,hash_driver_qualified=False,application_qualified=False,
   prior_failed_build_sha256=self.plan['saved']['receipt_sha256'])
  self.provider_closures={};self.environment=dict(os.environ)
  expected=self.frozen['launch_environment'];extra=set(self.environment)-set(expected)
  assert all(self.environment.get(k)==v for k,v in expected.items()) and extra<={'__CF_USER_TEXT_ENCODING'}
  if extra:
   cf=self.environment['__CF_USER_TEXT_ENCODING'].split(':')
   assert len(cf)==3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})',v) for v in cf)
   assert int(cf[0],16 if cf[0].lower().startswith('0x') else 10)==os.getuid()==501
  self.save()
 def save(self):owned.write(W/'receipt.json',self.record)
 def guard(self,full=True):
  b.Stage.guard(self,full)
  saved_guard(self.plan)
  controls_guard(self.plan)
 def command(self,row):
  assert row==self.plan['remaining_children'][len(self.record['commands'])]
  self.guard();out=W/'commands'/f'{len(self.record["commands"]):03}'
  try:result=monitor.run(row['argv'],cwd=S,environment=row['environment'],output=out,canonical_fd=self.lockfd)
  finally:
   if (out/'receipt.json').exists():
    child=read(out/'receipt.json');self.record['commands'].append(dict(path=str(out/'receipt.json'),sha256=sha(out/'receipt.json'),pid=child.get('pid'),command=row['argv']));self.save()
  raw=(out/'stdout').read_bytes();err=(out/'stderr').read_bytes()
  assert not re.search(rb'(?im)^\s*(?:downloading https?://|Building LLVM(?:\s|$)|Building GCC(?:\s|$)|HIR compiler experiment: bootstrap network)',raw+b'\n'+err)
  if 'stdout' in row:assert raw.decode()==row['stdout']
  if 'stderr' in row:assert err.decode()==row['stderr']
  self.guard();return raw,err
 def run(self):
  try:
   with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
    self.lockfd=fd;self.record.update(status='running',admitted_at=time.time(),free_bytes_before=owned.disk(OWNER,24));self.save()
    self.guard()
    for root,expected in self.plan['continued_outputs'].items():assert b.output_files(Path(root))==expected
    assert not (N/'beta-sysroot').exists() and not (S/'build'/m.HOST/'stage1').exists()
    self.provider_closures=saved_guard(self.plan,replay_loaders=True)
    owned.write(W/'saved-provider-replay.json',self.provider_closures)
    owned.write(W/'continued-provider-files.json',b.extracted(self.plan))
    self.guard();assert monitor.rejection(monitor.sample()) is None
    for number,row in enumerate(self.plan['stages'][2:],2):
     out,err=self.command(row)
     if number==2:
      combined=(out+err).decode();revision=self.plan['candidate_revision']
      for key,value in self.plan['tests']['assertions']['build_compiler_std']['compiler_commit_environment'].items():assert key+'=\"'+value+'\"' in combined,(key,value)
      for key,value in [('CFG_VIRTUAL_RUSTC_DEV_SOURCE_BASE_DIR','/rustc-dev/'+revision),('CFG_VIRTUAL_RUST_SOURCE_BASE_DIR','/rustc/'+revision)]:assert key+'=\"'+value+'\"' in combined
      stage1=b.stage1_inventory();owned.write(W/'stage1-inventory.json',stage1)
     if number==3:
      text=out.decode();assert not err
      for line in self.plan['tests']['assertions']['rustc_version']['required_lines']:assert line in text.splitlines()
      assert 'LLVM version: '+self.plan['llvm_version'] in text.splitlines()
      allowed={str(S/'build'/m.HOST/'stage1/bin/rustc'),*[item['resolved'] for item in stage1['closure']['identity']['libraries']]}
      probe=self.plan['remaining_children'][len(self.record['commands'])];probe_out,probe_err=self.command(probe);assert probe_out==out
      loaded=b.native_loader(probe_err,read(self.record['commands'][-1]['path'])['pid'],allowed)
      assert m.loaders.library_state(stage1['closure']['identity'])==stage1['closure']['state']
      for name,item in stage1['files'].items():
       if item['kind']=='file':assert m.file(Path(stage1['root'])/name)=={key:item[key] for key in ['sha256','stamp']}
      owned.write(W/'stage1-native-loader.json',loaded)
     if number==4:assert not err and out.decode()==str(S/'build'/m.HOST/'stage1')+'\n'
     if number==5:
      assert not err;options=set(re.findall(r'(?m)^\s*(?:-Z\s+)?([a-z][a-z0-9-]+)\s*=',out.decode()))
      assert set(self.plan['tests']['assertions']['rustc_unstable_help']['required_option_names'])<=options
     if number==6:b.check_tests(out+err,self.plan['tests']['interface'])
     if number==7:
      assert b'run_make_support' in out+err;owned.write(W/'run-make-support-inventory.json',b.support_inventory())
     b.extracted(self.plan)
     self.record.update(compiler_stages_completed=number+1,new_compiler_stages_completed=number-1);self.save()
    for row in self.plan['suffix_children']:self.command(row)
    assert len(self.record['commands'])==9
    self.guard();providers=b.extracted(self.plan);stage1=b.output_files(S/'build'/m.HOST/'stage1')
    owned.write(W/'stage1-final-loader-state.json',b.owned_closure_guard(read(W/'stage1-inventory.json')['closure']))
    prior=read(OLDWORK/'receipt.json')['commands'];history=[*prior,*self.record['commands']]
    assert len(history)==25
    owned.write(W/'compiled.json',dict(status='compiled-awaiting-native-recipe-and-B3-qualification',candidate_revision=self.plan['candidate_revision'],source_identity=self.plan['source_identity'],
     stage1=stage1,providers=providers,native_loader_sha256=sha(W/'stage1-native-loader.json'),run_make_support_sha256=sha(W/'run-make-support-inventory.json'),stages=8,
     all_lowering_tests=27,all_interface_tests=18,prior_failed_build_sha256=sha(OLDWORK/'receipt.json'),saved_children=16,actual_continuation_children=9,command_history=history))
    self.record.update(status='passed',compiled_sha256=sha(W/'compiled.json'),free_bytes_after=owned.disk(OWNER,9))
  except BaseException as error:self.record.update(status='failed',error=repr(error));raise
  finally:self.record['finished_at']=time.time();self.save()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True);args=parser.parse_args();Stage(args.inputs_sha256).run()
if __name__=='__main__':main()
