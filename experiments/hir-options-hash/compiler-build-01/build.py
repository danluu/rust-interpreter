#!/usr/bin/env python3
"""One bounded compiler build; native recipe/B3/application qualification follows."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
import bounded_command_v2 as bounded

OWNER=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
N=bounded.NAMESPACE
S=N/'source'
W=bounded.EVIDENCE
MHERE=OWNER/'experiments/hir-options-hash/compiler-metadata-03'
sys.path.insert(0,str(MHERE))
spec=importlib.util.spec_from_file_location('candidate_compiler_metadata',MHERE/'metadata.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
owned=m.owned

def read(p):return m.read(p)
def sha(p):return m.sha(p)
def output_files(root):
 result={}
 for parent,dirs,files in os.walk(root,followlinks=False):
  for name in sorted(dirs+files):
   p=Path(parent)/name;s=p.lstat();key=str(p.relative_to(root))
   if stat.S_ISLNK(s.st_mode):
    target=p.resolve(strict=True);assert target.is_relative_to(N),('output link escapes owned namespace',p,target)
    result[key]=dict(kind='link',target=os.readlink(p),resolved=str(target),stamp=m.stamp(p))
   elif stat.S_ISREG(s.st_mode):result[key]=dict(kind='file',**m.file(p))
   else:assert stat.S_ISDIR(s.st_mode)
 return result

def check_tests(raw,expected):
 text=raw.decode();names=re.findall(r'^test ([A-Za-z0-9_:]+) \.\.\. ok$',text,re.M)
 assert len(names)==len(set(names)), 'duplicate test output'
 assert set(names)==set(expected['names']) and len(names)==expected['count'],(names,expected)
 summaries=re.findall(r'^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;',text,re.M)
 assert (str(expected['count']),'0','0','0','0') in summaries,summaries
 assert not any(any(int(x) for x in row[1:]) for row in summaries),summaries

def owned_closure_guard(closure):
 """Keep bytes/routes/identity exact; record bootstrap's owned hardlink ctime."""
 current=m.loaders.library_state(closure['identity']);prior=closure['state']
 assert current['searches']==prior['searches']
 assert set(current['libraries'])==set(prior['libraries'])
 changed={}
 for library in closure['identity']['libraries']:
  name=library['logical'];path=Path(library['resolved'])
  assert path.is_relative_to(N) and path.resolve(strict=True)==path
  old=prior['libraries'][name];new=current['libraries'][name]
  # _stamp: resolved, dev, ino, mode, size, mtime, ctime,
  #          logical inode, logical mtime, logical ctime.
  assert len(old)==len(new)==10
  assert [v for i,v in enumerate(old) if i not in [6,9]]==[v for i,v in enumerate(new) if i not in [6,9]],name
  assert sha(path)==library['sha256'],name
  if old!=new:changed[name]=dict(path=str(path),before=old,after=new)
 for row in changed.values():
  row['current_nlink']=Path(row['path']).stat().st_nlink
 assert m.loaders.library_state(closure['identity'])==current,'provider changed while recording metadata'
 return dict(state=current,owned_alias_ctime_deltas=changed)

def native_loader(raw,pid,allowed):
 # Same two-form grammar as retained embedded-frontend source-03/run.py.
 loaded=set();basenames={};lines=[]
 prefix=rf'dyld\[{pid}\]: '
 for number,line in enumerate(raw.decode().splitlines(),1):
  image=re.fullmatch(prefix+r'(?:<[0-9A-Fa-f-]{36}>\s+)?(/.+)',line)
  move=re.fullmatch(prefix+r'move loaded to delayed: ([^/\r\n]+)',line)
  if image:
   path=image[1];assert str(Path(path))==path and '..' not in Path(path).parts
   basenames.setdefault(Path(path).name,set()).add(path)
   if not path.startswith(('/usr/lib/','/System/Library/')):
    assert path in allowed;loaded.add(path)
  elif move:
   matches=basenames.get(move[1],set())
   assert len(matches)==1 and all(x.startswith(('/usr/lib/','/System/Library/')) for x in matches)
  else:raise AssertionError(('unexpected native loader diagnostic',line))
  lines.append(dict(line=number,raw=line))
 assert loaded==set(allowed),(loaded,allowed)
 return dict(loaded_non_system=sorted(loaded),lines=lines,raw_sha256=hashlib.sha256(raw).hexdigest())

def stage1_inventory():
 root=S/'build'/m.HOST/'stage1';files=output_files(root)
 expected=root/'lib/rustlib'/m.HOST/'lib'
 for crate in ['std','core','alloc','test']:
  assert any(p.is_file() for p in expected.glob('lib'+crate+'-*.rlib')),crate
 assert any(p.is_file() for p in expected.glob('*.rmeta'))
 requests=[];closure=m.planned_closure(root/'bin/rustc',requests,{})
 for library in closure['identity']['libraries']:
  assert Path(library['resolved']).is_relative_to(root),'native runtime loader escaped fresh stage1'
 assert len([r for r in closure['identity']['libraries'] if Path(r['resolved']).name.startswith('librustc_driver-')])==1
 return dict(root=str(root),files=files,closure=closure,prospective_otool_commands=requests)

def support_inventory():
 root=S/'build'/m.HOST/'bootstrap-tools';assert root.is_dir()
 files=output_files(root)
 selected={name:row for name,row in files.items() if Path(name).name.startswith('librun_make_support-') and Path(name).suffix in ['.rlib','.rmeta','.dylib']}
 assert any(name.endswith('.rlib') for name in selected) and any(name.endswith('.rmeta') for name in selected)
 # Cargo's actual new-layout directories are discovered from owned output,
 # retained now and frozen before the separate direct recipe compilation.
 outdirs=sorted(str(p) for p in root.rglob('out') if p.is_dir())
 assert outdirs and all(Path(p).resolve(strict=True)==Path(p) for p in outdirs)
 return dict(root=str(root),selected=selected,files=files,build_out_directories=outdirs,recipe_compiled=False,recipe_executed=False)

def extracted(plan,full=True):
 records={}
 for archive,seed in plan['metadata_plan']['seeds'].items():
  if not seed['active']:continue
  root=S/'build'/m.HOST/seed['output_root']
  for name,row in seed['members'].items():
   p=root/name
   if row['kind']=='file':
    assert p.resolve(strict=True)==p and stat.S_ISREG(p.lstat().st_mode),p
    if full:assert sha(p)==row['sha256'],p
    records[str(p)]=dict(sha256=row['sha256'],stamp=m.stamp(p))
   else:
    assert p.is_symlink() and os.readlink(p)==row['target'],p
    records[str(p)]=dict(target=row['target'],stamp=m.stamp(p))
 assert not (S/'build'/m.HOST/'rustfmt').exists(),'unadmitted optional nightly provider was extracted'
 assert (S/'build'/m.HOST/'ci-llvm/.llvm-stamp').read_text()==m.LLVM+'false'
 return records

class Stage:
 def __init__(self,digest):
  assert sha(HERE/'inputs.json')==digest
  self.frozen=read(HERE/'inputs.json');assert sha(HERE/'plan.json')==self.frozen['plan_sha256']
  self.plan=read(HERE/'plan.json');self.mfreeze=read(MHERE/'inputs.json')
  assert Path.cwd()==OWNER and sys.dont_write_bytecode and not sys.flags.optimize
  assert str(Path(sys.executable).resolve(strict=True))==self.frozen['python']
  assert not W.exists();W.mkdir();(W/'commands').mkdir()
  self.record=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),commands=[],compiler_stages_completed=0,
   source=str(S),candidate_revision=self.plan['candidate_revision'],source_identity=self.plan['source_identity'],native_recipe_qualified=False,hash_driver_qualified=False,application_qualified=False)
  self.provider_closures={}
  self.environment=dict(os.environ)
  expected=self.frozen['launch_environment'];extra=set(self.environment)-set(expected)
  assert all(self.environment.get(k)==v for k,v in expected.items()) and extra<={'__CF_USER_TEXT_ENCODING'}
  if extra:
   cf=self.environment['__CF_USER_TEXT_ENCODING'].split(':')
   assert len(cf)==3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})',v) for v in cf)
   assert int(cf[0],16 if cf[0].lower().startswith('0x') else 10)==os.getuid()==501
  self.save()
 def save(self):owned.write(W/'receipt.json',self.record)
 def guard(self,full=True):
  assert dict(os.environ)==self.environment
  for name,closure in self.provider_closures.items():
   observation=owned_closure_guard(closure)
   if observation['owned_alias_ctime_deltas']:
    self.record.setdefault('provider_alias_transitions',[]).append(dict(after_children=len(self.record['commands']),provider=name,observation=observation))
    closure['state']=observation['state']
    self.save()
  for name,row in self.frozen['files'].items():
   p=Path(name);assert p.resolve(strict=True)==p and m.stamp(p)==row['stamp'],name
   if full:assert sha(p)==row['sha256'],name
  for module in list(sys.modules.values()):
   name=getattr(module,'__file__',None)
   if name and name.startswith('/Users/danluu/dev/'):
    assert str(Path(name).resolve(strict=True)) in self.frozen['files'] or str(Path(name).resolve(strict=True)) in self.mfreeze['files'],name
  assert sha(MHERE/'inputs.json')==self.plan['metadata_inputs_sha256']
  m.guard(self.plan['metadata_plan'],self.mfreeze,full)
 def command(self,row):
  assert row==self.plan['children'][len(self.record['commands'])]
  self.guard();out=W/'commands'/f'{len(self.record["commands"]):03}'
  try:result=bounded.run(row['argv'],cwd=S,environment=row['environment'],output=out,canonical_fd=self.lockfd)
  finally:
   if (out/'receipt.json').exists():
    child=read(out/'receipt.json');self.record['commands'].append(dict(path=str(out/'receipt.json'),sha256=sha(out/'receipt.json'),pid=child.get('pid'),command=row['argv']));self.save()
  raw=(out/'stdout').read_bytes();err=(out/'stderr').read_bytes();joined=raw+b'\n'+err
  # The finite private seeds and the denied curl command prohibit fetching. A
  # source LLVM build is also a distinct, forbidden producer for this attempt.
  assert not re.search(rb'(?im)^\s*(?:downloading https?://|Building LLVM(?:\s|$)|Building GCC(?:\s|$)|HIR compiler experiment: bootstrap network)',joined)
  if 'stdout' in row:assert raw.decode()==row['stdout'],row['argv']
  if 'stderr' in row:assert err.decode()==row['stderr'],row['argv']
  self.guard();return raw,err
 def run(self):
  try:
   with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
    self.lockfd=fd
    self.record.update(status='running',admitted_at=time.time(),free_bytes_before=owned.disk(OWNER,24));self.save()
    self.guard();assert output_files(S/'build')==self.plan['initial_build_files']
    assert not (N/'cargo-home/registry/src').exists() and not (N/'beta-sysroot').exists()
    assert bounded.rejection(bounded.sample()) is None
    for row in self.plan['prefix_children']:self.command(row)
    for number,row in enumerate(self.plan['stages']):
     out,err=self.command(row);self.record['compiler_stages_completed']=number+1;self.save()
     if number==0:
      providers=extracted(self.plan)
      owned.write(W/'extracted-provider-files.json',providers)
      closures={}
      for name,path in self.plan['new_closure_roots']:
       def inspect(argv,*,text):
        assert text is True
        desired=self.plan['children'][len(self.record['commands'])];assert desired['argv']==argv
        raw,stderr=self.command(desired);assert not stderr;return raw.decode()
       identity,state=m.loaders.library_closure(Path(path),m.HOST,inspect=inspect)
       expected=self.plan['new_closure_identities'][name];assert identity==expected,name
       closures[name]=dict(identity=identity,state=state)
      self.provider_closures=closures
      owned.write(W/'extracted-provider-closures.json',closures)
     if number==0:
      assert re.search(rb'(?m)^running: .*cargo.*\"check\".*rustc_ast_lowering',out+err),'missing actual lowering Cargo check'
     if number==1:check_tests(out+err,self.plan['tests']['lowering'])
     if number==2:
      combined=(out+err).decode();revision=self.plan['candidate_revision']
      for key,value in self.plan['tests']['assertions']['build_compiler_std']['compiler_commit_environment'].items():
       assert key+'=\"'+value+'\"' in combined,(key,value)
      for key,value in [('CFG_VIRTUAL_RUSTC_DEV_SOURCE_BASE_DIR','/rustc-dev/'+revision),('CFG_VIRTUAL_RUST_SOURCE_BASE_DIR','/rustc/'+revision)]:
       assert key+'=\"'+value+'\"' in combined,(key,value)
      stage1=stage1_inventory();owned.write(W/'stage1-inventory.json',stage1)
     if number==3:
      text=out.decode();assert not err
      for line in self.plan['tests']['assertions']['rustc_version']['required_lines']:assert line in text.splitlines(),line
      assert 'LLVM version: '+self.plan['llvm_version'] in text.splitlines()
      allowed={str(S/'build'/m.HOST/'stage1/bin/rustc'),*[row['resolved'] for row in stage1['closure']['identity']['libraries']]}
      probe=self.plan['children'][len(self.record['commands'])];probe_out,probe_err=self.command(probe)
      assert probe_out==out
      loaded=native_loader(probe_err,read(self.record['commands'][-1]['path'])['pid'],allowed)
      assert m.loaders.library_state(stage1['closure']['identity'])==stage1['closure']['state']
      for name,row in stage1['files'].items():
       if row['kind']=='file':assert m.file(Path(stage1['root'])/name)=={k:row[k] for k in ['sha256','stamp']}
      owned.write(W/'stage1-native-loader.json',loaded)
     if number==4:assert not err and out.decode()==str(S/'build'/m.HOST/'stage1')+'\n'
     if number==5:
      assert not err
      options=set(re.findall(r'(?m)^\s*(?:-Z\s+)?([a-z][a-z0-9-]+)\s*=',out.decode()))
      for flag in self.plan['tests']['assertions']['rustc_unstable_help']['required_option_names']:assert flag in options,flag
     if number==6:check_tests(out+err,self.plan['tests']['interface'])
     if number==7:
      assert b'run_make_support' in out+err
      support=support_inventory();owned.write(W/'run-make-support-inventory.json',support)
     extracted(self.plan)
    for row in self.plan['suffix_children']:self.command(row)
    assert len(self.record['commands'])==len(self.plan['children'])
    self.guard();providers=extracted(self.plan)
    stage1=output_files(S/'build'/m.HOST/'stage1')
    owned.write(W/'stage1-final-loader-state.json',owned_closure_guard(read(W/'stage1-inventory.json')['closure']))
    owned.write(W/'compiled.json',dict(status='compiled-awaiting-native-recipe-and-B3-qualification',candidate_revision=self.plan['candidate_revision'],source_identity=self.plan['source_identity'],stage1=stage1,providers=providers,native_loader_sha256=sha(W/'stage1-native-loader.json'),run_make_support_sha256=sha(W/'run-make-support-inventory.json'),stages=8,all_lowering_tests=self.plan['tests']['lowering']['count'],all_interface_tests=self.plan['tests']['interface']['count']))
    self.record.update(status='passed',compiled_sha256=sha(W/'compiled.json'),free_bytes_after=owned.disk(OWNER,9))
  except BaseException as error:self.record.update(status='failed',error=repr(error));raise
  finally:self.record['finished_at']=time.time();self.save()

def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs-sha256',required=True);a=p.parse_args();Stage(a.inputs_sha256).run()
if __name__=='__main__':main()
