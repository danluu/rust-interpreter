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
    assert not control.WORK.exists() and not (owner / '.work/experiments/runtime-installation-controls-supervisor-08').exists()
    names = []
    native = owner/'experiments/runtime-native-loader-probes-01'
    modules = [('test_installation',source),('test_native_loader',native),('test_imports',source)]
    for module, directory in modules:
        tree = ast.parse((directory / (module + '.py')).read_text())
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                names.extend(module + '.' + node.name + '.' + child.name for child in node.body
                             if isinstance(child, ast.FunctionDef) and child.name.startswith('test_'))
    assert len(names) == len(set(names)) == 48
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
    for name in ['entry.py', 'controller.py', 'audit_owner.py', 'routes.json', 'prepare.py', 'prepare_once.py', 'launch.py', 'imports.py', 'test_installation.py', 'test_imports.py']:
        add(source/name)
    for name in ['runtime_compiler.py', 'producer_recipe.py', 'audit_recipe.py', 'test_native_loader.py']:
        add(native/name)
    for path in ['/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/runtime_compiler.py', '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/custom_compiler.py', '/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/hir-options-hash/runtime-installation-01/recipe.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/installation-plan-01/specification.json']:
        add(path)
    add(owner/'experiments/runtime04-environment-adapter-01/environment.py')
    add(owner/'experiments/runtime-preflight-retry-05/routes.json')
    # Two ordinary passes are retained as provenance, separately from this
    # future combined controlled execution. Their original manifests are finite
    # subsets; later publication/readback notes outside them are not implied.
    development_reference={}
    for label, directory, expected_cwd, count, manifest_sha, result_sha, record_sha in [('installation_factory', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-installation07-test-development-02', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03', 30, '32714faef9db089fe00fa8c3abafdd3770f0b69e4846bf4b0f76b6f00b2c9079', '728e78190e4e1b93713ba54c615778c6dfaa4957b44ca873dddd19b2c520fcaf', '216932c3e9a0688aaa76ad75d276fa613d49fb137df2972952c4cd9014a2df3b'), ('native_loader', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-native-loader-development-01', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01', 18, '8a27d91ac6b6cb6286161c53f3b324992050b7e1343982cd766c98d38065dc69', '2484b106fa630791bf5f6d8d68a7f9c7b08a01e1bec742409de7623e5d257ac3', '6e9ba64778ca1e60e5e253cf02a9fea8be9d0f3a27be563fd1b1082b205c45d7')]:
        development=Path(directory)
        assert control.owned.sha(development/'manifest.json')==manifest_sha
        manifest=control.read(development/'manifest.json')
        assert len(manifest)==9 and 'manifest.json' not in manifest
        for name,row in manifest.items():
            assert Path(name).name==name and set(row)=={'bytes','sha256'}
            path=development/name
            assert path.stat().st_size==row['bytes'] and control.owned.sha(path)==row['sha256']
            add(path)
        add(development/'manifest.json')
        ordinary=control.read(development/'result.json');closed=control.read(development/'record.json')
        before=control.read(development/'source-before.json')
        assert before==control.read(development/'source-after.json')
        assert ordinary['status']=='passed' and ordinary['actual_tests']==count
        assert ordinary['controlled_qualification'] is False and ordinary['sources_unchanged'] is True
        assert ordinary['record_sha256']==record_sha==control.owned.sha(development/'record.json')
        assert control.owned.sha(development/'result.json')==result_sha
        assert closed['status']=='closed' and closed['returncode']==0
        assert closed['cwd']==expected_cwd and closed['command']==['/opt/homebrew/bin/python3','-B',str(development/'child.py')]
        for stream in ['stdout','stderr']:
            assert closed[stream+'_sha256']==control.owned.sha(development/stream)
        for path,row in before.items():
            assert control.owned.sha(Path(path))==row['sha256']
            assert control.stamp(Path(path))==[row['identity'][k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]
        development_reference[label]=dict(result=dict(path=str(development/'result.json'),sha256=result_sha),
            record=dict(path=str(development/'record.json'),sha256=record_sha),
            manifest=dict(path=str(development/'manifest.json'),sha256=manifest_sha))
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
                           'runtime-installation-controls-supervisor-08', '--', str(python), '-B',
                           str(here / 'run.py'), '--inputs-sha256', control.owned.sha(here / 'inputs.json')],
                  inputs_sha256=control.owned.sha(here / 'inputs.json'), helper_sha256=control.owned.sha(here / 'run.py'),
                  expected_children=1, controls=48, capacity=freeze['capacity'], bounds=freeze['bounds'])
    control.owned.write(here / 'launch.json', launch)
    control.guard(freeze)
    print(json.dumps(dict(status='prepared-unrun', launch_sha256=control.owned.sha(here / 'launch.json'),
                         inputs_sha256=launch['inputs_sha256'], files=len(files),
                         bytes=sum(row['stamp'][3] for row in files.values()), controls=48), indent=2))


if __name__ == '__main__':
    main()
