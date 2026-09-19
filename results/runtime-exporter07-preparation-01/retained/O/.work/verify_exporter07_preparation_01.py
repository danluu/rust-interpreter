"""Finite saved preparation and exact238 source readback; no provider walk."""
import hashlib
import json
import os
from pathlib import Path
import stat
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
H = ROOT/'experiments/runtime-exporter-after-installation07-01'
P = H/'packet-01'
E = ROOT/'.work/runtime-exporter07-preparation-execution-02'
PREFIX = X/'.work/hir-options-hash-exporter-source-01'
WORK = X/'.work/hir-options-hash-exporter-metadata-01'
TARGET = X/'.work/hir-options-hash-exporter-target-01'
read_files = {}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def stamp(path):
    value = path.lstat()
    return [value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink]


def file(path, expected=None):
    path = Path(path)
    require(path.resolve(strict=True) == path and not path.is_symlink(), 'ordinary canonical input')
    before = stamp(path)
    require(stat.S_ISREG(before[2]) and before[3] <= 8*2**20, 'finite ordinary input')
    data = path.read_bytes()
    require(before == stamp(path), 'read changed input')
    row = dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), identity=before)
    require(expected is None or row['sha256'] == expected, 'digest differs: '+str(path))
    old = read_files.setdefault(str(path), row)
    require(old == row, 'input changed between reads')
    return data, row


def read(path, expected=None):
    return json.loads(file(path, expected)[0])


def bound(row, path):
    require(row == file(path, row['sha256'])[1], 'typed reference differs: '+str(path))


def main():
    execution = read(E/'record.json', 'f0c11937dbf6cb40fa84422a0b747f9b080e376d145162da1a0075d042a69064')
    record_path = X/'.work/hir-options-hash-exporter-preparation-01/record.json'
    record = read(record_path, '540c0c7d5d8cd4f0ade839a6ed4777051d029ccd795678afc2452cf1eb8e0c17')
    require(execution['status'] == 'finished' and execution['returncode'] == 0
            and execution['may_be_live'] is False and execution['pid'] == record['pid'] == 88145
            and execution['parent_pid'] == record['parent_pid'] == 87433
            and execution['signals'] == execution['retries'] == 0
            and record['status'] == 'passed' and 'error' not in record
            and record['compiler_calls'] == record['provider_probes'] == 0
            and record['signals'] == record['retries'] == 0, 'preparation closure differs')
    require(execution['cwd'] == record['cwd'] == str(X)
            and execution['command'][:2] == ['/opt/homebrew/bin/python3', '-B']
            and execution['command'][2:] == record['command'], 'actual process argv/cwd differs')
    times = [execution['started_at'], execution['child_started_at'], record['started_at'],
             record['admitted_at'], record['finished_at'], execution['finished_at']]
    require(all(type(t) in (int, float) and 0 < t <= time.time() for t in times)
            and times == sorted(times), 'actual closure chronology differs')
    require(read(E/'stdout', execution['stdout_sha256']) == record
            and file(E/'stderr', execution['stderr_sha256'])[0] == b'', 'raw closure differs')
    require({p.name for p in E.iterdir()} == {'record.json', 'stdout', 'stderr'}, 'outer evidence membership differs')
    require({p.name for p in record_path.parent.iterdir()} == {'record.json'}, 'preparation evidence membership differs')
    pins = dict(plan='1768d1e75f8270e6fa6b799cde6c2b49b9bd1143b0cfe215e314db2d179618c6',
        inputs='a7540502493c547f33933e608c255a1ee894b48713ce4f5227bfa5c746e2fbe8',
        launch='a95687682739bd3b04cd62af2953f061622c96f90ac54d70e0e0edb0ea0c0071',
        compiler_roles='8f91fae6e1acc30eaedb0c2ff34d7b380c5ead20352ca42b807a82b972d8935a')
    names = dict(plan='plan.json', inputs='inputs.json', launch='launch.json', compiler_roles='compiler-roles.json')
    docs = {}
    for key, name in names.items():
        docs[key] = read(P/name, pins[key]); bound(record['outputs'][key], P/name)
    require({p.name for p in P.iterdir()} == set(names.values()), 'packet membership differs')
    plan, inputs, launch, roles = (docs[k] for k in ('plan', 'inputs', 'launch', 'compiler_roles'))
    bound(inputs['plan'], P/'plan.json'); bound(launch['plan'], P/'plan.json'); bound(launch['inputs'], P/'inputs.json')
    require(roles == plan['binding'] and plan['files'][str(P/'compiler-roles.json')] == record['outputs']['compiler_roles'],
            'exact typed compiler role declaration differs')
    sources_sha = '944a06741d51536a2b33d2312794dcd517e21f5ed290fca0b0136eb7392fad4d'
    sources = read(H/'sources.json', sources_sha)
    require(sources['files'] == inputs['files'] and len(inputs['files']) == 10
            and record['sources_sha256'] == sources_sha, 'metadata source selection differs')
    source_rows = []
    for path, digest in inputs['files'].items():
        row = file(path, digest)[1]
        require(row == plan['files'][path], 'current metadata source SHA/7-stamps differ')
        source_rows.append(row)
    # Python is only associated through its saved prepared row; no binary read.
    require(inputs['python'] == plan['files'][inputs['python']['path']], 'saved executor association differs')
    require(record['runtime'] == plan['runtime_qualification']
            and record['runtime']['audit']['sha256'] == '878a1f363e6ca5e3acdcb16645c79d8412a260e8721a9fe75eacd7823a481728'
            and record['runtime']['execution']['sha256'] == '1f4d4a70657aa071fb85540f97b8ecbfeed3dcde85e340360b5065e7a3ed7d43',
            'prepared runtime closure pins differ')
    census_ref = plan['source_snapshot_census']
    census = read(census_ref['path'], census_ref['sha256'])
    require(census_ref['sha256'] == '67137cfbe6808c240177150559331adda214003f605dbca9d45f96065030528c'
            and census['source_checkpoint'] == plan['source_checkpoint'] == '185efda9403389fcb408100e5765306179be2cbe'
            and census['all_exact_git_blobs_and_retained_snapshots_match'] is True
            and plan['source_root'] == str(PREFIX), 'authoritative238 source declaration differs')
    copied = plan['source_materialization']
    require(set(copied) == set(census['rows']) and len(copied) == 238, 'source membership differs')
    actual_names = set(); directory_names = {'.'}
    for parent, directories, files in os.walk(PREFIX, followlinks=False):
        for name in directories:
            path = Path(parent)/name
            require(stat.S_ISDIR(path.lstat().st_mode) and not path.is_symlink(), 'indirect source directory')
            directory_names.add(str(path.relative_to(PREFIX)))
        for name in files:
            actual_names.add(str((Path(parent)/name).relative_to(PREFIX)))
    require(actual_names == set(copied), 'materialized source has missing/extra names')
    expected_directories = {'.'} | {str(p) for name in copied for p in Path(name).parents}
    require(directory_names == expected_directories, 'source directory membership differs')
    copied_rows = []
    for name, expected in copied.items():
        require(str(Path(name)) == name and not Path(name).is_absolute() and '..' not in Path(name).parts,
                'unsafe materialized relative source name')
        path = PREFIX/name; row = file(path, expected['sha256'])[1]; original = census['rows'][name]
        require(row == expected == plan['files'][str(path)]
                and row['identity'] == plan['memberships'][str(PREFIX)][name]
                and row['identity'][6] == 1 and row['sha256'] == original['frozen_sha256']
                and row['bytes'] == original['frozen_bytes'], 'source copy bytes/stamps/census differ')
        copied_rows.append(row)
    require(sum(r['bytes'] for r in copied_rows) == record['outputs']['source_bytes'] == 2150761
            and record['outputs']['source_files'] == 238 and len(plan['files']) == record['outputs']['current_input_files'] == 5678,
            'finite prepared census differs')
    old_path = X/'experiments/runtime-exporter/metadata-02/plan.json'
    old = read(old_path, '6de794d266012bce0479ff5b25894cbad7cac3ba41815bfb33a917a790541d62')
    sdk = []
    for item in old['children']:
        if item['argv'][0] in ('/usr/bin/xcode-select', '/usr/bin/xcrun') and item['argv'] not in sdk:
            sdk.append(item['argv'])
    sdk_pins = ['024e83842db917ed79a567b48b5f70bf468a2a914d5dc6df59f9d19c25ad3a0e',
        'b293dacde6a681ca1a0b50b99cc135ec868ee21ecbd5f79c67eafbaf51b65121',
        '083060ae79a9cc17bc69cb6166b1e16396c638b533de036324d8c6d49b77af24',
        '83b2a256356bb337f057ffb453b4e32c9d5f5f96737855843feb966c59816c88',
        '87333ea93a0a48992374ad97233aa5457fa084938a44bef51450b05122aeee58']
    require(len(sdk) == 5, 'five reviewed SDK commands required')
    schedule = []; env = plan['launch_environment']
    def add(label, command, environment=env, cwd=str(X), stdout=None):
        schedule.append(dict(label=label, command=command, cwd=cwd, environment=environment,
                             expected=[0], expected_stdout_sha256=stdout))
    for i, command in enumerate(sdk): add('sdk-'+str(i), command, stdout=sdk_pins[i])
    d2 = Path(roles['build']['default_sysroot']); runtime = Path(roles['runtime']['default_sysroot'])
    binaries = [roles['build']['executable']['path'], roles['runtime']['executable']['path'], *old['support_executables'].values()]
    native = [name for name in plan['files'] if
        (Path(name).parent in (d2/'lib', runtime/'lib')
         and (Path(name).name.startswith('librustc_driver-') or Path(name).name == 'libLLVM.dylib'))
        or name.startswith('/opt/homebrew/') and Path(name).name == 'Python']
    require(plan['loader_binaries'] == binaries and len(set(binaries+native)) == 10, 'ten native inspector inputs required')
    for name in sorted(set(binaries+native)):
        for flag in ('-L', '-l'): add('loader-'+str(len(schedule)), ['/usr/bin/otool', '-arch', 'arm64', flag, name])
    for role in ('build', 'runtime'):
        exe = roles[role]['executable']['path']
        add(role+'-version', [exe, '-vV'], env|{'DYLD_PRINT_LIBRARIES':'1'})
        add(role+'-sysroot', [exe, '--print', 'sysroot'])
    cargo = old['support_executables']['cargo']
    add('cargo-version', [cargo, '-Vv'])
    add('cargo-metadata', [cargo, 'metadata', '--locked', '--offline', '--format-version=1', '--manifest-path', str(PREFIX/'Cargo.toml')],
        plan['build_environment']|{'CARGO_TARGET_DIR':str(WORK/'cargo-target')}, str(PREFIX))
    for i, command in enumerate(sdk): add('sdk-after-'+str(i), command, stdout=sdk_pins[i])
    require(schedule == plan['children'] and len(schedule) == record['outputs']['metadata_children'] == 36,
            'exact reviewed36 command/environment/cwd/expectation schedule differs')
    require(plan['metadata_target'] == str(WORK/'cargo-target')
            and launch['status'] == 'unexecuted' and launch['cwd'] == str(X)
            and launch['environment'] == env and launch['capacity'] == plan['capacity']
                == dict(entry_gib=16, stop_gib=9, floor_gib=8)
            and launch['command'] == ['/opt/homebrew/bin/python3', '-B', str(H/'metadata.py'),
                '--inputs-sha256', pins['inputs'], '--sources-sha256', sources_sha], 'metadata launch differs')
    wanted_build = [cargo, 'build', '--release', '--locked', '--offline', '--jobs', '2', '-vv',
        '--message-format=json-render-diagnostics', '--manifest-path', str(PREFIX/'Cargo.toml'), '--target-dir', str(TARGET),
        '-p', 'rust-interp-mir-export', '--bin', 'rust-interp-mir-export', '--bin', 'rust-interp-rustc-wrapper']
    require(plan['future_build'] == dict(command=wanted_build, cwd=str(PREFIX),
        environment=plan['build_environment']|{'TMPDIR':str(X/'.work/hir-options-hash-exporter-build-01/tmp')+'/'},
        exporter_builds=1, compiler_builds=0, VM_builds=0), 'future ordinary build recipe differs')
    for path, row in read_files.items(): require(stamp(Path(path)) == row['identity'], 'read input changed at final stamp check')
    output = dict(status='verified-finite-exporter07-preparation', finished_at=time.time(),
        reader=dict(path=str(Path(__file__)),sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
        preparation_execution=read_files[str(E/'record.json')], preparation_record=read_files[str(record_path)],
        parent_pid=87433, child_pid=88145, process_closed=True, packet_pins=pins,
        source238=dict(files=238,bytes=2150761,directories=len(directory_names),rows=copied_rows),
        metadata_sources=source_rows, reviewed_schedule=schedule, child_count=36,
        child_categories=dict(sdk_before_after=10,native_loader=20,compiler_identity=4,cargo_identity_metadata=2),
        source_current_stamps_rechecked=True, saved_files=list(read_files.values()),
        provider_payload_rehash=False, provider_tree_walk=False, target_imports=False, workload_execution=False,
        metadata_or_build_success_claim=False, future_build_reviewed_not_run=True)
    destination = O/'.work/runtime-exporter07-preparation-independent-readback-01.json'
    with destination.open('x') as stream: json.dump(output,stream,sort_keys=True,indent=2);stream.write('\n')
    print(json.dumps(dict(path=str(destination),sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
        sources=238,metadata_sources=10,children=36),sort_keys=True))


if __name__ == '__main__': main()
