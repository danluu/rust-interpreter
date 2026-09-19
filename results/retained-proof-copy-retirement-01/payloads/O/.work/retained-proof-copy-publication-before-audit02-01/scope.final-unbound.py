"""Unrun bounded metadata census; never read selected copies or provider blobs."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import stat
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HERE = Path(__file__).resolve().parent
SOURCE = ROOT/'experiments/retained-proof-copy-retirement-01'
TARGET = O/'.work/hir-options-hash-run-make-01/retained'
WORK = ROOT/'.work/retained-proof-copy-retirement-01'
DEST = ROOT/'results/retained-proof-copy-retirement-01'
OUTPUT = O/'.work/retained-proof-copy-publication-scope-01.json'
PROPOSAL = X/'.work/runtime04-retained-copy-retirement-proposal-01.json'
PROPOSAL_SHA = 'e0599d87ab842b9e18932fddb54bb63aaf850cd2366279f67507e875731b3481'
PACKET_SHA = '9d5d2ce855ec5ff52eadce25d332b2c81259305577630324146d3d9e1c3499fd'
RECOVERY_SHA = 'b671db7b48989f16ebcecbe67c0396abf89a5ec59e937cecd29edcb7c682f251'
RECOVERY_EXECUTION_SHA = '85ce36c2e82e112a03cb18e6d429a3aa5b04c24caa7c3a279e884c9bb93e1862'
READER_AUDIT_SHA = '494e64b61b17b943334d062f882d0fa944e7864e76d57d3ff9b2d97ece787662'
READER_PUBLICATION_SHA = '78f5e9f47db952c7a81fc81f99fcdeec557ecd365dea8438d4220c318d251f32'
FAILED_AUDIT_RECORD_SHA = 'c6c07ff73138803ce147fd67219f82ad8efcb7ea8a3400b422fa06bfbdacdb96'
FAILED_AUDIT_STDERR_SHA = 'f6d0270953f468523d91237df3b0eb029b198a963449bce7c5299d7a9b67cff4'
AUDIT_SOURCE_HANDOFF = ROOT/'.work/retirement-saved-auditor02-source-handoff-02.json'
AUDIT_SOURCE_HANDOFF_SHA = 'ef5a86265f2f7066ca7af6d9c6575eec8d8d1fe2bb73fa8d27255d070905fbc0'
PUBLICATION_HISTORY = O/'.work/retained-proof-copy-publication-before-audit02-01'
INTERIM_PUBLICATION_HISTORY = O/'.work/retained-proof-copy-publication-before-canonical-report-01'
ACTUAL = None  # receipt_sha256, execution_sha256, audit_sha256, audit_execution_sha256
REVIEW_FILES = None  # Exact list of final {path,sha256} root/peer source reviews.
LIMITS = dict(maximum_files=256, maximum_file_bytes=4*2**20,
              maximum_source_bytes=12*2**20, maximum_output_bytes=16*2**20)
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(path):
    info = Path(path).lstat()
    return {key: getattr(info, 'st_'+key) for key in FIELDS}


class Census:
    def __init__(self):
        self.started = time.monotonic()
        self.files = {}
        self.trees = {}
        self.read_bytes = 0

    def guard(self):
        require(time.monotonic()-self.started <= 300, 'finite publication census')
        require(shutil.disk_usage(ROOT).free >= 9*2**30, 'publication census live floor')

    def add(self, path, role, expected=None):
        self.guard(); path = Path(path)
        require(path.is_absolute() and '..' not in path.parts and not path.is_relative_to(TARGET),
                'selected-copy namespace cannot be read by publication')
        require(path.suffix not in ['.gz', '.rlib', '.dylib', '.so', '.a', '.o'],
                'provider/archive/blob bytes must remain external references')
        require(path.suffix in ['.py', '.json', '.jsonl', '.md', '.diff', '.log']
                or path.name in ['stdout', 'stderr'], 'only explicit source or saved evidence formats')
        owner = next(((name, root) for name, root in [('ROOT', ROOT), ('O', O), ('A', A), ('X', X)]
                      if path.is_relative_to(root)), None)
        require(owner is not None and path.resolve(strict=True) == path, 'ordinary explicit task-owned source')
        before = identity(path)
        require(stat.S_ISREG(before['mode']) and before['size'] <= LIMITS['maximum_file_bytes'],
                'bounded ordinary source only')
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
            opened = {key: getattr(os.fstat(stream.fileno()), 'st_'+key) for key in FIELDS}
            require(opened == before, 'source replaced before open')
            raw = stream.read(LIMITS['maximum_file_bytes']+1)
            require({key: getattr(os.fstat(stream.fileno()), 'st_'+key) for key in FIELDS} == before,
                    'source changed during read')
        require(identity(path) == before and len(raw) == before['size'], 'source route changed')
        digest = sha(raw); require(expected is None or digest == expected, 'exact evidence digest differs')
        self.read_bytes += len(raw)
        require(self.read_bytes <= 64*2**20, 'bounded cumulative census reads')
        destination = 'payloads/'+owner[0]+'/'+str(path.relative_to(owner[1]))
        row = dict(source=str(path), destination=destination, size=len(raw), sha256=digest,
                   identity=before, roles=[role])
        if str(path) in self.files:
            prior = self.files[str(path)]
            require(all(prior[key] == row[key] for key in row if key != 'roles'), 'repeated source changed')
            prior['roles'] = sorted(set(prior['roles']+[role]))
        else:
            self.files[str(path)] = row
        require(len(self.files) <= LIMITS['maximum_files']
                and sum(row['size'] for row in self.files.values()) <= LIMITS['maximum_source_bytes'],
                'finite selected publication scope')
        return raw

    def document(self, path, role, expected=None):
        def unique(pairs):
            value = {}
            for key, item in pairs:
                require(key not in value, 'duplicate JSON key'); value[key] = item
            return value
        return json.loads(self.add(path, role, expected), object_pairs_hook=unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))

    def tree(self, root, role):
        root = Path(root); self.guard()
        require(root.resolve(strict=True) == root and root.is_dir()
                and not root.is_relative_to(TARGET), 'exact ordinary evidence tree')
        inventory = {'.': dict(kind='directory', identity=identity(root))}
        pending = [root]
        while pending:
            directory = pending.pop()
            for path in sorted(directory.iterdir()):
                self.guard(); row = identity(path)
                require(not path.is_symlink() and len(inventory) < 256, 'finite ordinary evidence membership')
                if stat.S_ISDIR(row['mode']):
                    inventory[str(path.relative_to(root))] = dict(kind='directory', identity=row)
                    pending.append(path)
                else:
                    require(stat.S_ISREG(row['mode']), 'nonordinary evidence member')
                    self.add(path, role)
                    inventory[str(path.relative_to(root))] = dict(kind='file', identity=row)
        self.trees[str(root)] = inventory

    def closed(self, directory, expected, phase):
        directory = Path(directory)
        record = self.document(directory/'record.json', 'actual closed '+phase, expected)
        require(record['status'] == 'finished' and type(record['returncode']) is int and record['returncode'] == 0
                and record.get('observation_errors', []) == []
                and all(not record.get(key) for key in ['error', 'execution_error', 'publication_error',
                                                       'child_may_remain_live', 'capacity_violation']),
                'actual explicit successful closure required')
        require(type(record['pid']) is int and type(record['parent_pid']) is int
                and record['started_at'] <= record['finished_at'], 'actual child identity/time required')
        for name in ['stdout', 'stderr']:
            self.add(directory/name, 'actual raw '+phase, record[name+'_sha256'])
        require(self.files[str(directory/'stderr')]['size'] == 0, 'passed phase emitted stderr')
        self.tree(directory, 'complete closed '+phase+' source/raw/record')
        return record

    def failed_audit(self, actual):
        directory = ROOT/'.work/retained-proof-copy-retirement-audit-execution-01'
        record = self.document(directory/'record.json', 'original closed failed audit01', FAILED_AUDIT_RECORD_SHA)
        require(record['status'] == 'finished' and type(record['returncode']) is int
                and record['returncode'] == 1 and record['phase'] == 'audit'
                and record['pid'] == 19237 and record['parent_pid'] == 18291
                and record['observation_errors'] == [] and not record.get('child_may_remain_live')
                and 'canonical_released_at' not in record
                and record['started_at'] <= record['child_started_at'] <= record['finished_at'],
                'preserve exact failed audit closure without inventing a release')
        require(record['command'] == [
                '/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14',
                '-B', str(SOURCE/'verify_retirement.py'), '--inputs-sha256', PACKET_SHA,
                '--receipt-sha256', actual['receipt_sha256'], '--execution-sha256', actual['execution_sha256']]
                and record['error'] == "RuntimeError('phase failed after explicit child closure; no retry')",
                'failed audit belongs to unchanged passed retirement')
        self.add(directory/'stdout', 'original empty failed audit stdout', record['stdout_sha256'])
        self.add(directory/'stderr', 'original failed audit traceback', FAILED_AUDIT_STDERR_SHA)
        require(self.files[str(directory/'stdout')]['size'] == 0
                and record['stderr_sha256'] == FAILED_AUDIT_STDERR_SHA
                and 'result_path' not in record and 'result_sha256' not in record,
                'original failed audit has no successful report association')
        self.tree(directory, 'complete failed audit01 source/raw/record')
        return dict(execution=dict(path=str(directory/'record.json'), sha256=FAILED_AUDIT_RECORD_SHA),
                    stderr=dict(path=str(directory/'stderr'), sha256=FAILED_AUDIT_STDERR_SHA),
                    status='finished', returncode=1, successful_report_association=False,
                    release_timestamp_recorded=False)


def main():
    require(type(ACTUAL) is dict and set(ACTUAL) ==
            {'receipt_sha256', 'execution_sha256', 'audit_sha256', 'audit_execution_sha256'}
            and all(type(value) is str and len(value) == 64 for value in ACTUAL.values()),
            'actual retirement/audit closure remains unbound')
    require(type(REVIEW_FILES) is list and 0 < len(REVIEW_FILES) <= 32
            and all(set(row) == {'path', 'sha256'} for row in REVIEW_FILES), 'final reviewed source list remains unbound')
    require(not os.path.lexists(OUTPUT) and not os.path.lexists(DEST), 'fresh single-use publication scope')
    require(shutil.disk_usage(ROOT).free >= 16*2**30, 'fresh16 before census')
    resource.setrlimit(resource.RLIMIT_CPU, (300, 300)); resource.setrlimit(resource.RLIMIT_FSIZE, (4*2**20, 4*2**20))
    c = Census()
    proposal = c.document(PROPOSAL, 'immutable selected21 recovery map', PROPOSAL_SHA)
    packet = c.document(SOURCE/'plan-01.json', 'exact prepared retirement packet', PACKET_SHA)
    selected = sorted(str(TARGET/name) for name in proposal['selected'])
    require(len(selected) == len(set(selected)) == 21 and packet['selected_paths'] == selected,
            'exact original selected21 scope')
    recovery = c.document(ROOT/'.work/retained-proof-copy-recovery-01.json', 'actual full recovery', RECOVERY_SHA)
    recovered = c.closed(ROOT/'.work/retained-proof-copy-recovery-execution-01', RECOVERY_EXECUTION_SHA, 'recovery')
    require(recovery['status'] == 'verified-read-only-exact-copy-recovery'
            and recovered['result_sha256'] == RECOVERY_SHA, 'actual recovery association')
    terminal = c.document(WORK/'receipt.json', 'actual retirement terminal', ACTUAL['receipt_sha256'])
    outer = c.closed(ROOT/'.work/retained-proof-copy-retirement-execution-01', ACTUAL['execution_sha256'], 'retirement')
    failed_audit = c.failed_audit(ACTUAL)
    audit_path = ROOT/'.work/retained-proof-copy-retirement-independent-verification-01.json'
    audit = c.document(audit_path, 'actual independent retirement audit', ACTUAL['audit_sha256'])
    audited = c.closed(ROOT/'.work/retained-proof-copy-retirement-audit-execution-02', ACTUAL['audit_execution_sha256'], 'retirement audit02')
    handoff = c.document(AUDIT_SOURCE_HANDOFF, 'corrected audit02 canonical report provenance', AUDIT_SOURCE_HANDOFF_SHA)
    require(handoff['verifier']['sha256'] == audited['auditor_sha256']
            and handoff['executor']['sha256'] == audited['wrapper_sha256']
            and handoff['original_failed_audit'] == failed_audit['execution'],
            'exact reviewed corrected audit02 sources and failed01 association')
    for key in ['verifier', 'executor', 'before_verifier', 'before_executor']:
        row = handoff[key]; c.add(row['path'], 'corrected audit02 source history', row['sha256'])
    prior_ref = handoff['prior_handoff']
    prior_handoff = c.document(prior_ref['path'], 'initial audit02 directory-identity correction', prior_ref['sha256'])
    for row in handoff['diffs']+prior_handoff['diffs']:
        c.add(row['path'], 'exact audit02 source correction diff', row['sha256'])
    require(terminal['status'] == 'passed' and terminal['packet_sha256'] == PACKET_SHA
            and outer['receipt_sha256'] == ACTUAL['receipt_sha256']
            and outer['pid'] == terminal['pid'] and outer['parent_pid'] == terminal['parent_pid']
            and terminal['finished_at'] <= terminal['canonical_released_at'] <= outer['finished_at'],
            'actual passed retirement/outer association')
    require(audit['status'] == 'verified-exact-proof-copy-retirement'
            and type(audit['audit_attempt']) is int and audit['audit_attempt'] == 2
            and audit['prior_failed_audit'] == failed_audit['execution']
            and audit['audit_execution_directory'] == str(ROOT/'.work/retained-proof-copy-retirement-audit-execution-02')
            and audit['verifier_sha256'] == handoff['verifier']['sha256']
            and audit['receipt_sha256'] == ACTUAL['receipt_sha256'] and audit['execution_sha256'] == ACTUAL['execution_sha256']
            and audit['packet_sha256'] == PACKET_SHA and audit['selected_paths'] == selected
            and all(type(audit[key]) is int and audit[key] == value for key, value in
                    dict(removed_files=21, preserved_files=40, durable_events=63, removed_directories=0, chmod_operations=0).items())
            and all(audit[key] is True for key in ['full_ledger_replay', 'source_witness_readback', 'preserved40_readback'])
            and audited['result_path'] == str(audit_path) and audited['result_sha256'] == ACTUAL['audit_sha256']
            and audited['pid'] == audit['pid'] and audited['parent_pid'] == audit['parent_pid']
            and audit['finished_at'] <= audited['finished_at'] <= audited['canonical_released_at'],
            'actual independent closed exact21 audit required')
    c.tree(WORK, 'complete21 retirement/63-event ledger and two probes')
    ledger = c.add(WORK/'deleted.jsonl', 'all63 durable ledger events', audit['ledger_sha256'])
    require(ledger.endswith(b'\n') and len(ledger.splitlines()) == 63, 'complete saved ledger')
    for name in ['retained-proof-copy-recovery-preparation-execution-01',
                 'retained-proof-copy-retirement-preparation-execution-01']:
        prepared = c.closed(ROOT/'.work'/name, None, 'preparation')
        expected_packet = recovery['inputs_sha256'] if 'recovery-preparation' in name else PACKET_SHA
        require(prepared['prepared_packet']['sha256'] == expected_packet
                and prepared['finished_at'] <= prepared['canonical_released_at'],
                'actual preparation output/release association')
    c.tree(SOURCE, 'complete immutable recovery/retirement source and packets')
    c.tree(HERE, 'publication source')
    c.tree(PUBLICATION_HISTORY, 'preserved unbound publication draft and audit02 correction')
    c.tree(INTERIM_PUBLICATION_HISTORY, 'preserved interim report02 route and canonical report01 correction')
    declarations = c.document(packet['declarations']['path'], 'four-owner concrete declaration', packet['declarations']['sha256'])
    for row in declarations['no_consumer']['acknowledgments'].values():
        c.document(row['path'], 'actual owner acknowledgment', row['sha256'])
    for group in declarations['no_consumer']['closed_metadata']:
        for key in ['terminal', 'outer', 'launch', 'audit', 'launcher', 'result', 'execution', 'stdout', 'stderr']:
            if key in group:
                row = group[key]; c.add(row['path'], 'original closed owner/failure history', row['sha256'])
    for owner in declarations['no_consumer']['closed_owners']:
        row = owner['receipt']; c.add(row['path'], 'original exact historical PS-child receipt', row['sha256'])
    c.document(ROOT/'.work/runtime04-historical-copy-reader-independent-verification-05.json', 'qualified strict Reader rehearsal', READER_AUDIT_SHA)
    binding = c.document(ROOT/'.work/retained-proof-copy-actual-source-binding-01.json', 'reviewed source binding history')
    for row in binding['files'].values():
        for key in ['before', 'diff']:
            c.add(row[key]['path'], 'preserved source binding predecessor/diff', row[key]['sha256'])
    for row in REVIEW_FILES:
        c.add(row['path'], 'exact independently reviewed source/history', row['sha256'])
    runmake = O/'results/hir-options-hash-run-make-01'
    run_manifest = c.document(runmake/'manifest.json', 'complete original archived member map',
                              '9471239525c83c77902ab3fe1a1b507c9596315a2a56e48082a7fbde590c7ded')
    run_summary = c.document(runmake/'summary.json', 'original archive closure metadata',
                             '6020a63ccdfb0b48ad66faba3433ab2092cf905ae2ec580ffc58d09fd7dc2cb5')
    c.document(runmake/'independent-verification.json', 'original archive full member/EOF audit',
               'ecb0f20a3c6479da703d55e71e3f1b76d8589bcb54b178524a740230d6cae052')
    c.document(runmake/'archive-execution.json', 'original archive complete execution association',
               '44a2d35634bb6bf072ac4fb3d44c81b65382457795c7dbaa19904e51fca5646c')
    require(run_summary['archive_sha256'] == recovery['archive']['sha256']
            == proposal['archived_recovery']['archive']['sha256'], 'same exact external recovery archive')
    reader_pub = c.document(A/'.work/runtime04-reader03-publication-verification-01.json', 'lossless Reader/failure history publication', READER_PUBLICATION_SHA)
    reader_manifest_path = ROOT/'results/runtime04-reader-rehearsal-03/manifest.json'
    reader_manifest = c.document(reader_manifest_path, 'complete Reader/failure gzip member association',
                                  '31b6a0ac1426474af915ed6e630ee78f31782b17d1162bc311ad6bbe29777858')
    require(reader_pub['status'] == 'verified-lossless-reader03-publication'
            and reader_pub['manifest_sha256'] == c.files[str(reader_manifest_path)]['sha256'],
            'published Reader failure history association')
    external = dict(run_make_archive=proposal['archived_recovery'], selected21=proposal['recovery'],
                    reader_publication=dict(manifest=str(reader_manifest_path), manifest_sha256=c.files[str(reader_manifest_path)]['sha256'],
                                            audit=str(A/'.work/runtime04-reader03-publication-verification-01.json'),
                                            audit_sha256=READER_PUBLICATION_SHA, blobs=reader_manifest['blobs'],
                                            external_native_base=reader_manifest['external_native_base']),
                    protected_physical_table=dict(packet=str(SOURCE/'plan-01.json'), packet_sha256=PACKET_SHA,
                                                  fields='protected_files; metadata only, no payload duplication'))
    files = sorted(c.files.values(), key=lambda row: row['destination'])
    for row in files:
        require(identity(row['source']) == row['identity'], 'selected publication input changed before scope return')
    scope = dict(status='proposed-unpublished', destination=str(DEST), files=files, file_count=len(files),
                 source_bytes=sum(row['size'] for row in files), trees=c.trees, limits=LIMITS, actual=ACTUAL,
                 failed_independent_audit=failed_audit,
                 packet_sha256=PACKET_SHA, selected_paths=selected, external_recovery=external,
                 generated_files=['README.md', 'summary.json', 'manifest.json', 'publication-scope.json'],
                 claims=dict(removed_files=21, preserved_files=40, durable_events=63,
                             runtime_admission=False, performance_measurement=False, global_capacity_credit_bytes=0),
                 created_at=time.time(), source_mutations=False)
    data = encoded(scope); require(len(data) <= 2*2**20, 'bounded exact scope metadata')
    with OUTPUT.open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    require(OUTPUT.read_bytes() == data, 'scope full readback')
    print(json.dumps(dict(path=str(OUTPUT), sha256=sha(data), files=len(files), source_bytes=scope['source_bytes'])))


if __name__ == '__main__':
    main()
