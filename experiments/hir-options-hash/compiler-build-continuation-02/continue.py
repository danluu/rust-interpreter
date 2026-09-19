#!/usr/bin/env python3
"""Replay 22 successful commands and one failed route; execute three new rows."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import tomllib
import sys
import time

HERE=Path(__file__).resolve().parent
OWNER=HERE.parents[2]
PREVIOUS=HERE.with_name('compiler-build-continuation-01')
PREVIOUS_WORK=OWNER/'.work/hir-options-hash-compiler-build-continuation-01'
PREVIOUS_OUTER=OWNER/'.work/experiments/hir-options-hash-compiler-build-continuation-supervisor-01'
W=OWNER/'.work/hir-options-hash-compiler-build-continuation-02'

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 result=importlib.util.module_from_spec(spec);sys.modules[name]=result;spec.loader.exec_module(result);return result

prior=module('compiler_first_continuation',PREVIOUS/'continue.py')
monitor=module('compiler_support_continuation_monitor',HERE/'bounded_command_v2.py')
support_source=module('compiler_support_source',HERE/'support_source.py')
timing=module('compiler_support_timing',HERE/'timing_context.py')
parsers=module('compiler_support_parsers',HERE/'producer_parsers.py')
producer=module('compiler_support_producer',HERE/'support_producer.py')
b=prior.b;m=prior.m;owned=prior.owned;S=prior.S;N=prior.N
read=prior.read;sha=prior.sha;members=prior.members

def support_tests(raw,expected):
 names=re.findall(r'^test ([A-Za-z0-9_:]+) \.\.\. ok$',raw.decode(),re.M)
 assert len(names)==len(set(names))==15 and set(names)==set(expected['test_names']),(names,expected)
 # Bootstrap's JSON renderer prints TestOutcome.name; it does not append the
 # separate pretty-formatter should-panic annotation. The six exact source
 # attributes remain in the bound definition proof and libtest enforces them.
 assert expected['unit_output_policy']=='JSON TestOutcome.name, unchanged by bootstrap verbose rendering'
 assert sum(row['should_panic'] for row in expected['test_definitions'])==6
 assert b'test result: ok. 15 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;' in raw
 docs=[]
 for match in re.finditer(r'^test (.+\.rs) - (\S+) \(line (\d+)\) \.\.\. (ok|ignored)$',raw.decode(),re.M):
  name,item,line,status=match.groups()
  if name.startswith(str(S)+'/'):name=name[len(str(S))+1:]
  virtual='/rustc-dev/'+read(HERE/'plan.json')['candidate_revision']+'/'
  if name.startswith(virtual):name=name[len(virtual):]
  if name.startswith('src/') and not name.startswith('src/tools/'):
   name='src/tools/run-make-support/'+name
  docs.append(dict(path=name,item=item,line=int(line),status=status))
 target=[{key:row[key] for key in ['path','item','line','status']} for row in expected['doctests']]
 assert sorted(docs,key=str)==sorted(target,key=str),(docs,target)

def retained_terminal(terminal):
 assert terminal['status']=='failed' and len(terminal['commands'])==7 and terminal['compiler_stages_completed']==7
 assert terminal['new_compiler_stages_completed']==5 and terminal['saved_children']==16
 assert terminal['error']=="AssertionError('unexpected compiler-stage return code')"
 assert not any(terminal[k] for k in ['native_recipe_qualified','hash_driver_qualified','application_qualified'])

def support_controls_guard(plan):
 proof=plan['support_controls'];root=Path(proof['root']);outer=Path(proof['outer'])
 terminal=read(root/'receipt.json');status=read(outer/'status.json');child=read(root/'command/receipt.json')
 frozen=read(HERE/'control-inputs.json')
 assert sha(root/'receipt.json')==proof['receipt_sha256']
 assert terminal['status']=='passed' and terminal['controls_passed']==7
 assert terminal['commands']==[dict(path=str(root/'command/receipt.json'),sha256=sha(root/'command/receipt.json'),pid=child['pid'])]
 assert status['status']=='finished' and status['returncode']==0 and status['child_pid']==terminal['pid'] and status['supervisor_pid']==terminal['parent_pid']
 assert sha(outer/'plan.json')==status['plan_sha256'] and sha(outer/'command.log')==status['log_sha256']
 assert status['started_at']<=terminal['started_at']<=terminal['admitted_at']<=child['started_at']<=child['finished_at']<=terminal['finished_at']<=status['finished_at']
 assert child['status']=='finished' and child['returncode']==0 and child['supervisor_pid']==terminal['pid'] and child['parent_pid']==terminal['parent_pid']
 assert child['command']==frozen['command'] and child['cwd']==str(HERE) and child['environment']==dict(frozen['environment'],TMPDIR=str(root/'tmp'))
 for stream in ['stdout','stderr']:assert sha(root/'command'/stream)==child[stream+'_sha256']
 assert not (root/'command/stdout').read_bytes()
 stderr=(root/'command/stderr').read_text()
 assert re.search(r'^Ran 7 tests in [0-9.]+s\n\nOK\n$',stderr,re.M) and len(re.findall(r'^test_.* \.\.\. ok$',stderr,re.M))==7
 for name,expected in proof['membership'].items():assert members(Path(name))==expected

def recent_guard(plan):
 proof=plan['previous_continuation'];old=read(PREVIOUS/'plan.json')
 assert sha(PREVIOUS/'plan.json')==read(PREVIOUS/'inputs.json')['plan_sha256']==proof['plan_sha256']
 assert sha(PREVIOUS/'inputs.json')==proof['inputs_sha256']
 prior.saved_guard(old);prior.controls_guard(old)
 assert plan['support_route']==support_source.derive(S)
 assert plan['children'][:22]==old['children'][:22] and plan['children'][23:]==old['children'][23:]
 expected=json.loads(json.dumps(old['children'][22]));expected['argv'][1]='test'
 assert plan['children'][22]==expected and plan['remaining_children']==plan['children'][22:]
 assert plan['stages'][:7]==old['stages'][:7] and plan['stages'][7]==expected
 terminal=read(PREVIOUS_WORK/'receipt.json');outer=read(PREVIOUS_OUTER/'status.json')
 assert sha(PREVIOUS_WORK/'receipt.json')==proof['receipt_sha256']
 retained_terminal(terminal)
 assert outer['status']=='finished' and outer['returncode']==1
 assert outer['child_pid']==terminal['pid'] and outer['supervisor_pid']==terminal['parent_pid']
 assert sha(PREVIOUS_OUTER/'plan.json')==outer['plan_sha256'] and sha(PREVIOUS_OUTER/'command.log')==outer['log_sha256']
 assert outer['started_at']<=terminal['started_at']<=terminal['admitted_at']<=terminal['finished_at']<=outer['finished_at']
 previous=terminal['admitted_at'];missing=[]
 for index,(ref,row) in enumerate(zip(terminal['commands'],old['children'][16:23],strict=True)):
  directory=PREVIOUS_WORK/'commands'/f'{index:03}';child=read(directory/'receipt.json')
  assert ref==dict(path=str(directory/'receipt.json'),sha256=sha(directory/'receipt.json'),pid=child['pid'],command=row['argv'])
  assert child['expected']==[0]
  if index==6:assert child['status']=='failed' and child['returncode']==1 and child['error']==terminal['error']
  else:assert child['status']=='finished' and child['returncode']==0
  assert child['command']==row['argv'] and child['cwd']==row['cwd'] and child['environment']==row['environment']
  assert child['supervisor_pid']==terminal['pid'] and child['parent_pid']==terminal['parent_pid']
  assert previous<=child['started_at']<=child['finished_at']<=terminal['finished_at'];previous=child['finished_at']
  identity=child['identity'];ps=identity['ps'].splitlines()
  assert identity['ps_returncode']==0 and len(ps)==1
  assert ps[0].split()[:3]==[str(child['pid']),str(terminal['pid']),str(child['pid'])] and ps[0].endswith(' '.join(row['argv']))
  if identity['cwd_returncode']!=0 or not identity['cwd']:
   assert identity['cwd_returncode']==1 and not identity['cwd'];missing.append(index)
  else:assert 'n'+str(S) in identity['cwd'].splitlines()
  assert child['samples'] and not any((directory/name).exists() for name in ['owned-stop.json','budget-reason.json'])
  for sample in child['samples']:
   assert not sample['allocation_errors'] and sample['free_bytes']>=9*2**30
   assert sample['namespace_allocated_bytes']<=14*2**30 and sample['evidence_allocated_bytes']<=256*2**20
   roots=sample['evidence_allocation_sample']['roots']
   assert set(roots)=={str(OWNER/'.work/hir-options-hash-compiler-build-01'),str(prior.OLDWORK),str(PREVIOUS_WORK)}
   assert sample['evidence_allocated_bytes']==sum(value['bytes'] for value in roots.values())
  for stream in ['stdout','stderr']:
   assert sha(directory/stream)==child[stream+'_sha256']
   if stream in row:assert (directory/stream).read_bytes()==row[stream].encode()
  joined=(directory/'stdout').read_bytes()+b'\n'+(directory/'stderr').read_bytes()
  assert not re.search(rb'(?im)^\s*(?:downloading https?://|Building LLVM(?:\s|$)|Building GCC(?:\s|$)|HIR compiler experiment: bootstrap network)',joined)
 assert missing==proof['unavailable_contemporaneous_cwd_children']==[1]
 raw=(PREVIOUS_WORK/'commands/000/stdout').read_text()+(PREVIOUS_WORK/'commands/000/stderr').read_text()
 for key,value in old['tests']['assertions']['build_compiler_std']['compiler_commit_environment'].items():assert key+'="'+value+'"' in raw
 for key,value in [('CFG_VIRTUAL_RUSTC_DEV_SOURCE_BASE_DIR','/rustc-dev/'+old['candidate_revision']),('CFG_VIRTUAL_RUST_SOURCE_BASE_DIR','/rustc/'+old['candidate_revision'])]:assert key+'="'+value+'"' in raw
 version=(PREVIOUS_WORK/'commands/001/stdout').read_text()
 assert not (PREVIOUS_WORK/'commands/001/stderr').read_bytes()
 assert (PREVIOUS_WORK/'commands/002/stdout').read_text()==version
 for line in old['tests']['assertions']['rustc_version']['required_lines']+['LLVM version: '+old['llvm_version']]:assert line in version.splitlines()
 assert not (PREVIOUS_WORK/'commands/003/stderr').read_bytes()
 assert (PREVIOUS_WORK/'commands/003/stdout').read_text()==str(S/'build'/m.HOST/'stage1')+'\n'
 assert not (PREVIOUS_WORK/'commands/004/stderr').read_bytes()
 options=set(re.findall(r'(?m)^\s*(?:-Z\s+)?([a-z][a-z0-9-]+)\s*=',(PREVIOUS_WORK/'commands/004/stdout').read_text()))
 assert set(old['tests']['assertions']['rustc_unstable_help']['required_option_names'])<=options
 b.check_tests((PREVIOUS_WORK/'commands/005/stdout').read_bytes()+(PREVIOUS_WORK/'commands/005/stderr').read_bytes(),old['tests']['interface'])
 assert 'ERROR: no `build` rules matched ["src/tools/run-make-support"]' in (PREVIOUS_WORK/'commands/006/stderr').read_text()
 initial=read(PREVIOUS_WORK/'stage1-inventory.json')
 allowed={str(S/'build'/m.HOST/'stage1/bin/rustc'),*[row['resolved'] for row in initial['closure']['identity']['libraries']]}
 loaded=b.native_loader((PREVIOUS_WORK/'commands/002/stderr').read_bytes(),read(PREVIOUS_WORK/'commands/002/receipt.json')['pid'],allowed)
 assert loaded==read(PREVIOUS_WORK/'stage1-native-loader.json')
 b.owned_closure_guard(initial['closure'])
 for root,expected_members in proof['membership'].items():assert members(Path(root))==expected_members
 assert not (PREVIOUS_WORK/'compiled.json').exists() and not (PREVIOUS_WORK/'run-make-support-inventory.json').exists()
 return initial,loaded

class Stage(b.Stage):
 def __init__(self,digest):
  assert sha(HERE/'inputs.json')==digest
  self.frozen=read(HERE/'inputs.json');assert sha(HERE/'plan.json')==self.frozen['plan_sha256']
  self.plan=read(HERE/'plan.json');self.mfreeze=read(b.MHERE/'inputs.json')
  assert Path.cwd()==OWNER and sys.dont_write_bytecode and not sys.flags.optimize
  assert str(Path(sys.executable).resolve(strict=True))==self.frozen['python']
  self.environment=dict(os.environ);expected=self.frozen['launch_environment'];extra=set(self.environment)-set(expected)
  assert all(self.environment.get(k)==v for k,v in expected.items()) and extra<={'__CF_USER_TEXT_ENCODING'}
  if extra:
   cf=self.environment['__CF_USER_TEXT_ENCODING'].split(':')
   assert len(cf)==3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})',v) for v in cf)
   assert int(cf[0],16 if cf[0].lower().startswith('0x') else 10)==os.getuid()==501
  assert not W.exists();W.mkdir();(W/'commands').mkdir()
  self.record=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),commands=[],
   compiler_stages_completed=7,new_compiler_stages_completed=0,saved_children=22,saved_actual_children=23,
   saved_cwd_limitations=self.plan['previous_continuation']['cwd_limitation'],
   source=str(S),candidate_revision=self.plan['candidate_revision'],source_identity=self.plan['source_identity'],
   native_recipe_qualified=False,hash_driver_qualified=False,application_qualified=False,
   prior_failed_build_sha256=self.plan['saved']['receipt_sha256'],
   prior_failed_continuation_sha256=self.plan['previous_continuation']['receipt_sha256'])
  self.provider_closures={};self.save()
 def save(self):owned.write(W/'receipt.json',self.record)
 def guard(self,full=True):
  b.Stage.guard(self,full)
  recent_guard(self.plan)
  support_controls_guard(self.plan)
 def command(self,row):
  assert row==self.plan['remaining_children'][len(self.record['commands'])]
  self.guard();out=W/'commands'/f'{len(self.record['commands']):03}'
  try:monitor.run(row['argv'],cwd=S,environment=row['environment'],output=out,canonical_fd=self.lockfd)
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
    assert not (N/'beta-sysroot').exists()
    self.provider_closures=prior.saved_guard(read(PREVIOUS/'plan.json'),replay_loaders=True)
    owned.write(W/'saved-provider-replay.json',self.provider_closures)
    initial,loaded=recent_guard(self.plan)
    # These are exact copies of saved evidence, never new native probes.
    for name in ['stage1-inventory.json','stage1-native-loader.json']:
     with (W/name).open('xb') as stream:stream.write((PREVIOUS_WORK/name).read_bytes())
    owned.write(W/'saved-native-replay.json',dict(source=str(PREVIOUS_WORK),receipt_sha256=sha(PREVIOUS_WORK/'receipt.json'),probe_rerun=False))
    self.guard();assert monitor.rejection(monitor.sample()) is None
    out,err=self.command(self.plan['remaining_children'][0])
    support_tests(out+err,self.plan['support_route'])
    inventory=b.support_inventory()
    owned.write(W/'run-make-support-inventory.json',inventory)
    owned.write(W/'run-make-support-producer.json',producer.validate(out,err,self.plan['remaining_children'][0]['environment'],
     tomllib.loads((S/'bootstrap.toml').read_text()),self.plan['remaining_children'][0]['argv'],S,inventory,timing,parsers))
    b.extracted(self.plan);self.record.update(compiler_stages_completed=8,new_compiler_stages_completed=1);self.save()
    for row in self.plan['suffix_children']:self.command(row)
    assert len(self.record['commands'])==3
    self.guard();providers=b.extracted(self.plan);stage1=b.output_files(S/'build'/m.HOST/'stage1')
    owned.write(W/'stage1-final-loader-state.json',b.owned_closure_guard(initial['closure']))
    first=read(prior.OLDWORK/'receipt.json')['commands'];second=read(PREVIOUS_WORK/'receipt.json')['commands']
    history=[*first,*second[:6],*self.record['commands']];actual=[*first,*second,*self.record['commands']]
    assert len(history)==25 and len(actual)==26
    owned.write(W/'compiled.json',dict(status='compiled-awaiting-native-recipe-and-B3-qualification',candidate_revision=self.plan['candidate_revision'],source_identity=self.plan['source_identity'],
     stage1=stage1,providers=providers,native_loader_sha256=sha(W/'stage1-native-loader.json'),native_loader_original_path=str(PREVIOUS_WORK/'stage1-native-loader.json'),
     run_make_support_sha256=sha(W/'run-make-support-inventory.json'),run_make_support_producer_sha256=sha(W/'run-make-support-producer.json'),stages=8,all_lowering_tests=27,all_interface_tests=18,all_support_tests=15,
     prior_failed_build_sha256=sha(prior.OLDWORK/'receipt.json'),prior_failed_continuation_sha256=sha(PREVIOUS_WORK/'receipt.json'),
     saved_children=22,saved_actual_children=23,actual_continuation_children=3,command_history=history,actual_command_history=actual,failed_support_attempt=second[6]))
    self.record.update(status='passed',compiled_sha256=sha(W/'compiled.json'),free_bytes_after=owned.disk(OWNER,9))
  except BaseException as error:self.record.update(status='failed',error=repr(error));raise
  finally:self.record['finished_at']=time.time();self.save()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True);args=parser.parse_args();Stage(args.inputs_sha256).run()
if __name__=='__main__':main()
