"""Uninvoked explicit-wait source-manifest / saved-runtime audit executor.

Derived from the corrected Reader02 executor's observed-closure pattern. That
source was never an actual successful audit and is not claimed as qualification.
All phase digests arrive explicitly; this draft contains no future invocation.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import shutil
import stat
import subprocess
import sys
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HERE = ROOT/'experiments/hir-options-hash-runtime-audit-06'
QUALIFIED_AUDIT = ROOT/'experiments/hir-options-hash-runtime-audit-05'
ATTEMPT = ROOT/'experiments/runtime-preflight-retry-05'
ROUTES_PATH = ATTEMPT/'routes.json'
ROUTES_SHA = '893d6102741b5206a829e2f5e130614667140b1eacc09d0c55616f7311f82e6a'
ADAPTER = ATTEMPT
STARTUP_SOURCE = ROOT/'experiments/runtime04-environment-adapter-01'
RUNTIME = X/'experiments/hir-options-hash/runtime-installation-04'
PREPARATION_LAUNCHER = ATTEMPT/'prepare_once.py'
RUNTIME_LAUNCHER = ATTEMPT/'launch.py'
CANONICAL = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
PYTHON = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
OWNED = X/'experiments/stable-cgu/owned_stage.py'
OWNED_SHA = '7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e'
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
ENVIRONMENT = dict(HOME='/Users/danluu', USER='danluu', LOGNAME='danluu', LANG='C', LC_ALL='C', TZ='UTC',
                   PATH='/usr/bin:/bin:/usr/sbin:/sbin', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
PHASE_NAMES = ('launch', 'inputs', 'snapshot-plan', 'receipt', 'result', 'outer', 'launcher-record')
OBSERVED = {}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def same(left, right):
    return encoded(left) == encoded(right)


def stamp(info):
    return {key: getattr(info, 'st_'+key) for key in FIELDS}


def digest(value):
    require(type(value) is str and re.fullmatch('[a-f0-9]{64}', value), 'explicit actual SHA required')
    return value


def raw(value, expected=None, maximum=64*2**20, remember=True):
    p = Path(value)
    require(p.is_absolute() and p != Path('/') and str(p) == os.fspath(value) and '..' not in p.parts,
            'canonical explicit input route')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
    fds = [os.open('/', flags)]; links = []
    route = lambda info: (info.st_dev, info.st_ino, info.st_mode)
    try:
        for name in p.parts[1:-1]:
            parent = fds[-1]; before = os.stat(name, dir_fd=parent, follow_symlinks=False)
            require(stat.S_ISDIR(before.st_mode), 'ordinary input ancestor')
            child = os.open(name, flags, dir_fd=parent); fds.append(child)
            require(route(os.fstat(child)) == route(before), 'input ancestor changed during open')
            links.append((parent, name, child, route(before)))
        parent = fds[-1]; before = stamp(os.stat(p.name, dir_fd=parent, follow_symlinks=False))
        require(stat.S_ISREG(before['mode']) and 0 <= before['size'] <= maximum, 'bounded ordinary executor input')
        fd = os.open(p.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            require(same(stamp(os.fstat(stream.fileno())), before), 'opened executor input differs')
            data = stream.read(maximum+1)
            require(len(data) <= maximum and same(stamp(os.fstat(stream.fileno())), before), 'executor input changed during read')
        require(same(stamp(os.stat(p.name, dir_fd=parent, follow_symlinks=False)), before), 'executor input replaced')
        for parent, name, child, saved in links:
            require(route(os.fstat(child)) == saved and
                    route(os.stat(name, dir_fd=parent, follow_symlinks=False)) == saved, 'executor route changed')
        row = dict(size=len(data), sha256=hashlib.sha256(data).hexdigest(), identity=before)
        require(len(data) == before['size'] and (expected is None or row['sha256'] == digest(expected)), 'executor bytes differ')
        if remember:
            require(str(p) not in OBSERVED or same(OBSERVED[str(p)], row), 'executor input changed after first read')
            OBSERVED.setdefault(str(p), row)
        return data
    finally:
        for fd in reversed(fds):
            os.close(fd)


def read(value, expected=None, maximum=64*2**20):
    def unique(pairs):
        out = {}
        for key, item in pairs:
            require(key not in out, 'duplicate executor JSON key'); out[key] = item
        return out
    return json.loads(raw(value, expected, maximum), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def sha(value, expected=None, maximum=64*2**20):
    return hashlib.sha256(raw(value, expected, maximum)).hexdigest()


def inventory(args):
    value = read(args.source_inventory, args.source_inventory_sha256, 2**20)
    require(set(value) == {'policy', 'sources'} and value['policy'] == 'runtime06-reviewed-sources-v1'
            and type(value['sources']) is dict and 8 <= len(value['sources']) <= 24,
            'bounded reviewed final source inventory required')
    required = {str(HERE/name) for name in ['bootstrap.py','audit.py','prepare_manifest.py','execute.py']} | {
        str(QUALIFIED_AUDIT/name) for name in ['audit_io.py','reader.py','test_reader.py','test_audit_io.py']}
    require(required <= set(value['sources']), 'complete enclosing source inventory required')
    total = 0
    for name, expected in value['sources'].items():
        path = Path(name)
        require(str(path) == name and (path.parent in [HERE, ADAPTER] or str(path) in required or path == STARTUP_SOURCE/'environment.py')
                and re.fullmatch('[A-Za-z][A-Za-z0-9_.-]*', path.name),
                'source inventory must name only explicit successor/qualified helper routes')
        total += len(raw(name, digest(expected), 2**20))
    require(total <= 2*2**20 and str(Path(__file__)) == str(HERE/'execute.py'), 'bounded exact executor source required')
    declarations = [node.value for node in ast.parse(raw(HERE/'prepare_manifest.py')).body
                    if isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'INTEGRATION_SOURCE_PATHS']
    require(len(declarations) == 1, 'one literal reviewed integration source declaration required')
    integration = ast.literal_eval(declarations[0])
    require(type(integration) is list and len(integration) <= 16 and all(type(name) is str for name in integration)
            and len(set(integration)) == len(integration) and not required.intersection(integration)
            and set(value['sources']) == required | set(integration),
            'final integration source binding is unset or differs; refuse before evidence or child')
    startup_values = [node.value for node in ast.parse(raw(HERE/'prepare_manifest.py')).body
                      if isinstance(node, ast.Assign) and len(node.targets) == 1
                      and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'STARTUP_CHAIN']
    require(len(startup_values) == 1, 'one literal startup qualification declaration required')
    startup = ast.literal_eval(startup_values[0])
    require(type(startup) is dict and type(startup['count']) is int and startup['count'] == 39
            and all(type(startup[key]) is str and re.fullmatch('[a-f0-9]{64}', startup[key])
                    for key in ['audit_sha256', 'execution_sha256', 'preparation_sha256']),
            'future actual startup qualification remains unbound; refuse before evidence or child')
    retry_values = [node.value for node in ast.parse(raw(HERE/'prepare_manifest.py')).body
                    if isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'RETRY_CHAIN']
    require(len(retry_values) == 1, 'one literal retry qualification declaration required')
    retry = ast.literal_eval(retry_values[0])
    require(type(retry) is dict and type(retry['count']) is int and retry['count'] > 0
        and all(type(retry[key]) is str and re.fullmatch('[a-f0-9]{64}', retry[key])
                for key in ['audit_sha256','execution_sha256','preparation_sha256'])
        and all(type(retry[key]) is str and retry[key] for key in
                ['supervisor','dispatcher','launcher','verifier','executor','execution','preparation','preparation_wrapper']),
        'future actual retry qualification remains unbound; refuse before evidence or child')
    for path, name in [(HERE/'audit.py', 'RETRY_COUNT'), (HERE/'bootstrap.py', 'RETRY_COUNT'),
                       (ATTEMPT/'entry.py', 'RETRY_CONTROL_COUNT')]:
        values = [node.value for node in ast.parse(raw(path)).body
                  if isinstance(node, ast.Assign) and len(node.targets) == 1
                  and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name]
        require(len(values) == 1, 'one source-bound retry count required')
        count = ast.literal_eval(values[0])
        require(type(count) is int and count == retry['count'], 'retry producer/auditor counts differ before child')
    attempt_routes()
    sha(OWNED, OWNED_SHA, 2**20)
    return value


def recheck():
    for name, row in list(OBSERVED.items()):
        raw(name, row['sha256']); require(same(OBSERVED[name], row), 'saved input changed before/after child')


def manifest_root(phase):
    require(phase in ['preflight'], 'exact runtime phase')
    return ROOT/('.work/runtime06-saved-audit-'+phase+'-manifest-01')


def preparation_execution(phase):
    require(phase in ['preflight'], 'exact runtime phase')
    return ROOT/('.work/runtime06-saved-audit-'+phase+'-manifest-preparation-execution-01')


def attempt_routes():
    routes = read(ROUTES_PATH, ROUTES_SHA, 2**20)
    require(routes['phase'] == 'preflight' and routes['attempt_source'] == str(ATTEMPT)
        and routes['qualified_source'] == str(RUNTIME), 'fixed attempt routes differ')
    return routes


def runtime_paths(phase):
    require(phase == 'preflight', 'preflight-only retry audit')
    routes = attempt_routes()
    packet = Path(routes['packet']); work = Path(routes['work'])
    outer = Path(routes['supervisor']); launcher = Path(routes['launcher_execution'])
    return dict(launch=packet/'launch.json', inputs=packet/'inputs.json', snapshot_plan=packet/'snapshot-plan.json',
                receipt=work/'receipt.json', result=work/'source-probe/result.json', outer=outer/'status.json',
                launcher_record=launcher/'record.json')


def producer_preparation_closure(args):
    path = Path(attempt_routes()['preparation_execution'])/'record.json'
    record = read(path, args.runtime_preparation_sha256, 4*2**20)
    require(record['status'] == 'finished' and type(record['returncode']) is int and record['returncode'] == 0
            and record['phase'] == args.phase and record['preparation_passed'] is True
            and record['source_sha256'] == sha(PREPARATION_LAUNCHER, args.runtime_preparation_launcher_sha256)
            and record['observation_errors'] == [] and 'initial_publication_error' not in record
            and record.get('child_may_be_live', False) is False and record['canonical_owner'] == 'producer-child'
            and record['runtime_admission'] is False and record['signals'] == []
            and record['finished_at'] <= record['readback_finished_at'],
            'actual closed runtime preparation required before manifest preparation')
    return dict(preparation=dict(path=str(path), sha256=args.runtime_preparation_sha256),
                preparation_launcher=dict(path=str(PREPARATION_LAUNCHER), sha256=args.runtime_preparation_launcher_sha256))


def audit_closure(args, sources):
    """Small actual closure readback only; full provider/raw audit is the child."""
    output = manifest_root(args.phase); preparation_evidence = preparation_execution(args.phase)
    manifest = read(output/'manifest.json', args.manifest_sha256, 4*2**20)
    preparation = read(output/'preparation.json', args.preparation_sha256, 4*2**20)
    execution = read(preparation_evidence/'record.json', args.preparation_record_sha256, 4*2**20)
    require(set(manifest) == {'policy', 'files', 'actual53', 'phase45', 'preparation', 'preparation_launcher', 'startup_controls', 'retry_controls'}
            and manifest['policy'] == 'runtime05-retry-saved-audit-source-manifest-v1'
            and type(manifest['files']) is dict and 0 < len(manifest['files']) <= 256
            and all(type(row['size']) is int and row['size'] >= 0 for row in manifest['files'].values())
            and sum(row['size'] for row in manifest['files'].values()) <= 8*2**20,
            'complete bounded supplemental manifest required')
    require(preparation['status'] == 'prepared-audit-source-manifest' and preparation['phase'] == args.phase
            and same(preparation['manifest'], dict(path=str(output/'manifest.json'), sha256=args.manifest_sha256))
            and same(preparation['source_inventory'], dict(path=str(args.source_inventory), sha256=args.source_inventory_sha256))
            and execution['status'] == 'finished' and type(execution['returncode']) is int and execution['returncode'] == 0
            and execution['observation_errors'] == [] and execution['may_be_live'] is False
            and execution['mode'] == 'prepare' and execution['phase'] == args.phase and execution['result_sha256'] == args.preparation_sha256
            and execution['manifest_sha256'] == args.manifest_sha256
            and execution['pid'] == preparation['pid'] and execution['parent_pid'] == preparation['parent_pid']
            and execution['finished_at'] <= execution['canonical_released_at'] <= time.time()
            and 'execution_error' not in execution, 'closed manifest preparation association required')
    for stream in ['stdout', 'stderr']:
        sha(preparation_evidence/stream, execution[stream+'_sha256'], 4*2**20)
    require(raw(preparation_evidence/'stderr') == b''
            and execution['source_sha256'] == sources['sources'][str(HERE/'prepare_manifest.py')]
            and execution['execution_source_sha256'] == sources['sources'][str(HERE/'execute.py')]
            and sha(preparation_evidence/'source.py') == execution['source_sha256']
            and sha(preparation_evidence/'execution.py') == execution['execution_source_sha256']
            and sha(preparation_evidence/'owned_stage.py') == OWNED_SHA, 'retained manifest execution source differs')
    for name, row in manifest['files'].items():
        raw(name, row['sha256'], 8*2**20)
        require(same(OBSERVED[name], row), 'supplemental manifest source/raw identity differs')
    for name, expected in sources['sources'].items():
        require(name in manifest['files'] and manifest['files'][name]['sha256'] == expected,
                'reviewed enclosing source omitted from manifest')
    expected_preparation = Path(attempt_routes()['preparation_execution'])/'record.json'
    require(set(manifest['preparation']) == set(manifest['preparation_launcher']) == {'path', 'sha256'}
            and manifest['preparation']['path'] == str(expected_preparation)
            and manifest['preparation_launcher']['path'] == str(PREPARATION_LAUNCHER)
            and manifest['preparation']['sha256'] == manifest['files'][str(expected_preparation)]['sha256']
            and manifest['preparation_launcher']['sha256'] == manifest['files'][str(PREPARATION_LAUNCHER)]['sha256']
            and same(preparation['runtime_preparation']['preparation'], manifest['preparation'])
            and same(preparation['runtime_preparation']['preparation_launcher'], manifest['preparation_launcher']),
            'exact phase-specific runtime preparation association differs')
    paths = runtime_paths(args.phase)
    values = {name: read(path, getattr(args, name+'_sha256')) for name, path in paths.items()}
    terminal = values['receipt']; outer = values['outer']; launcher = values['launcher_record']
    require(terminal['status'] == 'passed' and terminal['phase'] == args.phase
            and outer['status'] == 'finished' and type(outer['returncode']) is int and outer['returncode'] == 0
            and launcher['status'] == 'terminal-observed' and type(launcher['returncode']) is int
            and launcher['returncode'] == 0 and type(launcher['launcher_returncode']) is int
            and launcher['launcher_returncode'] == 0 and launcher['outer_sha256'] == args.outer_sha256
            and launcher['launch_sha256'] == args.launch_sha256
            and terminal['pid'] == outer['child_pid'] == launcher['controller_pid']
            and terminal['parent_pid'] == outer['supervisor_pid'] == launcher['supervisor_pid']
            and terminal['finished_at'] <= outer['finished_at'] <= launcher['terminal_observed_at'],
            'exact actual runtime passed closure is required before independent audit')
    return dict(manifest_sha256=args.manifest_sha256, preparation_sha256=args.preparation_sha256,
                preparation_record_sha256=args.preparation_record_sha256,
                phase={name: dict(path=str(path), sha256=getattr(args, name+'_sha256')) for name, path in paths.items()})


def publish(path, value, replace=False):
    data = encoded(value); require(len(data) <= 4*2**20, 'bounded execution record')
    if replace:
        temporary = path.with_name(path.name+'.tmp')
        require(not os.path.lexists(temporary), 'fresh record temporary')
        with temporary.open('xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    else:
        with path.open('xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
    require(raw(path, remember=False, maximum=4*2**20) == data, 'execution publication readback differs')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'audit'])
    parser.add_argument('--source-inventory', type=Path, required=True)
    parser.add_argument('--source-inventory-sha256', required=True)
    parser.add_argument('--phase', choices=['preflight'], required=True)
    parser.add_argument('--runtime-preparation-sha256')
    parser.add_argument('--runtime-preparation-launcher-sha256')
    for name in ['manifest', 'preparation', 'preparation-record', *PHASE_NAMES]:
        parser.add_argument('--'+name+'-sha256')
    args = parser.parse_args()
    require(Path.cwd() == R and sys.dont_write_bytecode and not sys.flags.optimize
            and Path(sys.executable).resolve(strict=True) == PYTHON, 'fixed owner/unoptimized Python -B required')
    digest(args.source_inventory_sha256)
    resource.setrlimit(resource.RLIMIT_CPU, (900, 900))
    pins = [getattr(args, name.replace('-', '_')+'_sha256') for name in
            ['manifest', 'preparation', 'preparation-record', *PHASE_NAMES]]
    runtime_preparation_pins = [args.runtime_preparation_sha256, args.runtime_preparation_launcher_sha256]
    require((args.mode == 'prepare' and all(value is None for value in pins)
                and all(type(value) is str and re.fullmatch('[a-f0-9]{64}', value) for value in runtime_preparation_pins))
            or (args.mode == 'audit' and all(value is None for value in runtime_preparation_pins)
                and all(type(value) is str and re.fullmatch('[a-f0-9]{64}', value) for value in pins)),
            'exact mode and future actual bindings must be explicit')
    output = manifest_root(args.phase); preparation_evidence = preparation_execution(args.phase)
    sources = inventory(args)
    source = HERE/('prepare_manifest.py' if args.mode == 'prepare' else 'bootstrap.py')
    evidence = preparation_evidence if args.mode == 'prepare' else ROOT/('.work/runtime06-saved-audit-'+args.phase+'-execution-01')
    report = output/'preparation.json' if args.mode == 'prepare' else Path(attempt_routes()['report'])
    require(not os.path.lexists(evidence) and not os.path.lexists(report)
            and (args.mode != 'prepare' or not os.path.lexists(output)), 'fresh execution and publication routes')
    closure = producer_preparation_closure(args) if args.mode == 'prepare' else audit_closure(args, sources)
    free = shutil.disk_usage(R).free; require(free >= 16*2**30, 'fresh16GiB before evidence or child')
    resource.setrlimit(resource.RLIMIT_FSIZE, (4*2**20, 4*2**20))
    module_spec = importlib.util.spec_from_file_location('_runtime05_executor_owned', OWNED)
    owned = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(owned)
    require(owned.CANONICAL_LOCK == CANONICAL, 'qualified helper canonical route differs')
    evidence.mkdir(mode=0o700)
    for path, name in [(source, 'source.py'), (HERE/'execute.py', 'execution.py'), (OWNED, 'owned_stage.py'),
                       (args.source_inventory, 'source-inventory.json')]:
        data = raw(path); target = evidence/name
        with target.open('xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        require(raw(target) == data, 'retained source bytes differ')
    invocation = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    publish(evidence/'invocation.json', invocation)
    record = dict(status='waiting', mode=args.mode, phase=args.phase, started_at=time.time(),
                  parent_pid=os.getpid(), parent_parent_pid=os.getppid(), parent_pgid=os.getpgrp(), parent_argv=list(sys.argv),
                  cwd=str(R), environment=dict(ENVIRONMENT), entry_free_bytes=free, canonical_lock=str(CANONICAL),
                  wait_seconds=600, capacity=dict(entry_gib=16, live_gib=9, floor_gib=8),
                  maximum_child_cpu_seconds=900, maximum_child_read_seconds=1200, maximum_observation_seconds=1250,
                  maximum_child_file_bytes=4*2**20, maximum_manifest_rows=256, maximum_manifest_payload_bytes=8*2**20,
                  source_sha256=sources['sources'][str(source)], execution_source_sha256=sources['sources'][str(HERE/'execute.py')],
                  owned_source_sha256=OWNED_SHA, source_inventory=dict(path=str(args.source_inventory), sha256=args.source_inventory_sha256),
                  actual_closure_pins=closure, disk_samples=[], observation_errors=[], may_be_live=False,
                  compiler_calls=0, provider_probes=0, process_signals=0, network_calls=0,
                  runtime_admission=False, retirement_authorized=False, report=str(report),
                  identity_limitation='In-process parent and Popen child PID/argv/cwd/environment/times; no independent process probes or signals.')
    def save():
        publish(evidence/'record.json', record, replace=os.path.lexists(evidence/'record.json'))
    def note(stage, error):
        record['observation_error_count'] = record.get('observation_error_count', 0)+1
        if len(record['observation_errors']) < 256:
            record['observation_errors'].append(dict(stage=stage, error=repr(error), time=time.time()))
    def observe_save(stage):
        try:
            save()
        except BaseException as error:
            note(stage, error)
    save()
    try:
        with owned.workload_lock(CANONICAL, 600) as fd:
            require(same(inventory(args), sources), 'reviewed sources changed before admission')
            if args.mode == 'audit':
                require(same(audit_closure(args, sources), closure), 'saved actual closure changed before admission')
            else:
                require(same(producer_preparation_closure(args), closure), 'actual producer preparation changed before admission')
            recheck(); record.update(admitted_at=time.time(), free_bytes_before=owned.disk(R, 16))
            command = [str(PYTHON), '-B', str(source), '--canonical-fd', str(fd)]
            if args.mode == 'prepare':
                command.extend(['--phase', args.phase, '--source-inventory', str(args.source_inventory),
                                '--source-inventory-sha256', args.source_inventory_sha256,
                                '--runtime-preparation-sha256', args.runtime_preparation_sha256,
                                '--runtime-preparation-launcher-sha256', args.runtime_preparation_launcher_sha256])
            else:
                command.extend(['--phase', args.phase, '--source-manifest', str(output/'manifest.json'),
                                '--source-manifest-sha256', args.manifest_sha256])
                for name in PHASE_NAMES:
                    command.extend(['--'+name+'-sha256', getattr(args, name.replace('-', '_')+'_sha256')])
            record['command'] = command; save()
            with (evidence/'stdout').open('xb') as stdout, (evidence/'stderr').open('xb') as stderr:
                child = subprocess.Popen(command, cwd=R, env=ENVIRONMENT, stdin=subprocess.DEVNULL,
                                         stdout=stdout, stderr=stderr, pass_fds=(fd,))
                deadline = time.monotonic()+1250
                record.update(status='running', pid=child.pid, child_started_at=time.time(), may_be_live=True)
                try:
                    observe_save('initial-child-publication')
                    while True:
                        remaining = deadline-time.monotonic()
                        if remaining <= 0:
                            break
                        try:
                            child.wait(timeout=min(5, remaining)); break
                        except subprocess.TimeoutExpired:
                            try:
                                record['disk_samples'].append(dict(time=time.time(), free_bytes=shutil.disk_usage(R).free))
                            except BaseException as error:
                                note('disk-sample', error)
                            observe_save('sample-publication')
                        except BaseException as error:
                            note('child-wait', error)
                            # Observation remains bounded even when a wait or sample fails.
                            if time.monotonic() >= deadline:
                                break
                            time.sleep(min(.2, max(0, deadline-time.monotonic())))
                finally:
                    # Actual closure is recorded before disk, hashing or publication.
                    record.update(returncode=child.returncode, observation_finished_at=time.time())
                    if child.returncode is None:
                        record.update(status='unclosed-task-not-signaled', may_be_live=True)
                    else:
                        record.update(status='finished', finished_at=time.time(), may_be_live=False)
                    for key, path in [('stdout_sha256', evidence/'stdout'), ('stderr_sha256', evidence/'stderr')]:
                        try:
                            record[key] = sha(path, maximum=4*2**20)
                        except BaseException as error:
                            note(key, error)
                    observe_save('terminal-publication')
            require(child.returncode is not None, 'observer expired; child may be live, no signal or retry')
            require(child.returncode == 0 and raw(evidence/'stderr') == b'' and not record['observation_errors'],
                    'saved evidence child or observation failed; preserve all raw evidence')
            require(all(sample['free_bytes'] >= 9*2**30 for sample in record['disk_samples']), 'observed live9 floor violation')
            result = read(report, maximum=4*2**20)
            require(result['pid'] == child.pid and result['parent_pid'] == os.getpid(), 'actual report child association differs')
            if args.mode == 'prepare':
                require(result['status'] == 'prepared-audit-source-manifest' and result['phase'] == args.phase
                        and same(result['source_inventory'], record['source_inventory'])
                        and result['runtime_admission'] is result['retirement_authorized'] is False,
                        'actual source manifest preparation association differs')
                record['manifest_sha256'] = sha(output/'manifest.json', result['manifest']['sha256'], 4*2**20)
                require(read(evidence/'stdout') == dict(status=result['status'], manifest=result['manifest'],
                        preparation=dict(path=str(report), sha256=sha(report))), 'manifest stdout association differs')
            else:
                require(result['status'] == 'verified' and result['phase'] == args.phase
                        and same(result['source_manifest'], dict(path=str(output/'manifest.json'), sha256=args.manifest_sha256))
                        and result['receipt_sha256'] == args.receipt_sha256 and result['result_sha256'] == args.result_sha256
                        and result['inputs_sha256'] == args.inputs_sha256 and result['outer_sha256'] == args.outer_sha256
                        and result['launcher_record_sha256'] == args.launcher_record_sha256,
                        'actual saved-runtime report association differs')
                require(read(evidence/'stdout') == dict(status='verified', path=str(report), sha256=sha(report)),
                        'saved-runtime stdout association differs')
            recheck(); record.update(result_sha256=sha(report), free_bytes_after=owned.disk(R, 9)); save()
        record['canonical_released_at'] = time.time(); save()
        print(encoded(dict(record=str(evidence/'record.json'), sha256=sha(evidence/'record.json'),
                           report=str(report), report_sha256=record['result_sha256'], pid=record['pid'], returncode=0)).decode(), end='')
    except BaseException as error:
        record['execution_error'] = repr(error)
        try:
            save()
        except BaseException as publication_error:
            print(encoded(dict(status='publication-failed', error=repr(publication_error), observed_record=record)).decode(), end='', flush=True)
        raise


if __name__ == '__main__':
    main()
