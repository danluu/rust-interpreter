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
    assert not control.WORK.exists() and not (owner / '.work/experiments/hash-continuation-controls-supervisor-01').exists()
    names = []
    modules = {'test_catalog':source, 'test_failed_catalog':source, 'test_plan_reference':control.EXTRA_SOURCE}
    for module, directory in modules.items():
        tree = ast.parse((directory / (module + '.py')).read_text())
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                names.extend(module + '.' + node.name + '.' + child.name for child in node.body
                             if isinstance(child, ast.FunctionDef) and child.name.startswith('test_'))
    assert len(names) == len(set(names)) == 70
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
    for name in ['catalog.py', 'test_catalog.py', 'test_failed_catalog.py', 'README.md']:
        add(source/name)
    for name in ['plan_reference.py', 'test_plan_reference.py']:
        add(control.EXTRA_SOURCE/name)
    # Preserve the actual original33 source/owner/raw proof, without rerunning it
    # or treating the new58/70 source as already qualified.
    prior = owner/'experiments/completed-proof-snapshot-catalog-controls-01'
    prior_work = owner/'.work/completed-proof-snapshot-catalog-controls-01'
    prior_audit = owner/'.work/completed-proof-snapshot-catalog-controls-independent-verification-01.json'
    assert control.owned.sha(prior/'inputs.json') == 'a7d63a7514ad0af7b46557a7e4cceff7c266077cdab4c311b7d061f66e6360dd'
    assert control.owned.sha(prior_audit) == 'aab6a8376e93f8abb181950236afb95eb5fa6c89c5c68df6a2e95fabf6d122bd'
    original = control.read(prior/'inputs.json')
    for name, row in original['files'].items():
        add(name)
        assert files[name] == row
    for name, resolved in original['routes'].items():
        assert str(Path(name).resolve(strict=True)) == resolved
        routes[name] = resolved
    prior_paths = [prior/'inputs.json', prior/'launch.json', prior_audit,
        owner/'.work/launch_completed_proof_snapshot_catalog_controls_01_bounded.py',
        owner/'.work/verify_completed_proof_snapshot_catalog_controls_01.py',
        owner/'.work/execute_completed_proof_snapshot_catalog_controls_audit_01.py']
    for directory, names_to_keep in [
        (prior_work, ['receipt.json','result.json','command/receipt.json','command/stdout','command/stderr']),
        (owner/'.work/experiments/completed-proof-snapshot-catalog-controls-supervisor-01', ['status.json','plan.json','command.log']),
        (owner/'.work/completed-proof-snapshot-catalog-controls-launch-execution-01', ['record.json','stdout','stderr']),
        (owner/'.work/completed-proof-snapshot-catalog-controls-verification-execution-01', ['record.json','stdout','stderr','source.py','execution.py'])]:
        prior_paths.extend(directory/name for name in names_to_keep)
    for path in prior_paths:
        add(path)
    old_result = control.read(prior_work/'result.json'); old_receipt = control.read(prior_work/'receipt.json')
    old_audit = control.read(prior_audit)
    assert old_result['status'] == old_receipt['status'] == 'passed' and old_audit['status'] == 'verified'
    assert old_result['tests_run'] == old_receipt['controls_passed'] == old_audit['controls'] == 33
    assert old_audit['receipt_sha256'] == control.owned.sha(prior_work/'receipt.json')
    assert old_receipt['result_sha256'] == old_audit['result_sha256'] == control.owned.sha(prior_work/'result.json')
    assert (source/'test_catalog.py').read_bytes() == (owner/'experiments/completed-proof-snapshot-catalog-01/test_catalog.py').read_bytes()
    provenance = dict(source=str(prior), evidence=str(prior_work), controls=33,
        audit=dict(path=str(prior_audit), sha256=control.owned.sha(prior_audit)),
        receipt_sha256=control.owned.sha(prior_work/'receipt.json'),
        result_sha256=control.owned.sha(prior_work/'result.json'),
        original_tests_sha256=control.owned.sha(source/'test_catalog.py'))
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
                  source_only_hash_continuation_controls=True, original33_provenance=provenance,
                  compiler_calls=0, provider_probes=0, B3_compositions=0)
    control.owned.write(here / 'inputs.json', freeze)
    launch = dict(status='prepared-unrun-awaiting-review', owner=str(owner), environment=environment,
                  command=[str(python), '-B', str(owner / 'scripts/supervise_experiment.py'), '--run-id',
                           'hash-continuation-controls-supervisor-01', '--', str(python), '-B',
                           str(here / 'run.py'), '--inputs-sha256', control.owned.sha(here / 'inputs.json')],
                  inputs_sha256=control.owned.sha(here / 'inputs.json'), helper_sha256=control.owned.sha(here / 'run.py'),
                  expected_children=1, controls=70, capacity=freeze['capacity'], bounds=freeze['bounds'])
    control.owned.write(here / 'launch.json', launch)
    control.guard(freeze)
    print(json.dumps(dict(status='prepared-unrun', launch_sha256=control.owned.sha(here / 'launch.json'),
                         inputs_sha256=launch['inputs_sha256'], files=len(files),
                         bytes=sum(row['stamp'][3] for row in files.values()), controls=70), indent=2))


if __name__ == '__main__':
    main()
