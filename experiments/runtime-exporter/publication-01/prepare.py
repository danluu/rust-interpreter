"""Freeze final R-owner publication after saved frontend qualification passes."""
import ast
import hashlib
import json
from pathlib import Path
import publish as p

CONTINUE_HERE = p.OWNER / 'experiments/runtime-exporter/frontend-continue-01'
CONTINUE_WORK = p.OWNER / '.work/runtime-exporter-frontend-continue-01'
RHEAD = '1d202909849c65c123c318260da4f1f49cd25131'


def ref(path):
    return dict(path=str(path), sha256=p.sha(path))


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True); stream.write('\n')


def main():
    prior = p.read(CONTINUE_HERE / 'inputs.json')
    frontend = p.read(CONTINUE_WORK / 'receipt.json')
    assert frontend['status'] == 'passed' and frontend['frontend_qualified']
    assert frontend['completed_compiler_commands_rerun'] == 0 and frontend['prior_failed_attempt_unchanged']
    metadata = p.read(p.m.WORK / 'planned.json'); built = p.read(p.b.WORK / 'built-tools.json')
    runtime_sources = {str(path): p.m.file_record(path)['sha256'] for path in sorted((p.m.ROWNER / 'scripts').rglob('*.py'))}
    source_files = dict(metadata['crate_files'])
    for name in ('Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml'):
        source_files[str(p.OWNER / name)] = p.sha(p.OWNER / name)
    composition = dict(kind=p.m.runtime_tools.POLICY, compiler_key=p.m.RKEY, compiler_sysroot=str(p.m.R),
        binaries=built['binaries'], compiler_roles=metadata['binding'],
        source=dict(owner=str(p.OWNER), checkpoint=p.m.CHECKPOINT, files=source_files,
                    metadata=ref(p.m.WORK / 'receipt.json')),
        actual_build=dict(receipt=ref(p.b.WORK / 'receipt.json'), evidence=ref(p.b.WORK / 'cargo-build-evidence.json'),
                          tools=ref(p.b.WORK / 'built-tools.json'), command=metadata['future_build'],
                          environment=metadata['build_environment'], cargo_version=metadata['actual_cargo_version'],
                          strip_failures=0),
        adopted_VM=metadata['future_VM'],
        direct_frontend=dict(failed_attempt=ref(p.f.WORK / 'receipt.json'),
            continuation=ref(CONTINUE_WORK / 'receipt.json'), results=ref(CONTINUE_WORK / 'frontend-results.json'),
            library_closures=ref(p.f.WORK / 'tool-closures.json'), compiler_commands_repeated=0),
        ordinary_launcher=dict(owner=str(p.m.ROWNER), checkpoint=RHEAD, source_files=runtime_sources),
        guest_execution_qualified=False, benchmark=False)
    key = p.m.runtime_tools.digest(composition)
    directory = p.m.ROWNER / '.work/interpreter-tools' / key
    assert not directory.exists() and not directory.is_symlink()
    env = metadata['environment']
    runtime_children = [dict(argv=['/usr/bin/git', '-C', str(p.m.ROWNER), 'rev-parse', 'HEAD'],
                             stdout_sha256=hashlib.sha256((RHEAD + '\n').encode()).hexdigest()),
                        dict(argv=['/usr/bin/git', '-C', str(p.m.ROWNER), 'diff', '--exit-code', 'HEAD', '--', 'scripts'],
                             stdout_sha256=hashlib.sha256(b'').hexdigest())]
    source_children = [dict(argv=row['argv'], cwd=str(p.m.ROWNER), environment=env) for row in runtime_children]
    validation = dict(argv=[prior['python']['path'], '-B', str(p.HERE / 'validate_installed.py'),
                           '--tool-key', key, '--runtime-compiler-key', p.m.RKEY],
                      cwd=str(p.m.ROWNER), environment=env)
    children = metadata['children'][:8] + source_children
    children += [dict(argv=[str(directory / 'rust-interp-mir-export'), '--rust-interp-capabilities'],
                      cwd=str(p.OWNER), environment=env | {'DYLD_PRINT_LIBRARIES': '1'}),
                 dict(argv=[str(directory / 'rust-interp-rustc-wrapper'), '--rust-interp-compiler-roles'],
                      cwd=str(p.OWNER), environment=env), validation]
    children += source_children + metadata['children'][44:52]
    assert len(children) == 23
    required = ['stable-cgu-partitioning', 'compiler-argv-record-v1', 'function-cache-auto',
                'inline-leaves', 'trap-unsupported-calls', 'run-try-callbacks', 'host-proc-macro-opt-v1',
                'entry-catalog', 'list-tests']
    assert set(required) <= set(built['capabilities']['export_options'])
    plan = dict(p.read(p.f.HERE / 'plan.json'))
    plan.update(policy='runtime-exporter-publication-v1', status='prepared-unexecuted', children=children,
        frontend_continuation=ref(CONTINUE_WORK / 'receipt.json'), frontend_continuation_plan=ref(CONTINUE_HERE / 'plan.json'),
        frontend_results=ref(CONTINUE_WORK / 'frontend-results.json'),
        frontend_closures=ref(p.f.WORK / 'tool-closures.json'), composition=composition, tool_key=key,
        publication_owner=str(p.m.ROWNER), publication_directory=str(directory), runtime_launcher_sources=runtime_sources,
        runtime_source_checkpoint=RHEAD, runtime_source_children=runtime_children, installed_validation=validation,
        required_export_options=required, direct_frontend_controls=0, fresh_binary_otool_commands=0,
        actual_final_binary_probes=2, actual_installed_reader_validation=1,
        namespace_lock=str(p.m.ROWNER / '.work/interpreter-tools.lock'), publication=True,
        guest_execution=False, application_qualified=False, benchmark=False)
    write(p.HERE / 'plan.json', plan)
    files = dict(prior['files'])
    additions = [p.HERE / name for name in ('publish.py', 'validate_installed.py', 'prepare.py', 'plan.json')]
    additions += [CONTINUE_HERE / 'inputs.json', CONTINUE_HERE / 'launch.json',
                  p.OWNER / '.work/runtime-exporter-frontend-continue-launch-01.actual.json',
                  p.OWNER / '.work/verify_runtime_exporter_frontend_continue_01.py',
                  p.OWNER / '.work/runtime-exporter-frontend-continue-independent-verification-01.json']
    for directory in (CONTINUE_WORK, p.OWNER / '.work/experiments/runtime-exporter-frontend-continue-supervisor-01'):
        additions += p.m.ordinary_files(directory)
    additions += [Path(path) for path in runtime_sources]
    for path in additions:
        row = p.m.file_record(path)
        assert str(path) not in files or files[str(path)] == row['sha256']
        files[str(path)] = row['sha256']
    for path, value in files.items(): assert p.sha(path) == value, path
    frozen = dict(schema_version=1, files=files, plan_sha256=p.sha(p.HERE / 'plan.json'),
                  python=prior['python'], launch_environment=prior['launch_environment'], status='source-only-unexecuted')
    write(p.HERE / 'inputs.json', frozen)
    python = frozen['python']['path']; supervisor = p.OWNER / 'scripts/supervise_experiment.py'
    launch = dict(status='prepared-unexecuted-awaiting-root-review', owner=str(p.OWNER), environment=frozen['launch_environment'],
        command=[python, '-B', str(supervisor), '--run-id', 'runtime-exporter-publication-supervisor-01', '--',
                 python, '-B', str(p.HERE / 'publish.py'), '--inputs-sha256', p.sha(p.HERE / 'inputs.json')],
        helper=ref(p.HERE / 'publish.py'), inputs=ref(p.HERE / 'inputs.json'), plan=ref(p.HERE / 'plan.json'),
        supervisor=ref(supervisor), python=frozen['python'], expected_children=23, capacity=plan['capacity'],
        canonical_lock=plan['canonical_lock'], wait_seconds=600, exporter_builds=0, VM_builds=0, compiler_builds=0,
        publication=True, publication_owner=str(p.m.ROWNER), tool_key=key, guest_execution=False, benchmark=False)
    write(p.HERE / 'launch.json', launch)
    for name in ('publish.py', 'validate_installed.py', 'prepare.py'): ast.parse((p.HERE / name).read_text())
    print(json.dumps(dict(launch=ref(p.HERE / 'launch.json'), helper=launch['helper'], inputs=launch['inputs'],
                         plan=launch['plan'], files=len(files), tool_key=key), indent=2))


if __name__ == '__main__':
    main()
