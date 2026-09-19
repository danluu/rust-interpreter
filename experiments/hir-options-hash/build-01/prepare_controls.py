#!/usr/bin/env python3
"""Freeze local filesystem controls without executing them."""
import ast
import json
from pathlib import Path
import sys

import acquire as a


def write(path, value):
    with path.open('x') as stream:
        json.dump(value,stream,sort_keys=True,indent=2)
        stream.write('\n')


def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize
    python = Path(sys.executable).resolve(strict=True)
    paths = [a.HERE/n for n in ['acquire.py','test_acquire.py','run_controls.py','prepare_controls.py']]
    paths += [a.OWNER/'experiments/stable-cgu/owned_stage.py',a.OWNER/'scripts/supervise_experiment.py',python]
    files={str(p):dict(sha256=a.owned.sha(p),stamp=a.stamp(p)) for p in paths}
    for p in paths:
        if p.suffix=='.py':
            ast.parse(p.read_text())
    env=dict(PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',HOME='/Users/danluu',LANG='C',LC_ALL='C',
        PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHON_COLORS='0')
    command=[str(python),'-B','-m','unittest','-v','test_acquire']
    write(a.HERE/'control-inputs.json',dict(schema_version=1,files=files,symlinks={},configurations={},
        environment=env,command=command,status='prepared-unrun'))
    launch=dict(status='prepared-unrun-awaiting-review',owner=str(a.OWNER),environment=env,
        command=[str(python),'-B',str(a.OWNER/'scripts/supervise_experiment.py'),'--run-id',
            'hir-options-hash-acquisition-controls-supervisor-01','--',str(python),'-B',str(a.HERE/'run_controls.py'),
            '--inputs-sha256',a.owned.sha(a.HERE/'control-inputs.json')],
        inputs_sha256=a.owned.sha(a.HERE/'control-inputs.json'),expected_children=1,controls=4)
    write(a.HERE/'control-launch.json',launch)
    print(json.dumps(dict(launch_sha256=a.owned.sha(a.HERE/'control-launch.json'),inputs_sha256=launch['inputs_sha256'],files=len(files)),indent=2))


if __name__=='__main__':
    main()
