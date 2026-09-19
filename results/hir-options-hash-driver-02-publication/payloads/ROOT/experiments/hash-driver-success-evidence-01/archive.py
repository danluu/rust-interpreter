"""Bounded lossless retention of the independently qualified driver02 closure.

One archive-processing child, no provider commands and no source mutations.
The wrapper supplies the held canonical lock. No execution is authorized by
this source file's existence.
"""
import argparse
from contextlib import contextmanager
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import resource
import shutil
import stat
import sys
import tarfile
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
HERE = ROOT/'experiments/hash-driver-success-evidence-01'
WORK = ROOT/'.work/hash-driver-success-evidence-01'
RESULT = ROOT/'results/hir-options-hash-driver-02'
PROPOSAL = A/'.work/hash-driver02-lossless-publication-scope-02.json'
PROPOSAL_SHA = 'f6ea57ce5485de96bcc00aa6bb872cf2560ba023df48affea533806e3fac7264'
PYTHON = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
LIMITS = dict(maximum_members=512, maximum_file_bytes=8*2**20, maximum_logical_bytes=32*2**20,
              maximum_physical_bytes=32*2**20, maximum_compressed_bytes=16*2**20,
              maximum_expanded_tar_bytes=40*2**20, maximum_metadata_bytes=2*2**20)
EXACT_COUNT = 241
EXACT_BYTES = 13880266
RESERVATION = 64*2**20
ENVIRONMENT = dict(HOME='/Users/danluu', USER='danluu', LOGNAME='danluu', LANG='C', LC_ALL='C',
                   TZ='UTC', PATH='/usr/bin:/bin:/usr/sbin:/sbin', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
STARTUP_ADDITIONS = {'__CF_USER_TEXT_ENCODING': '0x1F5:0x0:0x52'}
START = time.monotonic()
READ_BYTES = 0


def require(value, message):
    if not value:
        raise RuntimeError(message)


def identity(path):
    s = Path(path).lstat()
    return {k: getattr(s, 'st_'+k) for k in FIELDS}


def held_identity(stream):
    s = os.fstat(stream.fileno())
    return {k: getattr(s, 'st_'+k) for k in FIELDS}


def guard():
    require(time.monotonic()-START <= 600, 'finite 600s archive wall bound')
    require(shutil.disk_usage(ROOT).free >= 9*2**30, 'live 9GiB archive floor')


def count_read(size):
    global READ_BYTES
    guard()
    READ_BYTES += size
    require(READ_BYTES <= 1024*2**20, 'finite total source and archive read bound')


@contextmanager
def ordinary(path, expected=None):
    path = Path(path)
    require(path.resolve(strict=True) == path, 'ordinary absolute input route')
    before = identity(path)
    require(stat.S_ISREG(before['mode']) and before['size'] <= max(LIMITS['maximum_file_bytes'], LIMITS['maximum_compressed_bytes']), 'bounded ordinary input')
    if expected is not None:
        require(before == expected, 'original input identity changed: '+str(path))
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
        require(held_identity(stream) == before, 'opened input identity changed')
        yield stream
        require(held_identity(stream) == before, 'held input identity changed')
    require(path.resolve(strict=True) == path and identity(path) == before, 'input route or identity changed')


def read_bytes(path, expected=None):
    with ordinary(path, expected) as stream:
        data = stream.read(LIMITS['maximum_file_bytes']+1)
        count_read(len(data))
        require(len(data) <= LIMITS['maximum_file_bytes'], 'input grew beyond bound')
        return data


def sha(path, expected=None):
    digest = hashlib.sha256()
    with ordinary(path, expected) as stream:
        while block := stream.read(2**20):
            count_read(len(block))
            digest.update(block)
    return digest.hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def write(path, data, replace=False):
    require(len(data) <= LIMITS['maximum_metadata_bytes'], 'finite generated document')
    target = path.with_name(path.name+'.staged') if replace else path
    with target.open('xb') as stream:
        require(stream.write(data) == len(data), 'short document write')
        stream.flush()
        os.fsync(stream.fileno())
    if replace:
        target.replace(path)
    sync_directory(path.parent)


def sync_directory(path):
    require(path.resolve(strict=True) == path and path.is_dir(), 'ordinary output directory')
    before = path.stat()
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        held = os.fstat(fd)
        require((held.st_dev, held.st_ino) == (before.st_dev, before.st_ino), 'output directory changed')
        os.fsync(fd)
        after = path.stat()
        require((held.st_dev, held.st_ino) == (after.st_dev, after.st_ino), 'output directory replaced')
    finally:
        os.close(fd)


def members_under(root):
    root = Path(root)
    require(root.resolve(strict=True) == root and root.is_dir(), 'ordinary closed evidence directory')
    found = {}
    for parent, dirs, files in os.walk(root, followlinks=False, onerror=lambda e: (_ for _ in ()).throw(e)):
        guard()
        for name in ['.', *dirs, *files]:
            path = Path(parent) if name == '.' else Path(parent)/name
            stamp = identity(path)
            require(stat.S_ISDIR(stamp['mode']) or stat.S_ISREG(stamp['mode']), 'closed evidence special entry')
            require(path.resolve(strict=True) == path, 'closed evidence route changed')
            found[str(path.relative_to(root))] = dict(kind='directory' if stat.S_ISDIR(stamp['mode']) else 'file', identity=stamp)
            require(len(found) <= 1024, 'finite closed evidence membership')
    return dict(sorted(found.items()))


def checked_json(row):
    data = read_bytes(row['path'], row['identity'])
    require(len(data) == row['size'] and hashlib.sha256(data).hexdigest() == row['sha256'], 'selected JSON differs')
    return json.loads(data)


def source_guards(proposal, rows):
    for row in rows.values():
        guard()
        require(sha(row['path'], row['identity']) == row['sha256'], 'selected source bytes changed')
    for root, expected in proposal['complete_scoped_directories'].items():
        require(members_under(root) == expected, 'closed source directory membership changed')






class SourceReader:
    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()
        self.size = 0

    def read(self, size):
        block = self.stream.read(size)
        count_read(len(block))
        self.size += len(block)
        self.digest.update(block)
        return block


class CappedOutput:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        guard()
        require(self.stream.tell()+len(data) <= LIMITS['maximum_compressed_bytes'], 'compressed archive cap before write')
        result = self.stream.write(data)
        require(result == len(data), 'short archive write')
        return result

    def flush(self):
        return self.stream.flush()

    def tell(self):
        return self.stream.tell()


def archive_readback(path, selected):
    class ExpandedReader:
        def __init__(self, stream):
            self.stream = stream
            self.total = 0

        def read(self, size):
            require(0 <= size <= 2**20, 'bounded gzip read request')
            block = self.stream.read(size)
            count_read(len(block))
            self.total += len(block)
            require(self.total <= LIMITS['maximum_expanded_tar_bytes'], 'expanded archive cap')
            return block

    seen = []
    with ordinary(path) as source, gzip.GzipFile(fileobj=source, mode='rb') as gz:
        expanded = ExpandedReader(gz)
        with tarfile.open(fileobj=expanded, mode='r|', format=tarfile.GNU_FORMAT) as archive:
            for entry in archive:
                require(len(seen) < len(selected) and entry.name == selected[len(seen)]['member'], 'exact ordered archive members')
                row = selected[len(seen)]
                require(entry.isfile() and entry.size == row['size'] and entry.mode == 0o644
                        and entry.mtime == entry.uid == entry.gid == 0 and not entry.uname and not entry.gname
                        and not entry.linkname, 'exact ordinary deterministic member')
                stream = archive.extractfile(entry)
                digest = hashlib.sha256(); size = 0
                while block := stream.read(2**20):
                    guard(); size += len(block); digest.update(block)
                require(size == row['size'] and digest.hexdigest() == row['sha256'], 'complete archive member readback')
                seen.append(entry.name)
            while block := archive.fileobj.read(2**20):
                require(not any(block), 'nonzero bytes after tar end marker')
        require(gz.read(1) == b'', 'full gzip EOF and trailer')
    require(len(seen) == len(selected) == EXACT_COUNT, 'complete selected archive readback')
    return dict(members=len(seen), expanded_bytes=expanded.total, full_member_readback=True, full_gzip_eof_crc=True)


def same(left, right):
    return encoded(left) == encoded(right)


def validate_history(proposal, rows):
    source = ROOT/'experiments/hir-options-hash-driver-stage-03'
    work = ROOT/'.work/hir-options-hash-driver-02'
    outer = ROOT/'.work/experiments/hir-options-hash-driver-supervisor-02'
    launcher = ROOT/'.work/hash-driver-launch-execution-02'
    audit_work = ROOT/'.work/hash-driver-independent-verification-execution-02'
    def doc(path):
        return checked_json(rows[str(path)])
    def digest(path):
        return rows[str(path)]['sha256']
    audit_path = ROOT/'.work/hir-options-hash-driver-independent-verification-02.json'
    audit, terminal, result = doc(audit_path), doc(work/'receipt.json'), doc(work/'result.json')
    history = proposal['history']; launch = doc(source/'launch.json'); wire = doc(source/'plan.json')
    require(digest(audit_path) == history['audit']['sha256'] ==
            '9540ad45b5423f793e323bac31d593f1c1b030fe0e1dd5fc3665565277885ebb'
            and audit['status'] == 'verified' and terminal['status'] == 'passed-awaiting-independent-audit'
            and result['status'] == 'hash-driver-observations-passed-awaiting-independent-audit',
            'exact independently qualified original driver owner required')
    require(audit['receipt_sha256'] == digest(work/'receipt.json') == history['receipt_sha256']
            and audit['result_sha256'] == terminal['result_sha256'] == digest(work/'result.json') == history['result_sha256']
            and audit['launch_sha256'] == digest(source/'launch.json')
            and audit['inputs_sha256'] == terminal['inputs_sha256'] == launch['inputs_sha256'] == digest(source/'inputs.json')
            and audit['snapshot_plan_sha256'] == terminal['snapshot_plan_sha256'] == launch['snapshot_plan_sha256'] == digest(source/'snapshot-plan.json')
            and launch['plan_sha256'] == digest(source/'plan.json'), 'actual source/packet/raw owner association')
    require(audit['actual_children'] == history['current_qualified_children'] == 3
            and audit['compilation_count'] == history['compilation_count'] == 1
            and audit['driver_process_count'] == history['driver_process_count'] == 2
            and audit['contexts_per_process'] == history['contexts_per_process'] == 8
            and audit['stdout_records_per_process'] == history['records_per_process'] == 9
            and audit['historical_failed_compiler_children'] == history['historical_failed_compiler_children'] == 1
            and audit['total_actual_hash_children'] == history['total_actual_hash_children'] == 4
            and audit['hash_driver_qualified'] is True
            and all(audit[k] is False for k in ['application_qualified', 'performance_measurement', 'runtime_installation'])
            and audit['full_frozen_byte_rehash'] is audit['full_provider_inventories'] is audit['static_and_actual_loaders_verified'] is True,
            'exact retained qualification scope')
    require(same(audit['metadata_plan_reference'], wire['reference'])
            and all(same(audit['continuation_controls'], value['continuation_controls'])
                    and same(audit['failed_predecessor']['owner'], value['failed_driver'])
                    for value in [terminal, result, wire['remainder']])
            and audit['failed_predecessor']['actual_children'] == 1
            and audit['failed_predecessor']['qualified_children'] == 0, 'failed and successful histories remain separate')
    dispatch, status, execution = doc(launcher/'record.json'), doc(outer/'status.json'), doc(audit_work/'record.json')
    require(status['status'] == 'finished' and status['returncode'] == 0
            and status['child_pid'] == terminal['pid'] and status['supervisor_pid'] == terminal['parent_pid']
            and status['command'] == launch['command'][6:] and status['cwd'] == str(ROOT)
            and status['plan_sha256'] == digest(outer/'plan.json') and status['log_sha256'] == digest(outer/'command.log')
            and status['child_started_at'] <= terminal['started_at'] <= terminal['admitted_at'] <= terminal['finished_at'] <= status['finished_at'],
            'actual original outer closure')
    require(dispatch['status'] == 'terminal-observed' and dispatch['returncode'] == dispatch['launcher_returncode'] == 0
            and dispatch['outer_sha256'] == digest(outer/'status.json') and dispatch['launch_sha256'] == digest(source/'launch.json')
            and dispatch['launcher_source_path'] == str(source/'launch.py') and dispatch['launcher_source_sha256'] == digest(source/'launch.py')
            and dispatch['command'] == launch['command'] and dispatch['environment'] == launch['environment']
            and dispatch['cwd'] == str(ROOT) and dispatch['controller_pid'] == terminal['pid']
            and dispatch['started_at'] <= dispatch['launcher_finished_at'] <= dispatch['finished_at']
            and status['finished_at'] <= dispatch['terminal_observed_at'] <= dispatch['finished_at'], 'closed explicit launcher')
    handoff = doc(launcher/'stdout')
    require(same(handoff, dispatch['supervisor_handoff']) and handoff['directory'] == str(outer)
            and handoff['supervisor_pid'] == dispatch['supervisor_pid'] == status['supervisor_pid'], 'original launcher handoff')
    for stream in ['stdout', 'stderr']:
        require(dispatch[stream+'_sha256'] == digest(launcher/stream)
                and execution[stream+'_sha256'] == digest(audit_work/stream), 'closed launcher/auditor raw bytes')
    require(execution['status'] == 'finished' and execution['returncode'] == 0
            and execution['report_sha256'] == digest(audit_path)
            and execution['source_sha256'] == audit['verifier_sha256'] == digest(source/'verify.py')
            and execution['finished_at'] <= execution['canonical_released_at']
            and execution['verified_output'] == doc(audit_work/'stdout')
            and execution['actual_closure'] == {str(work/'receipt.json'): digest(work/'receipt.json'),
                str(work/'result.json'): digest(work/'result.json'), str(outer/'status.json'): digest(outer/'status.json'),
                str(launcher/'record.json'): digest(launcher/'record.json')}, 'actual independent audit execution closure')
    for name in ['compile', 'serial', 'parallel']:
        child = doc(work/name/'receipt.json')
        require(child['returncode'] == 0 and child['supervisor_pid'] == terminal['pid'], 'retained successful actual child')
        for stream in ['stdout', 'stderr']:
            require(child[stream+'_sha256'] == digest(work/name/stream), 'complete original child raw retained')
    for name, row in audit['artifacts'].items():
        if row['kind'] == 'file':
            path = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01/hash-driver-02')/name
            require(digest(path) == row['sha256'] and rows[str(path)]['size'] == row['stamp'][3], 'exact executed output bytes retained')
    for role in ['original', 'derived']:
        ref = audit['driver_source_derivation'][role]
        require(digest(ref['path']) == ref['sha256'], 'exact driver source derivation retained')
    return audit


def validate_references(proposal, rows):
    manifests = {}
    def doc(path): return checked_json(rows[str(path)])
    for role, ref in proposal['prior_archives'].items():
        manifest, summary, audit = [doc(ref[key]['path']) for key in ['manifest', 'summary', 'independent_audit']]
        require(summary['status'] == 'passed' and audit['status'] == 'verified'
                and summary['archive']['sha256'] == ref['sha256'] and summary['archive']['bytes'] == ref['size']
                and summary['manifest_sha256'] == audit['manifest_sha256'] == ref['manifest']['sha256']
                and audit['summary_sha256'] == ref['summary']['sha256'], 'closed prior archive document association')
        if role == 'failed_driver01':
            require(audit['archive']['sha256'] == ref['sha256']
                    and audit['archive']['full_gzip_eof_crc'] is audit['archive']['full_member_readback'] is True
                    and manifest['proposal_sha256'] == summary['proposal_sha256'] == audit['proposal_sha256']
                    and audit['original_status'] == 'failed' and audit['hash_driver_qualified'] is False
                    and len(manifest['members']) == audit['selected_files'] == 168
                    and identity(ref['path']) == ref['identity'], 'retained failed archive proof remains unchanged')
            receipt, execution, audit_execution = [doc(ref[k]['path']) for k in ['receipt', 'execution_record', 'audit_execution_record']]
            require(receipt['status'] == 'passed' and execution['status'] == audit_execution['status'] == 'finished'
                    and execution['returncode'] == audit_execution['returncode'] == 0
                    and receipt['archive_sha256'] == ref['sha256'] and receipt['summary_sha256'] == ref['summary']['sha256']
                    and audit['receipt_sha256'] == ref['receipt']['sha256']
                    and audit['execution_record_sha256'] == ref['execution_record']['sha256']
                    and audit_execution['result_sha256'] == ref['independent_audit']['sha256']
                    and execution['finished_at'] <= execution['canonical_released_at']
                    and audit_execution['finished_at'] <= audit_execution['canonical_released_at'], 'actual failed-archive and independent-audit closure')
            manifests[role] = {row['member']:dict(bytes=row['size'], sha256=row['sha256']) for row in manifest['members']}
            require(len(manifests[role]) == 168, 'unique failed archive member map')
        else:
            require(role in ['beta', 'native'] and audit['archive_sha256'] == ref['sha256']
                    and audit['full_gzip_eof_crc'] is audit['full_member_readback'] is True
                    and type(ref['git_blob']) is str and len(ref['git_blob']) == 40,
                    'published prior archive retained byte/audit association')
            manifests[role] = manifest

    def association(ref, path, digest, size):
        require(ref['logical_member'] == str(path).lstrip('/') and ref['sha256'] == digest and ref['size'] == size
                and ref['archive_sha256'] == proposal['prior_archives'][ref['archive']]['sha256'], 'exact retained member source association')
        members = manifests[ref['archive']]; name = ref['logical_member']; chain = []
        while True:
            require(name in members and name not in chain and len(chain) < 256, 'bounded acyclic archive alias')
            chain.append(name); row = members[name]
            require(row['sha256'] == digest and row['bytes'] == size, 'archive alias bytes differ')
            if 'linkname' not in row: break
            name = row['linkname']
        require(chain == ref['alias_chain'] and name == ref['physical_member'], 'complete exact physical archive member')

    manifest = doc(ROOT/'.work/hir-options-hash-driver-02/source-snapshots.json'); snapshots = proposal['snapshots']
    require(len(manifest['files']) == snapshots['logical_files'] == 158
            and len(manifest['blobs']) == snapshots['physical_blobs'] == 147, 'complete qualified logical/physical snapshot set')
    stored = {k:v for k,v in manifest['storage'].items() if v['kind'] == 'stored'}
    reused = {k:v for k,v in manifest['storage'].items() if v['kind'] == 'reused'}
    require(len(stored) == snapshots['new_stored_blobs'] == 54 and len(reused) == snapshots['reused_blobs'] == 93
            and len(stored)+len(reused) == 147, 'complete physical classification')
    for key, storage in stored.items():
        blob, row = manifest['blobs'][key], rows[storage['path']]
        require(row['sha256'] == blob['sha256'] and row['size'] == blob['compressed_bytes'], 'complete new gzip bytes selected')
    require(sum(manifest['blobs'][k]['compressed_bytes'] for k in stored) == snapshots['new_stored_bytes'] == 690903,
            'new gzip byte count')
    refs = snapshots['reused_archive_associations']
    require(len(refs) == len({r['logical_sha256'] for r in refs}) == 93, 'all unique reused physical aliases')
    for ref in refs:
        source = ref['source']; key = ref['logical_sha256']
        require(key in reused and same(source, manifest['reuse'][key]) and source['path'] == reused[key]['path']
                and source['blob']['logical_sha256'] == key and source['blob']['logical_bytes'] == ref['logical_bytes'], 'exact original snapshot reference')
        association(ref['recovery'], source['path'], source['blob']['sha256'], source['blob']['compressed_bytes'])
    logical = [dict(source=path, sha256=row['sha256'], size=row['size'], physical_blob=row['path'],
                    storage=manifest['storage'][row['sha256']]['kind']) for path,row in sorted(manifest['files'].items())]
    require(same(logical, snapshots['logical_alias_map']), 'all logical snapshot aliases retained')
    base = snapshots['compact_base_archive_association']
    compact = doc(ROOT/'experiments/hir-options-hash-driver-stage-03/inputs.json')
    require(same(compact['file_table_base'], base['reference']), 'exact native full-table base')
    association(base['archived'], base['reference']['path'], base['reference']['sha256'], compact['files'][base['reference']['path']]['size'])
    wire = doc(ROOT/'experiments/hir-options-hash-driver-stage-03/plan.json')
    external = snapshots['external_metadata_plan_recovery']
    require(same(wire['reference'], external['reference']) and len(external['steps']) == 2, 'exact external raw metadata plan reference')
    first, last = external['steps']; match = [r for r in refs if r['logical_sha256'] == external['reference']['sha256']]
    require(len(match) == 1 and first['archive'] == match[0]['recovery']['archive'] == 'failed_driver01'
            and first['member'] == first['physical_member'] == match[0]['recovery']['physical_member']
            and first['sha256'] == match[0]['source']['blob']['sha256'] and first['bytes'] == match[0]['source']['blob']['compressed_bytes']
            and last == dict(operation='bounded-gzip-full-eof-crc-and-sha256', logical_sha256=external['reference']['sha256'],
                            logical_bytes=external['logical_bytes'])
            and last['logical_bytes'] == match[0]['logical_bytes'], 'lossless outer-member and inner-gzip recovery route')
    require(not proposal['missing_recovery_references'] and not proposal['forthcoming_archives'], 'all recovery proof bindings must be concrete')
    return dict(reused_blobs=93, new_blobs=54, logical_aliases=158, referenced_native_base=True, referenced_external_metadata_plan=True,
        prior_archive_payloads_read=False, prior_archive_payloads_included=False,
        meaning='Exact archived member/SHA/size/alias and independent full-EOF proof associations; recover prior beta/native bytes by their pinned Git objects and failed01 by its exact retained archive.')


def main(fd):
    require(Path.cwd() == ROOT and Path(__file__).resolve() == HERE/'archive.py'
            and Path(sys.executable).resolve() == PYTHON and sys.dont_write_bytecode and not sys.flags.optimize,
            'fixed owner, source and Python route')
    observed_environment = dict(os.environ)
    require(observed_environment == {**ENVIRONMENT, **STARTUP_ADDITIONS}, 'exact passed plus observed macOS startup environment')
    resource.setrlimit(resource.RLIMIT_CPU, (300, 300))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16*2**20, 16*2**20))
    opened = os.fstat(fd); current = LOCK.stat()
    require((opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino) and LOCK.resolve(strict=True) == LOCK,
            'exact inherited canonical descriptor')
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with LOCK.open('r+') as competing:
        try:
            fcntl.flock(competing, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
        else:
            raise RuntimeError('inherited canonical lock not held')
    require(shutil.disk_usage(ROOT).free >= 9*2**30+RESERVATION, 'entry 9GiB plus64MiB reservation before output')
    data = read_bytes(PROPOSAL)
    require(hashlib.sha256(data).hexdigest() == PROPOSAL_SHA, 'exact reviewed proposal')
    proposal = json.loads(data)
    require(proposal['archive_source'] == str(HERE) and proposal['work'] == str(WORK) and proposal['destination'] == str(RESULT)
            and same(proposal['limits'], LIMITS) and proposal['file_count'] == EXACT_COUNT and proposal['logical_bytes'] == EXACT_BYTES,
            'exact bounded retention scope')
    selected = proposal['files']
    require(len(selected) == EXACT_COUNT <= LIMITS['maximum_members']
            and sum(r['size'] for r in selected) == EXACT_BYTES <= LIMITS['maximum_logical_bytes']
            and EXACT_BYTES <= LIMITS['maximum_physical_bytes'], 'complete finite ordinary selection')
    rows = {r['path']:r for r in selected}
    require(len(rows) == len({r['member'] for r in selected}) == EXACT_COUNT and list(rows) == sorted(rows), 'unique ordered selection')
    for row in selected:
        name = PurePosixPath(row['member'])
        require(not name.is_absolute() and '..' not in name.parts and str(name) == row['path'].lstrip('/')
                and type(row['size']) is int and 0 <= row['size'] <= LIMITS['maximum_file_bytes']
                and row['identity']['size'] == row['size'] and row['identity']['nlink'] == 1,
                'safe finite ordinary archive member')
    source_guards(proposal, rows)
    validate_history(proposal, rows)
    refs = validate_references(proposal, rows)
    require(all(not p.exists() and not p.is_symlink() for p in [WORK, RESULT]), 'fresh archive output namespaces')
    WORK.mkdir(mode=0o700); sync_directory(WORK.parent)
    retained = dict(retained_current_qualified_children=3, retained_compilation_count=1, retained_driver_process_count=2,
                    retained_contexts_per_process=8, retained_historical_failed_compiler_children=1, retained_total_actual_hash_children=4,
                    hash_driver_qualified=True, application_qualified=False, performance_measurement=False, runtime_installation=False)
    receipt = dict(status='running', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
        proposal_sha256=PROPOSAL_SHA, engine_sha256=sha(Path(__file__)), workload_children=0, children=[],
        passed_environment=ENVIRONMENT, observed_environment=observed_environment, startup_environment_additions=STARTUP_ADDITIONS,
        original_status='passed-awaiting-independent-audit', original_independent_audit_status='verified', **retained)
    write(WORK/'receipt.json', encoded(receipt))
    try:
        RESULT.mkdir(mode=0o700); sync_directory(RESULT.parent)
        write(RESULT/'proposal.json', data)
        manifest = dict(policy='closed-qualified-driver-evidence-v1', proposal_sha256=PROPOSAL_SHA,
            members=selected, original_history=proposal['history'], prior_archives=proposal['prior_archives'],
            snapshots=proposal['snapshots'], complete_scoped_directories=proposal['complete_scoped_directories'],
            exclusions=proposal['exclusions'], recovery_requirements=proposal['recovery_requirements'])
        write(RESULT/'manifest.json', encoded(manifest))
        archive_path = RESULT/'evidence.tar.gz'
        with archive_path.open('xb') as output:
            with gzip.GzipFile(filename='', fileobj=CappedOutput(output), mode='wb', mtime=0, compresslevel=9) as gz:
                with tarfile.open(fileobj=gz, mode='w', format=tarfile.GNU_FORMAT) as archive:
                    for row in selected:
                        entry = tarfile.TarInfo(row['member']); entry.mode = 0o644; entry.mtime = 0; entry.size = row['size']
                        with ordinary(row['path'], row['identity']) as stream:
                            reader = SourceReader(stream); archive.addfile(entry, reader)
                            require(reader.size == row['size'] and reader.digest.hexdigest() == row['sha256'], 'complete archived source bytes')
            output.flush(); os.fsync(output.fileno())
        sync_directory(RESULT)
        proof = archive_readback(archive_path, selected)
        source_guards(proposal, rows)
        validate_history(proposal, rows)
        require(same(validate_references(proposal, rows), refs), 'recovery references changed during archive')
        require(sha(PROPOSAL) == PROPOSAL_SHA, 'proposal unchanged after archive')
        require(set(p.name for p in RESULT.iterdir()) == {'proposal.json', 'manifest.json', 'evidence.tar.gz'}, 'exact pre-summary archive output membership')
        summary = dict(status='passed', meaning='Lossless retention of three independently qualified driver02 commands plus one retained failed predecessor; no new workload qualification.',
            original_status='passed-awaiting-independent-audit', original_independent_audit_status='verified', workload_children=0,
            proposal_sha256=PROPOSAL_SHA, manifest_sha256=sha(RESULT/'manifest.json'),
            passed_environment=ENVIRONMENT, observed_environment=observed_environment, startup_environment_additions=STARTUP_ADDITIONS,
            archive=dict(sha256=sha(archive_path), bytes=archive_path.stat().st_size, logical_bytes=EXACT_BYTES, **proof),
            external_references=refs, source_bytes_and_identities_unchanged=True, limits=LIMITS, **retained)
        write(RESULT/'summary.json', encoded(summary))
        sync_directory(RESULT); sync_directory(RESULT.parent)
        require(set(p.name for p in RESULT.iterdir()) == {'proposal.json', 'manifest.json', 'evidence.tar.gz', 'summary.json'}, 'exact complete publication membership')
        receipt.update(status='passed', archive_sha256=summary['archive']['sha256'], manifest_sha256=summary['manifest_sha256'],
            summary_sha256=sha(RESULT/'summary.json'), member_count=EXACT_COUNT, logical_bytes=EXACT_BYTES,
            full_member_readback=True, full_gzip_eof_crc=True, free_bytes_after=shutil.disk_usage(ROOT).free, read_bytes=READ_BYTES)
        guard()
    except BaseException as error:
        receipt.update(status='failed', error=repr(error), partial_outputs_retained=True)
        raise
    finally:
        receipt['finished_at'] = time.time()
        write(WORK/'receipt.json', encoded(receipt), replace=True)
    print(json.dumps(dict(status='passed', receipt=str(WORK/'receipt.json'), receipt_sha256=sha(WORK/'receipt.json'),
        archive_sha256=receipt['archive_sha256'], workload_children=0)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--canonical-fd', required=True, type=int)
    main(parser.parse_args().canonical_fd)
