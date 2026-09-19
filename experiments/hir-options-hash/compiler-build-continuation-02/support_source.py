"""Pinned bootstrap dispatch and support-library expectations; source reads only."""
import hashlib
import re

def derive(source):
 files={}
 def text(name):
  p=source/name;raw=p.read_bytes();files[name]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw));return raw.decode()
 builder=text('src/bootstrap/src/core/builder/mod.rs')
 text('bootstrap.toml')
 build=builder.split('Kind::Build => describe!(',1)[1].split('),',1)[0]
 assert 'tool::RunMakeSupport' not in build
 assert 'test::CrateRunMakeSupport,' in builder.split('Kind::Test => describe!(',1)[1].split('),',1)[0]
 tests=text('src/bootstrap/src/core/build_steps/test.rs')
 route=tests.split('impl CommandLineStep for CrateRunMakeSupport {',1)[1].split('\n}\n',1)[0]
 for value in ['run.path("src/tools/run-make-support")','let compiler = builder.compiler(0, host);','Mode::ToolBootstrap,','Kind::Test,','"src/tools/run-make-support",','cargo.allow_features("test");','run_cargo_test(']:assert value in route
 renderer=text('src/bootstrap/src/utils/render_tests.rs')
 assert 'cmd.args(["-Z", "unstable-options", "--format", "json"]);' in renderer
 assert 'print!("test {} ... ", test.name);' in renderer
 assert renderer.index('builder.do_if_verbose(|| println!("running: {cmd:?}"));')<renderer.index('cmd.stream_capture_stdout(&builder.config.exec_ctx)')
 execution=text('src/bootstrap/src/utils/exec.rs')
 assert 'if !command.run_in_dry_run && self.dry_run() {' in execution
 assert 'if self.config.print_step_timings && !self.config.dry_run() {' in builder
 json_formatter=text('library/test/src/formatters/json.rs')
 assert 'self.write_event("test", desc.name.as_slice(), "ok", exec_time, stdout, None)' in json_formatter
 doctest=text('src/librustdoc/doctest.rs')
 assert 'ignore_message: None,' in doctest and '"{} - {item_path}(line {line})"' in doctest
 text('src/librustdoc/doctest/rust.rs');text('src/librustdoc/html/markdown.rs')
 tool=text('src/bootstrap/src/core/build_steps/tool.rs')
 assert 'RunMakeSupport, "src/tools/run-make-support", "run_make_support", artifact_kind = ToolArtifactKind::Library;' in tool
 cargo=text('src/bootstrap/src/core/builder/cargo.rs')
 for value in ['mode == Mode::ToolBootstrap ||','self.rustc_snapshot_sysroot().to_path_buf()','.env("RUSTC_REAL", self.rustc(compiler))','.env("RUSTC_STAGE", build_compiler_stage.to_string())','.env("RUSTC_SYSROOT", sysroot)']:assert value in cargo
 failed=text('src/bootstrap/src/core/build_steps/test/failed_tests.rs')
 assert 'if !builder.config.cmd.record() || builder.config.dry_run() {' in failed
 manifest=text('src/tools/run-make-support/Cargo.toml')
 assert 'crate-type = ["lib", "dylib"]' in manifest and 'edition = "2024"' in manifest
 root='src/tools/run-make-support/src/'
 lib=text(root+'lib.rs')
 for name in ['assertion_helpers','diff','path_helpers','external_deps']:assert 'pub mod '+name+';' in lib
 assert 'mod macros;' in lib
 for module in ['assertion_helpers','diff']:
  assert '#[cfg(test)]\nmod tests;' in text(root+module+'/mod.rs')
 names=[];test_definitions=[]
 for module in ['assertion_helpers','diff']:
  name=root+module+'/tests.rs';raw=text(name)
  assert '#[ignore' not in raw and '#[cfg' not in raw
  for match in re.finditer(r'#\[test\]\s*(?:#\[should_panic\]\s*)?fn ([a-z_]+)\(',raw):
   prefix=[module,'tests']
   if module=='assertion_helpers':
    containers=list(re.finditer(r'^mod (\w+) \{',raw[:match.start()],re.M));assert containers
    prefix.append(containers[-1][1])
   full='::'.join([*prefix,match[1]]);names.append(full)
   test_definitions.append(dict(name=full,path=name,line=raw[:match.start()].count('\n')+1,should_panic='#[should_panic]' in match[0]))
 assert len(names)==15 and len(set(names))==15
 docs=[]
 specifications=[('macros.rs','macros::impl_common_helpers','ignore (illustrative)',16,'ignored'),('external_deps/rustc.rs','external_deps::rustc::rustc_minicore','ignore (illustrative)',35,'ignored'),('path_helpers.rs','path_helpers::path','rust',23,'ok')]
 for name,item,language,line,status in specifications:
  raw=text(root+name);assert raw.splitlines()[line-1]=='/// ```'+language
  docs.append(dict(path=root+name,item=item,line=line,status=status,language=language))
 # Close all support source membership, so additional tests/fences cannot hide
 # outside the individually mapped files.
 all_tests=0;fences=[]
 for path in sorted((source/root).rglob('*.rs')):
  name=str(path.relative_to(source));raw=text(name)
  all_tests+=raw.count('#[test]')
  for index,line in enumerate(raw.splitlines(),1):
   match=re.fullmatch(r'\s*/// ```(.+)',line)
   if match:fences.append((name,index,match[1]))
 assert all_tests==15 and sorted(fences)==sorted((d['path'],d['line'],d['language']) for d in docs)
 assert sum(row['should_panic'] for row in test_definitions)==6
 return dict(test_names=sorted(names),test_definitions=test_definitions,doctests=docs,files=files,
  unit_output_policy='JSON TestOutcome.name, unchanged by bootstrap verbose rendering',
  route='registered CrateRunMakeSupport test; compiler0, Mode::ToolBootstrap; unit tests and ordinary doctests',
  producer_role='D2 snapshot compiler and libraries; Cargo test library artifacts, not internal ToolBuild metadata',
  source_scope='All support .rs files plus exact bootstrap dispatch/Cargo/test/failed-test sources and manifest; no source mutation or execution.')
