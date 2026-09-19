"""Explicit, authenticated runtime07 selection for the ordinary std CLI."""
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
from types import SimpleNamespace

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
HERE = ROOT/'experiments/runtime-std-after-installation07-01'
RUNTIME = ROOT/'experiments/runtime-native-loader-probes-01/runtime_compiler.py'
INSTALLATION = R/'.work/hir-options-hash-runtime-installation-07'
AUDIT = R/'.work/hir-options-hash-runtime-installation-independent-verification-07.json'
AUDIT_SOURCE = ROOT/'experiments/hir-options-hash-runtime-audit-12'
RUN_ID = 'hir-options-hash-runtime-std-07-01'
NAMESPACE = 'immutable-source-paths-v2:shared'
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
ORDER = ('custom_compiler', 'workflow_io', 'std_mir', 'compare_saved_runtime',
         'toolchain_lookup', 'runtime_compiler', 'custom_cargo_libraries',
         'verified_std_diagnostics', 'std_mir_source_paths')
PATHS = {name: R/'scripts'/(name+'.py') for name in ORDER}
PATHS['runtime_compiler'] = RUNTIME
PATHS['owned_stage'] = R/'experiments/stable-cgu/owned_stage.py'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def same(a, b):
    return json.dumps(a, sort_keys=True, separators=(',', ':'), allow_nan=False) == json.dumps(
        b, sort_keys=True, separators=(',', ':'), allow_nan=False)


@contextmanager
def aliases(values):
    missing = object()
    before = {name: sys.modules.get(name, missing) for name in values}
    path = list(sys.path)
    sys.modules.update(values)
    try:
        yield
    finally:
        sys.path[:] = path
        for name, value in before.items():
            if value is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


def load(name, path, check_source, dependencies=None):
    path = Path(path)
    check_source(path)
    full = '_runtime_std_after_installation07_'+name
    if full in sys.modules:
        value = sys.modules[full]
        require(Path(value.__file__).resolve(strict=True) == path, 'private std import route changed')
        return value
    spec = importlib.util.spec_from_file_location(full, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[full] = value
    try:
        with aliases(dependencies or {}):
            spec.loader.exec_module(value)
    except BaseException:
        sys.modules.pop(full, None)
        raise
    return value


def definitions(check_source):
    """Authenticate the entire finite closure before the first target import."""
    selection = HERE/'selection.json'
    check_source(selection)
    descriptor = json.loads(selection.read_bytes())
    require(descriptor['policy'] == 'runtime07-ordinary-std-module-selection-v1'
            and descriptor['owner'] == str(R)
            and set(descriptor['modules']) == set(PATHS), 'std module selection differs')
    script_paths = descriptor['ordinary_script_paths']
    require(type(script_paths) is list and len(script_paths) == 108
            and script_paths == sorted(set(script_paths))
            and all(Path(p).parent == R/'scripts' and Path(p).suffix == '.py' for p in script_paths),
            'original finite std script scope differs')
    for path in script_paths:
        check_source(Path(path))
    for name, path in PATHS.items():
        row = descriptor['modules'][name]
        require(set(row) == {'path', 'sha256'} and row['path'] == str(path)
                and check_source(path) == row['sha256'], 'selected std source differs: '+name)
    public = {}
    for name in ORDER:
        public[name] = load(name, PATHS[name], check_source, public)
    owned = load('owned_stage', PATHS['owned_stage'], check_source)
    return SimpleNamespace(public_aliases=public, runtime=public['runtime_compiler'],
        std=public['std_mir_source_paths'], cargo=public['custom_cargo_libraries'],
        toolchain=public['toolchain_lookup'], owned=owned)


def ordinary_arguments(plan):
    key = plan.get('runtime_key')
    require(type(key) is str and re.fullmatch('[0-9a-f]{64}', key) is not None,
            'std runtime key is unbound')
    return ['--runtime-compiler-key', key, '--namespace', NAMESPACE, '--run-id', RUN_ID,
            '--workload-lock', str(LOCK), '--lock-wait-seconds', '600']


def validate_plan(plan, frozen_sha):
    require(plan['status'] == 'prepared-unexecuted' and plan['owner'] == str(R)
            and plan['work'] == str(R/'.work/hir-options-hash-runtime-std-supervision-07-01')
            and plan['run_work'] == str(R/'.work'/RUN_ID)
            and plan['namespace'] == NAMESPACE, 'std plan is unbound or routes differ')
    require(type(frozen_sha) is str and re.fullmatch('[0-9a-f]{64}', frozen_sha) is not None,
            'std source freeze is unbound')
    require(same(plan['command'], ['/opt/homebrew/bin/python3', '-B', str(HERE/'std_cli.py'),
            '--frozen-sha', {'source_freeze_sha256': True}, *ordinary_arguments(plan)]),
            'std ordinary CLI command differs')
    require(plan['application_qualified'] is False and plan['benchmark'] is False
            and plan['full_presentation_qualified'] is False, 'unearned std plan scope')


def command(plan, frozen_sha):
    # The plan is itself in the freeze: its own digest must not appear in it.
    validate_plan(plan, frozen_sha)
    return [frozen_sha if type(item) is dict else item for item in plan['command']]


def runtime_proof(plan, check_source):
    """Consume the actual saved installation audit; do not replay its proof tree."""
    key = plan['runtime_key']
    prefix = R/'.work/runtime-compilers'/key
    expected = {'runtime_readiness': prefix/'ready.json',
                'runtime_admission': prefix/'admission.json',
                'runtime_qualification': prefix/'qualification.json',
                'runtime_installation_receipt': INSTALLATION/'receipt.json',
                'runtime_installation_audit': AUDIT}
    values = {}
    for name, path in expected.items():
        row = plan[name]
        require(type(row) is dict and set(row) == {'path', 'sha256'}
                and row['path'] == str(path) and type(row['sha256']) is str
                and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None,
                'std prerequisite remains unbound or route differs: '+name)
        require(check_source(path) == row['sha256'], 'std prerequisite bytes differ: '+name)
        values[name] = json.loads(path.read_bytes())
    audit = values['runtime_installation_audit']
    terminal = values['runtime_installation_receipt']
    ready = values['runtime_readiness']
    admission = values['runtime_admission']
    proof = values['runtime_qualification']
    require(audit['status'] == 'verified' and audit['phase'] == 'installation'
            and audit['saved_audit_source'] == str(AUDIT_SOURCE)
            and audit['receipt_sha256'] == plan['runtime_installation_receipt']['sha256']
            and type(audit['finished_at']) in (int, float)
            and 0 < audit['finished_at'] <= time.time(), 'actual installation audit association differs')
    phase = audit['phase_result']
    require(phase['runtime_key'] == key and phase['sysroot'] == str(prefix/'sysroot')
            and phase['ready_sha256'] == plan['runtime_readiness']['sha256']
            and phase['admission_sha256'] == plan['runtime_admission']['sha256']
            and phase['qualification_sha256'] == plan['runtime_qualification']['sha256'],
            'audited runtime publication differs')
    require(terminal['status'] == 'passed' and terminal['phase'] == 'installation'
            and terminal['runtime_key'] == terminal['installed_runtime_key'] == key
            and terminal['sysroot'] == str(prefix/'sysroot'), 'passed runtime owner differs')
    require(ready['status'] == 'installed' and ready['owner'] == str(R) and ready['key'] == key
            and ready['sysroot'] == str(prefix/'sysroot')
            and same(ready['identity']['admission'], admission)
            and proof['key'] == key and proof['owner'] == str(R), 'runtime ready/source qualification differs')
    for record in (audit, phase, terminal):
        require(all(record[name] is False for name in
                ('application_qualified', 'performance_measurement', 'exporter_qualified', 'std_mir_prepared')),
                'runtime prerequisite claims a different downstream scope')
    return dict(audit=plan['runtime_installation_audit'], runtime_key=key,
                ready=plan['runtime_readiness'], qualification=plan['runtime_qualification'])
