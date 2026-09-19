#!/usr/bin/env python3
"""Prepare, but do not execute, the allocation monitor's synthetic controls."""
import ast
import json
from pathlib import Path
import sys

import bounded_command_v2 as b

HERE=Path(__file__).resolve().parent


def write(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n')


def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize
    python=Path(sys.executable).resolve(strict=True)
    paths=[HERE/n for n in ['bounded_command_v2.py','test_monitor.py','test_drain.py','run_controls_02.py','prepare_controls_02.py']]
    paths += [python,b.OWNER/'experiments/stable-cgu/owned_stage.py',b.OWNER/'scripts/supervise_experiment.py']
    for p in paths:
        if p.suffix=='.py':ast.parse(p.read_text())
    old=json.loads((HERE/'control-inputs.json').read_bytes())
    for name,row in old['files'].items():
        path=Path(name);assert b.owned.sha(path)==row['sha256'];paths.append(path)
    paths += [HERE/'control-inputs.json',HERE/'control-launch.json']
    history=b.OWNER/'.work/experiments/hir-options-hash-build-continuation-controls-supervisor-01'
    paths += [path for path in history.rglob('*') if path.is_file()]
    paths += [b.OWNER/('.work/hir-options-hash-build-continuation-controls-launch-01.'+suffix) for suffix in ['actual.json','stdout','stderr']]
    assert not (b.OWNER/'.work/hir-options-hash-build-continuation-controls-01').exists()
    files={str(p):dict(sha256=b.owned.sha(p),bytes=p.stat().st_size) for p in paths}
    env=dict(PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',HOME='/Users/danluu',LANG='C',LC_ALL='C',
        PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHON_COLORS='0')
    write(HERE/'control-inputs-02.json',dict(files=files,environment=env,python=str(python),
        command=[str(python),'-B','-m','unittest','-v','test_monitor','test_drain'],status='prepared-unrun'))
    launch=dict(status='prepared-unrun-awaiting-review',owner=str(b.OWNER),environment=env,controls=13,expected_children=1,
        inputs_sha256=b.owned.sha(HERE/'control-inputs-02.json'),command=[str(python),'-B',str(b.OWNER/'scripts/supervise_experiment.py'),
            '--run-id','hir-options-hash-build-continuation-controls-supervisor-02','--',str(python),'-B',str(HERE/'run_controls_02.py'),
            '--inputs-sha256',b.owned.sha(HERE/'control-inputs-02.json')])
    write(HERE/'control-launch-02.json',launch)
    print(json.dumps(dict(launch_sha256=b.owned.sha(HERE/'control-launch-02.json'),inputs_sha256=launch['inputs_sha256'],
        files=len(files),bytes=sum(v['bytes'] for v in files.values())),indent=2))


if __name__=='__main__':
    main()
