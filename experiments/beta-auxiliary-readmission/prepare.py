"""Freeze B2 readmission sources and known-path metadata; never run the stage."""
import ast
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

OWNER = Path('/Users/danluu/dev/rust-interp-beta-auxiliary-readmission-20260918')
HERE = OWNER / 'experiments/beta-auxiliary-readmission'
BASE = Path('/Users/danluu/dev/rust-interp-beta-auxiliary-sysroot-20260913')
EMBED = Path('/Users/danluu/dev/rust-interp-embedded-frontend-bootstrap-20260913')
EREADMIT = Path('/Users/danluu/dev/rust-interp-runtime-readmission-20260918')
PYTHON = Path('/opt/homebrew/bin/python3')
ENVIRONMENT = dict(HOME='/Users/danluu', PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
    LANG='C', LC_ALL='C', TZ='UTC', TMPDIR='/private/tmp/', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True); stream.write('\n')


def identity(path):
    value = Path(path).lstat()
    return {key: getattr(value, 'st_' + key) for key in
            ('dev', 'ino', 'size', 'mode', 'nlink', 'mtime_ns', 'ctime_ns')}


def reference(path):
    return dict(path=str(path), sha256=sha(path))


def main():
    old_freeze = read(BASE / '.work/beta-auxiliary-metadata-source-01/inputs.json')
    old_path = EMBED / '.work/embedded-frontend-compatibility-02/planned.json'
    old = read(old_path)
    assert sha(old_path) == '7af688db0a0881b22bf5257b808e921697a338bd77ae81bd8ed2ca32c3f1c029'
    report_path = BASE / '.work/beta-auxiliary-platform-review-20260918-02/report.json'
    report = read(report_path)
    assert sha(report_path) == 'a39c3d46a9287cf3e6f5adb87b959d0056146477b98d4b1f266073b47a2f7aa2'
    records = read(EMBED / '.work/embedded-frontend-input-inspection-03/read-inputs.json')
    original = old['composition']
    for row in [*old['guard_files'], *original['proofs'], original['build_compiler'], original['runtime_driver'],
                original['stamp'], *(r['file'] for r in original['private']), *(r['file'] for r in original['archives'])]:
        assert row['path'] not in records or records[row['path']] == row
        records[row['path']] = row
    assert len(records) == 2498
    current_identities = {}
    changed = {p: r for p, r in report['sdk_tools'].items() if not r['bytes_unchanged']}
    assert set(changed) == {'/usr/bin/xcode-select', '/usr/bin/xcrun', '/usr/bin/otool'}
    for path, row in records.items():
        current = identity(path)
        if path in changed:
            assert current == changed[path]['identity']
        else:
            assert row['identity']['dev'] == 16777231 and current['dev'] == 16777229
            assert {k: v for k, v in row['identity'].items() if k != 'dev'} == {k: v for k, v in current.items() if k != 'dev'}
        current_identities[path] = current

    current_E = {key: reference(EREADMIT / '.work/runtime-readmission-01' / name) for key, name in
                 [('receipt', 'receipt.json'), ('metadata', 'metadata.json'), ('components', 'components-and-stamps.json')]}
    assert current_E['receipt']['sha256'] == '5812037c34c633f5ec7bfeec1b6036e63e2cd6c988b3b51b0ba90668e3643129'
    assert current_E['metadata']['sha256'] == '8c6c0bea014190db968db192078b320379408aaa900361b9f5568d14306c00dc'
    assert current_E['components']['sha256'] == '3c7b808f830ace079f3ec5c86f53bd6e14229a75bb751f5608af35502ab9a27b'
    eplan = read(EREADMIT / 'experiments/runtime-compiler-installation/readmission-01/plan.json')
    prior = read(eplan['evidence']['stage2_plan']['path'])['previous']
    environment = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin', HOME='/Users/danluu', LANG='C', LC_ALL='C',
        TZ='UTC', TMPDIR='/private/tmp/', CARGO_BUILD_JOBS='2', CARGO_NET_OFFLINE='true',
        PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    sdk_queries = [
        ['developer', ['/usr/bin/xcode-select', '-p']],
        ['sdk', ['/usr/bin/xcrun', '--sdk', 'macosx', '--show-sdk-path']],
        ['clang', ['/usr/bin/xcrun', '--sdk', 'macosx', '--find', 'clang']],
        ['linker', ['/usr/bin/xcrun', '--sdk', 'macosx', '--find', 'ld']],
        ['clang_version', [old['sdk']['clang'], '--version']],
        ['otool', ['/usr/bin/xcrun', '--sdk', 'macosx', '--find', 'otool']],
    ]
    sdk_outputs = {key: value if key == 'clang_version' else value + '\n'
                   for key, value in report['sdk_discovered_current'].items()}
    children = []
    def append(argv, cwd=OWNER, env=environment):
        children.append(dict(argv=argv, cwd=str(cwd), environment=env))
    git = eplan['children'][:5]
    for row in git:
        append(row['argv'], row['cwd'], prior['old_plan']['environment'])
    for _, argv in sdk_queries:
        append(argv)
    old_metadata = read(old['metadata_receipt'])
    assert len(old_metadata['commands']) == 35
    for row in old_metadata['commands'][5:25]:
        argv = row['command']
        append(argv, env=environment | {'DYLD_PRINT_LIBRARIES': '1'} if argv[-1] == '-vV' else environment)
    host = 'aarch64-apple-darwin'
    old_B = Path(old['destination'])
    copy = dict(source_destination='lib/libLLVM.dylib', destination=f'lib/rustlib/{host}/lib/libLLVM.dylib')
    tool = f'lib/rustlib/{host}/bin/rust-objcopy'
    for path in [tool, copy['source_destination']]:
        append(['/usr/bin/otool', '-arch', 'arm64', '-l', str(old_B / path)])
    for row in git:
        append(row['argv'], row['cwd'], prior['old_plan']['environment'])
    append(sdk_queries[-1][1])
    assert len(children) == 39
    executors = {}
    for name in sorted({'/usr/bin/git' if row['argv'][0] == 'git' else row['argv'][0] for row in children}):
        path = Path(name)
        assert path.resolve(strict=True) == path and path.is_file() and not path.is_symlink()
        # Compiler payload hashes come from their historical content records;
        # the metadata stage performs the fresh full input reads before children.
        expected = records[name]['sha256'] if name in records and name not in changed else sha(path)
        executors[name] = dict(identity=identity(path), sha256=expected)
    selected = Path(report['sdk_discovered_current']['otool'])
    assert selected.is_symlink()
    resolved = selected.resolve(strict=True)
    route = dict(selected=str(selected), resolved=str(resolved), link_text=os.readlink(selected),
                 link_identity=identity(selected), resolved_identity=identity(resolved), resolved_sha256=sha(resolved),
                 parents={str(p): identity(p) for p in selected.parents})

    # This is the previously reviewed pure planner, evaluated without importing
    # or constructing the old runner. Only fresh destination constants differ.
    previous_source = BASE / '.work/beta-auxiliary-metadata-source-01/check.py'
    tree = ast.parse(previous_source.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'future_commands')
    debug_source = b'#[inline(never)] fn value() -> u32 { 42 }\nfn main() { println!("{}", value()); }\n'
    output = OWNER / '.work/beta-auxiliary-sysroot-01'
    scope = dict(Path=Path, hashlib=hashlib, require=lambda ok, message: None if ok else (_ for _ in ()).throw(RuntimeError(message)),
                 B2=output / 'build-sysroot', OUTPUT=output, TOOL=tool, COPY=copy,
                 LLVM_SHA='0d514b73a257a599a433ea7076945639c326cb8483cb06d0dae91d7ceebd842a', DEBUG_SOURCE=debug_source)
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(previous_source), 'exec'), scope)
    amendment = read(EMBED / '.work/embedded-frontend-compatibility-source-03/amendment.json')
    stock = SimpleNamespace(B=old_B, E=Path(old['runtime_compiler']['default_sysroot']),
        D=Path(old['build_compiler']['path']), OUTPUT_ROOT=EMBED / '.work/embedded-frontend-compatibility-smoke-02')
    future = scope['future_commands'](old, amendment['build_argv'], stock)
    plan = dict(schema_version=1, policy='beta-auxiliary-current-platform-metadata-v1', status='source-only-unexecuted',
        historical_inputs=records, current_input_identities=current_identities,
        device_transition=dict(historical_device=16777231, current_device=16777229),
        changed_system_executors=changed, current_platform=report['platform_current'],
        historical_platform=report['platform_before'], platform_delta_report=reference(report_path),
        current_E=current_E, guard_inputs=eplan['guard_inputs'], stage2_plan=eplan['evidence']['stage2_plan'],
        old_plan_sha256=eplan['old_plan_sha256'], compositor_controls=old_freeze['controls_summary'],
        children=children, sdk_queries=sdk_queries, sdk_outputs=sdk_outputs, executors=executors, otool_route=route,
        future=future, historical_launch=reference(BASE / '.work/beta-auxiliary-metadata-launch-01.json'),
        supersedes_hash_only_readiness=reference(BASE / '.work/beta-auxiliary-metadata-revalidation-20260918-01.json'),
        original_launch_still_unexecuted=True, capacity=dict(entry_gib=16, stop_gib=9, floor_gib=8),
        canonical_lock='/Users/danluu/dev/rust-interp/.work/benchmark.lock', lock_wait_seconds=600,
        compiler_builds=0, assemblies=0, benchmark=False, historical_records_changed=False)
    write(HERE / 'plan.json', plan)
    files = dict(old_freeze['files'])
    new = [HERE / name for name in ['readmit.py', 'test_readmit.py', 'prepare.py', 'plan.json']]
    new += [OWNER / 'experiments/stable-cgu/owned_stage.py', OWNER / 'scripts/supervise_experiment.py',
            BASE / '.work/beta-auxiliary-metadata-source-01/inputs.json', report_path,
            Path(report['identity_comparisons']['path']), BASE / '.work/beta-auxiliary-metadata-launch-01.json',
            BASE / '.work/beta-auxiliary-metadata-revalidation-20260918-01.json']
    new += [Path(ref['path']) for ref in current_E.values()]
    for ref in report['sdk_readonly_children']:
        new += [Path(ref['path']), Path(ref['path']).parent / 'stdout', Path(ref['path']).parent / 'stderr']
    for path in new:
        assert path.resolve(strict=True) == path and not path.is_symlink()
        value = sha(path)
        assert str(path) not in files or files[str(path)] == value
        files[str(path)] = value
    for path, expected in files.items():
        assert sha(path) == expected
    imports = sorted(set(old_freeze['import_sources']) | {str(HERE / 'readmit.py'), str(OWNER / 'experiments/stable-cgu/owned_stage.py')})
    freeze = dict(schema_version=1, files=files, import_sources=imports, snapshot_inputs=sorted(set(old_freeze['snapshot_inputs']) | set(map(str, new))),
        plan_sha256=sha(HERE / 'plan.json'), launch_environment=ENVIRONMENT,
        python=dict(path=str(PYTHON), resolved=str(PYTHON.resolve()), sha256=sha(PYTHON)),
        status='source-only-unexecuted', candidate_payload_hashing_performed=False, native_children_started=0)
    write(HERE / 'inputs.json', freeze)
    supervisor = OWNER / 'scripts/supervise_experiment.py'
    launch = dict(status='prepared-unexecuted-awaiting-root-review', owner=str(OWNER), environment=ENVIRONMENT,
        command=[str(PYTHON), '-B', str(supervisor), '--run-id', 'beta-auxiliary-readmission-supervisor-01', '--',
                 str(PYTHON), '-B', str(HERE / 'readmit.py'), '--inputs-sha256', sha(HERE / 'inputs.json')],
        helper=reference(HERE / 'readmit.py'), inputs=reference(HERE / 'inputs.json'), plan=reference(HERE / 'plan.json'),
        supervisor=reference(supervisor), python=freeze['python'], expected_native_children=39,
        capacity=plan['capacity'], canonical_lock=plan['canonical_lock'], wait_seconds=600,
        assemblies=0, compiler_builds=0, original_launch_unchanged=True, original_launch_unexecuted=True)
    write(HERE / 'launch.json', launch)
    print(json.dumps(dict(launch=reference(HERE / 'launch.json'), helper=launch['helper'],
                         inputs=launch['inputs'], plan=launch['plan'], frozen_files=len(files)), indent=2))


if __name__ == '__main__':
    main()
