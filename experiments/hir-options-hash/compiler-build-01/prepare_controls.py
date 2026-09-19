#!/usr/bin/env python3
"""Prepare, but do not execute, the allocation monitor's synthetic controls."""
import ast
import json
from pathlib import Path
import sys

import bounded_command as b

HERE=Path(__file__).resolve().parent


def write(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n')


def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize
    python=Path(sys.executable).resolve(strict=True)
    paths=[HERE/n for n in ['bounded_command.py','test_bounded_command.py','run_controls.py','prepare_controls.py']]
    paths += [python,b.OWNER/'experiments/stable-cgu/owned_stage.py',b.OWNER/'scripts/supervise_experiment.py']
    for p in paths:
        if p.suffix=='.py':ast.parse(p.read_text())
    files={str(p):dict(sha256=b.owned.sha(p),bytes=p.stat().st_size) for p in paths}
    env=dict(PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',HOME='/Users/danluu',LANG='C',LC_ALL='C',
        PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHON_COLORS='0')
    write(HERE/'control-inputs.json',dict(files=files,environment=env,
        command=[str(python),'-B','-m','unittest','-v','test_bounded_command'],status='prepared-unrun'))
    launch=dict(status='prepared-unrun-awaiting-review',owner=str(b.OWNER),environment=env,controls=5,expected_children=1,
        inputs_sha256=b.owned.sha(HERE/'control-inputs.json'),command=[str(python),'-B',str(b.OWNER/'scripts/supervise_experiment.py'),
            '--run-id','hir-options-hash-build-budget-controls-supervisor-01','--',str(python),'-B',str(HERE/'run_controls.py'),
            '--inputs-sha256',b.owned.sha(HERE/'control-inputs.json')])
    write(HERE/'control-launch.json',launch)
    print(json.dumps(dict(launch_sha256=b.owned.sha(HERE/'control-launch.json'),inputs_sha256=launch['inputs_sha256'],
        files=len(files),bytes=sum(v['bytes'] for v in files.values())),indent=2))


if __name__=='__main__':
    main()
