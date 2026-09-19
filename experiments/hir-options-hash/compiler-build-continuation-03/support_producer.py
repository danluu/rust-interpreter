"""Actual ToolBootstrap support producer, with full timing/context provenance."""
import hashlib
from pathlib import Path
import re

def validate(stdout,stderr,inherited,configuration,outer,source,inventory,timing,parse):
 source=Path(source);host='aarch64-apple-darwin';d=source/'build'/host/'stage0'
 root=source/'build'/host/'bootstrap-tools';shim=str(source/'build/bootstrap/debug/rustc')
 command=['./x','test','--stage','1','src/tools/run-make-support','--jobs','2','-vv']
 timing.configured(configuration,outer,[command])
 assert Path(inventory['root'])==root
 def approve(cargo,step):
  argv=cargo['argv'];environment=cargo['environment']
  assert argv[:2]==[str(d/'bin/cargo'),'test']
  assert parse.single(argv,'--manifest-path')==str(source/'src/tools/run-make-support/Cargo.toml')
  assert parse.single(argv,'--target')==host
  assert environment.get('CARGO_TARGET_DIR')==environment.get('CARGO_BUILD_BUILD_DIR')==str(root)
  assert '--' in argv and parse.single(argv[argv.index('--')+1:],'--format')=='json'
  assert not any(word in ['-p','--package','--workspace','--exclude','--message-format'] or word.startswith(('--package=','--message-format=')) for word in argv[:argv.index('--')])
  if step is not None:assert step=='test::CrateRunMakeSupport { host: '+host+' }',step
  return 'test::CrateRunMakeSupport/run_cargo_test/render_tests::run_tests'
 printed=[]
 for stream,raw in [('stdout',stdout),('stderr',stderr)]:
  for number,line in enumerate(raw.splitlines(keepends=True),1):
   if line.startswith(b'running: ') and ('"'+str(d/'bin/cargo')+'"').encode() in line:
    # Metadata setup calls cannot emit library artifacts. Every printed
    # build/check/test Cargo context is parsed and must match this route.
    if not re.search(rb'"(?:build|check|test)"',line):continue
    coordinate=dict(stream=stream,line=number,line_sha256=hashlib.sha256(line).hexdigest())
    printed.append(dict(command=coordinate,parsed=parse.bootstrap_line(raw,coordinate,source)))
 contexts=[];timings={}
 for stream,raw in [('stdout',stdout),('stderr',stderr)]:
  entries=[row for row in printed if row['command']['stream']==stream]
  if stream=='stderr':
   assert not entries and b'[TIMING' not in raw,'unexpected Cargo/timing stream'
  else:
   timings[stream]=timing.classify(raw,entries,approve);contexts.extend(timings[stream]['commands'])
 real=[row for row in contexts if row['execution']=='real']
 assert real and printed
 def environment(row,cargo):
  assert row['argv'][:2]==[shim,shim],row['argv']
  parse.loader_policy(row,cargo,inherited,source)
  env=dict(inherited)
  for name in cargo['removed']:env.pop(name,None)
  env.update(cargo['environment'])
  for name,value in row['environment'].items():
   assert name not in env or env[name]==value or not name.startswith(('RUSTC','CFG_')),(name,value,env.get(name))
   env[name]=value
  required=dict(RUSTC=shim,RUSTC_WRAPPER=shim,RUSTC_REAL=str(d/'bin/rustc'),RUSTC_SNAPSHOT=str(d/'bin/rustc'),
   RUSTC_LIBDIR=str(d/'lib'),RUSTC_SNAPSHOT_LIBDIR=str(d/'lib'),RUSTC_STAGE='0',RUSTC_SYSROOT=str(d),
   CARGO_TARGET_DIR=str(root),CARGO_BUILD_BUILD_DIR=str(root),RUSTDOC_REAL=str(d/'bin/rustdoc'))
  assert all(env.get(name)==value for name,value in required.items()),required
  assert not any(env.get(name) for name in ['RUSTC_WRAPPER_REAL','RUSTC_FORCE_RUSTC_VERSION','RUSTC_ADDITIONAL_SYSROOT_PATHS','DYLD_FALLBACK_LIBRARY_PATH','DYLD_INSERT_LIBRARIES'])
  assert '--sysroot' not in row['argv'] and not any(word.startswith('--sysroot=') for word in row['argv'])
  assert parse.single(row['argv'],'--target')==host
  return env
 candidates=[];same_crate=[]
 for stream,raw in [('stdout',stdout),('stderr',stderr)]:
  for number,line in enumerate(raw.splitlines(keepends=True),1):
   if not re.fullmatch(rb'\s*Running `.+`\r?\n?',line):continue
   coordinate=dict(stream=stream,line=number,line_sha256=hashlib.sha256(line).hexdigest())
   row=parse.running_line(raw,coordinate);argv=row['argv']
   if '--crate-name' not in argv or parse.single(argv,'--crate-name')!='run_make_support':continue
   same_crate.append(dict(command=coordinate,parsed=row))
   if argv[0]==str(source/'build/bootstrap/debug/rustdoc'):
    assert '--test' in argv,'unexpected Rustdoc producer';continue
   environments=[environment(row,context['parsed']) for context in real]
   assert all(value==environments[0] for value in environments),'ambiguous same-child complete Cargo environment'
   if '--test' in argv:continue
   types=[]
   for index,word in enumerate(argv):
    if word=='--crate-type':types.extend(argv[index+1].split(','))
    elif word.startswith('--crate-type='):types.extend(word.split('=',1)[1].split(','))
   assert len(types)==2 and set(types)=={'lib','dylib'}
   assert set(parse.single(argv,'--emit').split(','))=={'dep-info','metadata','link'}
   output=Path(parse.single(argv,'--out-dir'));assert output.resolve(strict=True)==output and output.is_relative_to(root)
   extra=[argv[index+1] for index,word in enumerate(argv[:-1]) if word=='-C' and argv[index+1].startswith('extra-filename=')]
   assert len(extra)==1 and re.fullmatch(r'extra-filename=-[0-9a-f]+',extra[0])
   stem='librun_make_support'+extra[0].split('=',1)[1]
   paths=[output/(stem+extension) for extension in ['.rlib','.rmeta','.dylib']]
   assert all(str(path.relative_to(root)) in inventory['selected'] for path in paths)
   candidates.append(dict(command=coordinate,parsed=row,effective_environment=environments[0],
    real_contexts=[context['command'] for context in real],output_directory=str(output),artifacts=[str(path) for path in paths]))
 assert len(candidates)==1,candidates
 return dict(cargo_catalog=printed,timing_contexts=timings,same_crate_commands=same_crate,library_producer=candidates[0],
  role='D2 compiler0 ToolBootstrap Cargo test library; actual non-test lib+dylib outputs',not_internal_toolbuild=True,
  stdout_sha256=hashlib.sha256(stdout).hexdigest(),stderr_sha256=hashlib.sha256(stderr).hexdigest())
