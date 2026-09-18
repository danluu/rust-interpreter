#!/usr/bin/env python3
"""Freeze one ordinary Ruff diagnostic after the composed tools are published."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ruff_diagnostic_plan', HERE / 'run_ruff_diagnostic.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def reference(path):
    return dict(path=str(path), sha256=a.sha(path))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--publication-receipt', type=Path, required=True)
    args = parser.parse_args()
    a.require(sys.dont_write_bytecode and not sys.flags.optimize, 'Python -B required')
    sys.path.insert(0, str(a.R_OWNER / 'scripts'))
    from runtime_compiler import load_runtime_compiler
    from runtime_tools import validate_tool_runtime
    from interpreter import installed_tools
    compiler = load_runtime_compiler(a.R_OWNER, a.RUNTIME_KEY)
    tools, key = installed_tools(args.tool_key)
    validate_tool_runtime(tools, key, compiler)
    publication = json.loads((tools/'compiler.json').read_bytes())
    exporter_owner = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
    receipt_path = args.publication_receipt
    a.require(receipt_path.resolve(strict=True) == receipt_path
        and receipt_path.parent.parent == exporter_owner/'.work'
        and receipt_path.parent.name.startswith('runtime-exporter-publication-')
        and receipt_path.name == 'receipt.json', 'ordinary exporter publication receipt required')
    terminal = json.loads(receipt_path.read_bytes())
    a.require(terminal['status'] == 'passed' and terminal['policy'] == 'runtime-exporter-publication-v1'
        and terminal['publication'] and terminal['frontend_qualified'] and terminal['source_unchanged']
        and terminal['D_B2_R_unchanged'] and terminal['adopted_VM_unchanged']
        and terminal['owner'] == publication['source']['owner'] == str(exporter_owner)
        and terminal['runtime_owner'] == str(a.R_OWNER) and terminal['runtime_key'] == compiler.key
        and terminal['tool_key'] == key and terminal['published_directory'] == str(tools)
        and terminal['source_checkpoint'] == publication['source']['checkpoint']
        and len(terminal['commands']) == 23 and not terminal['guest_execution']
        and not terminal['application_qualified'] and not terminal['benchmark'],
        'publication terminal does not qualify these exact installed runtime tools')
    published_path = receipt_path.parent/'published-tools.json'
    published = json.loads(published_path.read_bytes())
    a.require(a.sha(published_path) == terminal['published_tools_sha256']
        and published['tool_key'] == key and published['directory'] == str(tools)
        and published['composition'] == publication
        and published['capabilities'] == json.loads((tools/'capabilities.json').read_bytes())
        and {name:row['destination']['sha256'] for name,row in published['copied'].items()} == publication['binaries'],
        'actual publication outputs differ from the installed tool composition')
    destination = HERE / 'ruff-diagnostic-01'
    a.require(not destination.exists(), 'fresh diagnostic plan required')
    python = Path('/opt/homebrew/bin/python3')
    native = Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin')
    developer = Path('/Applications/Xcode.app/Contents/Developer')
    xcode = developer / 'Toolchains/XcodeDefault.xctoolchain/usr/bin'
    sdk = developer / 'Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
    sdk_alias = sdk.with_name('MacOSX26.4.sdk')
    cargo_home = Path('/Users/danluu/.cargo')
    env = dict(HOME='/Users/danluu', CARGO_HOME=str(cargo_home), RUSTUP_HOME='/Users/danluu/.rustup',
        RUSTUP_TOOLCHAIN='nightly-2026-09-08', RUSTUP_DIST_SERVER='file:///dev/null', CARGO_NET_OFFLINE='true',
        PATH='/Users/danluu/.cargo/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
        DEVELOPER_DIR=str(developer), TMPDIR=str(a.WORK / 'tmp') + '/', LANG='C', LC_ALL='C', TZ='UTC',
        PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', CARGO_TERM_VERBOSE='true',
        __CF_USER_TEXT_ENCODING='0x1F5:0x0:0x0')
    executor_paths = [python, cargo_home/'bin/cargo', cargo_home/'bin/rustup', native/'bin/cargo',
        native/'bin/rustc', Path('/usr/bin/git'), Path('/bin/ps'), Path('/usr/sbin/lsof'),
        Path('/bin/sh'), Path('/usr/bin/cc'), Path('/usr/bin/clang'), Path('/usr/bin/c++'),
        Path('/usr/bin/ld'), Path('/usr/bin/ar'), Path('/usr/bin/ranlib'), Path('/usr/bin/xcrun')]
    providers = [xcode/name for name in ('clang', 'ld', 'ar', 'ranlib')]
    providers += [sdk/'SDKSettings.json', sdk/'usr/lib/libSystem.tbd',
        native/'lib/libLLVM.dylib', native/'lib/rustlib/aarch64-apple-darwin/bin/rust-objcopy',
        native/'lib/rustlib/aarch64-apple-darwin/lib/libLLVM.dylib']
    drivers = list((native/'lib').glob('librustc_driver-*.dylib'))
    a.require(len(drivers) == 1, 'exact one native rustc driver required')
    providers += drivers
    configuration_paths = [a.SOURCE/'.rust-interp-owned.json', a.SOURCE/'.git/config', a.SOURCE/'.git/HEAD',
        Path('/Users/danluu/.rustup/settings.toml')]
    for root in [a.OWNER, a.R_OWNER, a.SOURCE, a.R_OWNER/'.work/interpreter-workspaces', a.R_OWNER/'.work/runs'/a.RUN_ID]:
        configuration_paths += [ancestor/'.cargo'/name for ancestor in [root, *root.parents]
                                for name in ('config', 'config.toml')]
    configuration_paths += [cargo_home/name for name in ('config', 'config.toml')]
    configuration = {}
    for path in sorted(set(configuration_paths)):
        a.require(not path.is_symlink(), 'indirect diagnostic configuration')
        configuration[str(path)] = dict(exists=path.exists())
        if path.exists():
            a.require(path.is_file(), 'configuration must be ordinary file')
            configuration[str(path)].update(sha256=a.sha(path))
    acquisition = a.OWNER/'.work/ruff-source-acquisition-02'
    inventory = acquisition/'acquired-inventory.json'
    runtime = compiler.directory if hasattr(compiler, 'directory') else compiler.sysroot.parent
    std = a.R_OWNER/'.work/std-mir'/a.STD_KEY
    plan = dict(schema_version=1, policy='runtime-ruff-hir-diagnostic-v1', status='unexecuted',
        owner=str(a.OWNER), runtime_owner=str(a.R_OWNER), tool_key=key, runtime_composition=publication,
        tool_publication=reference(receipt_path), published_tools=reference(published_path),
        python=dict(path=str(python), resolved=str(python.resolve()), sha256=a.sha(python)),
        command=a.command(key, str(python)), environment=env, platform=list(os.uname()),
        executors={str(p):a.provider(p) for p in executor_paths},
        providers={str(p):a.provider(p) for p in providers},
        provider_directories={str(p):dict(resolved=str(p.resolve(strict=True)),
            link_text=os.readlink(p) if p.is_symlink() else None) for p in [developer, sdk, sdk_alias, native]},
        provider_scope='Selected native executors, rustc driver, LLVM/objcopy and selected Xcode SDK provider files; native tool identity also probed by ordinary workflow.',
        configuration=configuration, source_inventory=reference(inventory), source_acquisition=reference(acquisition/'receipt.json'),
        native_objcopy_static_route=reference(a.OWNER/'.work/ruff-native-provider-inspection-01/objcopy-macho.json'),
        runtime_ready=reference(runtime/'ready.json'), std_ready=reference(std/'ready.json'),
        canonical_lock=a.CANONICAL_LOCK, wait_seconds=600, lock_owner='ordinary workflow child',
        expected_workflow_commands=24, expected_native_identity_commands=8, jobs=2,
        expected_custom_flags={mode:a.flags(mode) for mode in ('baseline','candidate')},
        bounds=dict(entry_free_gib=16, active_child_stop_gib=9, running_floor_gib=8,
            retained_input_bytes=96*2**20, retained_single_input_bytes=32*2**20),
        instrumented=True, timing_scope='diagnostic only', performance_target_qualified=False,
        compatibility_scope='Existing Ruff tests using trap-unsupported-calls and run-try-callbacks; not strict unsupported-call-free readiness')
    destination.mkdir()
    write(destination/'plan.json', plan)
    files = list((a.R_OWNER/'scripts').glob('*.py'))
    files += [HERE/'run_ruff_diagnostic.py', Path(__file__).resolve(), destination/'plan.json',
        a.OWNER/'experiments/stable-cgu/owned_stage.py', a.OWNER/'scripts/supervise_experiment.py',
        a.R_OWNER/'benchmarks/corpus.json', inventory, acquisition/'receipt.json',
        a.OWNER/'.work/ruff-native-provider-inspection-01/objcopy-macho.json',
        a.OWNER/'results/runtime-ruff-source-acquisition-02/manifest.json',
        a.OWNER/'results/runtime-ruff-source-acquisition-02/summary.json',
        runtime/'ready.json', runtime/'admission.json', runtime/'qualification.json', std/'ready.json', std/'owner.json',
        tools/'ready.json', tools/'capabilities.json', tools/'compiler.json',
        receipt_path, published_path,
        python.resolve().parents[1]/'Python']
    files += [p.resolve(strict=True) for p in executor_paths]
    files += [Path(name) for name,row in configuration.items() if row['exists']]
    files = sorted(set(files))
    a.require(all(p.resolve(strict=True) == p and p.is_file() for p in files), 'ordinary frozen inputs required')
    a.require(max(p.stat().st_size for p in files) <= 32*2**20
        and sum(p.stat().st_size for p in files) <= 96*2**20, 'diagnostic input freeze exceeds bound')
    frozen = dict(schema_version=1, owner=str(a.OWNER), files={str(p):a.sha(p) for p in files})
    write(destination/'inputs.json', frozen)
    launch = dict(schema_version=1, status='unexecuted', owner=str(a.OWNER), cwd=str(a.OWNER),
        environment=env, helper=reference(HERE/'run_ruff_diagnostic.py'), plan=reference(destination/'plan.json'),
        source_freeze=reference(destination/'inputs.json'), python=plan['python'],
        command=[str(python), '-B', str(a.OWNER/'scripts/supervise_experiment.py'), '--run-id',
            'ruff-hir-diagnostic-supervisor-01', '--', str(python), '-B', str(HERE/'run_ruff_diagnostic.py'),
            '--plan', str(destination/'plan.json'), '--freeze', str(destination/'inputs.json'),
            '--freeze-sha256', a.sha(destination/'inputs.json')],
        canonical_lock=a.CANONICAL_LOCK, wait_seconds=600, bounds=plan['bounds'],
        expected_direct_children=1, expected_workflow_commands=24, expected_native_identity_commands=8,
        review_required_before_launch=True)
    write(destination/'launch.json', launch)
    print(json.dumps(dict(plan=launch['plan'], freeze=launch['source_freeze'], launch=reference(destination/'launch.json'),
        input_files=len(files), input_bytes=sum(p.stat().st_size for p in files)), indent=2))


if __name__ == '__main__':
    main()
