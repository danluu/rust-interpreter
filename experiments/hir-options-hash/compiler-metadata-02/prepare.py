#!/usr/bin/env python3
"""Read-only derivation and freezing of the next exact metadata launch."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import metadata as m

def write(p,value):
 with p.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')
def main():
 assert sys.dont_write_bytecode and not sys.flags.optimize
 assert not m.WORK.exists()
 acquired=m.read(m.ACQUIRED);terminal=m.read(m.ACQUIRED.parent/'receipt.json')
 assert terminal['status']=='passed' and terminal['acquired_sha256']==m.sha(m.ACQUIRED)
 assert acquired['candidate_revision']=='4de35bdacef0e3cd18a66bc30b5459c19e09b118'
 files={};links={}
 def add(path):
  p=Path(path);record=m.file(p);assert str(p) not in files or files[str(p)]==record;files[str(p)]=record
  return record
 def addlink(p):
  links[str(p)]=dict(stamp=m.stamp(p),target=os.readlink(p),resolved=str(p.resolve(strict=True)))
 environment=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',
  PATH=str(m.HERE/'offline-bin')+':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
  PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',
  GIT_CONFIG_COUNT='3',GIT_CONFIG_KEY_0='protocol.allow',GIT_CONFIG_VALUE_0='never',
  GIT_CONFIG_KEY_1='core.hooksPath',GIT_CONFIG_VALUE_1='/dev/null',GIT_CONFIG_KEY_2='core.fsmonitor',GIT_CONFIG_VALUE_2='false',
  GIT_TERMINAL_PROMPT='0',GIT_OPTIONAL_LOCKS='0',CARGO_HOME=str(m.NAMESPACE/'cargo-home'),CARGO_NET_OFFLINE='true',
  RUSTUP_DIST_SERVER='file:///dev/null',TMPDIR=str(m.NAMESPACE/'tmp')+'/',CARGO_TERM_COLOR='never')
 children=[]
 def row(argv,cwd=m.OWNER,stdout=None,stderr='',expected=(0,)):
  d=dict(argv=list(map(str,argv)),cwd=str(cwd),environment=environment,expected=list(expected))
  if stdout is not None:d['stdout']=stdout
  if stderr is not None:d['stderr']=stderr
  children.append(d);return d
 def git(*args):
  argv=['/usr/bin/git',*args];raw=subprocess.run(argv,cwd=m.SOURCE,env=environment,capture_output=True,check=True)
  assert not raw.stderr;row(argv,m.SOURCE,raw.stdout.decode());return raw.stdout.decode()
 assert git('rev-parse','HEAD').strip()==acquired['candidate_revision']
 assert git('diff','HEAD','--')==''
 author='bors@rust-lang\\.org'
 closest=git('rev-list','--author-date-order','--author='+author,'-n1','HEAD').strip();assert len(closest)==40
 paths=['src/llvm-project','src/bootstrap/download-ci-llvm-stamp','src/version']
 assert git('rev-list','--first-parent','-n1',closest,'--author',author,'--',*paths).strip()==m.LLVM
 assert git('diff-index',m.LLVM,'--name-only','--',*paths)==''
 assert git('show',m.LLVM+':src/ci/channel').strip()=='nightly'
 llvm_version=git('show',m.LLVM+':src/version').strip()
 legacy=m.read(Path('/Users/danluu/dev/rust-interp-beta-auxiliary-readmission-20260918/experiments/beta-auxiliary-readmission/plan.json'))
 for key,argv in legacy['sdk_queries']:row(argv,stdout=legacy['sdk_outputs'][key])
 row(['/usr/bin/xcrun','--find','git'],stdout='/Applications/Xcode.app/Contents/Developer/usr/bin/git\n')
 row(['/usr/bin/git','--exec-path'],stdout='/Applications/Xcode.app/Contents/Developer/usr/libexec/git-core\n')
 deny=m.HERE/'offline-bin/curl';row([deny,'--version'],stdout='',stderr='HIR compiler experiment: bootstrap network download is forbidden\n',expected=(86,))
 prefix=list(children)
 python=Path(sys.executable).resolve(strict=True)
 closure_roots=[['python',str(python)],['git','/Applications/Xcode.app/Contents/Developer/usr/bin/git'],['clang',str(m.CLANG)],['ld',str(m.CLANG.with_name('ld'))],
  ['stage0-rustc',str(m.OLD/'build'/m.HOST/'stage0/bin/rustc')],['stage0-cargo',str(m.OLD/'build'/m.HOST/'stage0/bin/cargo')],
  ['llvm-config',str(m.OLD/'build'/m.HOST/'ci-llvm/bin/llvm-config')]]
 closures={name:m.planned_closure(path,children,environment,drop_self_id=name=='ld') for name,path in closure_roots}
 suffix=[]
 llvmprobe=row([m.OLD/'build'/m.HOST/'ci-llvm/bin/llvm-config','--version']);llvmprobe['llvm_version_probe']=True;suffix.append(llvmprobe)
 ldprobe=row([m.CLANG.with_name('ld'),'-v'],stderr=None);ldprobe['environment']=environment|{'DYLD_PRINT_LIBRARIES':'1'};ldprobe['linker_probe']=True;suffix.append(ldprobe)
 for argv,stdout in [(['/usr/bin/git','rev-parse','HEAD'],acquired['candidate_revision']+'\n'),(['/usr/bin/git','diff','HEAD','--'],'')]:suffix.append(row(argv,m.SOURCE,stdout))
 for path in [m.OWNER/'experiments/hir-options-hash/compiler-metadata-01/launch.json',m.OWNER/'experiments/hir-options-hash/compiler-metadata-01/inputs.json',m.OWNER/'experiments/hir-options-hash/compiler-metadata-01/plan.json',m.OWNER/'experiments/hir-options-hash/compiler-metadata-01/metadata.py',m.ACQUIRED,m.ACQUIRED.parent/'receipt.json',m.ACQUIRE/'acquisition-inputs.json',m.ACQUIRE/'acquisition-plan.json',m.ACQUIRE/'source-01/manifest.json',m.ACQUIRE/'source-01/candidate.patch',m.OWNER/'.work/hir-options-hash-acquisition-verification-01.json']:
  add(path)
 for root,entries in [(m.SOURCE,acquired['source_files']),(m.SOURCE/'library/backtrace',acquired['backtrace_files'])]:
  for name,record in entries.items():
   p=root/name
   if record['mode']=='120000':addlink(p)
   else:assert add(p)['sha256']==record['sha256']
 for copy in acquired['copies']:assert add(copy['destination'])['sha256']==copy['sha256']
 seeds=m.seed_members(acquired['copies'])
 stage0=dict(line.split('=',1) for line in (m.SOURCE/'src/stage0').read_text().splitlines() if line and not line.startswith('#'))
 for path,seed in seeds.items():
  if not Path(path).name.startswith('rust-dev-'):assert stage0['dist/2026-08-30/'+Path(path).name]==seed['sha256']
  for member in seed['members'].values():
   if member['kind']=='file':assert add(member['existing'])==member['current']
   else:addlink(Path(member['existing']))
 for name,path in closure_roots:add(Path(path))
 for closure in closures.values():
  for library in closure['identity']['libraries']:add(Path(library['resolved']))
 for p in ['/usr/bin/git','/usr/bin/xcrun','/usr/bin/xcode-select','/usr/bin/otool','/usr/bin/env','/bin/sh',str(m.CLANG.with_name('llvm-otool'))]:add(Path(p))
 # Full SDK files and internal link routes; no claim that settings alone bind headers.
 sdk=m.inventory(m.SDK,True)
 for name,record in sdk.items():
  p=m.SDK/name
  if record['kind']=='file':files[str(p)]={k:record[k] for k in ['sha256','stamp']}
  elif record['kind']=='link':addlink(p)
 old=m.read(m.OWNER/'experiments/runtime-exporter/metadata-02/plan.json')
 routes=dict(old['routes']);routes['/usr/bin/clang']=str(Path('/usr/bin/clang').resolve(strict=True))
 config=m.read(m.ACQUIRE/'acquisition-inputs.json')['configurations']
 config[str(m.NAMESPACE/'cargo-home/config')]=None;config[str(m.NAMESPACE/'cargo-home/config.toml')]=None
 build_environment=environment|dict(SDKROOT=legacy['sdk_outputs']['sdk'].strip(),CC=str(m.CLANG),CXX=str(m.CLANG.with_name('clang++')),CARGO_BUILD_JOBS='2')
 add(m.CLANG.with_name('clang++').resolve(strict=True));routes[str(m.CLANG.with_name('clang++'))]=str(m.CLANG.with_name('clang++').resolve(strict=True))
 plan=dict(status='prepared-unrun',owner=str(m.OWNER),candidate_revision=acquired['candidate_revision'],source=str(m.SOURCE),
  platform=m.loaders.platform_identity(),configuration=config,routes=routes,children=children,prefix_children=prefix,suffix_children=suffix,
  closure_roots=closure_roots,closures=closures,linker_expected_loaded=[str(m.CLANG.with_name('ld')),*[r['resolved'] for r in closures['ld']['identity']['libraries']]],seeds=seeds,sdk_inventory=sdk,environment=environment,build_environment=build_environment,
  llvm=dict(closest_upstream=closest,commit=m.LLVM,rust_version_at_llvm_commit=llvm_version,channel='nightly',assertions=False,
   cache_key='llvm-'+m.HOST+'-'+m.LLVM+'-false',download_ci=True,source_rebuild_allowed=False),
  network_block=dict(path=str(deny),sha256=m.sha(deny),exit=86,scope='All bootstrap.py and bootstrap Rust download paths invoke PATH curl; blocked wrapper fails explicitly. Cargo is offline; Git protocols are disabled. No network or provider fallback.'),
  capacity=dict(entry_gib=24,stop_gib=9,floor_gib=8,namespace_gib=14,evidence_mib=256),canonical_lock=str(m.owned.CANONICAL_LOCK),wait_seconds=600,compiler_builds=0)
 write(m.HERE/'plan.json',plan)
 for p in [*m.HERE.rglob('*'),m.OWNER/'experiments/stable-cgu/owned_stage.py',m.OWNER/'scripts/supervise_experiment.py',m.OWNER/'scripts/custom_cargo_libraries.py',m.OWNER/'scripts/custom_compiler.py',m.OWNER/'scripts/compiler_association.py',m.OWNER/'scripts/toolchain_lookup.py']:
  if p.is_file():add(p)
  if p.suffix=='.py':ast.parse(p.read_text())
 freeze=dict(files=files,links=links,plan_sha256=m.sha(m.HERE/'plan.json'),python=str(python),launch_environment=environment)
 write(m.HERE/'inputs.json',freeze)
 launch=dict(status='prepared-unrun-awaiting-review',owner=str(m.OWNER),environment=environment,
  command=[str(python),'-B',str(m.OWNER/'scripts/supervise_experiment.py'),'--run-id','hir-options-hash-compiler-metadata-supervisor-02','--',str(python),'-B',str(m.HERE/'metadata.py'),'--inputs-sha256',m.sha(m.HERE/'inputs.json')],
  inputs_sha256=m.sha(m.HERE/'inputs.json'),plan_sha256=m.sha(m.HERE/'plan.json'),helper_sha256=m.sha(m.HERE/'metadata.py'),expected_children=len(children),capacity=plan['capacity'],compiler_builds=0)
 write(m.HERE/'launch.json',launch)
 print(json.dumps(dict(inputs=len(files),links=len(links),children=len(children),launch_sha256=m.sha(m.HERE/'launch.json'),inputs_sha256=launch['inputs_sha256'],plan_sha256=launch['plan_sha256']),indent=2))
if __name__=='__main__':main()
