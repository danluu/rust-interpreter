"""Freeze current source and exact metadata children; no native metadata launch."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import metadata as m


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True); stream.write('\n')


def ref(path):
    return dict(path=str(path), sha256=m.sha(path))


def git(*args):
    child = subprocess.run(['/usr/bin/git', *args], cwd=m.OWNER, capture_output=True, check=True)
    assert not child.stderr
    return child.stdout


def main():
    assert git('rev-parse', 'HEAD').decode().strip() == m.CHECKPOINT
    bfreeze = m.read(m.BHERE / 'assembly-inputs.json')
    bplan = m.read(m.BHERE / 'plan.json')
    bmeta = m.read(m.BETA / '.work/beta-auxiliary-readmission-01/planned.json')
    old = m.read(m.OLDWORK / 'plan.json')
    runtime = m.runtime_compiler.load_runtime_compiler(m.ROWNER, m.RKEY)
    bterminal = m.BETA / '.work/beta-auxiliary-assembly-01/receipt.json'
    assert m.sha(bterminal) == 'e7ca6e60ba69c5ec2bfd66e7e24d97aa90979441401ccb77e5548dce8502ef94'
    assert m.read(bterminal)['status'] == 'passed'
    runtime_ready = m.R.parent / 'ready.json'
    assert m.sha(runtime_ready) == 'da897791f07d27bf18ef26476b8bd4e66b51b09a612345a5bc04821a892e3d21'
    assert m.sha(m.R.parent / 'qualification.json') == 'f9be945780d024fa77a2c16a5b1e9964085d4445669a42e4feb1b25731cb26b2'
    build = bmeta['probes']['build_compiler']
    d = Path(build['path'])
    driver = next(name for name in runtime.identity['files'] if name.startswith('lib/librustc_driver-'))
    private = m.BWORK / 'composition/private-sysroot.json'
    flags = ['--sysroot=' + str(m.B2), '-Lnative=' + str(m.R / 'lib'), '-Clinker=' + bplan['sdk_outputs']['clang'].strip()]
    binding = dict(schema_version=1, policy='separate-compiler-roles-v1',
        build=dict(executable=dict(path=str(d), sha256=build['sha256']), verbose_version=build['version'], default_sysroot=build['default_sysroot']),
        runtime=dict(executable=dict(path=str(runtime.rustc), sha256=runtime.identity['files']['bin/rustc']),
                     verbose_version=runtime.identity['compiler'], default_sysroot=str(m.R)),
        runtime_source_commit=runtime.identity['provenance']['source_commit'],
        runtime_driver=dict(path=str(m.R / driver), sha256=runtime.identity['files'][driver]),
        private_sysroot_manifest=ref(private), build_rustflags=flags)
    m.runtime_tools.runtime_binding(runtime, binding)
    assert m.read(private)['files']['lib/rustlib/' + m.HOST + '/lib/' + Path(driver).name] == binding['runtime_driver']['sha256']
    environment = dict(HOME='/Users/danluu', CARGO_HOME='/Users/danluu/.cargo', RUSTUP_HOME='/Users/danluu/.rustup',
        PATH=str(d.parent) + ':' + str(m.PUBLIC / 'bin') + ':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
        TMPDIR=str(m.WORK / 'tmp') + '/', LANG='C', LC_ALL='C', TZ='UTC', CARGO_TERM_COLOR='never',
        CARGO_NET_OFFLINE='true', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    environment['SDKROOT'] = old['sdk']['path']
    build_environment = environment | dict(RUSTC=str(d), RUSTDOC=str(d.with_name('rustdoc')), RUSTC_BOOTSTRAP='1',
        RUST_INTERP_COMPILER_ROLES=str(m.WORK / 'compiler-roles.json'), CARGO_ENCODED_RUSTFLAGS='\x1f'.join(flags))
    cargo_metadata = [str(m.PUBLIC / 'bin/cargo'), 'metadata', '--locked', '--offline', '--format-version=1',
                      '--manifest-path', str(m.OWNER / 'Cargo.toml')]
    build_command = [str(m.PUBLIC / 'bin/cargo'), 'build', '--release', '--locked', '--offline', '--jobs', '2', '-vv',
        '--message-format=json-render-diagnostics', '--manifest-path', str(m.OWNER / 'Cargo.toml'),
        '--target-dir', str(m.TARGET), '-p', 'rust-interp-mir-export', '--bin', 'rust-interp-mir-export',
        '--bin', 'rust-interp-rustc-wrapper']
    source_prefixes = ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', 'EXPORTER_COMPILER_ROLES.md', 'crates',
                       'tests/fixtures/borrowck-cache']
    checkout_children = []
    for argv in [['/usr/bin/git', 'rev-parse', 'HEAD'], ['/usr/bin/git', 'diff', 'HEAD', '--', *source_prefixes],
                 ['/usr/bin/git', 'ls-files', '--stage', '-z', '--', *source_prefixes]]:
        raw = git(*argv[1:])
        if argv[1] == 'diff':
            assert not raw
        checkout_children.append(dict(argv=argv, stdout_sha256=hashlib.sha256(raw).hexdigest()))
    children = []
    def append(argv, env=environment, cwd=m.OWNER):
        children.append(dict(argv=argv, environment=env, cwd=str(cwd)))
    for child in checkout_children: append(child['argv'])
    children += bplan['children'][:5]
    for _, argv in bplan['sdk_queries']: append(argv)
    for child in bplan['children'][11:21]:
        env = environment | ({'DYLD_PRINT_LIBRARIES': '1'} if child['argv'][-1] == '-vV' else {})
        append(child['argv'], env)
    old_e = bmeta['probes']['runtime_compiler']['default_sysroot']
    for child in bplan['children'][21:31]:
        argv = [word.replace(old_e, str(m.R)) for word in child['argv']]
        env = environment | ({'DYLD_PRINT_LIBRARIES': '1'} if argv[-1] == '-vV' else {})
        append(argv, env)
    support = dict(cargo=str(m.PUBLIC / 'bin/cargo'), python=bfreeze['python']['resolved'],
                   clang=bplan['sdk_outputs']['clang'].strip())
    for name, executable in support.items():
        append(['/usr/bin/otool', '-arch', 'arm64', '-L', executable])
        append(['/usr/bin/otool', '-arch', 'arm64', '-l', executable])
        if name == 'python':
            library = old['closures'][3]['identity']['libraries'][0]['logical']
            append(['/usr/bin/otool', '-arch', 'arm64', '-L', library])
            append(['/usr/bin/otool', '-arch', 'arm64', '-l', library])
    append([str(m.PUBLIC / 'bin/cargo'), '-Vv'])
    append(cargo_metadata, build_environment)
    children += bplan['children'][:5]
    for child in checkout_children: append(child['argv'])
    append(bplan['sdk_queries'][-1][1])
    records = {}
    for path, row in bplan['executors'].items(): records[path] = m.file_record(path, row['sha256'])
    for row in m.read(m.BETA / '.work/beta-auxiliary-readmission-01/current-inputs.json').values():
        records[row['path']] = dict(path=row['path'], sha256=row['sha256'], identity=row['identity'])
    for name, expected in runtime.identity['files'].items():
        if name.startswith(('bin/', 'lib/')) and 'rustlib/src/' not in name and 'rustlib/rustc-src/' not in name:
            records[str(m.R / name)] = m.file_record(m.R / name, expected)
    for closure in old['closures'][2:]:
        for item in closure['identity']['libraries']:
            records[item['resolved']] = m.file_record(item['resolved'], item['sha256'])
    for path in [*support.values(), d.with_name('rustdoc'), runtime_ready, m.R.parent / 'qualification.json']:
        records[str(Path(path).resolve(strict=True))] = m.file_record(Path(path).resolve(strict=True))
    registry, packages = {}, []
    for package in old['dependencies']['packages']:
        if package['source'] is None: continue
        source_files = []
        base = Path(package['manifest_path']).parent
        for row in package['files']:
            p = Path(row['path']); record = m.file_record(p, row['sha256']); actual = record['identity']; historical = row['stamp']
            assert historical[1] == 16777231 and actual['dev'] == 16777229
            assert [actual[k] for k in ['ino','mode','size','mtime_ns','ctime_ns']] == historical[2:7]
            registry[str(p)] = record
            if p.is_relative_to(base): source_files.append(str(p))
        assert {str(p) for p in m.ordinary_files(base)} == set(source_files)
        packages.append(dict(name=package['name'], version=package['version'], manifest_path=package['manifest_path'],
                             source_files=sorted(source_files)))
    b2 = {str(m.B2 / name): dict(path=str(m.B2 / name), sha256=row['sha256'], identity=row['identity'])
          for name, row in m.read(m.BWORK / 'composition/output-inventory.json').items()}
    for p, row in b2.items(): assert m.file_record(p) == row
    assert len(b2) == 335 and len(packages) == 26
    vm_owner = Path('/Users/danluu/dev/rust-interp')
    vm_key = 'df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
    vm_root = vm_owner / '.work/interpreter-tools' / vm_key
    vm = m.file_record(vm_root / 'rust-interp-vm', '6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf')
    records[vm['path']] = vm
    vm_diff = git('diff', '7082378a59dc85957cdf5f72985135e08f99536a', m.CHECKPOINT, '--',
                  'Cargo.toml', 'Cargo.lock', 'crates/bytecode', 'crates/function-cache', 'crates/rustc-dispatch')
    with (m.HERE / 'vm-source-diff.patch').open('xb') as stream: stream.write(vm_diff)
    changed = git('diff', '--name-only', '7082378a59dc85957cdf5f72985135e08f99536a', m.CHECKPOINT, '--',
                  'Cargo.toml', 'Cargo.lock', 'crates/bytecode', 'crates/function-cache', 'crates/rustc-dispatch').decode().splitlines()
    assert len(changed) == 24 and all(p.startswith('crates/bytecode/') for p in changed)
    vm_source = m.read(vm_root / 'source.json')
    vm_manifest = m.read(vm_root / 'ready.json')
    assert vm_source['tool_key'] == vm_key == m.runtime_compiler.digest(vm_source['composition'])
    assert vm_source['composition']['binaries'] == vm_manifest and vm_manifest['rust-interp-vm'] == vm['sha256']
    assert m.read(vm_root / 'capabilities.json')['bytecode_version'] == 5
    vm_proof = [vm_root / n for n in ['ready.json', 'source.json', 'capabilities.json']]
    vm_proof += [vm_owner / '.work/scratch-memory-values-build-02/plan.json']
    integration = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
    for name in ['scratch-memory-values-build-02', 'scratch-scalar-main-qualification-01']:
        vm_proof += [integration / 'results' / name / n for n in ['summary.json','terminal.json']]
    vm_proof.append(integration / 'results/scratch-scalar-main-qualification-01/assessment.md')
    vm_choice = dict(action='reuse-adopted-qualified-VM', source_owner=str(vm_owner), tool_key=vm_key, binary=vm,
        bytecode_version=5, source_qualification_revision='7082378a59dc85957cdf5f72985135e08f99536a',
        current_source_revision=m.CHECKPOINT, source_diff=ref(m.HERE / 'vm-source-diff.patch'), changed_paths=changed,
        assessment='The 24 path changes add test/census modules and test-gated instrumentation. '
                   'The production range planner delegates to plan_with_minimum with the unchanged minimum 8. '
                   'Serialized bytecode declarations, VM entry point and Cargo manifests are unchanged. '
                   'This reuses the historical qualified binary; it does not claim current source byte equality.',
        evidence=[ref(p) for p in vm_proof], new_VM_build=False, current_host_composed_behavior_qualification_required=True)
    routes = {path: str(Path(path).resolve(strict=True)) for path in [old['sdk']['path'], *old['sdk']['discovered'].values(),
              bplan['otool_route']['selected'], '/opt/homebrew/bin/python3']}
    crate_files = {str(p): m.sha(p) for p in m.ordinary_files(m.OWNER / 'crates')}
    config = m.configuration(); assert not any(config.values())
    plan = dict(schema_version=1, status='prepared-unexecuted', owner=str(m.OWNER), source_checkpoint=m.CHECKPOINT,
        platform=m.loaders.platform_identity(), environment=environment, build_environment=build_environment,
        binding=binding, checkout_children=checkout_children, children=children, cargo_metadata=cargo_metadata,
        historical_cargo_version=old['versions']['cargo'], allowed_cargo_version_delta='only the single os: reporting line',
        support_executables=support, records=records, registry_files=registry, registry_packages=packages,
        registry_device_transition=dict(historical=16777231,current=16777229,all_other_historical_fields_and_bytes_match=True),
        b2_files=b2, runtime_owner=str(m.ROWNER), runtime_key=m.RKEY, runtime_stamps=m.tree_stamps(m.R),
        runtime_ready=ref(runtime_ready), runtime_qualification=ref(m.R.parent / 'qualification.json'),
        b2_assembly=ref(bterminal), b2_strip=ref(bterminal.parent / 'strip-proof.json'), routes=routes,
        crate_files=crate_files, configuration=config, future_build=build_command, future_target=str(m.TARGET),
        future_VM=vm_choice, publication_owner=str(m.ROWNER), publication_namespace='.work/interpreter-tools',
        required_publication_kind=m.runtime_tools.POLICY, require_captured_exporter_and_wrapper_roles=True,
        require_zero_strip_failures=True, benchmark=False, publication=False, compiler_builds=0,
        exporter_builds=0, capacity=dict(entry_gib=16, stop_gib=9, floor_gib=8), canonical_lock=str(m.owned.CANONICAL_LOCK), wait_seconds=600)
    write(m.HERE / 'plan.json', plan)
    files = dict(bfreeze['files'])
    extra = [m.HERE / n for n in ['metadata.py','prepare.py','test_metadata.py','plan.json','vm-source-diff.patch']]
    extra += [m.BHERE / 'assembly-inputs.json', runtime_ready, m.R.parent / 'qualification.json',
              m.OLDWORK / 'plan.json', m.OLDWORK / 'plan/cargo-metadata.json', m.OLDWORK / 'run-03/commands/005/receipt.json',
              m.OLDWORK / 'run-03/commands/005/stdout', m.OLDWORK / 'run-03/commands/005/stderr', *vm_proof]
    extra += list((m.OWNER / 'scripts').glob('*.py')) + [m.OWNER / 'experiments/stable-cgu/owned_stage.py']
    extra += [m.OWNER / n for n in ['Cargo.toml','Cargo.lock','rust-toolchain.toml','EXPORTER_COMPILER_ROLES.md']]
    extra += m.ordinary_files(m.OWNER / 'crates') + m.ordinary_files(m.OWNER / 'tests/fixtures/borrowck-cache')
    for directory in [m.BETA / '.work/beta-auxiliary-assembly-01', m.BETA / '.work/experiments/beta-auxiliary-assembly-supervisor-01']:
        extra += m.ordinary_files(directory)
    extra += [m.BWORK / 'composition' / name for name in ['output-inventory.json','private-sysroot.json','proof-copies.json']]
    for path in extra:
        row = m.file_record(path); assert str(path) not in files or files[str(path)] == row['sha256']; files[str(path)] = row['sha256']
    for path, value in files.items(): assert m.sha(path) == value, path
    frozen = dict(schema_version=1, files=files, plan_sha256=m.sha(m.HERE / 'plan.json'), python=bfreeze['python'],
                  launch_environment=bfreeze['launch_environment'], status='source-only-unexecuted')
    write(m.HERE / 'inputs.json', frozen)
    python = frozen['python']['path']; supervisor = m.OWNER / 'scripts/supervise_experiment.py'
    launch = dict(status='prepared-unexecuted-awaiting-root-review', owner=str(m.OWNER), environment=frozen['launch_environment'],
        command=[python, '-B', str(supervisor), '--run-id', 'runtime-exporter-metadata-supervisor-01', '--',
                 python, '-B', str(m.HERE / 'metadata.py'), '--inputs-sha256', m.sha(m.HERE / 'inputs.json')],
        helper=ref(m.HERE / 'metadata.py'), inputs=ref(m.HERE / 'inputs.json'), plan=ref(m.HERE / 'plan.json'),
        supervisor=ref(supervisor), python=frozen['python'], expected_children=len(children),
        capacity=plan['capacity'], canonical_lock=plan['canonical_lock'], wait_seconds=600,
        exporter_builds=0, VM_builds=0, publication=False, benchmark=False)
    write(m.HERE / 'launch.json', launch)
    for name in ['metadata.py','prepare.py']: ast.parse((m.HERE / name).read_text())
    print(json.dumps(dict(launch=ref(m.HERE / 'launch.json'), files=len(files), children=len(children),
        registry_files=len(registry), crate_files=len(crate_files), runtime_files=len(runtime.identity['files'])), indent=2))


if __name__ == '__main__':
    main()
