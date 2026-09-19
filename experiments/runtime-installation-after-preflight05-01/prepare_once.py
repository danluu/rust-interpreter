"""Bounded launcher for the installation-after-preflight05 read-only preparation.

An explicit reviewed invocation binds actual rehearsal, retirement and source
evidence. Preparation owns canonical admission itself; this outer does not nest
that lock. No compiler, provider probe, signal or automatic retry is permitted.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import runpy
import shutil
import stat
import subprocess
import sys
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
SOURCE = X/'experiments/hir-options-hash/runtime-installation-04'
ADAPTER = ROOT/'experiments/runtime-installation-after-preflight05-01'
ROUTES_SHA = '789fbe817e19c886824cda20ad66fd020e57d7a862af627986cdad40bc07605f'
HASH = ROOT/'experiments/hir-options-hash-driver-stage-03'
PYTHON = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
CANONICAL = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
ENV = dict(HOME='/Users/danluu', USER='danluu', LOGNAME='danluu', LANG='C', LC_ALL='C', TZ='UTC',
           PATH='/usr/bin:/bin:/usr/sbin:/sbin', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
OUTPUT_NAMES = {'source-policy-proof.json', 'specification.json', 'plan.json', 'inputs.json',
                'snapshot-plan.json', 'metadata-preflight.json', 'launch.json'}
MAXIMUM_CHILD_SECONDS = 1800  # Includes the producer's existing 600-second lock wait.
MAXIMUM_OBSERVATION_SECONDS = 1850
MAXIMUM_CPU_SECONDS = 900


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def identity(info):
    return {key: getattr(info, 'st_'+key) for key in FIELDS}


def raw(path, limit=64*2**20):
    path = Path(path)
    before = identity(path.lstat())
    require(path.is_absolute() and path.resolve(strict=True) == path and stat.S_ISREG(before['mode'])
            and before['size'] <= limit, 'bounded ordinary input required')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        require(identity(os.fstat(stream.fileno())) == before, 'opened input changed')
        data = stream.read(limit+1)
        require(identity(os.fstat(stream.fileno())) == before, 'read input changed')
    require(len(data) == before['size'] and identity(path.lstat()) == before, 'input route changed')
    return data, dict(identity=before, size=len(data), sha256=hashlib.sha256(data).hexdigest())


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def document(ref):
    require(type(ref) is dict and set(ref) == {'path', 'sha256'}, 'exact byte reference required')
    data, row = raw(ref['path'])
    require(row['sha256'] == ref['sha256'], 'reviewed input digest differs')
    return json.loads(data, object_pairs_hook=unique,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def write(path, value, *, replace=False):
    data = encoded(value)
    require(len(data) <= 4*2**20, 'bounded launcher evidence')
    target = path.with_name(path.name+'.staged') if replace else path
    with target.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if replace:
        target.replace(path)


def source_rows(invocation):
    """Use a separately completed rehearsal table, never edit its membership."""
    wire = document(invocation['rehearsal_inputs'])
    base = document(wire['file_table_base'])
    require('file_table_base' not in base and not set(base['files']) & set(wire['files']), 'disjoint nonrecursive table')
    files = dict(base['files'], **wire['files'])
    require(len(files) <= 180000 and wire['file_table_integrity'] == dict(count=len(files),
        total_bytes=sum(row['size'] for row in files.values()), sha256=hashlib.sha256(encoded(files)).hexdigest()),
        'complete authenticated rehearsal table required')
    rows = {name: row for name, row in files.items()
            if name.startswith('/Users/danluu/dev/') and Path(name).suffix == '.py'}
    adapter = invocation['adapter']
    require(type(adapter) is dict and set(adapter) == {'preparer', 'source_manifest', 'startup_controls', 'retry_controls', 'installation_controls'}
            and adapter['preparer']['path'] == str(ADAPTER/'prepare.py'), 'exact preparation adapter declaration')
    manifest = document(adapter['source_manifest'])
    require(set(manifest) == {'status', 'files'} and manifest['status'] == 'reviewed-runtime-installation05-startup-source-closure'
            and type(manifest['files']) is dict, 'reviewed complete startup source closure')
    historical = set(document(invocation['retirement'])['selected_paths'])
    extra = dict(manifest['files'])
    manifest_path = adapter['source_manifest']['path']
    require(manifest_path not in extra, 'source manifest cannot contain itself')
    extra[manifest_path] = raw(manifest_path)[1]
    require(not set(extra) & (historical | set(wire['absent_paths'])), 'startup source cannot relabel retired or absent input')
    for name, row in extra.items():
        require(name not in files or encoded(files[name]) == encoded(row), 'startup source overlaps prepared input differently')
        require(name not in rows or encoded(rows[name]) == encoded(row), 'startup source overlaps authenticated source differently')
        rows[name] = row
    require(str(ADAPTER/'prepare.py') in rows and rows[str(ADAPTER/'prepare.py')]['sha256'] == adapter['preparer']['sha256']
            and adapter['startup_controls']['path'] in rows
            and rows[adapter['startup_controls']['path']]['sha256'] == adapter['startup_controls']['sha256']
            and adapter['retry_controls']['path'] in rows
            and rows[adapter['retry_controls']['path']]['sha256'] == adapter['retry_controls']['sha256']
            and adapter['installation_controls']['path'] in rows
            and rows[adapter['installation_controls']['path']]['sha256'] == adapter['installation_controls']['sha256'],
            'adapter source and all three actual control proofs must be members of the source manifest')
    require(0 < len(rows) <= 512 and sum(row['size'] for row in rows.values()) <= 8*2**20,
            'finite complete local Python and supplemental source closure')
    for name, row in rows.items():
        require(encoded(raw(name)[1]) == encoded(row), 'authenticated producer source changed')
    require(str(SOURCE/'prepare.py') in rows, 'producer preparer absent from source closure')
    require({str(ADAPTER/name) for name in ['entry.py', 'controller.py', 'audit_owner.py',
            'routes.json', 'prepare.py', 'prepare_once.py', 'launch.py', 'test_installation.py']} <= set(rows)
            and rows[str(ADAPTER/'routes.json')]['sha256'] == ROUTES_SHA,
            'complete fresh installation source and fixed route descriptor required')
    return rows


def validate(args):
    require(Path.cwd() == R and sys.dont_write_bytecode and not sys.flags.optimize
            and Path(sys.executable).resolve(strict=True) == PYTHON, 'fixed preparation owner/Python')
    require(raw(Path(__file__).resolve())[1]['sha256'] == args.source_sha256, 'reviewed launcher source required')
    invocation = document(dict(path=args.invocation, sha256=args.invocation_sha256))
    require(set(invocation) == {'status', 'phase', 'rehearsal', 'rehearsal_inputs', 'retirement',
            'hash_plan', 'audits', 'evidence', 'preflight', 'adapter'} and invocation['status'] == 'reviewed-runtime-installation05-preparation',
            'concrete invocation remains unprepared or differs')
    phase = invocation['phase']
    require(phase == args.phase and phase == 'installation', 'exact runtime phase')
    rehearsal = document(invocation['rehearsal'])
    retirement = document(invocation['retirement'])
    require(rehearsal['status'] == 'verified-strict-callback-rehearsal'
            and rehearsal['runtime_admission'] is False and rehearsal['retirement_authorized'] is False
            and rehearsal['inputs'] == invocation['rehearsal_inputs'],
            'actual independent rehearsal required')
    require(retirement['status'] == 'verified-exact-proof-copy-retirement'
            and retirement['runtime_rehearsal'] == invocation['rehearsal']
            and retirement['selected_paths'] == rehearsal['selected_paths']
            and type(retirement['removed_files']) is int and retirement['removed_files'] == 21,
            'actual exact independently audited retirement required')
    for name in retirement['selected_paths']:
        require(not Path(name).exists() and not Path(name).is_symlink(), 'retired physical copy was recreated')
    require(invocation['hash_plan'] == dict(path=str(HASH/'plan.json'),
        sha256='24faa0611eacda26748727e443bef844c695c3ed362cda75b5aa60223e4d6055'), 'fixed adopted hash plan')
    previous = document(invocation['hash_plan'])
    require(set(previous) == {'integrity', 'member', 'policy', 'reference', 'remainder'}
            and previous['policy'] == 'external-json-member-v1' and previous['member'] == 'metadata_plan',
            'exact actual compact plan representation')
    # Only these literal remainder fields are needed here. The producer performs
    # the qualified full external-member expansion before any runtime admission.
    expected_audits = dict(previous['remainder']['independent_audits'])
    expected_audits.pop('compiler')
    expected_audits['hash'] = dict(path=str(ROOT/'.work/hir-options-hash-driver-independent-verification-02.json'),
        sha256='9540ad45b5423f793e323bac31d593f1c1b030fe0e1dd5fc3665565277885ebb')
    require(invocation['audits'] == expected_audits and set(invocation['evidence']) == set(expected_audits),
            'four exact completed prerequisite roles required')
    adapter = invocation['adapter']
    startup = document(adapter['startup_controls'])
    require(startup['status'] == 'verified' and type(startup['controls']) is int and startup['controls'] > 0,
            'actual independently verified startup controls required')
    retry = document(adapter['retry_controls'])
    require(retry['status'] == 'verified' and type(retry['controls']) is int and retry['controls'] > 0,
            'actual independently verified retry controls required')
    installation = document(adapter['installation_controls'])
    require(installation['status']=='verified' and type(installation['controls']) is int and installation['controls']>0,
        'actual independently verified installation controls required')
    command = [str(PYTHON), '-B', str(ADAPTER/'prepare.py'), '--phase', phase,
        '--startup-audit-sha256', adapter['startup_controls']['sha256'],
        '--retry-audit-sha256', adapter['retry_controls']['sha256'],
        '--installation-audit-sha256', adapter['installation_controls']['sha256'],
        '--preparation-passed-environment-json', encoded(ENV).decode().strip(),
        '--preparation-record', str(R/('.work/hir-options-hash-runtime-'+phase+'-preparation-execution-05/record.json')),
        '--startup-source-manifest', adapter['source_manifest']['path'],
        '--startup-source-manifest-sha256', adapter['source_manifest']['sha256']]
    for role in ['beta', 'native', 'run_make', 'hash']:
        ref = invocation['audits'][role]
        proof = document(ref)
        path = Path(invocation['evidence'][role])
        terminal_raw, terminal_row = raw(path/'receipt.json')
        terminal = json.loads(terminal_raw)
        require(proof['status'] == 'verified' and proof['receipt_sha256'] == terminal_row['sha256']
                and terminal['status'] == ('passed-awaiting-independent-audit' if role == 'hash' else 'passed'),
                'actual completed prerequisite association')
        key = role.replace('_', '-')
        command.extend(['--'+key+'-audit', ref['path'], '--'+key+'-audit-sha256', ref['sha256'],
                        '--'+key+'-evidence', str(path)])
    command.extend(['--copy-retirement-audit', invocation['retirement']['path'],
                    '--copy-retirement-audit-sha256', invocation['retirement']['sha256']])
    if phase == 'installation':
        prior = document(invocation['preflight'])
        routes=document(dict(path=str(ADAPTER/'routes.json'),sha256=ROUTES_SHA))
        selected=routes['preflight'];work=Path(selected['work']);packet=Path(selected['packet'])
        require(invocation['preflight']['path']==selected['report'] and prior['status']=='verified'
            and prior['phase']=='preflight' and type(prior['actual_children']) is int and prior['actual_children']==2
            and prior['attempt']==selected['descriptor'] and prior['receipt_sha256']==raw(work/'receipt.json')[1]['sha256']
            and prior['result_sha256']==raw(work/'source-probe/result.json')[1]['sha256']
            and prior['inputs_sha256']==raw(packet/'inputs.json')[1]['sha256']
            and prior['plan_sha256']==raw(packet/'plan.json')[1]['sha256'], 'actual independent preflight05 required')
        command.extend(['--source-preflight-audit', invocation['preflight']['path'],
                        '--source-preflight-audit-sha256', invocation['preflight']['sha256']])
    else:
        require(invocation['preflight'] is None, 'no invented future preflight result')
    return invocation, command, source_rows(invocation)


def child(args):
    resource.setrlimit(resource.RLIMIT_CPU, (MAXIMUM_CPU_SECONDS, MAXIMUM_CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16*2**20, 16*2**20))
    packet = ADAPTER/(args.phase+'-plan-01')
    evidence = R/('.work/hir-options-hash-runtime-'+args.phase+'-preparation-execution-05')
    started = time.monotonic()
    observations = dict(passed=ENV, before_validation=dict(os.environ))
    allowed = {str(packet/name) for name in OUTPUT_NAMES}
    observation_path = str(evidence/'child-observation.json')
    rows = {}
    blocked = []
    publishing_observation = False

    def reject(event):
        blocked.append(event)
        raise RuntimeError('preparation attempted forbidden API: '+event)

    def audit(event, values):
        if not publishing_observation:
            require(time.monotonic()-started <= MAXIMUM_CHILD_SECONDS, 'bounded preparation lifetime')
        if event.startswith(('subprocess.', 'os.exec', 'os.posix_spawn')) or event in [
                'os.system', 'socket.connect', 'os.kill', 'os.killpg']:
            reject(event)
        if event in ['os.remove', 'os.unlink', 'os.rmdir', 'os.rename', 'os.chmod', 'os.chown',
                     'os.truncate', 'os.utime', 'os.link', 'os.symlink', 'os.chdir', 'os.chroot']:
            reject(event)
        if event == 'exec':
            filename = values[0].co_filename
            if filename.startswith('/Users/danluu/dev/'):
                require(filename in rows and encoded(raw(filename)[1]) == encoded(rows[filename]), 'unauthenticated local Python execution')
        if event == 'open':
            name, mode, flags = values
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                require(isinstance(name, (str, bytes)), 'unattributed writable descriptor')
                path = Path(os.fsdecode(name)).absolute()
                if publishing_observation:
                    require(str(path) == observation_path and path.resolve(strict=False) == path,
                            'only final observation may be written after return or failure')
                else:
                    lock = path == CANONICAL and not flags & (os.O_CREAT | os.O_TRUNC | os.O_APPEND)
                    require(lock or (str(path) in allowed and path.resolve(strict=False) == path), 'undeclared preparer output')
        if event == 'os.mkdir':
            name, mode, fd = values
            require(not publishing_observation and fd == -1
                    and Path(os.fsdecode(name)).absolute() == packet, 'undeclared preparer directory')

    sys.addaudithook(audit)
    outcome = dict(status='started', pid=os.getpid(), parent_pid=os.getppid(),
                   environments=observations, started_at=time.time())
    try:
        invocation, command, rows = validate(args)
        outcome['command'] = command
        observations['before_producer_imports'] = dict(os.environ)
        sys.argv[:] = command[2:]
        sys.path.insert(0, str(SOURCE))
        sys.path.insert(0, str(ADAPTER))
        runpy.run_path(str(ADAPTER/'prepare.py'), run_name='__main__')
        outcome['status'] = 'returned'
    except BaseException as error:
        outcome.update(status='failed', error=repr(error))
        raise
    finally:
        observations['at_return_or_failure'] = dict(os.environ)
        outcome.update(finished_at=time.time(), blocked_events=blocked)
        # A deadline failure must not prevent its own bounded final observation.
        # All process/network/signal/mutation restrictions remain active.
        publishing_observation = True
        write(evidence/'child-observation.json', outcome)


def parent(args):
    invocation, command, rows = validate(args)
    phase = invocation['phase']
    packet = ADAPTER/(phase+'-plan-01')
    evidence = R/('.work/hir-options-hash-runtime-'+phase+'-preparation-execution-05')
    runtime = R/('.work/hir-options-hash-runtime-'+phase+'-05')
    supervisor = R/('.work/experiments/hir-options-hash-runtime-'+phase+'-supervisor-05')
    require(all(not p.exists() and not p.is_symlink() for p in [packet, evidence, runtime, supervisor]), 'fresh preparation scope')
    free = shutil.disk_usage(R).free
    require(free >= 24*2**30, 'fresh24GiB before preparation evidence or process')
    evidence.mkdir(mode=0o700)
    source, row = raw(Path(__file__).resolve())
    with (evidence/'launcher.py').open('xb') as stream:
        stream.write(source)
        stream.flush()
        os.fsync(stream.fileno())
    write(evidence/'invocation.json', invocation)
    write(evidence/'source-rows.json', rows)
    argv = [str(PYTHON), '-B', str(Path(__file__).resolve()), '--child', '--phase', phase,
            '--source-sha256', args.source_sha256, '--invocation', args.invocation,
            '--invocation-sha256', args.invocation_sha256]
    record = dict(status='prepared-child-unstarted', phase=phase, started_at=time.time(),
        parent_pid=os.getpid(), parent_parent_pid=os.getppid(), parent_pgid=os.getpgrp(),
        cwd=str(R), command=argv, producer_command=command, environment=ENV,
        canonical_lock=str(CANONICAL), canonical_owner='producer-child', wait_seconds=600,
        entry_free_bytes=free, capacity=dict(entry_gib=24, live_gib=9, floor_gib=8),
        maximum_observation_seconds=MAXIMUM_OBSERVATION_SECONDS, maximum_child_seconds=MAXIMUM_CHILD_SECONDS,
        maximum_cpu_seconds=MAXIMUM_CPU_SECONDS, source_sha256=row['sha256'],
        invocation=dict(path=args.invocation, sha256=args.invocation_sha256), samples=[], observation_errors=[],
        identity_limitation='Exact Popen PID plus in-process parent identity; no contemporaneous ps/cwd probes or signals.',
        compiler_calls=0, provider_probes=0, runtime_admission=False, signals=[])
    def save():
        write(evidence/'record.json', record, replace=True)
    save()
    with (evidence/'stdout').open('xb') as out, (evidence/'stderr').open('xb') as err:
        process = subprocess.Popen(argv, cwd=R, env=ENV, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
        deadline = time.monotonic()+MAXIMUM_OBSERVATION_SECONDS
        try:
            record.update(status='running', pid=process.pid, child_started_at=time.time())
            try:
                save()
            except BaseException as error:
                record['initial_publication_error'] = repr(error)
            while True:
                try:
                    process.wait(timeout=min(5, max(.001, deadline-time.monotonic())))
                    break
                except subprocess.TimeoutExpired:
                    try:
                        record['samples'].append(dict(time=time.time(), free_bytes=shutil.disk_usage(R).free))
                    except BaseException as error:
                        record['observation_errors'].append(dict(stage='disk-sample', error=repr(error), time=time.time()))
                    if time.monotonic() >= deadline:
                        break
        finally:
            record.update(returncode=process.returncode, observation_closed_at=time.time())
            if process.returncode is None:
                record.update(status='unclosed-task-not-signaled', child_may_be_live=True)
            else:
                record.update(status='finished', finished_at=time.time())
                for name in ['stdout', 'stderr']:
                    try:
                        record[name+'_sha256'] = raw(evidence/name)[1]['sha256']
                    except BaseException as error:
                        record['observation_errors'].append(dict(stage=name+'-hash', error=repr(error), time=time.time()))
            save()
    try:
        require(process.returncode == 0 and 'initial_publication_error' not in record
                and not record['observation_errors'], 'failed or unclosed preparation; preserve evidence')
        require(raw(evidence/'stderr')[0] == b'', 'preparation emitted stderr')
        observation_raw, observation_row = raw(evidence/'child-observation.json')
        observed = json.loads(observation_raw)
        require(observed['status'] == 'returned' and observed['pid'] == process.pid and not observed['blocked_events'], 'actual child observation')
        record['child_observation_sha256'] = observation_row['sha256']
        require({p.name for p in packet.iterdir()} == OUTPUT_NAMES, 'complete exact prepared membership')
        record['outputs'] = {name: raw(packet/name, 16*2**20)[1] for name in sorted(OUTPUT_NAMES)}
        require(sum(row['size'] for row in record['outputs'].values()) <= 64*2**20, 'bounded complete preparation packet')
        require(not runtime.exists() and not runtime.is_symlink() and not supervisor.exists()
                and not supervisor.is_symlink(), 'preparation created runtime workload')
        require(shutil.disk_usage(R).free >= 9*2**30
                and all(sample['free_bytes'] >= 9*2**30 for sample in record['samples']), 'observed live floor violation')
        source_rows(invocation)
        record.update(preparation_passed=True, readback_finished_at=time.time())
        save()
    except BaseException as error:
        record.update(preparation_passed=False, readback_error=repr(error), readback_finished_at=time.time())
        save()
        raise
    print(json.dumps(dict(status='prepared-awaiting-packet-review', path=str(evidence/'record.json'),
                         sha256=raw(evidence/'record.json')[1]['sha256'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['installation'], required=True)
    parser.add_argument('--invocation', required=True)
    parser.add_argument('--invocation-sha256', required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--child', action='store_true')
    args = parser.parse_args()
    (child if args.child else parent)(args)
