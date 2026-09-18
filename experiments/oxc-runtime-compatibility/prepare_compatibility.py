#!/usr/bin/env python3
"""Freeze Oxc compatibility only after source acquisition and actual tool publication."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import run_compatibility as a


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as output:
        json.dump(value, output, sort_keys=True, indent=2)
        output.write('\n')


def reference(path):
    return dict(path=str(path), sha256=a.sha(path))


def publication_provenance(receipt_path, tool_key, tools, compiler):
    owner = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
    a.acquisition.ordinary(receipt_path)
    run = re.fullmatch(r'runtime-exporter-publication-([0-9]{2})', receipt_path.parent.name)
    a.require(receipt_path.name == 'receipt.json' and receipt_path.parent.parent == owner/'.work' and run,
              'publication receipt is outside its recorded owner')
    stage = owner/'experiments/runtime-exporter'/('publication-' + run[1])
    terminal = a.read(receipt_path)
    expected = dict(status='passed', policy='runtime-exporter-publication-v1', publication=True,
        frontend_qualified=True, source_unchanged=True, D_B2_R_unchanged=True, adopted_VM_unchanged=True,
        owner=str(owner), runtime_owner=str(a.RROOT), runtime_key=a.RUNTIME_KEY,
        source_checkpoint='185efda9403389fcb408100e5765306179be2cbe', tool_key=tool_key,
        published_directory=str(tools), guest_execution=False, application_qualified=False, benchmark=False)
    a.require(all(terminal.get(name) == value for name, value in expected.items()) and
              tools == a.RROOT/'.work/interpreter-tools'/tool_key, 'publication is not this qualified runtime/tool route')
    plan_path, freeze_path = stage/'plan.json', stage/'inputs.json'
    a.require(a.sha(plan_path) == terminal['plan_sha256'] and a.sha(freeze_path) == terminal['inputs_sha256'],
              'publication plan/source freeze differs from terminal')
    publication_plan, frozen = a.read(plan_path), a.read(freeze_path)
    a.require(frozen['plan_sha256'] == terminal['plan_sha256'] and
              publication_plan['tool_key'] == tool_key and publication_plan['runtime_key'] == compiler.key and
              publication_plan['runtime_owner'] == str(a.RROOT) and publication_plan['publication_directory'] == str(tools),
              'publication plan selected another runtime/tool directory')
    published_path = receipt_path.parent/'published-tools.json'
    a.require(a.sha(published_path) == terminal['published_tools_sha256'], 'published tool receipt changed')
    published = a.read(published_path)
    composition, binaries, capabilities = (a.read(tools/name) for name in ['compiler.json', 'ready.json', 'capabilities.json'])
    a.require(published['tool_key'] == tool_key and published['directory'] == str(tools) and
              published['composition'] == composition == publication_plan['composition'] and
              composition['compiler_key'] == compiler.key and composition['compiler_sysroot'] == str(compiler.sysroot)
              and composition['binaries'] == binaries and published['capabilities'] == capabilities and
              set(published['copied']) == set(binaries) and published['guest_execution'] is False and
              published['benchmark'] is False, 'published tool/runtime composition differs from installed bytes')
    for name, copied in published['copied'].items():
        a.require(copied['destination']['path'] == str(tools/name) and
                  copied['destination']['sha256'] == copied['source']['sha256'] == binaries[name] == a.sha(tools/name),
                  'published destination is not the installed binary')
    commands = terminal['commands']
    a.require(len(commands) == len(publication_plan['children']) == 23 and
              published['installed_validation'] == commands[12]['path'], 'publication/installed-reader history incomplete')
    files = [receipt_path, plan_path, freeze_path, published_path]
    for observed, planned in zip(commands, publication_plan['children']):
        path = Path(observed['path'])
        a.require(path.is_relative_to(receipt_path.parent/'commands') and path.name == 'receipt.json' and
                  a.sha(path) == observed['sha256'] and observed['command'] == planned['argv'] and
                  observed['returncode'] == 0, 'publication child association differs')
        row = a.read(path)
        a.require(row['command'] == planned['argv'] and row['cwd'] == planned['cwd'] and
                  row['environment'] == planned['environment'] and row['returncode'] == 0 and row['status'] == 'finished',
                  'publication raw child differs from declared history')
        for channel in ['stdout', 'stderr']:
            raw = path.parent/channel
            a.require(a.sha(raw) == row[channel + '_sha256'], 'publication raw child bytes changed')
            files.append(raw)
        files.append(path)
    reader = Path(published['installed_validation']).parent
    a.require(a.read(reader/'stdout')['status'] == 'passed' and (reader/'stderr').read_bytes() == b'',
              'ordinary installed-tool reader did not qualify the actual route')
    return published_path, files


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--publication-receipt', type=Path, required=True)
    args = parser.parse_args()
    a.require(Path.cwd() == a.OWNER and sys.dont_write_bytecode and not sys.flags.optimize,
              'fixed owner and unoptimized Python -B required')
    output = a.HERE / 'runtime-plan-01'
    a.acquisition.absent(output)
    a.acquisition.absent(a.WORK)
    acquired = a.acquisition.WORK
    receipt = a.read(acquired / 'receipt.json')
    a.require(receipt['status'] == 'passed' and receipt['source_acquired'] and receipt['registry_packages'] == 323
              and not receipt['runtime_compatible'], 'complete source/registry acquisition required')
    a.acquisition.ordinary(args.publication_receipt)
    publication_receipt = a.read(args.publication_receipt)
    a.require(publication_receipt['status'] == 'passed', 'actual successful tool publication required')
    sys.path.insert(0, str(a.RROOT / 'scripts'))
    from runtime_compiler import load_runtime_compiler
    from runtime_tools import validate_tool_runtime
    from interpreter import installed_tools, require_export_option
    from std_mir_source_paths import load as load_std, namespace_for
    from workflow_measurements import source_states
    compiler = load_runtime_compiler(a.RROOT, a.RUNTIME_KEY)
    tools, key = installed_tools(args.tool_key)
    validate_tool_runtime(tools, key, compiler)
    published_path, publication_files = publication_provenance(args.publication_receipt, key, tools, compiler)
    require_export_option(tools, key, 'entry-catalog')
    std = a.RROOT / '.work/std-mir' / a.STD_KEY
    runtime = compiler.sysroot.parent
    python = Path('/opt/homebrew/bin/python3')
    cargo_home = Path('/Users/danluu/.cargo')
    native = Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin')
    developer = Path('/Applications/Xcode.app/Contents/Developer')
    xcode = developer / 'Toolchains/XcodeDefault.xctoolchain/usr/bin'
    sdk = developer / 'Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
    environment = dict(HOME='/Users/danluu', CARGO_HOME=str(cargo_home), RUSTUP_HOME='/Users/danluu/.rustup',
        RUSTUP_TOOLCHAIN='nightly-2026-09-08', RUSTUP_DIST_SERVER='file:///dev/null', CARGO_NET_OFFLINE='true',
        PATH='/Users/danluu/.cargo/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
        DEVELOPER_DIR=str(developer), TMPDIR=str(a.WORK / 'tmp') + '/', LANG='C', LC_ALL='C', TZ='UTC',
        PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', CARGO_TERM_VERBOSE='true',
        RUST_INTERP_LAUNCH_STATS='1', __CF_USER_TEXT_ENCODING='0x1F5:0x0:0x0', GIT_OPTIONAL_LOCKS='0')
    previous_environment = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(environment)
        selected_std = load_std(a.RROOT, a.STD_KEY, compiler,
            namespace_for('source-paths-v2-shared', 'unused'), rehash=True)
    finally:
        os.environ.clear()
        os.environ.update(previous_environment)
    a.require(selected_std[0] == std / 'sysroot' and selected_std[2] == a.STD_KEY, 'prepared std selection differs')
    executors = [python, cargo_home/'bin/cargo', cargo_home/'bin/rustup', native/'bin/cargo',
        native/'bin/rustc', Path('/usr/bin/git'), Path('/bin/ps'), Path('/usr/sbin/lsof'),
        Path('/bin/sh'), Path('/usr/bin/cc'), Path('/usr/bin/clang'), Path('/usr/bin/c++'),
        Path('/usr/bin/ld'), Path('/usr/bin/ar'), Path('/usr/bin/ranlib'), Path('/usr/bin/xcrun')]
    providers = [xcode/name for name in ('clang', 'ld', 'ar', 'ranlib')]
    providers += [sdk/'SDKSettings.json', sdk/'usr/lib/libSystem.tbd', native/'lib/libLLVM.dylib',
        native/'lib/rustlib/aarch64-apple-darwin/bin/rust-objcopy',
        native/'lib/rustlib/aarch64-apple-darwin/lib/libLLVM.dylib']
    drivers = list((native/'lib').glob('librustc_driver-*.dylib'))
    a.require(len(drivers) == 1, 'one actual stock compiler driver required')
    providers += drivers
    configuration_paths = [a.SOURCE/'.rust-interp-owned.json', a.SOURCE/'.git/config', a.SOURCE/'.git/HEAD',
                           Path('/Users/danluu/.rustup/settings.toml')]
    for root in [a.OWNER, a.RROOT, a.SOURCE, a.WORK, a.WORK/'cache/interpreter', a.WORK/'cache/jit']:
        configuration_paths += [ancestor/'.cargo'/name for ancestor in [root, *root.parents]
                                for name in ['config', 'config.toml']]
    configuration_paths += [cargo_home/name for name in ['config', 'config.toml']]
    acquisition_plan = a.read(a.acquisition.PLAN)
    for relative, proof in acquisition_plan['indexes'].items():
        path = cargo_home / relative
        for selected in proof['records']:
            a.require(a.acquisition.index_record(path, selected['name'], selected['version'], selected['checksum']) ==
                      selected['record'], 'required acquired index record changed')
        configuration_paths.append(path)
    configuration_paths += [cargo_home/'registry/index'/a.acquisition.REGISTRY/'config.json']
    configuration = {}
    for path in sorted(set(configuration_paths)):
        a.require(not path.is_symlink(), 'indirect compatibility configuration')
        configuration[str(path)] = dict(exists=path.exists())
        if path.exists():
            a.acquisition.ordinary(path)
            configuration[str(path)]['sha256'] = a.sha(path)
    case = a.read(a.CASE_PATH)['case']
    original = (a.SOURCE / case['file']).read_bytes()
    states = list(source_states(original.decode(), case, 1, ['native', 'interpreter', 'jit'], False))
    states.append(dict(state=4, source=original))
    state_hashes = [hashlib.sha256(row['source']).hexdigest() for row in states]
    native_receipt = a.OWNER / '.work/oxc-native-compatibility-02/receipt.json'
    native_proof = a.read(native_receipt)
    a.require(native_proof['status'] == 'passed' and native_proof['clean_native_performance_qualified'] and
              [row['source_sha256'] for row in native_proof['states']] == state_hashes,
              'runtime case differs from complete qualified native history')
    source_inventory = acquired / 'acquired-source-inventory.json'
    registry_inventory = acquired / 'shared-registry-checksums.json'
    a.require(a.acquisition.inventory(a.SOURCE) == a.read(source_inventory), 'acquired source changed before freeze')
    plan = dict(schema_version=1, owner=str(a.OWNER), runtime_owner=str(a.RROOT),
        policy='oxc-plugin-interpreter-jit-compatibility-v1', runtime_key=a.RUNTIME_KEY, std_key=a.STD_KEY,
        tool_key=key, runtime_composition=a.read(tools/'compiler.json'), publication=reference(args.publication_receipt),
        published_tools=reference(published_path),
        source_acquisition=reference(acquired/'receipt.json'), source_inventory=reference(source_inventory),
        registry_inventory=reference(registry_inventory), native_history=reference(native_receipt),
        python=dict(path=str(python), resolved=str(python.resolve()), sha256=a.sha(python)),
        environment=environment, platform=list(os.uname()), configuration=configuration,
        executors={str(path):a.provider(path) for path in executors},
        providers={str(path):a.provider(path) for path in providers},
        provider_directories={str(path):dict(resolved=str(path.resolve(strict=True)),
            link_text=os.readlink(path) if path.is_symlink() else None)
            for path in [developer, sdk, sdk.with_name('MacOSX26.4.sdk'), native]},
        provider_scope='Qualified runtime/std/tool bytes; selected stock compiler, Cargo, LLVM/objcopy and Xcode routes/files. SDKSettings is not a hash of every SDK header/library.',
        source_states=state_hashes, commands=a.history(key, str(python), case['tests']),
        canonical_lock='/Users/danluu/dev/rust-interp/.work/benchmark.lock', wait_seconds=600,
        expected_children=16, entry_gib=24, stop_gib=9, floor_gib=8,
        cache_limit_bytes=12*2**30, evidence_limit_bytes=2*2**30,
        benchmark=False, performance_qualified=False, application_flags=a.flags(),
        compatibility_scope='The same three unchanged Oxc tests with trap-unsupported-calls and run-try-callbacks, interpreter plus resumable JIT. Successful paths are supported; this does not establish general Rust or strict unsupported-call-free readiness.')
    output.mkdir()
    plan_path = output / 'plan.json'
    write(plan_path, plan)
    files = list((a.RROOT/'scripts').rglob('*.py'))
    files += [a.HERE/'run_compatibility.py', Path(__file__).resolve(), a.HERE/'acquire_runtime_source.py',
        a.HERE/'PREPARATION.md', plan_path, a.CASE_PATH, a.acquisition.PLAN,
        a.OWNER/'experiments/stable-cgu/owned_stage.py', a.OWNER/'experiments/oxc-plugin-normalization/registry_cache.py',
        a.OWNER/'scripts/supervise_experiment.py', source_inventory, registry_inventory, acquired/'receipt.json',
        native_receipt, *publication_files,
        runtime/'ready.json', runtime/'admission.json', runtime/'qualification.json',
        std/'ready.json', std/'owner.json', tools/'ready.json', tools/'capabilities.json', tools/'compiler.json',
        python.resolve().parents[1]/'Python']
    files += [path.resolve(strict=True) for path in executors]
    # These route bytes identify R's unchanged branch without reading or freezing
    # unrelated peers' Git references or their evolving .work trees.
    files += [Path(name) for name in acquisition_plan['runtime_files'] if not Path(name).is_relative_to(a.RROOT/'scripts')]
    # Index files may be large and are already fully content-bound in the plan;
    # retain the small actual Cargo/project configuration and ownership records.
    files += [Path(name) for name, row in configuration.items() if row['exists']
              and not Path(name).is_relative_to(cargo_home/'registry/index')]
    files = sorted(set(files))
    for path in files:
        a.acquisition.frozen_input_file(path, plan['executors'])
    a.require(max(path.stat().st_size for path in files) <= 32*2**20 and
              sum(path.stat().st_size for path in files) <= 96*2**20, 'compatibility freeze exceeds retention bound')
    freeze = dict(schema_version=1, owner=str(a.OWNER), files={str(path):a.sha(path) for path in files})
    freeze_path = output / 'inputs.json'
    write(freeze_path, freeze)
    launch = dict(owner=str(a.OWNER), cwd=str(a.OWNER), environment=environment,
        command=[str(python), '-B', str(a.OWNER/'scripts/supervise_experiment.py'), '--run-id',
            'oxc-runtime-compatibility-supervisor-01', '--', str(python), '-B', str(a.HERE/'run_compatibility.py'),
            '--plan', str(plan_path), '--freeze', str(freeze_path), '--frozen-sha256', a.sha(freeze_path)],
        plan=reference(plan_path), freeze=reference(freeze_path), expected_children=16,
        review_required_before_execution=True)
    write(output/'launch.json', launch)
    print(json.dumps(dict(plan=reference(plan_path), freeze=reference(freeze_path), launch=reference(output/'launch.json'),
                         files=len(files), bytes=sum(path.stat().st_size for path in files)), indent=2))


if __name__ == '__main__':
    main()
