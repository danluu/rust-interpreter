"""Freeze source and pure-control inputs only; this does not launch controls."""
import ast
import json
from pathlib import Path
import sys

import run as control


def main():
    here, source, owner = control.HERE, control.SOURCE, control.OWNER
    assert Path.cwd() == owner and sys.dont_write_bytecode
    assert not any((here / name).exists() for name in ['inputs.json', 'launch.json'])
    assert not control.WORK.exists() and not (owner / '.work/experiments/runtime-installation-controls-supervisor-07').exists()
    names = []
    modules = ['test_installation']
    for module in modules:
        tree = ast.parse((source / (module + '.py')).read_text())
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                names.extend(module + '.' + node.name + '.' + child.name for child in node.body
                             if isinstance(child, ast.FunctionDef) and child.name.startswith('test_'))
    assert len(names) == len(set(names)) == 25
    files, routes = {}, {}
    def add(path):
        path = Path(path); resolved = path.resolve(strict=True)
        routes[str(path)] = str(resolved)
        before = control.stamp(resolved)
        assert resolved.is_file() and resolved.stat().st_size <= 96 * 2**20
        row = dict(sha256=control.owned.sha(resolved), stamp=before)
        assert control.stamp(resolved) == before
        assert str(resolved) not in files or files[str(resolved)] == row
        files[str(resolved)] = row
        if path.suffix == '.py':
            ast.parse(path.read_text(), filename=str(path))
    assert {path.name for path in here.iterdir()} == {'run.py', 'prepare.py', 'child.py'}
    for name in ['run.py', 'prepare.py', 'child.py']:
        path = here / name
        assert path.is_file() and not path.is_symlink()
        add(path)
    for name in ['entry.py', 'controller.py', 'audit_owner.py', 'routes.json', 'prepare.py', 'prepare_once.py', 'launch.py', 'test_installation.py']:
        add(source/name)
    add(owner/'experiments/runtime04-environment-adapter-01/environment.py')
    add(owner/'experiments/runtime-preflight-retry-05/routes.json')
    # Retain the completed ordinary development pass as provenance. It does not
    # substitute for this future independently audited controlled execution.
    development=owner/'results/runtime-installation06-test-development-01'
    assert control.owned.sha(development/'manifest.json')=='cfb87bc70ee8d39ab72d37555ff6a8f3c678e0e432497af81507803ac6eaa505'
    manifest=control.read(development/'manifest.json')
    assert len(manifest)==12 and 'manifest.json' not in manifest
    for name,row in manifest.items():
        assert Path(name).name==name and set(row)=={'bytes','sha256'}
        path=development/name
        assert path.stat().st_size==row['bytes'] and control.owned.sha(path)==row['sha256']
        add(path)
    add(development/'manifest.json')
    ordinary=control.read(development/'result.json');closed=control.read(development/'record.json')
    before=control.read(development/'source-before.json')
    assert before==control.read(development/'source-after.json')
    assert ordinary['status']=='passed' and ordinary['actual_tests']==25
    assert ordinary['controlled_qualification'] is False and ordinary['sources_unchanged'] is True
    assert ordinary['record_sha256']==control.owned.sha(development/'record.json')
    assert closed['status']=='closed' and closed['returncode']==0
    assert closed['cwd']==str(source) and closed['command']==['/opt/homebrew/bin/python3','-B',str(development/'child.py')]
    for stream in ['stdout','stderr']:
        assert closed[stream+'_sha256']==control.owned.sha(development/stream)
    for path,row in before.items():
        assert control.owned.sha(Path(path))==row['sha256']
        assert control.stamp(Path(path))==[row['identity'][k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]
    development_reference=dict(result=dict(path=str(development/'result.json'),sha256=control.owned.sha(development/'result.json')),
        record=dict(path=str(development/'record.json'),sha256=ordinary['record_sha256']),
        manifest=dict(path=str(development/'manifest.json'),sha256=control.owned.sha(development/'manifest.json')))
    python = Path(sys.executable).resolve(strict=True)
    for path in [python, '/opt/homebrew/bin/python3', '/bin/ps', '/usr/sbin/lsof',
                 owner / 'scripts/supervise_experiment.py', control.X / 'experiments/stable-cgu/owned_stage.py']:
        add(path)
    environment = dict(HOME='/Users/danluu', USER='danluu', LOGNAME='danluu', LANG='C', LC_ALL='C', TZ='UTC',
                       PATH='/usr/bin:/bin:/usr/sbin:/sbin', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
                       TMPDIR=str(control.WORK / 'tmp'))
    command = [str(python), '-B', str(here / 'child.py')]
    freeze = dict(status='prepared-unrun', owner=str(owner), python=str(python), environment=environment,
                  files=files, routes=routes, expected_names=sorted(names), command=command,
                  canonical_lock=str(control.owned.CANONICAL_LOCK), wait_seconds=600,
                  capacity=dict(entry_gib=10, stop_gib=9, floor_gib=8),
                  bounds=dict(child_alarm_seconds=120, child_cpu_seconds=60, maximum_file_bytes=256 * 1024,
                              maximum_writable_names=256, maximum_directory_names=2048,
                              maximum_cumulative_child_file_payload_bytes=258 * 256 * 1024,
                              maximum_retained_stage_file_bytes=2 * 2**20),
                  source_only_installation_route_phase_prerequisite_controls=True, compiler_calls=0, provider_probes=0, B3_compositions=0)
    freeze['ordinary_development_reference']=development_reference
    control.owned.write(here / 'inputs.json', freeze)
    launch = dict(status='prepared-unrun-awaiting-review', owner=str(owner), environment=environment,
                  command=[str(python), '-B', str(owner / 'scripts/supervise_experiment.py'), '--run-id',
                           'runtime-installation-controls-supervisor-07', '--', str(python), '-B',
                           str(here / 'run.py'), '--inputs-sha256', control.owned.sha(here / 'inputs.json')],
                  inputs_sha256=control.owned.sha(here / 'inputs.json'), helper_sha256=control.owned.sha(here / 'run.py'),
                  expected_children=1, controls=25, capacity=freeze['capacity'], bounds=freeze['bounds'])
    control.owned.write(here / 'launch.json', launch)
    control.guard(freeze)
    print(json.dumps(dict(status='prepared-unrun', launch_sha256=control.owned.sha(here / 'launch.json'),
                         inputs_sha256=launch['inputs_sha256'], files=len(files),
                         bytes=sum(row['stamp'][3] for row in files.values()), controls=25), indent=2))


if __name__ == '__main__':
    main()
