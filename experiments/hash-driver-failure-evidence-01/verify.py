"""Independent bounded read-only audit of the exact failed-driver archive.

Actual receipt, wrapper record and summary digests are supplied only after
archive closure. This file does not import or execute the archive engine.
"""
import argparse
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import stat
import sys
import tarfile
import time

R = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
H = R/'experiments/hash-driver-failure-evidence-01'
W = R/'.work/hash-driver-failure-evidence-01'
E = R/'.work/hash-driver-failure-retention-execution-01'
D = R/'results/hir-options-hash-driver-failure-01'
OUT = O/'.work/hash-driver-failure-retention-independent-verification-01.json'
PROPOSAL = O/'.work/hash-driver-failure-retention-proposal-01.json'
PROPOSAL_SHA = '8a3b56f5dd8d52e12e14389bba3771fea32c3d06cf3b2b4b5348330aeebafe13'
ENGINE_SHA = 'b25988ef89e6254a9ae2871ee97eabc07d0701c4548023fc348df690f74fd8ad'
WRAPPER_SHA = '7374e447ed5a5b785b6968ad29abff4c2b89fbb36c30e4abdfbdd17b8ac60568'
OWNED = X/'experiments/stable-cgu/owned_stage.py'
OWNED_SHA = '7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e'
PYTHON = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
ENVIRONMENT = dict(HOME='/Users/danluu', USER='danluu', LOGNAME='danluu', LANG='C', LC_ALL='C',
                   TZ='UTC', PATH='/usr/bin:/bin:/usr/sbin:/sbin', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
START = time.monotonic()
READ = 0


def check(ok, message):
    if not ok:
        raise RuntimeError(message)


def guard():
    check(time.monotonic()-START <= 300 and shutil.disk_usage(O).free >= 9*2**30, 'finite read-only time and live floor')


def count(size):
    global READ
    guard(); READ += size
    check(READ <= 512*2**20, 'bounded total audit reads')


def identity(path):
    s = Path(path).lstat()
    return {key: getattr(s, 'st_'+key) for key in FIELDS}


def raw(path, row=None):
    path = Path(path); before = identity(path)
    check(path.resolve(strict=True) == path and stat.S_ISREG(before['mode']) and before['size'] <= 64*2**20, 'ordinary bounded audit input')
    if row is not None:
        check(before == row['identity'], 'selected input identity')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        held = os.fstat(stream.fileno())
        check({k: getattr(held, 'st_'+k) for k in FIELDS} == before, 'opened audit input')
        data = stream.read(64*2**20+1); count(len(data))
        held = os.fstat(stream.fileno())
        check({k: getattr(held, 'st_'+k) for k in FIELDS} == before, 'held audit input unchanged')
    check(len(data) == before['size'] and path.resolve(strict=True) == path and identity(path) == before, 'stable complete audit input')
    if row is not None:
        check(len(data) == row['size'] and hashlib.sha256(data).hexdigest() == row['sha256'], 'selected source bytes')
    return data


def digest(path):
    return hashlib.sha256(raw(path)).hexdigest()


def read(path):
    return json.loads(raw(path))


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def membership(path):
    path = Path(path)
    check(path.resolve(strict=True) == path and path.is_dir(), 'ordinary closed evidence root')
    found = []; total = 0
    for root, dirs, files in os.walk(path, followlinks=False, onerror=lambda e: (_ for _ in ()).throw(e)):
        guard()
        for name in dirs+files:
            p = Path(root)/name; s = p.lstat(); total += 1
            check(total <= 1024 and (stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode)), 'bounded closed ordinary membership')
            if stat.S_ISREG(s.st_mode):
                found.append(str(p.relative_to(path)))
    return sorted(found)


def verify_external(proposal, original_manifest, rows):
    catalogs = {}
    for role, archive in proposal['prior_archives'].items():
        docs = {}
        for key in ['manifest', 'summary', 'independent_audit']:
            reference = archive[key]; row = rows[reference['path']]
            check(row['sha256'] == reference['sha256'] and row['size'] == reference['size'] and row['identity'] == reference['identity'], 'selected prior archive proof')
            docs[key] = json.loads(raw(row['path'], row))
        manifest, summary, audit = (docs[k] for k in ['manifest', 'summary', 'independent_audit'])
        check(summary['status'] == 'passed' and audit['status'] == 'verified'
              and summary['archive']['sha256'] == audit['archive_sha256'] == archive['sha256']
              and summary['archive']['bytes'] == archive['size']
              and summary['manifest_sha256'] == audit['manifest_sha256'] == archive['manifest']['sha256']
              and audit['summary_sha256'] == archive['summary']['sha256']
              and audit['full_gzip_eof_crc'] is audit['full_member_readback'] is True, 'published archive qualification')
        check(re.fullmatch('[0-9a-f]{40}', archive['git_blob']) is not None, 'explicit retained Git object reference')
        catalogs[role] = manifest

    def resolve(ref, original_path, expected_sha, size):
        check(ref['logical_member'] == original_path.lstrip('/') and ref['sha256'] == expected_sha and ref['size'] == size,
              'exact original-to-archive member reference')
        catalog = catalogs[ref['archive']]; current = ref['logical_member']; chain = []
        while True:
            check(current in catalog and current not in chain and len(chain) < 256, 'finite acyclic published member route')
            chain.append(current); row = catalog[current]
            check(row['sha256'] == expected_sha and row['bytes'] == size, 'published member byte association')
            if 'linkname' not in row:
                break
            current = row['linkname']
        check(chain == ref['alias_chain'] and current == ref['physical_member'], 'complete exact physical archive reference')

    snapshots = proposal['snapshots']; seen = set()
    for ref in snapshots['reused_archive_associations']:
        source = ref['source']; key = source['blob']['logical_sha256']
        check(key not in seen and source == original_manifest['reuse'][key]
              and original_manifest['storage'][key] == dict(kind='reused', path=source['path']), 'complete unique reused blob')
        seen.add(key)
        resolve(ref['archived'], source['path'], source['blob']['sha256'], source['blob']['compressed_bytes'])
    check(len(seen) == 34 and seen == set(original_manifest['reuse']), 'every reused blob associated')
    base = snapshots['compact_base_archive_association']
    compact_path = str(R/'experiments/hir-options-hash-driver-stage-02/inputs.json')
    compact = json.loads(raw(compact_path, rows[compact_path]))
    check(base['reference'] == compact['file_table_base'], 'exact original native03 base reference')
    resolve(base['archived'], base['reference']['path'], base['reference']['sha256'], compact['files'][base['reference']['path']]['size'])
    return dict(reused_blobs=34, referenced_native_base=True, prior_archive_payloads_reread=False,
                reference_semantics='Exact published manifest, member aliases, SHA-256 and Git object associations; prior full archive audits remain historical observations.')


def archive_members(selected, expected_sha):
    path = D/'evidence.tar.gz'; before = identity(path)
    check(path.resolve(strict=True) == path and stat.S_ISREG(before['mode']) and before['size'] <= 32*2**20, 'exact bounded ordinary archive')
    check(digest(path) == expected_sha, 'actual summary authenticates compressed bytes before parsing')
    expanded = 0
    # Establish a finite complete gzip stream before decoding tar metadata.
    with gzip.open(path, 'rb') as stream:
        while block := stream.read(2**20):
            count(len(block)); expanded += len(block)
            check(expanded <= 132*2**20, 'finite full expanded gzip stream')
    check(identity(path) == before, 'archive changed during bounded preliminary EOF check')
    class BoundedTarReader:
        def __init__(self, stream):
            self.stream = stream
            self.total = 0
        def read(self, size):
            check(type(size) is int and 0 <= size <= 2**20, 'bounded tar decoder input request')
            block = self.stream.read(size)
            count(len(block)); self.total += len(block)
            check(self.total <= 132*2**20, 'finite tar metadata and payload expansion')
            return block
    count_members = 0; logical = 0
    with gzip.open(path, 'rb') as source:
        bounded = BoundedTarReader(source)
        with tarfile.open(fileobj=bounded, mode='r|') as archive:
            for member in archive:
                guard()
                check(count_members < 168, 'bounded actual archive members')
                row = selected[count_members]
                check(member.name == row['member'] and member.isfile() and member.size == row['size']
                      and member.mode == 0o644 and member.mtime == member.uid == member.gid == 0
                      and member.uname == member.gname == member.linkname == '', 'exact deterministic ordered ordinary member')
                stream = archive.extractfile(member); h = hashlib.sha256(); size = 0
                while block := stream.read(2**20):
                    guard(); size += len(block); h.update(block)
                check(size == row['size'] and h.hexdigest() == row['sha256'], 'independent complete archive member hash')
                logical += size; count_members += 1
            while block := archive.fileobj.read(2**20):
                check(not any(block), 'nonzero tar trailer')
        check(source.read(1) == b'' and bounded.total == expanded, 'complete independent bounded tar and gzip EOF')
    check(count_members == 168 and logical == 40467639 and expanded >= logical and identity(path) == before
          and path.resolve(strict=True) == path, 'complete stable archive and full gzip EOF')
    return dict(members=count_members, logical_bytes=logical, expanded_bytes=expanded,
                bytes=before['size'], sha256=digest(path), full_member_readback=True, full_gzip_eof_crc=True)


def main(args):
    check(Path.cwd() == O and Path(sys.executable).resolve() == PYTHON and sys.dont_write_bytecode and not sys.flags.optimize,
          'fixed independent audit owner and Python')
    check(not OUT.exists() and not OUT.is_symlink(), 'fresh independent audit result')
    resource.setrlimit(resource.RLIMIT_CPU, (180, 180)); resource.setrlimit(resource.RLIMIT_FSIZE, (2*2**20, 2*2**20))
    opened = os.fstat(args.canonical_fd); current = LOCK.stat()
    check((opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino) and LOCK.resolve(strict=True) == LOCK, 'held canonical descriptor')
    fcntl.flock(args.canonical_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with LOCK.open('r+') as competing:
        try:
            fcntl.flock(competing, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
        else:
            raise RuntimeError('canonical descriptor was not held')
    started = time.time(); guard()
    for value in [args.receipt_sha256, args.execution_record_sha256, args.summary_sha256]:
        check(re.fullmatch('[0-9a-f]{64}', value) is not None, 'explicit actual closure digest')
    check(digest(W/'receipt.json') == args.receipt_sha256 and digest(E/'record.json') == args.execution_record_sha256
          and digest(D/'summary.json') == args.summary_sha256, 'exact actual closed archive bindings')
    check(digest(H/'archive.py') == ENGINE_SHA and digest(H/'execute.py') == WRAPPER_SHA and digest(OWNED) == OWNED_SHA
          and digest(PROPOSAL) == PROPOSAL_SHA and raw(PROPOSAL) == raw(D/'proposal.json'), 'reviewed source and exact retained proposal')
    proposal = read(PROPOSAL); selected = proposal['files']; rows = {r['path']: r for r in selected}
    check(len(rows) == len(selected) == 168 and sum(r['size'] for r in selected) == 40467639, 'exact proposal census')
    for row in selected:
        raw(row['path'], row)
    for root, expected in proposal['complete_scoped_directories'].items():
        check(membership(root) == expected, 'complete closed original membership')
    terminal = read(W/'receipt.json'); execution = read(E/'record.json'); summary = read(D/'summary.json'); manifest = read(D/'manifest.json')
    check(execution['status'] == 'finished' and execution['returncode'] == 0 and execution['result_sha256'] == args.summary_sha256
          and execution['execution_source_sha256'] == WRAPPER_SHA and execution['source_hashes'] == {str(H/'archive.py'): ENGINE_SHA, str(OWNED): OWNED_SHA, str(PROPOSAL): PROPOSAL_SHA}
          and execution['cwd'] == str(R) and execution['environment'] == ENVIRONMENT
          and execution['command'][:3] == [str(PYTHON), '-B', str(H/'archive.py')]
          and len(execution['command']) == 5 and execution['command'][3] == '--canonical-fd'
          and execution['command'][4].isdigit(), 'actual explicit archive child owner and argv')
    check(terminal['status'] == summary['status'] == 'passed' and terminal['children'] == []
          and terminal['workload_children'] == summary['workload_children'] == 0
          and terminal['pid'] == execution['pid'] and terminal['parent_pid'] == execution['parent_pid']
          and execution['started_at'] <= execution['admitted_at'] <= terminal['started_at'] <= terminal['finished_at'] <= execution['finished_at']
          <= execution['canonical_released_at'] <= started and not execution.get('may_be_live')
          and not execution.get('execution_error') and not execution.get('initial_child_publication_error'), 'closed actual archive lifetime and release')
    check(execution['canonical_lock'] == str(LOCK) and execution['wait_seconds'] == 600
          and execution['maximum_child_cpu_seconds'] == 300 and execution['maximum_child_read_seconds'] == 600
          and execution['maximum_observation_seconds'] == 650 and execution['maximum_file_bytes'] == 32*2**20
          and execution['capacity'] == dict(entry_bytes=9*2**30+64*2**20, stop_gib=9, floor_gib=8, reservation_bytes=64*2**20)
          and execution['entry_free_bytes'] >= 9*2**30+64*2**20 and execution['free_bytes_before'] >= 9*2**30+64*2**20
          and execution['free_bytes_after'] >= 9*2**30 and all(r['free_bytes'] >= 9*2**30 for r in execution['disk_samples']), 'unchanged actual capacity gates')
    for name in ['stdout', 'stderr']:
        check(digest(E/name) == execution[name+'_sha256'], 'actual archive raw association')
    check(not raw(E/'stderr'), 'clean archive child stderr')
    check(read(E/'stdout') == dict(status='passed', receipt=str(W/'receipt.json'), receipt_sha256=args.receipt_sha256,
                                  archive_sha256=terminal['archive_sha256'], workload_children=0), 'actual archive child output')
    for original, name in [(H/'archive.py', 'archive.py'), (PROPOSAL, 'proposal.json'), (OWNED, 'owned_stage.py'), (H/'execute.py', 'execution.py')]:
        check(raw(original) == raw(E/'source'/name), 'full retained source capsule')
    check(membership(E) == sorted(['record.json', 'stderr', 'stdout', 'source/archive.py', 'source/proposal.json', 'source/owned_stage.py', 'source/execution.py'])
          and membership(W) == ['receipt.json'] and membership(D) == ['evidence.tar.gz', 'manifest.json', 'proposal.json', 'summary.json'], 'complete current retention output membership')
    expected_manifest = dict(policy='closed-failed-driver-evidence-v1', proposal_sha256=PROPOSAL_SHA,
                             members=selected, original_history=proposal['history'], prior_archives=proposal['prior_archives'],
                             snapshots=proposal['snapshots'], prior_packet_audits=proposal['prior_packet_audits'], exclusions=proposal['exclusions'])
    check(encoded(manifest) == encoded(expected_manifest) and terminal['manifest_sha256'] == summary['manifest_sha256'] == digest(D/'manifest.json')
          and terminal['summary_sha256'] == args.summary_sha256 and terminal['engine_sha256'] == ENGINE_SHA
          and terminal['proposal_sha256'] == summary['proposal_sha256'] == PROPOSAL_SHA, 'complete manifest/source/summary association')
    proof = archive_members(selected, summary['archive']['sha256'])
    check(encoded(proof) == encoded(summary['archive']) and terminal['archive_sha256'] == proof['sha256']
          and terminal['member_count'] == 168 and terminal['logical_bytes'] == 40467639
          and terminal['full_member_readback'] is terminal['full_gzip_eof_crc'] is summary['source_bytes_and_identities_unchanged'] is True,
          'independent actual readback equals claimed result')
    failed_work = R/'.work/hir-options-hash-driver-01'
    original = read(failed_work/'receipt.json'); failure = read(R/'.work/hir-options-hash-driver-failure-verification-01.json')
    check(original['status'] == 'failed' and failure['status'] == 'verified-retained-failure'
          and failure['receipt_sha256'] == digest(failed_work/'receipt.json') == proposal['history']['receipt_sha256']
          and digest(R/'.work/hir-options-hash-driver-failure-verification-01.json') == proposal['history']['failure_audit_sha256']
          and failure['actual_compiler_children'] == 1 and failure['actual_driver_processes'] == 0, 'original audited failure unchanged')
    check(summary['original_status'] == terminal['original_status'] == 'failed'
          and summary['actual_compiler_children'] == terminal['actual_compiler_children'] == 1
          and summary['actual_driver_processes'] == terminal['actual_driver_processes'] == 0
          and summary['hash_driver_qualified'] is summary['application_qualified'] is summary['performance_measurement'] is False,
          'retention never qualifies the failed compiler')
    old_manifest = read(failed_work/'source-snapshots.json')
    check(len(old_manifest['files']) == 103 and len(old_manifest['blobs']) == 99, 'complete original logical selection')
    stored = {k: v for k, v in old_manifest['storage'].items() if v['kind'] == 'stored'}
    check(len(stored) == 65 and sum(old_manifest['blobs'][k]['compressed_bytes'] for k in stored) == 9460166, 'all newly stored snapshot blobs')
    for key, value in stored.items():
        row = rows[value['path']]; blob = old_manifest['blobs'][key]
        check(row['sha256'] == blob['sha256'] and row['size'] == blob['compressed_bytes'], 'selected new snapshot bytes')
    references = verify_external(proposal, old_manifest, rows)
    for row in selected:
        check(identity(row['path']) == row['identity'], 'final source identities unchanged')
    check(digest(W/'receipt.json') == args.receipt_sha256 and digest(E/'record.json') == args.execution_record_sha256
          and digest(D/'summary.json') == args.summary_sha256 and digest(D/'evidence.tar.gz') == proof['sha256'],
          'actual closure and archive stable through independent audit')
    report = dict(status='verified', pid=os.getpid(), parent_pid=os.getppid(), started_at=started, finished_at=time.time(),
                  verifier_sha256=digest(Path(__file__)), proposal_sha256=PROPOSAL_SHA, engine_sha256=ENGINE_SHA,
                  wrapper_sha256=WRAPPER_SHA, receipt_sha256=args.receipt_sha256, execution_record_sha256=args.execution_record_sha256,
                  summary_sha256=args.summary_sha256, manifest_sha256=summary['manifest_sha256'], archive=proof,
                  complete_selected_source_bytes_and_identities=True, closed_archive_processing_children=1, workload_children=0,
                  original_status='failed', historical_compiler_children=1, historical_driver_processes=0,
                  application_qualified=False, hash_driver_qualified=False, performance_measurement=False,
                  selected_files=168, logical_bytes=40467639, new_gzip_blobs=65, external_references=references,
                  original_failure_audit_sha256=proposal['history']['failure_audit_sha256'], read_bytes=READ,
                  identity_limitation=execution['identity_limitation'])
    data = (json.dumps(report, sort_keys=True, indent=2)+'\n').encode()
    check(len(data) <= 2*2**20, 'bounded independent report')
    with OUT.open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps(dict(report=str(OUT), sha256=digest(OUT), status='verified')), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--receipt-sha256', required=True)
    p.add_argument('--execution-record-sha256', required=True)
    p.add_argument('--summary-sha256', required=True)
    p.add_argument('--canonical-fd', required=True, type=int)
    main(p.parse_args())
