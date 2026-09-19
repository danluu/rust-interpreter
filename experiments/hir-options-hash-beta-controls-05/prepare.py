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
    assert not control.WORK.exists() and not (owner / '.work/experiments/hir-options-hash-beta-controls-supervisor-05').exists()
    names = []
    modules = ['test_compose_sysroot', 'test_strip', 'test_producer', 'test_controller', 'test_ancestor_workspace', 'test_timing_context', 'test_output_catalog', 'test_provider_observations', 'test_history', 'test_nonprivate_outputs']
    for module in modules:
        tree = ast.parse((source / (module + '.py')).read_text())
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                names.extend(module + '.' + node.name + '.' + child.name for child in node.body
                             if isinstance(child, ast.FunctionDef) and child.name.startswith('test_'))
    assert len(names) == len(set(names)) == 97
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
    for directory in [here, source]:
        for path in sorted(directory.iterdir()):
            assert path.is_file() and not path.is_symlink()
            add(path)
    references = control.read(source / 'source-bindings.json')
    for row in [*references['references'].values(), *references['predecessor_draft'].values(), *references['timing_sources'].values(), *references['provider_grammar_references'].values()]:
        add(row['path']); record = files[str(Path(row['path']).resolve(strict=True))]
        assert record['sha256'] == row['sha256'] and record['stamp'][3] == row['size']
    python = Path(sys.executable).resolve(strict=True)
    for path in [python, '/opt/homebrew/bin/python3', '/bin/ps', '/usr/sbin/lsof',
                 owner / 'scripts/supervise_experiment.py', owner / 'experiments/hir-options-hash-stage-monitor/monitor.py', control.X / 'experiments/stable-cgu/owned_stage.py']:
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
                  source_only_actual_manifest_control=True, compiler_calls=0, provider_probes=0, B3_compositions=0)
    control.owned.write(here / 'inputs.json', freeze)
    launch = dict(status='prepared-unrun-awaiting-review', owner=str(owner), environment=environment,
                  command=[str(python), '-B', str(owner / 'scripts/supervise_experiment.py'), '--run-id',
                           'hir-options-hash-beta-controls-supervisor-05', '--', str(python), '-B',
                           str(here / 'run.py'), '--inputs-sha256', control.owned.sha(here / 'inputs.json')],
                  inputs_sha256=control.owned.sha(here / 'inputs.json'), helper_sha256=control.owned.sha(here / 'run.py'),
                  expected_children=1, controls=97, capacity=freeze['capacity'], bounds=freeze['bounds'])
    control.owned.write(here / 'launch.json', launch)
    control.guard(freeze)
    print(json.dumps(dict(status='prepared-unrun', launch_sha256=control.owned.sha(here / 'launch.json'),
                         inputs_sha256=launch['inputs_sha256'], files=len(files),
                         bytes=sum(row['stamp'][3] for row in files.values()), controls=97), indent=2))


if __name__ == '__main__':
    main()
