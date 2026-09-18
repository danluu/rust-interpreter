"""Freeze a fresh two-binary build from passed current D/B2/R metadata."""
import ast
import json
from pathlib import Path

import build as b


def ref(path):
    return dict(path=str(path), sha256=b.sha(path))


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True); stream.write('\n')


def main():
    metadata = b.read(b.m.WORK / 'planned.json')
    assert b.sha(b.m.WORK / 'planned.json') == '4b2cf356e0f04e2d210454b16bfd206ea101be629e390a2b652df0e31762f74d'
    assert b.sha(b.m.WORK / 'receipt.json') == '82ab3670c0f18a6a77be0ad308f0a417ed65ad468ed3e9e923ba3987a42be39a'
    assert b.read(b.m.WORK / 'receipt.json')['status'] == 'passed'
    prior = b.read(b.m.HERE / 'inputs.json')
    children = metadata['children'][:8]
    def append(argv, environment):
        children.append(dict(argv=argv, cwd=str(b.OWNER), environment=environment))
    append(metadata['future_build'], metadata['build_environment'])
    append([str(b.m.TARGET / 'release/rust-interp-mir-export'), '--rust-interp-capabilities'],
           metadata['environment'] | {'DYLD_PRINT_LIBRARIES': '1'})
    append([str(b.m.TARGET / 'release/rust-interp-rustc-wrapper'), '--rust-interp-compiler-roles'], metadata['environment'])
    children += metadata['children'][44:52]
    assert len(children) == 19
    plan = dict(schema_version=1, policy='runtime-exporter-build-v1', status='prepared-unexecuted',
        metadata_plan=ref(b.m.WORK / 'planned.json'), metadata_receipt=ref(b.m.WORK / 'receipt.json'),
        metadata_independent_verification=ref(b.OWNER / '.work/runtime-exporter-metadata-independent-verification-01.json'),
        children=children, source_checkpoint=b.m.CHECKPOINT, runtime_owner=str(b.m.ROWNER), runtime_key=b.m.RKEY,
        compiler_roles=metadata['binding'], target=str(b.m.TARGET), capacity=metadata['capacity'],
        canonical_lock=metadata['canonical_lock'], wait_seconds=600, future_VM=metadata['future_VM'],
        expected_built_binaries=['rust-interp-mir-export','rust-interp-rustc-wrapper'], VM_builds=0,
        compiler_builds=0, exporter_builds=1, strip_failures_allowed=0, actual_exporter_driver_must_be_installed_R=True,
        wrapper_must_report_identical_roles=True, benchmark=False, publication=False, guest_execution=False,
        application_qualification_required_before_publication=True)
    write(b.HERE / 'plan.json', plan)
    files = dict(prior['files'])
    additions = [b.HERE / name for name in ['build.py','prepare.py','test_build.py','plan.json']]
    additions += [b.m.HERE / 'inputs.json', b.OWNER / '.work/runtime-exporter-metadata-independent-verification-01.json',
        b.OWNER / '.work/runtime-exporter-metadata-controls-independent-verification-01.json',
        b.OWNER / '.work/runtime-exporter-metadata-launch-01.actual.json',
        b.OWNER / '.work/runtime-exporter-metadata-controls-launch-01.actual.json',
        b.m.OLD / '.work/exporter-split-role-source-04/cargo_output.py']
    for directory in [b.m.WORK, b.OWNER / '.work/experiments/runtime-exporter-metadata-supervisor-01',
                      b.OWNER / '.work/runtime-exporter-metadata-controls-01',
                      b.OWNER / '.work/experiments/runtime-exporter-metadata-controls-supervisor-01']:
        additions += b.m.ordinary_files(directory)
    for path in additions:
        row = b.m.file_record(path)
        assert str(path) not in files or files[str(path)] == row['sha256']
        files[str(path)] = row['sha256']
    for path, value in files.items(): assert b.sha(path) == value, path
    frozen = dict(schema_version=1, files=files, plan_sha256=b.sha(b.HERE / 'plan.json'),
                  python=prior['python'], launch_environment=prior['launch_environment'], status='source-only-unexecuted')
    write(b.HERE / 'inputs.json', frozen)
    python = frozen['python']['path']; supervisor = b.OWNER / 'scripts/supervise_experiment.py'
    launch = dict(status='prepared-unexecuted-awaiting-root-review', owner=str(b.OWNER), environment=frozen['launch_environment'],
        command=[python, '-B', str(supervisor), '--run-id', 'runtime-exporter-build-supervisor-01', '--',
                 python, '-B', str(b.HERE / 'build.py'), '--inputs-sha256', b.sha(b.HERE / 'inputs.json')],
        helper=ref(b.HERE / 'build.py'), inputs=ref(b.HERE / 'inputs.json'), plan=ref(b.HERE / 'plan.json'),
        supervisor=ref(supervisor), python=frozen['python'], expected_children=19, capacity=plan['capacity'],
        canonical_lock=plan['canonical_lock'], wait_seconds=600, exporter_builds=1, VM_builds=0,
        compiler_builds=0, publication=False, guest_execution=False, benchmark=False)
    write(b.HERE / 'launch.json', launch)
    for name in ['build.py','prepare.py','test_build.py']: ast.parse((b.HERE / name).read_text())
    print(json.dumps(dict(launch=ref(b.HERE / 'launch.json'), helper=launch['helper'], inputs=launch['inputs'],
                         plan=launch['plan'], files=len(files)), indent=2))


if __name__ == '__main__':
    main()
