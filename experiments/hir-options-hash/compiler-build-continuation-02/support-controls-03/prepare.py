"""Freeze the reviewed bounded wrapper around the unchanged seven controls."""
import ast
import json
from pathlib import Path
import sys

import run as control

def main():
 here,source,owner=control.HERE,control.SOURCE,control.OWNER
 assert Path.cwd()==owner and sys.dont_write_bytecode and not sys.flags.optimize
 assert not any((here/name).exists() for name in ['inputs.json','launch.json'])
 assert not control.WORK.exists()
 old=control.read(source/'control-inputs.json')
 assert control.owned.sha(source/'control-inputs.json')=='76f56e9efce461a34efcca97f35a5d21e40546745db9a0f26312c38889ebfb5f'
 assert control.owned.sha(source/'control-launch.json')=='9c10584ec109df0bea8470a3f00a73e53c718130f66ae437c6bb57fd54ee5497'
 tree=ast.parse((source/'test_support.py').read_bytes())
 names=sorted('test_support.'+node.name+'.'+child.name for node in tree.body if isinstance(node,ast.ClassDef) for child in node.body if isinstance(child,ast.FunctionDef) and child.name.startswith('test_'))
 assert len(names)==len(set(names))==7
 files={};routes={}
 def add(path):
  path=Path(path);resolved=path.resolve(strict=True);routes[str(path)]=str(resolved)
  before=control.stamp(resolved);assert resolved.is_file() and resolved.stat().st_size<=96*2**20
  row=dict(sha256=control.owned.sha(resolved),stamp=before)
  assert control.stamp(resolved)==before
  assert str(resolved) not in files or files[str(resolved)]==row
  files[str(resolved)]=row
  if path.suffix=='.py':ast.parse(path.read_bytes(),filename=str(path))
 for name,row in old['files'].items():
  add(name);assert files[name]['sha256']==row['sha256'] and files[name]['stamp'][3]==row['bytes']
 for path in sorted((source/'support-controls-02').iterdir()):
  assert path.is_file() and not path.is_symlink();add(path)
 for path in [owner/'.work/hir-options-hash-support-controls-launch-02.actual.json',owner/'.work/hir-options-hash-support-controls-launch-02.stdout',owner/'.work/hir-options-hash-support-controls-launch-02.stderr',owner/'.work/hir-options-hash-support-controls-launch-observation-02.json']:
  add(path)
 for path in sorted(here.iterdir()):
  assert path.is_file() and not path.is_symlink();add(path)
 for path in [source/'control-inputs.json',source/'control-launch.json',Path(sys.executable).resolve(strict=True),'/opt/homebrew/bin/python3','/bin/ps','/usr/sbin/lsof']:
  add(path)
 environment=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',
  PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR=str(control.WORK/'tmp'))
 freeze=dict(status='prepared-unrun',owner=str(owner),python=str(Path(sys.executable).resolve(strict=True)),environment=environment,
  files=files,routes=routes,expected_names=names,command=[str(Path(sys.executable).resolve(strict=True)),'-B',str(here/'child.py')],
  unrun_prior_outputs=[str(owner/'.work/hir-options-hash-support-controls-01'),str(owner/'.work/experiments/hir-options-hash-support-controls-supervisor-01'),str(owner/'.work/hir-options-hash-support-controls-02'),str(owner/'.work/experiments/hir-options-hash-support-controls-supervisor-02')],
  prior_unrun_launch_sha256=control.owned.sha(source/'control-launch.json'),canonical_lock=str(control.owned.CANONICAL_LOCK),wait_seconds=600,
  capacity=dict(entry_gib=16,stop_gib=9,floor_gib=8),bounds=dict(child_alarm_seconds=120,child_cpu_seconds=60,maximum_file_bytes=256*1024,
   maximum_writable_names=256,maximum_directory_names=2048,maximum_cumulative_child_file_payload_bytes=258*256*1024,maximum_retained_stage_file_bytes=2*2**20),
  controls=7,compiler_calls=0,provider_probes=0,B3_compositions=0)
 control.owned.write(here/'inputs.json',freeze)
 launch=dict(status='prepared-unrun-authorized-after-source-and-input-review',owner=str(owner),environment=environment,
  command=[freeze['python'],'-B',str(owner/'scripts/supervise_experiment.py'),'--run-id','hir-options-hash-support-controls-supervisor-03','--',freeze['python'],'-B',str(here/'run.py'),'--inputs-sha256',control.owned.sha(here/'inputs.json')],
  inputs_sha256=control.owned.sha(here/'inputs.json'),helper_sha256=control.owned.sha(here/'run.py'),expected_children=1,controls=7,capacity=freeze['capacity'],bounds=freeze['bounds'])
 control.owned.write(here/'launch.json',launch);control.guard(freeze)
 print(json.dumps(dict(status='prepared-unrun',launch_sha256=control.owned.sha(here/'launch.json'),inputs_sha256=launch['inputs_sha256'],files=len(files),bytes=sum(row['stamp'][3] for row in files.values()),controls=7),indent=2))

if __name__=='__main__':main()
