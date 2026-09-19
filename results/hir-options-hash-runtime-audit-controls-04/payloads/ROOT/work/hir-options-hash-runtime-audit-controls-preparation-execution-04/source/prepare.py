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
    assert not control.WORK.exists() and not (owner / '.work/experiments/hir-options-hash-runtime-audit-controls-supervisor-04').exists()
    names = []
    modules = ['test_recipe', 'test_preflight', 'test_final_runtime']
    for module in modules:
        tree = ast.parse((source / (module + '.py')).read_text())
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                names.extend(module + '.' + node.name + '.' + child.name for child in node.body
                             if isinstance(child, ast.FunctionDef) and child.name.startswith('test_'))
    assert len(names) == len(set(names)) == 45
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
    for path in sorted(here.iterdir()):
        assert path.is_file() and not path.is_symlink()
        add(path)
    for name in ['recipe.py', 'preflight.py', 'final_runtime.py', 'reader.py', 'test_recipe.py', 'test_preflight.py', 'test_final_runtime.py', 'README.md']:
        add(source/name)
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
                  capacity=dict(entry_gib=16, stop_gib=9, floor_gib=8),
                  bounds=dict(child_alarm_seconds=120, child_cpu_seconds=60, maximum_file_bytes=256 * 1024,
                              maximum_writable_names=256, maximum_directory_names=2048,
                              maximum_cumulative_child_file_payload_bytes=258 * 256 * 1024,
                              maximum_retained_stage_file_bytes=2 * 2**20),
                  source_only_saved_runtime_audit_callback_controls=True, compiler_calls=0, provider_probes=0, B3_compositions=0)
    control.owned.write(here / 'inputs.json', freeze)
    launch = dict(status='prepared-unrun-awaiting-review', owner=str(owner), environment=environment,
                  command=[str(python), '-B', str(owner / 'scripts/supervise_experiment.py'), '--run-id',
                           'hir-options-hash-runtime-audit-controls-supervisor-04', '--', str(python), '-B',
                           str(here / 'run.py'), '--inputs-sha256', control.owned.sha(here / 'inputs.json')],
                  inputs_sha256=control.owned.sha(here / 'inputs.json'), helper_sha256=control.owned.sha(here / 'run.py'),
                  expected_children=1, controls=45, capacity=freeze['capacity'], bounds=freeze['bounds'])
    control.owned.write(here / 'launch.json', launch)
    control.guard(freeze)
    print(json.dumps(dict(status='prepared-unrun', launch_sha256=control.owned.sha(here / 'launch.json'),
                         inputs_sha256=launch['inputs_sha256'], files=len(files),
                         bytes=sum(row['stamp'][3] for row in files.values()), controls=45), indent=2))


if __name__ == '__main__':
    main()
