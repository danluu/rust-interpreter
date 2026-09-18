"""Prepare the exact assembly/strip launch from passed metadata; no assembly."""
import ast
import hashlib
import json
from pathlib import Path

OWNER = Path('/Users/danluu/dev/rust-interp-beta-auxiliary-readmission-20260918')
HERE = OWNER / 'experiments/beta-auxiliary-readmission'
METADATA = OWNER / '.work/beta-auxiliary-readmission-01'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True); stream.write('\n')


def ref(path):
    return dict(path=str(path), sha256=sha(path))


def main():
    metadata = read(METADATA / 'planned.json')
    assert sha(METADATA / 'planned.json') == '3e1eb36ff072d13227377f4e69ce6d738c37ddeb81d51c865a2c69546060bb5b'
    assert sha(METADATA / 'receipt.json') == 'd7a399cb3b0ed74dd30387f56f94ba8ffe84d9b35aa368dd24d31b3ad2c9d505'
    assert sha(METADATA / 'current-inputs.json') == '3bac163f21aa0c3b00c130661adf156467632cb5b1ae115e0ea5c8ad4916f7ab'
    admission = read(HERE / 'plan.json')
    previous_freeze = read(HERE / 'inputs.json')
    children = list(admission['children'][:5])
    environment = admission['children'][5]['environment']
    def append(argv, env=environment):
        children.append(dict(argv=argv, cwd=str(OWNER), environment=env))
    selection = admission['sdk_queries'][-1][1]
    append(selection)
    future = metadata['future']
    for argv in future['auxiliary_declarations']:
        append(argv)
    append(future['auxiliary_version'], future['auxiliary_environment'])
    append(future['debug_build'], future['debug_environment'])
    append(future['debug_declarations'][0])
    append(future['strip'], future['strip_environment'])
    append(future['debug_declarations'][1])
    append(selection)
    children += admission['children'][:5]
    assert len(children) == 19
    plan = dict(schema_version=1, policy='beta-auxiliary-assembly-strip-v1', status='prepared-unexecuted',
        metadata_admission=ref(HERE / 'plan.json'), metadata_plan=ref(METADATA / 'planned.json'),
        metadata_receipt=ref(METADATA / 'receipt.json'), current_inputs=ref(METADATA / 'current-inputs.json'),
        metadata_independent_verification=ref(OWNER / '.work/beta-auxiliary-readmission-independent-verification-01.json'),
        children=children, destination=metadata['destination'], evidence=metadata['evidence'],
        composition_sha256=metadata['composition_sha256'], composition_files=335, private_files=256,
        payload_bytes=metadata['copy_payload_bytes'], proof_payload_bytes=metadata['proof_copy_bytes'],
        capacity=dict(entry_gib=16, stop_gib=9, floor_gib=8), canonical_lock=admission['canonical_lock'],
        wait_seconds=600, debug_source=metadata['future']['debug_source'],
        minimum_real_debug_section=['__DWARF', '__debug_info'], nondebug_section_bytes_must_be_identical=True,
        source_and_original_object_must_be_unchanged=True, object_execution=False,
        required_beta_llvm=metadata['future']['required_auxiliary_llvm'],
        stock_compiler_compatibility=False, exporter_rebuild=False, benchmark=False, publication=False)
    write(HERE / 'assembly-plan.json', plan)
    files = dict(previous_freeze['files'])
    additions = [HERE / name for name in ['assemble.py', 'test_strip.py', 'prepare_assembly.py', 'assembly-plan.json', 'inputs.json']]
    additions += [OWNER / '.work/beta-auxiliary-readmission-independent-verification-01.json',
                  OWNER / '.work/b2-readmission-controls-independent-verification-01.json',
                  OWNER / '.work/b2-readmission-controls-launch-01.actual.json',
                  OWNER / '.work/b2-readmission-launch-01.actual.json']
    for directory in [METADATA, OWNER / '.work/b2-readmission-controls-01',
                      OWNER / '.work/experiments/beta-auxiliary-readmission-supervisor-01',
                      OWNER / '.work/experiments/b2-readmission-controls-supervisor-01']:
        for path in sorted(directory.rglob('*')):
            assert not path.is_symlink()
            if path.is_file():
                additions.append(path)
    for path in additions:
        assert path.resolve(strict=True) == path and not path.is_symlink()
        value = sha(path)
        assert str(path) not in files or files[str(path)] == value
        files[str(path)] = value
    for path, value in files.items():
        assert sha(path) == value
    snapshot_inputs = [str(HERE / name) for name in ['assemble.py', 'test_strip.py', 'prepare_assembly.py', 'assembly-plan.json',
                                                  'readmit.py', 'plan.json', 'inputs.json']]
    snapshot_inputs += [str(METADATA / name) for name in ['receipt.json', 'planned.json', 'current-inputs.json']]
    frozen = dict(schema_version=1, files=files, import_sources=sorted(set(previous_freeze['import_sources']) | {str(HERE / 'assemble.py')}),
        snapshot_inputs=snapshot_inputs, plan_sha256=sha(HERE / 'assembly-plan.json'), python=previous_freeze['python'],
        launch_environment=previous_freeze['launch_environment'], status='source-only-unexecuted')
    write(HERE / 'assembly-inputs.json', frozen)
    python = frozen['python']['path']
    supervisor = OWNER / 'scripts/supervise_experiment.py'
    launch = dict(status='prepared-unexecuted-awaiting-root-review', owner=str(OWNER), environment=frozen['launch_environment'],
        command=[python, '-B', str(supervisor), '--run-id', 'beta-auxiliary-assembly-supervisor-01', '--',
                 python, '-B', str(HERE / 'assemble.py'), '--inputs-sha256', sha(HERE / 'assembly-inputs.json')],
        helper=ref(HERE / 'assemble.py'), inputs=ref(HERE / 'assembly-inputs.json'), plan=ref(HERE / 'assembly-plan.json'),
        supervisor=ref(supervisor), python=frozen['python'], capacity=plan['capacity'], canonical_lock=plan['canonical_lock'],
        wait_seconds=600, expected_children=19, assemblies=1, debug_object_compilations=1,
        compiler_builds=0, object_execution=False, exporter_rebuild=False, benchmark=False)
    write(HERE / 'assembly-launch.json', launch)
    for path in [HERE / 'assemble.py', HERE / 'test_strip.py', Path(__file__)]:
        ast.parse(path.read_text())
    print(json.dumps(dict(launch=ref(HERE / 'assembly-launch.json'), helper=launch['helper'], inputs=launch['inputs'],
        plan=launch['plan'], files=len(files)), indent=2))


if __name__ == '__main__':
    main()
