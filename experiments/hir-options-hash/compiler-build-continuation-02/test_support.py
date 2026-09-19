"""Bounded source/fixture controls; no compiler, probes, process control or N writes."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('support_continuation_controls',HERE/'continue.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class SupportControls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.expect=c.support_source.derive(c.S)
 def rendered(self):
  text=''.join('test '+name+' ... ok\n' for name in self.expect['test_names'])
  text+='test result: ok. 15 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;\n'
  text+=''.join(f"test {row['path']} - {row['item']} (line {row['line']}) ... {row['status']}\n" for row in self.expect['doctests'])
  return text.encode()
 def parse_rendered(self,raw):
  with mock.patch.object(c,'read',return_value={'candidate_revision':'candidate'}):c.support_tests(raw,self.expect)
 def fixture(self,root):
  source=root/'source';host='aarch64-apple-darwin';d=source/'build'/host/'stage0'
  output=source/'build'/host/'bootstrap-tools'/host/'release/build/run_make_support/hash/out';output.mkdir(parents=True)
  tree=source/'build'/host/'bootstrap-tools';shim=str(source/'build/bootstrap/debug/rustc')
  env=dict(RUSTC=shim,RUSTC_WRAPPER=shim,RUSTC_REAL=str(d/'bin/rustc'),RUSTC_SNAPSHOT=str(d/'bin/rustc'),RUSTC_LIBDIR=str(d/'lib'),RUSTC_SNAPSHOT_LIBDIR=str(d/'lib'),RUSTC_STAGE='0',RUSTC_SYSROOT=str(d),CARGO_TARGET_DIR=str(tree),CARGO_BUILD_BUILD_DIR=str(tree),RUSTDOC_REAL=str(d/'bin/rustdoc'),DYLD_LIBRARY_PATH=':'.join(c.parsers.test_loader_paths(source)),ENV_INPUT='original')
  argv=[str(d/'bin/cargo'),'test','--target',host,'--manifest-path',str(source/'src/tools/run-make-support/Cargo.toml'),'--','-Z','unstable-options','--format','json']
  def line(e):return ('running: cd '+json.dumps(str(source))+' && env -u UNUSED '+' '.join(k+'='+json.dumps(v) for k,v in e.items())+' '+' '.join(json.dumps(v) for v in argv)+' (failure_mode=Exit)\n').encode()
  step='test::CrateRunMakeSupport { host: '+host+' }'
  dry=line(env);real=(f'[TIMING:start] {step}\n'.encode()+line(env)+f'[TIMING:end] {step} -- 0.100\n'.encode())
  args=[shim,shim,'--crate-name','run_make_support','--crate-type','lib','--crate-type','dylib','--emit=dep-info,metadata,link','--target',host,'--out-dir',str(output),'-C','extra-filename=-abc']
  stderr=('Running `'+' '.join(args)+'`\n').encode()
  selected={str((output/('librun_make_support-abc'+ext)).relative_to(tree)):{} for ext in ['.rlib','.rmeta','.dylib']}
  return dict(source=source,inventory=dict(root=str(tree),selected=selected),stdout=dry+real,stderr=stderr,
   inherited={},configuration={'build':{'print-step-timings':True}},outer=['./x','test','--stage','1','src/tools/run-make-support','--jobs','2','-vv']),line,env,step
 def validate(self,fixture):return c.producer.validate(**fixture,timing=c.timing,parse=c.parsers)
 def test_source_definitions_and_plain_json_names(self):
  self.assertEqual(sum(row['should_panic'] for row in self.expect['test_definitions']),6)
  self.assertEqual([row['status'] for row in self.expect['doctests']],['ignored','ignored','ok'])
  self.parse_rendered(self.rendered())
 def test_renderer_rejects_missing_panic_test_or_changed_doctest_policy(self):
  raw=self.rendered();name=next(row['name'] for row in self.expect['test_definitions'] if row['should_panic'])
  for changed in [raw.replace(('test '+name+' ... ok\n').encode(),b''),raw.replace((name+' ...').encode(),(name+' - should panic ...').encode()),raw.replace(b'... ignored',b'... ok',1)]:
   with self.subTest(changed=changed[:40]),self.assertRaises(AssertionError):self.parse_rendered(changed)
 def test_real_and_selfcheck_preserved_with_exact_producer(self):
  with tempfile.TemporaryDirectory() as tmp:
   fixture,_,_,_=self.fixture(Path(tmp));proof=self.validate(fixture)
   self.assertEqual([r['execution'] for r in proof['timing_contexts']['stdout']['commands']],['self-check-print','real'])
   self.assertEqual(proof['library_producer']['effective_environment']['ENV_INPUT'],'original')
   self.assertEqual(len(proof['library_producer']['artifacts']),3)
 def test_selfcheck_only_or_wrong_timing_route_is_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   fixture,line,env,step=self.fixture(Path(tmp))
   for stdout in [line(env)+b'[TIMING:start] tool::Other\n[TIMING:end] tool::Other -- 0.001\n',fixture['stdout'].replace(step.encode(),b'test::Other')]:
    with self.subTest(stdout=stdout[-80:]),self.assertRaises((AssertionError,ValueError)):self.validate(dict(fixture,stdout=stdout))
 def test_distinct_real_environment_is_not_deduplicated(self):
  with tempfile.TemporaryDirectory() as tmp:
   fixture,line,env,step=self.fixture(Path(tmp));changed=dict(env,ENV_INPUT='changed')
   extra=f'[TIMING:start] {step}\n'.encode()+line(changed)+f'[TIMING:end] {step} -- 0.001\n'.encode()
   with self.assertRaisesRegex(AssertionError,'ambiguous'):self.validate(dict(fixture,stdout=fixture['stdout']+extra))
 def test_wrong_toolbootstrap_role_shim_or_duplicate_producer_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   fixture,_,env,_=self.fixture(Path(tmp));root=str(fixture['source'])
   changed=fixture['stdout'].replace(('RUSTC_SYSROOT='+json.dumps(env['RUSTC_SYSROOT'])).encode(),('RUSTC_SYSROOT='+json.dumps(root+'/build/aarch64-apple-darwin/stage0-sysroot')).encode())
   variants=[dict(fixture,stdout=changed),dict(fixture,stderr=fixture['stderr'].replace((env['RUSTC']+' '+env['RUSTC']).encode(),(env['RUSTC']+' /wrong/rustc').encode())),dict(fixture,stderr=fixture['stderr']*2)]
   for variant in variants:
    with self.subTest(variant=variant['stderr'][:80]),self.assertRaises((AssertionError,ValueError)):self.validate(variant)
 def test_retained_failure_cannot_be_reclassified_as_success(self):
  terminal=dict(status='failed',commands=[{} for _ in range(7)],compiler_stages_completed=7,new_compiler_stages_completed=5,saved_children=16,error="AssertionError('unexpected compiler-stage return code')",native_recipe_qualified=False,hash_driver_qualified=False,application_qualified=False)
  c.retained_terminal(terminal)
  for change in [dict(status='passed'),dict(commands=terminal['commands'][:6]),dict(native_recipe_qualified=True),dict(error='different failure')]:
   with self.subTest(change=change),self.assertRaises(AssertionError):c.retained_terminal(dict(terminal,**change))

if __name__=='__main__':unittest.main()
