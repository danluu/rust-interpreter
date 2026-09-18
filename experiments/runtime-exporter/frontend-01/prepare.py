"""Freeze direct frontend qualification after the actual two-tool build passes."""
import ast
import json
from pathlib import Path
import frontend as f


def ref(path):
    return dict(path=str(path), sha256=f.sha(path))


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True); stream.write('\n')


def main():
    prior = f.read(f.b.HERE / 'inputs.json')
    build = f.read(f.b.WORK / 'receipt.json')
    control = f.read(f.OWNER / '.work/runtime-exporter-frontend-controls-01/summary.json')
    assert control['status'] == 'passed' and control['controls'] == 4
    assert control['helper_sha256'] == f.sha(f.HERE / 'frontend.py')
    assert build['status'] == 'passed' and build['proper_strip_build_qualified']
    assert build['actual_exporter_loaded_installed_R'] and build['actual_wrapper_bound_installed_R']
    assert build['adopted_VM_unchanged'] and build['exporter_builds'] == 1
    metadata = f.read(f.m.WORK / 'planned.json')
    built = f.read(f.b.WORK / 'built-tools.json')
    assert f.sha(f.b.WORK / 'built-tools.json') == build['built_tools_sha256']
    sdk = dict(clang=metadata['support_executables']['clang'], path=metadata['environment']['SDKROOT'])
    controls = f.application_commands(sdk)
    children = metadata['children'][:8]
    for name in ('rust-interp-mir-export', 'rust-interp-rustc-wrapper', 'rust-interp-vm'):
        binary = metadata['future_VM']['binary']['path'] if name == 'rust-interp-vm' else str(f.TARGET / 'release' / name)
        for flag in ('-L', '-l'):
            children.append(dict(argv=['/usr/bin/otool', '-arch', 'arm64', flag, binary],
                                 cwd=str(f.OWNER), environment=metadata['environment']))
    children += [dict(argv=row['argv'], cwd=str(f.FIXTURE), environment=f.application_environment(row, sdk),
                      expected=[1, 2] if row['error'] else [0]) for row in controls]
    children += metadata['children'][44:52]
    assert len(children) == 40
    recipe = f.m.OLD / '.work/exporter-split-role-source-02/check.py'
    plan = dict(schema_version=1, policy='runtime-exporter-frontend-v1', status='prepared-unexecuted',
        metadata_plan=ref(f.m.WORK / 'planned.json'), metadata_receipt=ref(f.m.WORK / 'receipt.json'),
        build_plan=ref(f.b.HERE / 'plan.json'), build_receipt=ref(f.b.WORK / 'receipt.json'),
        built_tools=ref(f.b.WORK / 'built-tools.json'), children=children, sdk=sdk, application_commands=controls,
        binding=metadata['binding'], source_checkpoint=f.m.CHECKPOINT, prior_frontend_recipe=ref(recipe),
        runtime_owner=str(f.m.ROWNER), runtime_key=f.m.RKEY, capacity=metadata['capacity'],
        canonical_lock=metadata['canonical_lock'], wait_seconds=600, benchmark=False,
        publication=False, guest_execution=False, compiler_builds=0, exporter_builds=0, VM_builds=0,
        direct_frontend_controls=18, fresh_binary_otool_commands=6,
        library_metadata_reuse=dict(kind='previously captured actual R library commands; bytes and exact stamps remain guarded',
            actual_child_indices=list(range(24, 32)), owner=str(f.m.WORK),
            restrictions='Only exporter may load admitted R driver/LLVM. Wrapper and adopted VM must have no non-system libraries.'),
        composed_guest_qualification_required_before_benchmarks=True)
    write(f.HERE / 'plan.json', plan)
    files = dict(prior['files'])
    additions = [f.HERE / name for name in ('frontend.py', 'prepare.py', 'test_frontend.py', 'plan.json')]
    additions += [f.b.HERE / 'inputs.json', f.b.HERE / 'launch.json', recipe,
        f.OWNER / '.work/verify_runtime_exporter_build_01.py',
        f.OWNER / '.work/runtime-exporter-build-independent-verification-01.json',
        f.OWNER / '.work/runtime-exporter-build-controls-independent-verification-02.json',
        f.OWNER / '.work/runtime-exporter-build-launch-01.actual.json',
        f.OWNER / '.work/runtime-exporter-build-controls-launch-02.actual.json',
        f.OWNER / '.work/runtime-exporter-frontend-controls-independent-verification-01.json',
        f.OWNER / '.work/runtime-exporter-frontend-controls-launch-01.actual.json']
    additions += [f.OWNER / 'tests/fixtures/borrowck-cache' / name for name in ('basic.rs', 'test_export.rs')]
    for directory in [f.b.WORK, f.OWNER / '.work/experiments/runtime-exporter-build-supervisor-01',
                      f.OWNER / '.work/runtime-exporter-build-controls-02',
                      f.OWNER / '.work/experiments/runtime-exporter-build-controls-supervisor-02',
                      f.OWNER / '.work/runtime-exporter-frontend-controls-01',
                      f.OWNER / '.work/experiments/runtime-exporter-frontend-controls-supervisor-01']:
        additions += f.m.ordinary_files(directory)
    for path in additions:
        row = f.m.file_record(path)
        assert str(path) not in files or files[str(path)] == row['sha256']
        files[str(path)] = row['sha256']
    for path, value in files.items(): assert f.sha(path) == value, path
    frozen = dict(schema_version=1, files=files, plan_sha256=f.sha(f.HERE / 'plan.json'),
                  python=prior['python'], launch_environment=prior['launch_environment'], status='source-only-unexecuted')
    write(f.HERE / 'inputs.json', frozen)
    python = frozen['python']['path']; supervisor = f.OWNER / 'scripts/supervise_experiment.py'
    launch = dict(status='prepared-unexecuted-awaiting-root-review', owner=str(f.OWNER), environment=frozen['launch_environment'],
        command=[python, '-B', str(supervisor), '--run-id', 'runtime-exporter-frontend-supervisor-01', '--',
                 python, '-B', str(f.HERE / 'frontend.py'), '--inputs-sha256', f.sha(f.HERE / 'inputs.json')],
        helper=ref(f.HERE / 'frontend.py'), inputs=ref(f.HERE / 'inputs.json'), plan=ref(f.HERE / 'plan.json'),
        supervisor=ref(supervisor), python=frozen['python'], expected_children=40, capacity=plan['capacity'],
        canonical_lock=plan['canonical_lock'], wait_seconds=600, exporter_builds=0, VM_builds=0,
        compiler_builds=0, publication=False, guest_execution=False, benchmark=False)
    write(f.HERE / 'launch.json', launch)
    for name in ('frontend.py', 'prepare.py', 'test_frontend.py'): ast.parse((f.HERE / name).read_text())
    print(json.dumps(dict(launch=ref(f.HERE / 'launch.json'), helper=launch['helper'], inputs=launch['inputs'],
                         plan=launch['plan'], files=len(files)), indent=2))


if __name__ == '__main__':
    main()
