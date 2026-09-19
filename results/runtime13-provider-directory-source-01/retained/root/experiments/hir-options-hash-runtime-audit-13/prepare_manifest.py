"""Source-only bounded supplemental manifest draft; no runtime admission.

The executor holds canonical and passes its descriptor. A separately reviewed
final source inventory binds the explicit integration list below.
No target module, compiler, provider, subprocess or network API is used here.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import stat
import sys
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HERE = ROOT/'experiments/hir-options-hash-runtime-audit-13'
QUALIFIED_AUDIT = ROOT/'experiments/hir-options-hash-runtime-audit-05'
ATTEMPT = ROOT/'experiments/runtime-installation-after-preflight05-03'
ROUTES_PATH = ATTEMPT/'routes.json'
ROUTES_SHA = 'd339e74a11edb948f3cf4bcc0afbbba76887cc61aed125c8bb8bf62b1633723a'
SOURCE_PREFLIGHT_SHA = 'e2ec858a1e52e6b7573807d8834673699efcdf29ccdd801a84a973322cd9179a'
ADAPTER = ATTEMPT
LOADER_SOURCE = ROOT/'experiments/runtime-native-loader-probes-01'
STARTUP_SOURCE = ROOT/'experiments/runtime04-environment-adapter-01'
LINK_SOURCE = ROOT/'experiments/runtime-frozen-link-reader-01'
LINK_CONTROL = ROOT/'experiments/runtime-frozen-link-controls-01'
LINK_RESULT = ROOT/'results/runtime-frozen-link-controls-01/result.json'


RUNTIME = X/'experiments/hir-options-hash/runtime-installation-04'
PREPARATION_LAUNCHER = ATTEMPT/'prepare_once.py'
RUNTIME_LAUNCHER = ATTEMPT/'launch.py'
CANONICAL = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
PYTHON = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
OWNED = X/'experiments/stable-cgu/owned_stage.py'
OWNED_SHA = '7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e'
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
STAMP_FIELDS = ('dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink')
POLICY = 'runtime07-installation-native-loader-saved-audit-source-manifest-v1'
# Source routes only. Reviewed source digests and the future retry-control
# proof chain must be bound independently before this draft can run.
INTEGRATION_SOURCE_PATHS = ['/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/entry.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/controller.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/audit_owner.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/routes.json',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/prepare.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/prepare_once.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/launch.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/test_installation.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime04-environment-adapter-01/environment.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-frozen-link-reader-01/links.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-frozen-link-reader-01/test_links.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-frozen-link-controls-01/run_once.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-frozen-link-controls-01/child.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-frozen-link-controls-01/plan.json',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/imports.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/test_imports.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/runtime_compiler.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/producer_recipe.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/audit_recipe.py',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/test_native_loader.py']
CORE_PATHS = tuple(HERE/name for name in ['bootstrap.py','audit.py','prepare_manifest.py','execute.py','test_completed_directories.py','test_tail.py']) + tuple(
    QUALIFIED_AUDIT/name for name in ['audit_io.py','reader.py','test_reader.py','test_audit_io.py'])
START = time.monotonic()
LAST = 0
SAMPLES = []
OBSERVED = {}

# Every non-None anchor below was read from an actual closed control execution.
# The future runtime phase itself is deliberately absent from this table.
CHAINS = (
    dict(count=53, namespace='runtime-saved-audit-controls-05',
         supervisor='runtime-saved-audit-controls-supervisor-05',
         audit='runtime-saved-audit-controls-independent-verification-05.json',
         audit_sha256='8eab665dd1cd8107ff203056decf12b54c5f0724e3332fe5f6ccdf6f61a54333',
         dispatcher='launch_runtime_saved_audit_controls_05_bounded.py',
         launcher='runtime-saved-audit-controls-launch-execution-05',
         verifier='verify_runtime_saved_audit_controls_05.py',
         executor='execute_runtime_saved_audit_controls_audit_05.py',
         execution='runtime-saved-audit-controls-verification-execution-05',
         execution_sha256='5edb4d6194804e0ffea0a95e3534f9eed9283a848bc2a3fe6fe9c84910ac29ec',
         preparation='runtime-saved-audit-controls-preparation-execution-05',
         preparation_wrapper='prepare_runtime_saved_audit_controls_05_once.py',
         preparation_sha256='9185469a998167b6f1f6b6813626d8a0a153a799e039c7d6bca1b6eb8cc8d8e0',
         tests=['test_reader.py', 'test_audit_io.py'], tested_source='hir-options-hash-runtime-audit-05'),
    dict(count=45, namespace='hir-options-hash-runtime-audit-controls-04',
         supervisor='hir-options-hash-runtime-audit-controls-supervisor-04',
         audit='hir-options-hash-runtime-audit-controls-independent-verification-04.json',
         audit_sha256='c86c5f2e33c0aeed5b67fd75256e20f47626b21bdbb494bcd4eb6b74af57b25d',
         dispatcher='launch_runtime_audit_controls_04_bounded.py',
         launcher='hir-options-hash-runtime-audit-controls-launch-execution-04',
         verifier='verify_runtime_audit_controls_04.py',
         executor='execute_runtime_audit_controls_audit_04.py',
         execution='hir-options-hash-runtime-audit-controls-verification-execution-04',
         execution_sha256='5702fde956529705c67a2d1a40fbc006f13a53d4f3cadc99abc306092a3de8a1',
         preparation='hir-options-hash-runtime-audit-controls-preparation-execution-04',
         preparation_wrapper='prepare_runtime_audit_controls_04_once.py',
         preparation_sha256='73ba8a41a9ca4010e740d7de0608b6e39ca55063fb8e23c77971885594c22481',
         tests=['test_recipe.py', 'test_preflight.py', 'test_final_runtime.py'],
         tested_source='hir-options-hash-runtime-audit-04'),
)
STARTUP_CHAIN = {
    'count': 39, 'namespace': 'runtime-startup-environment-controls-01',
    'supervisor': 'runtime-startup-environment-controls-supervisor-01',
    'audit': 'runtime-startup-environment-controls-independent-verification-01.json',
    'audit_sha256': '016e80b8169e8da75a82d29cecb3be9c0dd3e89cd6deae90b50522b927fa88f0',
    'dispatcher': 'launch_runtime_startup_environment_controls_01_bounded.py',
    'launcher': 'runtime-startup-environment-controls-launch-execution-01',
    'verifier': 'verify_runtime_startup_environment_controls_01.py',
    'executor': 'execute_runtime_startup_environment_controls_audit_01.py',
    'execution': 'runtime-startup-environment-controls-verification-execution-01',
    'execution_sha256': 'bb3e28dddbfc2c7d5307d1d3b13fb075a5c56d300ae20e2f08499df86ffd9119',
    'preparation': 'runtime-startup-environment-controls-preparation-execution-01',
    'preparation_wrapper': 'prepare_runtime_startup_environment_controls_01_once.py',
    'preparation_sha256': '619a7d568e902bbbbdc0919fe7c099a0509df0c06414912907f8e94442f89628',
    'tests': ['test_environment.py', 'test_audit_owner.py'],
    'tested_source': 'runtime04-environment-adapter-01',
}


# Future actual route/count/digests must be supplied from the closed retry packet.
RETRY_CHAIN = {
    'count': 33,
    'namespace': 'runtime-preflight-retry-controls-05',
    'audit': 'runtime-preflight-retry-controls-independent-verification-05.json',
    'audit_sha256': '65c10f5917dde90d0d03d7abd951e33c09ba076b401c6d0b00d9fbc046ff19a9',
    'execution_sha256': 'd3e9f4bb9393b3bf314c5cd5ad0525b1b632de32a43c9d66f6611547414895f9',
    'preparation_sha256': '4b49072f34b609c6a5b7adc5d9764328e62c5e02aa60ec2a9deb551073251a30',
    'supervisor': 'runtime-preflight-retry-controls-supervisor-05',
    'dispatcher': 'launch_runtime_preflight_retry_controls_05_bounded.py',
    'launcher': 'runtime-preflight-retry-controls-launcher-05',
    'verifier': 'verify_runtime_preflight_retry_controls_05.py',
    'executor': 'execute_runtime_preflight_retry_controls_audit_05.py',
    'execution': 'runtime-preflight-retry-controls-verification-execution-05',
    'preparation': 'runtime-preflight-retry-controls-preparation-execution-05',
    'preparation_wrapper': 'prepare_runtime_preflight_retry_controls_05_once.py',
    'tests': ['test_retry.py'], 'tested_source': 'runtime-preflight-retry-05',
}

PREPARATION_TABLE = {'path': '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/.work/hir-options-hash-runtime-installation-preparation-execution-07/source-rows.json',
 'record_sha256': '61fe20cc4533fdff67f6336b62bc4bd0bf324a6c5d44ef6bf207ca716e0f39ce',
 'row': {'identity': {'ctime_ns': 1789830489516653977,
                      'dev': 16777229,
                      'ino': 1057227250,
                      'mode': 33152,
                      'mtime_ns': 1789830489516653977,
                      'nlink': 1,
                      'size': 186987},
         'sha256': '93d681a9462efe3c8e52f8110ce0b5644de786342dd82a7e8f26260c375939c9',
         'size': 186987}}

# Future exact preparation-source gaps must be derived from its actual authenticated source table.
# No provider data or removed retained copies are added.
PREPARATION_EXTRA_PATHS = []
PREPARATION_EXTRA_COUNT = 0  # Actual source-table comparison must establish this separately.


LINK_COUNT = 24  # Source-derived; actual result/record/manifest must be independently bound.
LINK_PROOF = {'result_sha256': 'cfb7577f2345147a9c5f4d44b7c562d7e92e61bdcc91e7b95fbba48c8ac22497', 'record_sha256': 'a2acb45bb98cb6c3b44bddbb7b2f43331281f38aa219a14aa56ac7bddf06441c', 'manifest_sha256': 'a4380c58427d256f7e7c450752e6d724d20d528f45a6d9766f876cc6d1ebab80'}


INSTALLATION_CHAIN = {'count': 25,
 'namespace': 'runtime-installation-controls-07',
 'audit': 'runtime-installation-controls-independent-verification-07.json',
 'audit_sha256': 'f644dc4252351654dcbfea4237ab3b42e7d1df7f94555f13d6c9f8b6998b845c',
 'execution_sha256': '5f574079215d9bfa437ebabb3b3afd94f75e23747ff98a32d55ef31bdf826f64',
 'preparation_sha256': 'c2677570a8fceaa67b4964715ce008bc658c3c827a96b06cd1da670f2d2e84d5',
 'supervisor': 'runtime-installation-controls-supervisor-07',
 'dispatcher': 'launch_runtime_installation_controls_07_bounded.py',
 'launcher': 'runtime-installation-controls-launcher-07',
 'verifier': 'verify_runtime_installation_controls_07.py',
 'executor': 'execute_runtime_installation_controls_audit_07.py',
 'execution': 'runtime-installation-controls-verification-execution-07',
 'preparation': 'runtime-installation-controls-preparation-execution-07',
 'preparation_wrapper': 'prepare_runtime_installation_controls_07_once.py',
 'tests': ['test_installation.py'],
 'tested_source': 'runtime-installation-after-preflight05-02'}

NATIVE_CHAIN = {'count': 48,
 'namespace': 'runtime-installation-controls-08',
 'audit': 'runtime-installation-controls-independent-verification-08.json',
 'audit_sha256': 'a9c87c2f554f0abeaf877923c24636fce390b0f00cdf25d5117a6f902c4afa7d',
 'execution_sha256': '06f7db8da2385245e29fd4f8f1b0b947b4d44e3313bc83f3c77eb6163618192f',
 'preparation_sha256': '28e757e6eaf0397446aea4358f1170d86caa28d20717584dd7cb41798b5a103d',
 'supervisor': 'runtime-installation-controls-supervisor-08',
 'dispatcher': 'launch_runtime_installation_controls_08_bounded.py',
 'launcher': 'runtime-installation-controls-launcher-08',
 'verifier': 'verify_runtime_installation_controls_08.py',
 'executor': 'execute_runtime_installation_controls_audit_08.py',
 'execution': 'runtime-installation-controls-verification-execution-08',
 'preparation': 'runtime-installation-controls-preparation-execution-08',
 'preparation_wrapper': 'prepare_runtime_installation_controls_08_once.py',
 'tests': ['/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/test_installation.py',
           '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/test_imports.py',
           '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/test_native_loader.py'],
 'tested_source': 'runtime-installation-after-preflight05-03'}


def output_root(phase):
    require(phase in ['installation'], 'exact runtime phase')
    return ROOT/('.work/runtime13-saved-audit-'+phase+'-manifest-01')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def same(left, right):
    return encoded(left) == encoded(right)


def sha_value(value):
    require(type(value) is str and re.fullmatch('[a-f0-9]{64}', value), 'concrete SHA required')
    return value


def stamp(info):
    return {key: getattr(info, 'st_'+key) for key in FIELDS}


def guard():
    global LAST
    require(time.monotonic()-START <= 1200, 'finite 1200-second manifest read bound')
    if time.monotonic()-LAST >= 1:
        free = shutil.disk_usage(R).free
        require(free >= 9*2**30, 'live 9GiB manifest read floor')
        SAMPLES.append(dict(time=time.time(), free_bytes=free)); LAST = time.monotonic()


def raw(value, expected=None):
    """Held nofollow route, complete first identity and bounded full byte read."""
    p = Path(value)
    require(p.is_absolute() and p != Path('/') and '..' not in p.parts
            and str(p) == os.fspath(value), 'canonical input route required')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
    descriptors = [os.open('/', flags)]; links = []
    route = lambda info: (info.st_dev, info.st_ino, info.st_mode)
    try:
        for name in p.parts[1:-1]:
            parent = descriptors[-1]; before = os.stat(name, dir_fd=parent, follow_symlinks=False)
            require(stat.S_ISDIR(before.st_mode), 'ordinary input ancestor')
            child = os.open(name, flags, dir_fd=parent); descriptors.append(child)
            require(route(os.fstat(child)) == route(before), 'input ancestor replaced at open')
            links.append((parent, name, child, route(before)))
        parent = descriptors[-1]; before = stamp(os.stat(p.name, dir_fd=parent, follow_symlinks=False))
        require(stat.S_ISREG(before['mode']) and 0 <= before['size'] <= 8*2**20,
                'ordinary input within complete 8MiB bound required')
        fd = os.open(p.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            require(same(stamp(os.fstat(stream.fileno())), before), 'opened leaf differs')
            parts = []; count = 0
            while True:
                chunk = stream.read(2**20)
                if not chunk:
                    break
                count += len(chunk); require(count <= 8*2**20, 'input grew beyond bound')
                parts.append(chunk); guard()
            guard(); require(same(stamp(os.fstat(stream.fileno())), before), 'read leaf changed')
        require(same(stamp(os.stat(p.name, dir_fd=parent, follow_symlinks=False)), before), 'named leaf changed')
        for parent, name, child, saved in links:
            require(route(os.fstat(child)) == saved and
                    route(os.stat(name, dir_fd=parent, follow_symlinks=False)) == saved, 'input route changed')
        data = b''.join(parts)
        row = dict(size=len(data), sha256=hashlib.sha256(data).hexdigest(), identity=before)
        require(len(data) == before['size'] and (expected is None or row['sha256'] == sha_value(expected)),
                'exact input bytes differ')
        require(str(p) not in OBSERVED or same(OBSERVED[str(p)], row), 'input changed after first observation')
        OBSERVED.setdefault(str(p), row)
        require(len(OBSERVED) <= 368 and sum(r['size'] for r in OBSERVED.values()) <= 8*2**20,
                'complete supplemental table exceeds 368 rows or 8MiB')
        return data
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


def read(value, expected=None):
    def unique(pairs):
        result = {}
        for key, item in pairs:
            require(key not in result, 'duplicate input JSON key'); result[key] = item
        return result
    return json.loads(raw(value, expected), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def sha(value, expected=None):
    raw(value, expected)
    return OBSERVED[str(value)]['sha256']


def finished(value):
    require(value['status'] == 'finished' and type(value['returncode']) is int and value['returncode'] == 0
            and value['started_at'] <= value['finished_at'] and type(value['pid']) is int and value['pid'] > 0,
            'explicit actual closed successful child required')
    require(not any(key in value for key in ['execution_error', 'initial_child_publication_error'])
            and value.get('observation_errors', []) == [] and value.get('may_be_live', False) is False,
            'actual closure retained an error or unresolved child')


def streams(directory, record):
    for name in ['stdout', 'stderr']:
        require(sha(directory/name) == record[name+'_sha256'], 'saved raw stream differs')


def control_chain(spec):
    """Authenticate fixed original proof paths; never scan a workspace tree."""
    count = spec['count']; source = ROOT/'experiments'/spec['namespace']; work = ROOT/'.work'/spec['namespace']
    outer = ROOT/'.work/experiments'/spec['supervisor']; launcher = ROOT/'.work'/spec['launcher']
    execution = ROOT/'.work'/spec['execution']; preparation = ROOT/'.work'/spec['preparation']
    audit_path = ROOT/'.work'/spec['audit']; verifier = ROOT/'.work'/spec['verifier']
    audit = read(audit_path, spec['audit_sha256']); e = read(execution/'record.json', spec['execution_sha256'])
    p = read(preparation/'record.json', spec['preparation_sha256']); finished(e); finished(p)
    streams(execution, e); streams(preparation, p)
    require(sha(verifier) == sha(execution/'source.py') == e['source_sha256'] == audit['verifier_sha256']
            and sha(ROOT/'.work'/spec['executor']) == sha(execution/'execution.py') == e['execution_source_sha256'],
            'actual independent auditor and executor source association differs')
    require(e['command'] == [str(PYTHON), '-B', str(verifier)] and e['cwd'] == str(ROOT)
            and same(e['verified_output'], dict(path=str(audit_path), sha256=spec['audit_sha256'],
                                               receipt_sha256=audit['receipt_sha256'])),
            'actual audit output/command association differs')
    require(read(execution/'stdout') == e['verified_output'] and raw(execution/'stderr') == b'',
            'actual auditor output or stderr differs')
    require(sha(ROOT/'.work'/spec['preparation_wrapper']) == sha(preparation/'source/execution.py')
            == p['execution_source_sha256'] and sha(preparation/'source/owned_stage.py') == sha(OWNED, OWNED_SHA)
            == p['owned_source_sha256'], 'actual preparer source association differs')
    freeze = read(source/'inputs.json'); launch = read(source/'launch.json'); terminal = read(work/'receipt.json')
    result = read(work/'result.json'); o = read(outer/'status.json'); l = read(launcher/'record.json')
    require(type(freeze['files']) is dict and 0 < len(freeze['files']) <= 256, 'bounded frozen source table')
    for name, row in freeze['files'].items():
        sha(name, row['sha256'])
        require(same([OBSERVED[name]['identity'][key] for key in STAMP_FIELDS], row['stamp']),
                'complete actual frozen identity differs')
    for name, target in freeze['routes'].items():
        require(str(Path(name).resolve(strict=True)) == target, 'actual interpreter route differs')
    for name in ['run.py', 'prepare.py', 'child.py']:
        require(sha(source/name) == sha(preparation/'source'/name) == p['source_sha256'][name],
                'retained actual harness source differs')
    require(p['command'] == [str(PYTHON), '-B', str(source/'prepare.py')] and p['cwd'] == str(ROOT)
            and p['canonical_lock'] == str(CANONICAL) and p['wait_seconds'] == 600
            and p['canonical_released_at'] <= terminal['started_at'], 'actual preparation closure association differs')
    require(same(p['prepared_packet'], dict(status='prepared-unrun', files=len(freeze['files']),
            bytes=sum(row['stamp'][3] for row in freeze['files'].values()), controls=count,
            inputs_sha256=sha(source/'inputs.json'), launch_sha256=sha(source/'launch.json'))),
            'actual prepared packet differs')
    require(terminal['status'] == result['status'] == 'passed' and audit['status'] == 'verified'
            and all(type(value) is int and value == count for value in
                    [terminal['controls_passed'], result['tests_run'], audit['controls'], launch['controls']])
            and terminal['inputs_sha256'] == launch['inputs_sha256'] == sha(source/'inputs.json')
            and terminal['result_sha256'] == audit['result_sha256'] == sha(work/'result.json')
            and audit['receipt_sha256'] == sha(work/'receipt.json'), 'actual count/result/source proof differs')
    require(all(type(result[key]) is int and result[key] == 0 for key in
                ['failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes', 'child_processes', 'compiler_calls']),
            'actual controls include failure, omission or unexpected child')
    tests = [ROOT/'experiments'/spec['tested_source']/name for name in spec['tests']]; names = []
    for path in tests:
        require(str(path) in freeze['files'], 'unqualified test source')
        for cls in ast.parse(raw(path), filename=str(path)).body:
            if isinstance(cls, ast.ClassDef):
                names.extend(path.stem+'.'+cls.name+'.'+method.name for method in cls.body
                             if isinstance(method, ast.FunctionDef) and method.name.startswith('test_'))
    require(len(names) == len(set(names)) == count and sorted(names) == freeze['expected_names']
            == result['expected_names'] == sorted(audit['exact_names']), 'actual AST-derived names differ')
    child = read(work/'command/receipt.json'); streams(work/'command', child)
    require(same(terminal['commands'], [dict(path=str(work/'command/receipt.json'), pid=child['pid'],
                                            sha256=sha(work/'command/receipt.json'))])
            and child['status'] == 'finished' and type(child['returncode']) is int and child['returncode'] == 0
            and same(child['command'], freeze['command']) and same(child['environment'], freeze['environment'])
            and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid']
            and terminal['admitted_at'] <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
            'actual one-child raw command association differs')
    require(same(audit['raw_sha256'], {name: sha(work/'command'/name) for name in ['stdout', 'stderr']}),
            'actual child audit raw differs')
    raw_names = re.findall(r'^test_[^ ]+ \(([^)]+)\) \.\.\. ok$', raw(work/'command/stderr').decode(), re.MULTILINE)
    require(sorted(raw_names) == sorted(names) and raw(work/'command/stdout') == b'', 'actual control raw names differ')
    require(o['status'] == 'finished' and type(o['returncode']) is int and o['returncode'] == 0
            and o['child_pid'] == terminal['pid'] and o['supervisor_pid'] == terminal['parent_pid']
            and o['command'] == launch['command'][6:] and o['cwd'] == launch['owner'] == str(ROOT)
            and o['plan_sha256'] == sha(outer/'plan.json') and o['log_sha256'] == sha(outer/'command.log')
            and o['child_started_at'] <= terminal['started_at'] <= terminal['finished_at'] <= o['finished_at'],
            'actual complete outer closure differs')
    streams(launcher, l)
    require(l['status'] == 'terminal-observed' and type(l['returncode']) is int and l['returncode'] == 0
            and type(l['launcher_returncode']) is int and l['launcher_returncode'] == 0
            and l['launch_sha256'] == sha(source/'launch.json') and l['launch_path'] == str(source/'launch.json')
            and l['command'] == launch['command'] and same(l['environment'], launch['environment'])
            and l['cwd'] == str(ROOT) and l['outer_sha256'] == audit['outer_sha256'] == sha(outer/'status.json')
            and audit['launcher_sha256'] == sha(launcher/'record.json')
            and l['launcher_source_path'] == str(ROOT/'.work'/spec['dispatcher'])
            and l['launcher_source_sha256'] == sha(ROOT/'.work'/spec['dispatcher'])
            and o['finished_at'] == l['finished_at'] <= l['terminal_observed_at'] <= e['started_at'],
            'actual dispatcher/outer/auditor association differs')
    handoff = read(launcher/'stdout')
    require(handoff['directory'] == str(outer) and handoff['supervisor_pid'] == o['supervisor_pid']
            == l['supervisor_pid'] and l['controller_pid'] == terminal['pid'] and raw(launcher/'stderr') == b'',
            'actual launcher raw handoff differs')
    if count in [53, 39] or spec['namespace'] in [RETRY_CHAIN['namespace'],INSTALLATION_CHAIN['namespace'],NATIVE_CHAIN['namespace']]:
        require(l['observation_errors'] == [] and l['wrapper_may_be_live'] is False
                and l['actual_task_may_be_live'] is False and e['observation_errors'] == []
                and p['observation_errors'] == [], 'actual53 corrected observer retained an error')
    require(same(e['environment'], freeze['environment']) and same(p['environment'], freeze['environment']),
            'saved control environment was relabeled')
    return dict(controls=count, audit=dict(path=str(audit_path), sha256=spec['audit_sha256']),
                preparation=dict(path=str(preparation/'record.json'), sha256=spec['preparation_sha256']),
                execution=dict(path=str(execution/'record.json'), sha256=spec['execution_sha256']),
                receipt_sha256=sha(work/'receipt.json'), result_sha256=sha(work/'result.json'))


def frozen_link_controls(reference, *, read_json, read_bytes, sha, identity):
    """Authenticate the direct real-filesystem controls, not reader.controls."""
    require(type(LINK_COUNT) is int and LINK_COUNT == 24
        and all(type(value) is str and re.fullmatch('[a-f0-9]{64}', value)
                for value in LINK_PROOF.values()), 'actual frozen-link controls remain unbound')
    output = LINK_RESULT.parent
    require(same(reference, dict(path=str(LINK_RESULT), sha256=LINK_PROOF['result_sha256']))
        and sha(LINK_RESULT) == reference['sha256'], 'exact actual frozen-link result required')
    result = read_json(LINK_RESULT)
    require(result['status'] == 'verified-frozen-link-controls' and type(result['tests']) is int
        and result['tests'] == LINK_COUNT and result['source_unchanged'] is True
        and type(result['compiler_calls']) is int and result['compiler_calls'] == 0
        and all(result[key] is False for key in ['network','provider_writes','canonical_lock_access','runtime_audit_qualified'])
        and type(result['owned_bytes']) is int and 0 <= result['owned_bytes'] <= 8*2**20,
        'complete successful direct control result required')
    def check_row(path, row):
        require(type(row) is dict and set(row) == {'bytes','sha256','identity'}
            and type(row['bytes']) is int and 0 <= row['bytes'] <= 64*2**20
            and type(row['identity']) is dict and set(row['identity']) ==
                {'dev','ino','mode','nlink','size','mtime_ns','ctime_ns'}
            and all(type(v) is int for v in row['identity'].values())
            and sha(path) == row['sha256'] and same(identity(path), row['identity'])
            and row['bytes'] == row['identity']['size'], 'actual control byte/identity row differs')
    refs = dict(record=output/'record.json',source_before=output/'source-before.json',
        source_after=output/'source-after.json',stdout=output/'stdout',stderr=output/'stderr',plan=LINK_CONTROL/'plan.json')
    for key,path in refs.items():
        require(type(result[key]) is dict and set(result[key]) == {'path','sha256'}
            and result[key]['path'] == str(path) and sha(path) == result[key]['sha256'],
            'exact direct control closure reference differs')
    require(result['record']['sha256'] == LINK_PROOF['record_sha256']
        and sha(output/'manifest.json') == LINK_PROOF['manifest_sha256'], 'actual direct control closure anchors differ')
    manifest = read_json(output/'manifest.json')
    members = {'run_once.py','child.py','plan.json','started.json','record.json','source-before.json',
               'source-after.json','stdout','stderr','result.json'}
    require(set(manifest) == members and {p.name for p in output.iterdir()} == members|{'manifest.json','tmp'}
        and stat.S_ISDIR((output/'tmp').lstat().st_mode) and not list((output/'tmp').iterdir()),
        'complete direct control output membership differs')
    for name,row in manifest.items(): check_row(output/name,row)
    record = read_json(output/'record.json'); started = read_json(output/'started.json')
    plan = read_json(LINK_CONTROL/'plan.json')
    before = read_json(output/'source-before.json'); after = read_json(output/'source-after.json')
    require(same(before,after) and same(before,result['sources']), 'control sources changed before/after')
    python = str(Path('/opt/homebrew/bin/python3').resolve(strict=True))
    expected_sources = {str(LINK_SOURCE/'links.py'),str(LINK_SOURCE/'test_links.py'),
        str(LINK_CONTROL/'run_once.py'),str(LINK_CONTROL/'child.py'),str(LINK_CONTROL/'plan.json'),python}
    require(set(before) == expected_sources and plan['python_resolved'] == python,
        'complete direct-control implementation/test/runner/interpreter source set differs')
    for name,row in before.items(): check_row(name,row)
    for name in ['run_once.py','child.py','plan.json']:
        require(sha(output/name) == sha(LINK_CONTROL/name), 'retained direct-control source differs')
    require(plan['policy'] == 'owned-temp-frozen-link-controls-v1' and plan['actual_result'] is None
        and plan['source_root'] == str(LINK_SOURCE) and plan['control_source'] == str(LINK_CONTROL)
        and plan['future_output'] == str(output) and plan['cwd'] == str(LINK_SOURCE)
        and plan['command'] == ['/opt/homebrew/bin/python3','-B',str(LINK_CONTROL/'child.py')]
        and plan['canonical_lock_access'] is False and plan['provider_writes'] is False
        and plan['network'] is False and type(plan['compiler_calls']) is int and plan['compiler_calls'] == 0
        and same(plan['bounds'],dict(cpu_seconds=30,entry_free_bytes=256*2**20,file_bytes=256*1024,
            observer_seconds=60,owned_bytes=8*2**20,stop_free_bytes=128*2**20)), 'direct-control plan/bounds differ')
    for key,names in [('sources',[LINK_CONTROL/'child.py',LINK_SOURCE/'links.py',LINK_SOURCE/'test_links.py']),
                      ('test_sources',[LINK_SOURCE/'links.py',LINK_SOURCE/'test_links.py'])]:
        require(same(plan[key],{str(name):before[str(name)] for name in names}), 'source-bound direct control plan differs')
    names = sorted('test_links.'+cls.name+'.'+method.name
        for cls in ast.parse(read_bytes(LINK_SOURCE/'test_links.py')).body if isinstance(cls,ast.ClassDef)
        for method in cls.body if isinstance(method,ast.FunctionDef) and method.name.startswith('test_'))
    require(len(names) == len(set(names)) == LINK_COUNT and type(plan['tests']) is int and plan['tests'] == LINK_COUNT
        and same(names,plan['test_names']) and same(names,result['test_names']), 'source-derived actual link test names differ')
    environment = dict(PATH='/usr/bin:/bin:/opt/homebrew/bin',LANG='C',LC_ALL='C',TMPDIR=str(output/'tmp'),
        PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHONHASHSEED='0')
    require(record['status'] == 'closed' and type(record['returncode']) is int and record['returncode'] == 0
        and record['may_be_live'] is False and record['observation_errors'] == []
        and record['command'] == plan['command'] and record['cwd'] == str(LINK_SOURCE)
        and same(record['environment'],environment) and record['plan_sha256'] == result['plan']['sha256']
        and all(type(record[key]) is int and record[key] > 0 for key in ['pid','parent_pid','parent_parent_pid'])
        and record['started_at'] <= record['spawned_at'] <= record['observation_finished_at'] <= record['finished_at']
        and record['finished_at']-record['spawned_at'] <= 60
        and record['cpu_seconds'] == 30 and record['observer_seconds'] == 60
        and record['file_bytes'] == 256*1024 and record['namespace_bytes'] == 8*2**20
        and record['canonical_lock_access'] is False and type(record['compiler_calls']) is int and record['compiler_calls'] == 0
        and type(record['retries']) is int and record['retries'] == 0 and record['signals'] == []
        and not any(key in record for key in ['execution_error','publication_error']),
        'actual direct-control child closure/identity/limits differ')
    require(started['status'] == 'running' and started['may_be_live'] is True
        and all(same(started[key],record[key]) for key in ['command','cwd','environment','pid','parent_pid',
            'parent_parent_pid','started_at','spawned_at','plan_sha256']), 'retained started child association differs')
    for key in ['stdout','stderr']: check_row(output/key,record[key])
    raw = read_bytes(output/'stdout').decode(); require(read_bytes(output/'stderr') == b'', 'direct controls emitted stderr')
    lines = raw.splitlines(); footer = [line for line in lines if line.startswith('FROZEN_LINK_CONTROL_RESULT ')]
    require(len(footer) == 1 and [line for line in lines if line.startswith('test_')] ==
        [name.rsplit('.',1)[1]+' ('+name+') ... ok' for name in names], 'complete actual24 raw names differ')
    proof = json.loads(footer[0].split(' ',1)[1])
    require(same(proof,result['child_proof']) and proof['status'] == 'passed'
        and type(proof['tests']) is int and proof['tests'] == LINK_COUNT and same(proof['test_names'],names)
        and proof['child_pid'] == record['pid'] and proof['parent_pid'] == record['parent_pid']
        and proof['cwd'] == str(LINK_SOURCE) and same(proof['test_sources'],plan['test_sources'])
        and all(type(proof[key]) is int and proof[key] == 0 for key in ['skipped','failures','errors']),
        'actual direct-control child result differs')
    observed = proof['observed_environment']
    require(same(observed,environment) or same(observed,dict(environment,__CF_USER_TEXT_ENCODING='0x1F5:0x0:0x52')),
        'passed/observed startup environments differ beyond explicit validated CF addition')
    policy = proof['io_policy']
    require(policy['owned_tmp'] == str(output/'tmp') and policy['temporary_members_after'] == []
        and policy['denied_events'] == [] and type(policy['mutation_events']) is int and 0 <= policy['mutation_events'] <= 1024
        and all(policy[key] is False for key in ['provider_writes','subprocess_calls','network_calls','signal_calls']),
        'actual temporary-filesystem controls escaped their policy')
    return dict(status='verified-frozen-link-controls',tests=LINK_COUNT,test_names=names,result=dict(reference),
        record=dict(result['record']),manifest=dict(path=str(output/'manifest.json'),sha256=LINK_PROOF['manifest_sha256']),
        source_before=dict(result['source_before']),source_after=dict(result['source_after']),
        stdout=dict(result['stdout']),stderr=dict(result['stderr']),sources=before,
        passed_environment=environment,observed_environment=observed,
        controls_are_separate_from_actual53=True,compiler_calls=0)


def source_preflight_reference(expected_sha):
    routes = read(ROUTES_PATH, ROUTES_SHA)
    prior = routes['preflight']
    reference = dict(path=prior['report'], sha256=sha_value(expected_sha))
    require(reference['sha256'] == SOURCE_PREFLIGHT_SHA, 'actual completed audit10 digest required')
    audit = read(reference['path'], reference['sha256'])
    require(audit['status'] == 'verified' and audit['phase'] == 'preflight'
            and type(audit['actual_children']) is int and audit['actual_children'] == 2
            and same(audit['attempt'], prior['descriptor']),
            'actual separately audited source-preflight prerequisite required')
    return reference


def runtime_preparation(phase, record_sha, launcher_sha, startup, retry, installation, native, preflight):
    """Bind a completed producer preparation, never its own future record.

    The seven original packet rows remain in the original prepared scope. Their
    declared identities are authenticated by the closed record here; the saved
    phase auditor independently rereads the packet itself under its full guard.
    """
    routes = read(ROUTES_PATH, ROUTES_SHA)
    require(routes['phase'] == phase and routes['attempt_source'] == str(ATTEMPT)
        and routes['qualified_source'] == str(RUNTIME), 'fixed attempt preparation descriptor differs')
    directory = Path(routes['preparation_execution'])
    path = directory/'record.json'; record = read(path, sha_value(record_sha)); finished(record)
    require(record['phase'] == phase and record['cwd'] == str(R) and record['preparation_passed'] is True
            and record['canonical_owner'] == 'producer-child' and record['runtime_admission'] is False
            and record['signals'] == [] and record['observation_errors'] == []
            and all(type(record[key]) is int and record[key] == 0 for key in ['compiler_calls', 'provider_probes']),
            'actual completed read-only runtime preparation required')
    require(record['command'][2] == str(PREPARATION_LAUNCHER)
            and record['producer_command'][2] == str(ADAPTER/'prepare.py')
            and record['source_sha256'] == sha(PREPARATION_LAUNCHER, sha_value(launcher_sha))
            == sha(directory/'launcher.py'), 'exact original preparation launcher and retained source required')
    require({p.name for p in directory.iterdir()} == {'record.json', 'stdout', 'stderr', 'launcher.py',
                'invocation.json', 'source-rows.json', 'child-observation.json'}, 'complete seven-file preparation closure')
    streams(directory, record)
    require(raw(directory/'stderr') == b'', 'passed preparation emitted stderr')
    observation = read(directory/'child-observation.json', record['child_observation_sha256'])
    require(observation['status'] == 'returned' and observation['blocked_events'] == []
            and observation['pid'] == record['pid'] and observation['parent_pid'] == record['parent_pid']
            and same(observation['command'], record['producer_command'])
            and record['started_at'] <= record['child_started_at'] <= observation['started_at']
            <= observation['finished_at'] <= record['finished_at'] <= record['readback_finished_at'],
            'actual preparation child/raw/time association differs')
    invocation_ref = record['invocation']
    require(set(invocation_ref) == {'path', 'sha256'}, 'exact original preparation invocation reference')
    invocation = read(invocation_ref['path'], invocation_ref['sha256'])
    require(same(invocation, read(directory/'invocation.json')) and invocation['phase'] == phase,
            'retained original preparation invocation differs')
    adapter = invocation['adapter']
    require(set(adapter) == {'preparer', 'source_manifest', 'startup_controls', 'retry_controls', 'installation_controls'}
            and same(adapter['startup_controls'], startup['audit'])
            and same(adapter['retry_controls'], retry['audit'])
            and same(adapter['installation_controls'], native['audit'])
            and same(invocation['preflight'], preflight)
            and same(adapter['preparer'], dict(path=str(ADAPTER/'prepare.py'), sha256=sha(ADAPTER/'prepare.py'))),
            'actual preparation startup qualification/source association differs')
    ref = adapter['source_manifest']; require(set(ref) == {'path', 'sha256'}, 'exact startup source manifest reference')
    manifest = read(ref['path'], ref['sha256']); rows = read(directory/'source-rows.json')
    require(set(manifest) == {'status', 'files'} and manifest['status'] == 'reviewed-runtime-installation07-startup-source-closure'
            and type(manifest['files']) is dict and type(rows) is dict and len(rows) <= 520
            and sum(row['size'] for row in rows.values()) <= 8*2**20,
            'bounded actual preparation source table required')
    require(str(directory/'source-rows.json') == PREPARATION_TABLE['path']
        and record_sha == PREPARATION_TABLE['record_sha256']
        and same(OBSERVED[str(directory/'source-rows.json')],PREPARATION_TABLE['row']),
        'separately reviewed actual preparation table byte/identity binding differs')
    require(type(PREPARATION_EXTRA_COUNT) is int and PREPARATION_EXTRA_COUNT >= 0
        and type(PREPARATION_EXTRA_PATHS) is list and len(PREPARATION_EXTRA_PATHS) == PREPARATION_EXTRA_COUNT
        and PREPARATION_EXTRA_PATHS == sorted(set(PREPARATION_EXTRA_PATHS)),
        'exact reviewed preparation source gap declaration required')
    for name in PREPARATION_EXTRA_PATHS:
        require(name in rows and name.startswith('/Users/danluu/dev/') and Path(name).suffix == '.py',
            'supplemental preparation source is not in the authenticated table')
        sha(name, rows[name]['sha256'])
        require(same(OBSERVED[name], rows[name]), 'additional preparation source differs')
    # The bootstrap independently expands the original full runtime table and
    # requires every saved preparation row before expensive reads.
    for name, row in manifest['files'].items():
        require(name in rows and same(rows[name], row), 'startup source omitted from actual preparation table')
        if name in OBSERVED:
            require(same(OBSERVED[name], row), 'supplemental startup source changed since preparation')
    for name, row in OBSERVED.items():
        if name in rows:
            require(same(row, rows[name]), 'current supplemental row differs from actual preparation source')
    require(set(record['outputs']) == {'source-policy-proof.json', 'specification.json', 'plan.json', 'inputs.json',
                                     'snapshot-plan.json', 'metadata-preflight.json', 'launch.json'},
            'complete original seven-output identity declarations required')
    for name, row in record['outputs'].items():
        require(set(row) == {'size', 'sha256', 'identity'} and type(row['size']) is int and 0 <= row['size'] <= 16*2**20
                and set(row['identity']) == set(FIELDS) and all(type(row['identity'][key]) is int for key in FIELDS)
                and row['identity']['size'] == row['size'] and stat.S_ISREG(row['identity']['mode']),
                'typed actual preparation output identity differs')
        sha_value(row['sha256'])
    require(sum(row['size'] for row in record['outputs'].values()) <= 64*2**20, 'original packet declaration bound')
    return dict(preparation=dict(path=str(path), sha256=record_sha),
                preparation_launcher=dict(path=str(PREPARATION_LAUNCHER), sha256=launcher_sha),
                declared_packet_outputs=record['outputs'])


def publish(path, value):
    data = encoded(value); require(len(data) <= 4*2**20, 'bounded manifest publication')
    with path.open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    require(path.read_bytes() == data, 'exclusive manifest readback differs')
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['installation'], required=True)
    parser.add_argument('--canonical-fd', type=int, required=True)
    parser.add_argument('--source-inventory', type=Path, required=True)
    parser.add_argument('--source-inventory-sha256', required=True)
    parser.add_argument('--runtime-preparation-sha256', required=True)
    parser.add_argument('--runtime-preparation-launcher-sha256', required=True)
    parser.add_argument('--source-preflight-audit-sha256', required=True)
    args = parser.parse_args()
    output = output_root(args.phase)
    require(Path.cwd() == R and sys.dont_write_bytecode and not sys.flags.optimize
            and Path(sys.executable).resolve(strict=True) == PYTHON, 'fixed manifest owner/Python required')
    require(type(INTEGRATION_SOURCE_PATHS) is list and len(INTEGRATION_SOURCE_PATHS) == 20
            and all(type(name) is str for name in INTEGRATION_SOURCE_PATHS)
            and len(set(INTEGRATION_SOURCE_PATHS)) == len(INTEGRATION_SOURCE_PATHS)
            and all((Path(name).parent in [HERE, ADAPTER] or name == str(STARTUP_SOURCE/'environment.py')
                         or name in {str(LOADER_SOURCE/'runtime_compiler.py'),str(LOADER_SOURCE/'producer_recipe.py'),
                                     str(LOADER_SOURCE/'audit_recipe.py'),str(LOADER_SOURCE/'test_native_loader.py')}
                         or name in {str(LINK_SOURCE/'links.py'),str(LINK_SOURCE/'test_links.py'),
                                     str(LINK_CONTROL/'run_once.py'),str(LINK_CONTROL/'child.py'),str(LINK_CONTROL/'plan.json')})
                    and str(Path(name)) == name
                    and name not in {str(path) for path in CORE_PATHS} for name in INTEGRATION_SOURCE_PATHS),
            'final reviewed integration source list remains unbound')
    sha_value(ROUTES_SHA)
    require(type(NATIVE_CHAIN['count']) is int and NATIVE_CHAIN['count'] > 0, 'current native-loader count remains unbound')
    require(type(RETRY_CHAIN['count']) is int and RETRY_CHAIN['count'] > 0, 'actual retry count remains unbound')
    require(all(type(RETRY_CHAIN[key]) is str and RETRY_CHAIN[key] for key in
        ['supervisor','dispatcher','launcher','verifier','executor','execution','preparation','preparation_wrapper']),
        'actual retry proof routes remain unbound')
    for name in ['audit_sha256', 'execution_sha256', 'preparation_sha256']:
        sha_value(STARTUP_CHAIN[name]); sha_value(RETRY_CHAIN[name]); sha_value(INSTALLATION_CHAIN[name]); sha_value(NATIVE_CHAIN[name])
    held = os.fstat(args.canonical_fd); named = CANONICAL.lstat()
    require(stat.S_ISREG(named.st_mode) and named.st_nlink == held.st_nlink == 1
            and (held.st_dev, held.st_ino) == (named.st_dev, named.st_ino), 'inherited canonical descriptor differs')
    require(shutil.disk_usage(R).free >= 16*2**30, 'fresh16GiB before manifest evidence')
    resource.setrlimit(resource.RLIMIT_CPU, (900, 900)); resource.setrlimit(resource.RLIMIT_FSIZE, (4*2**20, 4*2**20))
    require(not os.path.lexists(output), 'fresh phase-specific manifest output required')
    inventory = read(args.source_inventory, sha_value(args.source_inventory_sha256))
    require(set(inventory) == {'policy', 'sources'} and inventory['policy'] == 'runtime13-reviewed-sources-v1'
            and type(inventory['sources']) is dict
            and set(inventory['sources']) == ({str(path) for path in CORE_PATHS} | set(INTEGRATION_SOURCE_PATHS)),
            'exact separately reviewed enclosing source inventory required')
    for name, digest in inventory['sources'].items():
        sha(name, sha_value(digest))
    require(Path(__file__) == HERE/'prepare_manifest.py', 'exact manifest preparer source route')
    proofs = [control_chain(spec) for spec in CHAINS]
    startup = control_chain(STARTUP_CHAIN)
    retry = control_chain(RETRY_CHAIN)
    installation = control_chain(INSTALLATION_CHAIN)
    native = control_chain(NATIVE_CHAIN)
    preflight = source_preflight_reference(args.source_preflight_audit_sha256)
    frozen_links = frozen_link_controls(dict(path=str(LINK_RESULT),sha256=LINK_PROOF['result_sha256']),
        read_json=read,read_bytes=raw,sha=sha,identity=lambda name:OBSERVED[str(name)]['identity'])
    preparation = runtime_preparation(args.phase, args.runtime_preparation_sha256,
                                      args.runtime_preparation_launcher_sha256, startup, retry, installation, native, preflight)
    rows = dict(sorted(OBSERVED.items()))
    manifest = dict(policy=POLICY, files=rows, actual53=proofs[0]['audit'], phase45=proofs[1]['audit'],
                    preparation=preparation['preparation'], preparation_launcher=preparation['preparation_launcher'],
                    startup_controls=startup['audit'], retry_controls=retry['audit'],
                    frozen_links_controls=frozen_links['result'],
                    installation_controls=installation['audit'], native_loader_controls=native['audit'], source_preflight_audit=preflight)
    for name, row in rows.items():
        sha(name, row['sha256']); require(same(OBSERVED[name], row), 'source changed before manifest publication')
    guard(); output.mkdir(mode=0o700)
    digest = publish(output/'manifest.json', manifest)
    for name, row in rows.items():
        sha(name, row['sha256']); require(same(OBSERVED[name], row), 'source changed after manifest publication')
    summary = dict(status='prepared-audit-source-manifest', phase=args.phase, pid=os.getpid(), parent_pid=os.getppid(),
                   source_inventory=dict(path=str(args.source_inventory), sha256=args.source_inventory_sha256),
                   manifest=dict(path=str(output/'manifest.json'), sha256=digest), controls=[*proofs, startup, retry, installation, native, frozen_links], source_preflight_audit=preflight,
                   runtime_preparation=preparation,
                   files=len(rows), logical_bytes=sum(row['size'] for row in rows.values()),
                   compiler_calls=0, provider_probes=0, process_signals=0, network_calls=0,
                   runtime_admission=False, retirement_authorized=False, samples=SAMPLES, finished_at=time.time())
    summary_sha = publish(output/'preparation.json', summary)
    for directory in [output, output.parent]:
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    print(encoded(dict(status=summary['status'], manifest=summary['manifest'],
                       preparation=dict(path=str(output/'preparation.json'), sha256=summary_sha))).decode(), end='')


if __name__ == '__main__':
    main()
