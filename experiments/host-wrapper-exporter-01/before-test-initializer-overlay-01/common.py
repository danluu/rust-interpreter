"""Finite source/provider binding for an ordinary separate-role exporter build.

Only explicit modules are imported. Old metadata02 is input data, never imported:
its historical B2 controller is not the current D2/B3/R07 provider validator.
"""
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import time
from types import SimpleNamespace

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
HERE = ROOT/'experiments/host-wrapper-exporter-01'
PREFIX = X/'.work/host-wrapper-exporter-source-01'
TARGET = X/'.work/host-wrapper-exporter-target-01'
PACKET = HERE/'packet-01'
WORK = X/'.work/host-wrapper-exporter-metadata-01'
PREPARATION = X/'.work/host-wrapper-exporter-preparation-01'
D2 = X/'.work/hir-options-hash-compiler-01/source/build/aarch64-apple-darwin/stage0'
B3 = X/'.work/hir-options-hash-compiler-01/beta-sysroot'
KEY = 'f031d981666f450f760ccf303dccba986053ec6b9a143a60f3d26680f9ac7c70'
RUNTIME = R/'.work/runtime-compilers'/KEY/'sysroot'
AUDIT = R/'.work/hir-options-hash-runtime-installation-independent-verification-07.json'
AUDIT_EXECUTION = ROOT/'.work/runtime13-saved-audit-installation-execution-01'
PRIVATE = A/'.work/hir-options-hash-beta-composition-08/assembly/private-sysroot.json'
B3_AUDIT = A/'.work/beta-composition-independent-verification-08.json'
CENSUS = X/'.work/options-hash-exporter-source-census-01.json'
OLD = X/'experiments/runtime-exporter/metadata-02/plan.json'
COMPILED = X/'.work/hir-options-hash-compiler-build-continuation-03/compiled.json'
PROVIDER_SELECTION = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/exporter-d2-b3-saved-provider-route-assessment-01.json')
SDK_PLAN = X/'experiments/hir-options-hash/compiler-metadata-03/plan.json'
CHECKPOINT = '185efda9403389fcb408100e5765306179be2cbe'
HOST = 'aarch64-apple-darwin'
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
PYTHON = '/opt/homebrew/bin/python3'
OVERLAY = HERE/'source-overlay.json'
HOST_HELPER = ROOT/'experiments/host-wrapper-opt-01/host_codegen_opt.py'
PINS = {
    str(OVERLAY): '93e2b66b101c019be5ba59c7cd16c8b8beaada43cfe0051c87ff5a12080e1f4f',
    str(CENSUS): '67137cfbe6808c240177150559331adda214003f605dbca9d45f96065030528c',
    str(OLD): '6de794d266012bce0479ff5b25894cbad7cac3ba41815bfb33a917a790541d62',
    str(PRIVATE): 'a9707c26e48cae023ed32cec4a0d119d2c80d33f1904006aab495f60b8980d4e',
    str(B3_AUDIT): '9d23767296bfbf4147d170f8138711effcfda47eb744391edf52253a3da8891d',
    str(COMPILED): 'd25af45ba1a77bcd35d11cc6a4476651614c2c33688a51fb11cd63a5ac38b572',
    str(PROVIDER_SELECTION): 'af3426b262f2f6ce9b9e6aec7d4a140232e930a53f1f4a70c102dd757abe3272',
    str(SDK_PLAN): '250b19e48b158efe78e726e78223791cb4ff55b5b5d2b9eaa59b41ba2b1727c2',
}
MODULES = {name: R/'scripts'/(name+'.py') for name in
           ('custom_compiler', 'workflow_io', 'toolchain_lookup', 'runtime_tools', 'custom_cargo_libraries')}
MODULES['runtime_compiler'] = ROOT/'experiments/runtime-native-loader-probes-01/runtime_compiler.py'
MODULES['owned_stage'] = R/'experiments/stable-cgu/owned_stage.py'
ORDER = ('custom_compiler', 'workflow_io', 'toolchain_lookup', 'runtime_compiler',
         'runtime_tools', 'custom_cargo_libraries', 'owned_stage')


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def stamp(path):
    value = Path(path).lstat()
    return [value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink]


def file(path, expected=None, *, payload=False):
    path = Path(path)
    require(path.resolve(strict=True) == path and path.is_file() and not path.is_symlink(),
            'ordinary canonical input required: '+str(path))
    before = stamp(path); digest = hashlib.sha256(); chunks = []; size = 0
    with path.open('rb') as stream:
        while block := stream.read(1024*1024):
            size += len(block); digest.update(block)
            if payload:
                require(size <= 32*2**20, 'bounded metadata/source input exceeded')
                chunks.append(block)
    require(stamp(path) == before and size == before[3], 'input changed: '+str(path))
    row = dict(path=str(path), sha256=digest.hexdigest(), bytes=size, identity=before)
    require(expected is None or row['sha256'] == expected, 'input SHA differs: '+str(path))
    return (b''.join(chunks), row) if payload else row


def read(path, expected=None):
    return json.loads(file(path, expected, payload=True)[0])


def write(path, value):
    payload = value if isinstance(value, bytes) else encoded(value)
    with Path(path).open('xb') as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    return file(path, hashlib.sha256(payload).hexdigest())


def relative(name):
    require(type(name) is str and name and not name.startswith('/')
            and str(PurePosixPath(name)) == name and '..' not in PurePosixPath(name).parts,
            'noncanonical relative input')
    return name


def tree(root):
    root = Path(root)
    require(root.resolve(strict=True) == root and root.is_dir(), 'ordinary provider root required')
    result = {}
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in sorted(directories+files):
            path = Path(parent)/name; row = stamp(path); mode = row[2]
            require(stat.S_ISDIR(mode) or stat.S_ISREG(mode), 'indirect/special tree input: '+str(path))
            if stat.S_ISREG(mode):
                result[str(path.relative_to(root))] = row
    return result


def configuration():
    directories = {Path('/Users/danluu/.cargo'), *[p/'.cargo' for p in [PREFIX, *PREFIX.parents]]}
    paths = sorted(p/name for p in directories for name in ('config', 'config.toml'))
    require(not any(p.is_symlink() for path in paths for p in path.parents), 'indirect Cargo search route')
    result = {str(p): os.path.lexists(p) for p in paths}
    require(not any(result.values()), 'unreviewed Cargo configuration in source ancestors/home')
    return result


@contextmanager
def aliases(values):
    missing = object(); before = {name: sys.modules.get(name, missing) for name in values}
    sys.modules.update(values)
    try:
        yield
    finally:
        for name, value in before.items():
            if value is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


def modules(sources):
    # All selected source bytes are authenticated before the first local import.
    require(set(MODULES.values()) <= {Path(p) for p in sources}, 'incomplete import authentication')
    for path, expected in sources.items():
        file(path, expected)
    public = {}
    for name in ORDER:
        path = MODULES[name]; private = '_exporter_runtime07_'+name
        require(private not in sys.modules, 'unexpected existing private module')
        spec = importlib.util.spec_from_file_location(private, path)
        value = importlib.util.module_from_spec(spec); sys.modules[private] = value
        with aliases(public):
            spec.loader.exec_module(value)
        public[name] = value
    return SimpleNamespace(public=public, runtime=public['runtime_compiler'],
        tools=public['runtime_tools'], loaders=public['custom_cargo_libraries'], owned=public['owned_stage'])


def audit_gate(audit_sha, execution_sha):
    for digest in (audit_sha, execution_sha):
        require(type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest), 'actual audit pin required')
    audit = read(AUDIT, audit_sha)
    execution = read(AUDIT_EXECUTION/'record.json', execution_sha)
    require(execution['status'] == 'finished' and execution['returncode'] == 0
            and execution['may_be_live'] is False and execution.get('observation_errors', []) == []
            and execution['report'] == str(AUDIT) and execution['result_sha256'] == audit_sha,
            'installation audit has no matching successful closed execution')
    for name in ('stdout', 'stderr'):
        file(AUDIT_EXECUTION/name, execution[name+'_sha256'])
    require((AUDIT_EXECUTION/'stderr').read_bytes() == b'', 'successful audit stderr differs')
    require(audit['status'] == 'verified' and audit['phase'] == 'installation'
            and audit['saved_audit_source'] == str(ROOT/'experiments/hir-options-hash-runtime-audit-13')
            and audit['phase_result']['runtime_key'] == KEY
            and audit['phase_result']['sysroot'] == str(RUNTIME), 'qualified runtime07 required')
    selection = read(PROVIDER_SELECTION, PINS[str(PROVIDER_SELECTION)])
    require(audit['inputs_sha256'] == selection['runtime07_inputs']['sha256'],
            'D2 metadata projection is not the audited runtime07 input table')
    require(execution.get('process_signals') == 0 and 'error' not in execution
            and 0 < execution['started_at'] <= execution['finished_at'] <= time.time(),
            'audit execution closure differs')
    require(audit['pid'] == execution['pid'] and audit['parent_pid'] == execution['parent_pid'],
            'audit report/closed execution process association differs')
    chronology = [execution['started_at'],execution['admitted_at'],execution['child_started_at'],
                  audit['started_at'],audit['finished_at'],execution['finished_at'],execution['canonical_released_at']]
    require(all(type(t) in (int,float) and 0 < t <= time.time() for t in chronology)
            and chronology == sorted(chronology), 'audit report/closed execution chronology differs')
    output = read(AUDIT_EXECUTION/'stdout')
    require(output == dict(status='verified',path=str(AUDIT),sha256=audit_sha),
            'actual audit stdout association differs')
    terminal_path = R/'.work/hir-options-hash-runtime-installation-07/receipt.json'
    terminal = read(terminal_path, audit['receipt_sha256'])
    require(terminal['status'] == 'passed' and terminal['installed_runtime_key'] == KEY,
            'passed installation owner differs')
    phase = audit['phase_result']
    ready = read(RUNTIME.parent/'ready.json', phase['ready_sha256'])
    admission = read(RUNTIME.parent/'admission.json', phase['admission_sha256'])
    read(RUNTIME.parent/'qualification.json', phase['qualification_sha256'])
    require(ready['key'] == KEY and ready['identity'] == admission['identity'], 'runtime publication differs')
    return dict(audit=dict(path=str(AUDIT), sha256=audit_sha),
                execution=dict(path=str(AUDIT_EXECUTION/'record.json'), sha256=execution_sha)), ready


def source_rows():
    census = read(CENSUS, PINS[str(CENSUS)])
    require(census['source_checkpoint'] == CHECKPOINT and census['files'] == 238
            and census['logical_bytes'] == 2150761
            and census['all_exact_git_blobs_and_retained_snapshots_match'] is True,
            'exact238 source census differs')
    rows = census['rows']
    require(len(rows) == 238 and sum(v['frozen_bytes'] for v in rows.values()) == 2150761,
            'exact source membership/size differs')
    for name, row in rows.items():
        relative(name)
        require(row['path'] == str(X/name) and row['retained_snapshot']['sha256'] == row['frozen_sha256'],
                'retained source association differs')
    overlay = read(OVERLAY, PINS[str(OVERLAY)])
    expected = {'crates/mir-export/src/'+n for n in
                ('host_proc_macro.rs', 'wrapper_route.rs', 'wrapper_main.rs', 'main.rs')}
    require(set(overlay) == {'policy', 'baseline_census', 'baseline_files', 'baseline_checkpoint', 'files'}
            and overlay['policy'] == 'host-wrapper-exporter-source-overlay-v1'
            and overlay['baseline_census'] == dict(path=str(CENSUS), sha256=PINS[str(CENSUS)])
            and overlay['baseline_files'] == 238 and overlay['baseline_checkpoint'] == CHECKPOINT
            and set(overlay['files']) == expected, 'exact qualified-baseline overlay required')
    for name, replacement in overlay['files'].items():
        original = rows[name]
        require(set(replacement) == {'original_sha256', 'path', 'sha256', 'bytes'}
                and replacement['original_sha256'] == original['frozen_sha256']
                and replacement['path'] == str(ROOT/'experiments/host-wrapper-opt-01'/name),
                'overlay does not match the qualified source238 donor')
        file(original['retained_snapshot']['path'], original['frozen_sha256'])
        new = file(replacement['path'], replacement['sha256'])
        require(type(replacement['bytes']) is int and new['bytes'] == replacement['bytes'],
                'overlay source length differs')
        rows[name] = dict(original, frozen_sha256=new['sha256'], frozen_bytes=new['bytes'],
                         retained_snapshot=new)
    require(len(rows) == 238, 'overlay changed ordinary source membership')
    return rows


def materialize(rows):
    require(not os.path.lexists(PREFIX) and not os.path.lexists(TARGET), 'fresh source prefix/target required')
    # Validate every selected retained byte before the first source-prefix write.
    payloads = {name: file(row['retained_snapshot']['path'], row['frozen_sha256'], payload=True)[0]
                for name, row in rows.items()}
    require(all(len(payloads[n]) == r['frozen_bytes'] for n, r in rows.items()), 'retained source size differs')
    PREFIX.mkdir()
    for name, data in payloads.items():
        path = PREFIX/name; path.parent.mkdir(parents=True, exist_ok=True); write(path, data)
    require(set(tree(PREFIX)) == set(rows), 'materialized source membership differs')
    actual = {name: file(PREFIX/name, row['frozen_sha256']) for name, row in rows.items()}
    require(all(v['identity'][6] == 1 for v in actual.values()), 'source copy is not independent')
    for row in rows.values():
        file(row['retained_snapshot']['path'], row['frozen_sha256'])
    return actual


def providers(mods, ready, old):
    """Validate qualified live inputs, with finite file membership and fresh stamps."""
    private = read(PRIVATE, PINS[str(PRIVATE)])
    audit = read(B3_AUDIT, PINS[str(B3_AUDIT)])
    require(audit['status'] == 'verified' and audit['full_B3_inventory'] is True
            and audit['B3_files'] == len(private['files']) == 335
            and private['sysroot'] == str(B3) and private['host'] == HOST,
            'qualified private335 composition differs')
    compiled = read(COMPILED, PINS[str(COMPILED)])
    d2 = {str(Path(p).relative_to(D2)): row for p, row in compiled['providers'].items()
          if Path(p).is_relative_to(D2)}
    require(len(d2) == 85 and all(set(row) == {'sha256', 'stamp'} for row in d2.values()),
            'qualified D2 file selection differs')
    selection = read(PROVIDER_SELECTION, PINS[str(PROVIDER_SELECTION)])
    d2_files = {str(Path(n).relative_to(D2)): row['sha256']
                for n, row in selection['d2_full_saved_rows'].items()}
    require(len(d2_files) == 148 and selection['d2_prepared_links'] == 0
            and all(d2_files[n] == row['sha256'] for n, row in d2.items()),
            'complete prepared D2 selection differs from the qualified85 seed')
    groups = {'D2': (D2, d2_files),
              'B3': (B3, private['files']), 'runtime': (RUNTIME, ready['identity']['files'])}
    result, memberships = {}, {}
    for name, (root, expected) in groups.items():
        actual = tree(root)
        require(set(actual) == set(expected), 'provider member set differs: '+name)
        memberships[str(root)] = actual
        for path, digest in expected.items():
            relative(path); item = root/path; result[str(item)] = file(item, digest)
    driver = next(n for n in ready['identity']['files'] if n.startswith('lib/librustc_driver-'))
    require(private['files']['lib/rustlib/'+HOST+'/lib/'+Path(driver).name]
            == ready['identity']['files'][driver], 'private/native driver identity differs')
    require(private['runtime_source_commit'] == ready['identity']['provenance']['source_commit']
            and private['build_compiler_sha256'] == result[str(D2/'bin/rustc')]['sha256'],
            'D2/B3/runtime source roles differ')
    # Current executors and SDK tools retain the already admitted byte selection;
    # no historical proof snapshots are imported as if they were live providers.
    for path, row in old['records'].items():
        if path.startswith(('/usr/bin/', '/Applications/Xcode.app/', '/opt/homebrew/')) or path == old['support_executables']['cargo']:
            result[path] = file(path, row['sha256'])
    for path, row in old['registry_files'].items():
        result[path] = file(path, row['sha256'])
    for package in old['registry_packages']:
        root = Path(package['manifest_path']).parent
        current = tree(root)
        require({str(root/p) for p in current} == set(package['source_files']), 'registry membership differs')
        memberships[str(root)] = current
    require(len(old['registry_packages']) == 26, 'ordinary registry package count differs')
    for path, target in old['routes'].items():
        require(str(Path(path).resolve(strict=True)) == target, 'SDK/executor route changed')
    compiler = mods.runtime.load_runtime_compiler(R, KEY)
    require(compiler.identity == ready['identity'] and mods.runtime.loader_probe_policy(
        compiler.identity['admission']) == dict(policy='darwin-native-loader-probe-v1',host=HOST,architecture='arm64'),
        'current native-policy runtime reader differs')
    return result, memberships, compiler


def sdk_guard(*, full=False):
    selection = read(PROVIDER_SELECTION, PINS[str(PROVIDER_SELECTION)])
    root = Path(selection['sdk_inventory_root'])
    expected = read(SDK_PLAN, PINS[str(SDK_PLAN)])['sdk_inventory']
    require(len(expected) == 49647 and root.resolve(strict=True) == root, 'SDK inventory/root differs')
    actual = {'': stamp(root)}
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in directories+files:
            path = Path(parent)/name; relative_name = str(path.relative_to(root))
            actual[relative_name] = stamp(path)
    require(set(actual) == set(expected), 'SDK complete tree membership differs')
    for name, observed in actual.items():
        row = expected[name]; path = root/name
        require(observed == row['stamp'], 'SDK input stamp changed: '+name)
        if row['kind'] == 'file':
            require(stat.S_ISREG(observed[2]), 'SDK file type changed')
            if full:
                file(path, row['sha256'])
        elif row['kind'] == 'link':
            require(stat.S_ISLNK(observed[2]) and os.readlink(path) == row['target']
                    and str(path.resolve(strict=True)) == row['resolved'], 'SDK link changed')
        else:
            require(row['kind'] == 'directory' and stat.S_ISDIR(observed[2]), 'SDK directory type changed')


def guard(plan, mods, *, full=False, allow_target=False):
    require(dict(os.environ) == plan['launch_environment'], 'metadata environment changed')
    require(mods.loaders.platform_identity() == plan['platform'] and configuration() == plan['configuration'],
            'platform/Cargo configuration changed')
    sdk_guard(full=full)
    for path, target in plan['routes'].items():
        require(str(Path(path).resolve(strict=True)) == target, 'SDK/executor route changed')
    for root, expected in plan['memberships'].items():
        require(tree(root) == expected, 'current exact provider/source membership changed: '+root)
    for path, row in plan['files'].items():
        require(stamp(path) == row['identity'], 'frozen input stamp changed: '+path)
        if full:
            require(file(path) == row, 'frozen input contents changed: '+path)
    with aliases(mods.public):
        compiler = mods.runtime.load_runtime_compiler(R, KEY)
        mods.tools.runtime_binding(compiler, plan['binding'])
    require(allow_target or not os.path.lexists(TARGET), 'metadata must not create build output')


def dependency_contract(metadata, original, source):
    expected = {(p['name'],p['version'],p['source']): p for p in original['packages']}
    packages = metadata['packages']; features = {n['id']:n['features'] for n in metadata['resolve']['nodes']}
    require(len(packages) == len(expected) == 30 and metadata['workspace_root'] == str(source)
            and {(p['name'],p['version'],p['source']) for p in packages} == set(expected),
            'ordinary thirty-package workspace differs')
    old_features = {n['id']:n['features'] for n in original['resolve']['nodes']}
    for package in packages:
        previous = expected[(package['name'],package['version'],package['source'])]
        require(features[package['id']] == old_features[previous['id']], 'dependency features changed')
        wanted = previous['manifest_path'] if package['source'] else str(source/Path(previous['manifest_path']).relative_to(X))
        require(package['manifest_path'] == wanted, 'dependency manifest root differs')
        targets=[]
        for target in previous['targets']:
            target=dict(target)
            if package['source'] is None:
                target['src_path']=str(source/Path(target['src_path']).relative_to(X))
            targets.append(target)
        require(package['targets']==targets, 'ordinary Cargo target declarations differ')
    require(set(features) == {p['id'] for p in packages}, 'dependency graph node membership differs')
    # Re-map IDs through semantic package identities, then compare every edge.
    def graph(data):
        ids = {p['id']:(p['name'],p['version'],p['source']) for p in data['packages']}
        return {ids[n['id']]: sorted((d['name'],ids[d['pkg']],json.dumps(d['dep_kinds'],sort_keys=True))
                for d in n['deps']) for n in data['resolve']['nodes']}
    require(graph(metadata) == graph(original), 'ordinary dependency edges/target kinds differ')
    def members(data, key):
        ids={p['id']:(p['name'],p['version'],p['source']) for p in data['packages']}
        return [ids[n] for n in data[key]]
    for key in ('workspace_members','workspace_default_members'):
        require(members(metadata,key)==members(original,key),'ordinary workspace membership differs')
    return dict(packages=packages, resolve=metadata['resolve'])
