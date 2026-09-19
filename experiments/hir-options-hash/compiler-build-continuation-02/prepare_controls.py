#!/usr/bin/env python3
"""Freeze seven pure support/producer/history controls without executing them."""
import ast
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('support_control_dependencies',HERE/'continue.py')
c=importlib.util.module_from_spec(spec);sys.modules[spec.name]=c;spec.loader.exec_module(c)

def write(path,value):
 with path.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')

def main():
 assert sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd()==c.OWNER
 python=Path(sys.executable).resolve(strict=True)
 paths={python,c.OWNER/'scripts/supervise_experiment.py'}
 for path in HERE.iterdir():
  if path.is_file():paths.add(path)
 for module in list(sys.modules.values()):
  name=getattr(module,'__file__',None)
  if name and name.startswith('/Users/danluu/dev/'):paths.add(Path(name).resolve(strict=True))
 proof=c.support_source.derive(c.S)
 paths.update(c.S/name for name in proof['files'])
 for path in paths:
  assert path.resolve(strict=True)==path and path.is_file() and not path.is_symlink()
  if path.suffix=='.py':ast.parse(path.read_bytes())
 files={str(path):dict(sha256=c.sha(path),bytes=path.stat().st_size) for path in sorted(paths)}
 env=dict(PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',HOME='/Users/danluu',LANG='C',LC_ALL='C',
  PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHON_COLORS='0')
 write(HERE/'control-inputs.json',dict(files=files,environment=env,python=str(python),
  command=[str(python),'-B','-m','unittest','-v','test_support'],controls=7,status='prepared-unrun'))
 launch=dict(status='prepared-unrun-awaiting-review',owner=str(c.OWNER),environment=env,controls=7,expected_children=1,
  inputs_sha256=c.sha(HERE/'control-inputs.json'),command=[str(python),'-B',str(c.OWNER/'scripts/supervise_experiment.py'),
   '--run-id','hir-options-hash-support-controls-supervisor-01','--',str(python),'-B',str(HERE/'run_controls.py'),
   '--inputs-sha256',c.sha(HERE/'control-inputs.json')])
 write(HERE/'control-launch.json',launch)
 print(json.dumps(dict(launch_sha256=c.sha(HERE/'control-launch.json'),inputs_sha256=launch['inputs_sha256'],files=len(files),bytes=sum(row['bytes'] for row in files.values())),indent=2))

if __name__=='__main__':main()
