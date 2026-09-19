"""Lossless adjacent copies for the exact passed driver02 archive closure.

Source-only draft until reviewed. No archive extraction, provider read, subprocess,
Git operation, source mutation, cleanup, or retry. Partial output remains on failure.
Derived from the actual failure01 capsule copier; held no-follow reads are from
our actually executed continuation70 copier. The unchanged archive holds all241
selected payloads; this capsule retains processing source/raw and recovery proof.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time

A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
PROPOSAL = A/'.work/hash-driver-success-retention-publication-proposal-01.json'
EXPECTED = '0af3f9ce71b81ffc5c26682ce86807619af0aaded86ca5b5898f6d26cc72e031'
DEST = ROOT/'results/hir-options-hash-driver-02-publication'
PROTECTED = ROOT/'results/hir-options-hash-driver-02'
REPORT = A/'.work/hash-driver-success-retention-publication-verification-01.json'
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
BOUNDS = dict(maximum_files=256, maximum_source_bytes=8*2**20,
              maximum_file_bytes=2*2**20, maximum_publication_bytes=12*2**20)
GENERATED = ['README.md','STATUS.md','summary.json','manifest.json',
             'publication-proposal.json','publication-copier.py']
SOURCE_TREES = {
 str(ROOT/'experiments/hash-driver-success-evidence-01'),
 str(ROOT/'experiments/hash-driver-success-evidence-02'),
 str(ROOT/'experiments/hash-driver-success-evidence-03'),
 str(ROOT/'.work/hash-driver-success-retention-execution-01'),
 str(ROOT/'.work/hash-driver-success-retention-execution-02'),
 str(A/'.work/hash-driver-success-retention-audit-execution-02'),
 str(A/'.work/hash-driver-success-retention-audit-execution-03'),
 str(ROOT/'.work/hash-driver-success-evidence-01'),
 str(ROOT/'.work/published-failure-archive-git-proof-01'),
}

def require(value, message):
    if not value:
        raise RuntimeError(message)


def stamp(info):
    return {key:getattr(info, 'st_'+key) for key in FIELDS}


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique(pairs):
    answer = {}
    for key, value in pairs:
        require(key not in answer, 'duplicate JSON member')
        answer[key] = value
    return answer


def parsed(data):
    return json.loads(data, object_pairs_hook=unique,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def canonical(path):
    path = Path(path)
    require(path.is_absolute() and str(path).startswith('/') and not str(path).startswith('//')
            and '..' not in path.parts and not any(ord(c) < 32 or ord(c) == 127 for c in str(path)),
            'canonical absolute source/destination required')
    return path


def directory_key(info):
    return info.st_dev, info.st_ino, info.st_mode


@contextmanager
def held_directory(path):
    """Keep every no-follow ancestor open until the caller finishes its read."""
    path = canonical(path); descriptors = []; links = []
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptors.append(os.open('/', flags))
        for component in path.parts[1:]:
            parent = descriptors[-1]
            child = os.open(component, flags, dir_fd=parent)
            descriptors.append(child); expected = directory_key(os.fstat(child))
            require(stat.S_ISDIR(expected[2]), 'ordinary directory required')
            links.append((parent, component, child, expected))
        def check():
            for parent, name, child, expected in links:
                require(directory_key(os.fstat(child)) == expected
                        and directory_key(os.stat(name, dir_fd=parent, follow_symlinks=False)) == expected,
                        'held ordinary directory route changed')
        check()
        yield descriptors[-1], check
        check()
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def read_file(path, expected=None, limit=2*2**20):
    """Complete bounded bytes/hash and seven-field identity before/after read."""
    path = canonical(path)
    with held_directory(path.parent) as (parent, check):
        before = stamp(os.stat(path.name, dir_fd=parent, follow_symlinks=False))
        require(stat.S_ISREG(before['mode']) and 0 <= before['size'] <= limit,
                'bounded ordinary file required: '+str(path))
        if expected is not None:
            require(before == expected['identity'] and before['size'] == expected['size'],
                    'exact source identity changed: '+str(path))
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            require(stamp(os.fstat(descriptor)) == before, 'file changed while opening')
            pieces = []; total = 0
            while True:
                block = os.read(descriptor, min(65536, limit+1-total))
                if not block:
                    break
                total += len(block); require(total <= limit, 'bounded file grew')
                pieces.append(block)
            data = b''.join(pieces)
            require(total == before['size'] and stamp(os.fstat(descriptor)) == before
                    and stamp(os.stat(path.name, dir_fd=parent, follow_symlinks=False)) == before,
                    'file bytes or route changed during read')
            check()
        finally:
            os.close(descriptor)
    if expected is not None:
        require(digest(data) == expected['sha256'], 'exact source SHA changed: '+str(path))
    return data, dict(path=str(path), size=len(data), sha256=digest(data), identity=before)



def membership(root):
    """Read every member without following links, retaining every directory FD."""
    answer = {}
    with held_directory(root) as (descriptor, check):
        def walk(fd, relative):
            before = stamp(os.fstat(fd))
            answer[relative] = dict(kind='directory', identity=before)
            names = sorted(os.listdir(fd))
            for name in names:
                entry = name if relative == '.' else relative+'/'+name
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), 'tree contains special member')
                require(len(answer) < 1024, 'finite complete tree membership')
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        require(stamp(os.fstat(child)) == stamp(info), 'child directory changed on open')
                        walk(child, entry)
                        require(stamp(os.stat(name, dir_fd=fd, follow_symlinks=False)) == stamp(info),
                                'directory route changed')
                    finally:
                        os.close(child)
                else:
                    answer[entry] = dict(kind='file', identity=stamp(info))
            require(names == sorted(os.listdir(fd)) and stamp(os.fstat(fd)) == before, 'tree changed during enumeration')
        walk(descriptor, '.')
        check()
    return answer


def source_row(row):
    require(set(row) == {'source','destination','size','sha256','identity','roles'}
            and set(row['identity']) == set(FIELDS)
            and all(type(v) is int for v in row['identity'].values())
            and type(row['size']) is int and 0 <= row['size'] <= BOUNDS['maximum_file_bytes']
            and row['size'] == row['identity']['size'] and row['identity']['nlink'] == 1
            and stat.S_ISREG(row['identity']['mode']) and re.fullmatch('[a-f0-9]{64}', row['sha256']),
            'complete typed ordinary source row required')
    canonical(row['source'])
    rel = Path(row['destination'])
    require(str(rel) == row['destination'] and not rel.is_absolute() and len(rel.parts) >= 3
            and rel.parts[0] == 'payloads' and '..' not in rel.parts
            and not any(ord(c) < 32 or ord(c) == 127 for c in str(rel)), 'safe exact payload destination required')


def main():
    require(Path.cwd() == ROOT and sys.dont_write_bytecode and not sys.flags.optimize,
            'ROOT working directory and Python -B without optimization required')
    require(not DEST.exists() and not DEST.is_symlink() and not REPORT.exists() and not REPORT.is_symlink(),
            'fresh exclusive publication/report required; partial failures are never retried')
    started = time.time()
    raw, proposal_record = read_file(PROPOSAL)
    require(proposal_record['sha256'] == EXPECTED, 'exact reviewed proposal required')
    p = parsed(raw)
    publisher_raw, publisher = read_file(Path(__file__).absolute())
    require(p['destination'] == str(DEST) and p['status'] == 'proposed-unpublished'
            and p['file_count'] == len(p['files']) == 121
            and p['source_bytes'] == sum(r['size'] for r in p['files']) == 4465474
            and {k:p[k] for k in BOUNDS} == BOUNDS and p['generated_files'] == GENERATED
            and set(p['complete_source_trees']) == SOURCE_TREES, 'exact reviewed scope and bounds')
    rows = p['files']; sources = set(); names = set()
    for row in rows:
        source_row(row)
        require(row['source'] not in sources and row['destination'] not in names, 'unique source and destination')
        sources.add(row['source']); names.add(row['destination'])
    require(set(p['required_evidence']) <= sources and len(p['required_evidence']) == 7,
            'complete saved processing/audit/Git proof closure')
    require(p['source_bytes'] <= BOUNDS['maximum_source_bytes']
            and len(rows)+len(GENERATED) == 127 <= BOUNDS['maximum_files'], 'finite complete publication')
    require(p['protected_result_directory'] == str(PROTECTED)
            and p['protected_result_files'] == len(p['protected_results']) == 5, 'five protected archive outputs')
    protected_rows = {r['source']:r for r in p['protected_results']}
    require(set(protected_rows) == {str(PROTECTED/n) for n in
        ['evidence.tar.gz','manifest.json','previous-attempt.json','proposal.json','summary.json']}, 'exact protected names')
    require(sources.isdisjoint(protected_rows), 'archive outputs must not be copied')
    original_tree = membership(PROTECTED)

    def protect_archive():
        require(membership(PROTECTED) == original_tree, 'five original archive identities/membership changed')
        require(set(original_tree) == {'.',*[Path(n).name for n in protected_rows]}, 'exact ordinary archive directory')
        for row in p['protected_results']:
            # Protected archive is read only, not a publication file; it has its own exact 2,559,860-byte bound.
            require(0 <= row['size'] <= 3*2**20, 'bounded protected archive input')
            read_file(row['source'], row, limit=3*2**20)

    def check_trees():
        for root, expected in p['complete_source_trees'].items():
            require(encoded(membership(root)) == encoded(expected), 'exact complete source tree changed: '+root)
            require({str(Path(root)/name) for name, row in expected.items() if row['kind'] == 'file'} <= sources,
                    'every member of each closed source tree must be copied')

    def check_metadata():
        read_file(PROPOSAL, proposal_record)
        read_file(publisher['path'], publisher)

    protect_archive()
    archived_manifest = parsed(read_file(PROTECTED/'manifest.json', protected_rows[str(PROTECTED/'manifest.json')])[0])
    require(encoded(archived_manifest['members']) == encoded(p['selected_archive_sources'])
            and len(archived_manifest['members']) == p['selected_archive_source_count'] == 241
            and p['selected_archive_recovery'] == dict(
                archive_sha256=protected_rows[str(PROTECTED/'evidence.tar.gz')]['sha256'],
                manifest_sha256=protected_rows[str(PROTECTED/'manifest.json')]['sha256'],
                members_use_original_path_without_initial_slash=True), 'exact241 archive recovery mapping')
    require(all(r['member'] == r['path'].lstrip('/') for r in archived_manifest['members']), 'unchanged original member naming')
    audit_ref = p['summary']['archive_audit']
    audit_row = next(r for r in rows if r['source'] == audit_ref['path'])
    require(audit_row['sha256'] == audit_ref['sha256'] ==
            '6473ffef9b51944ccc660e2e074769042b044290576d3732e09a526b94bd545b', 'actual final audit binding')
    audit = parsed(read_file(audit_row['source'], audit_row)[0])
    require(audit['manifest_sha256'] == protected_rows[str(PROTECTED/'manifest.json')]['sha256']
            and audit['summary_sha256'] == protected_rows[str(PROTECTED/'summary.json')]['sha256']
            and audit['original_driver_audit_sha256'] == p['summary']['driver']['audit']['sha256'],
            'passed archive readback binds unchanged adjacent outputs and actual driver audit')
    manifest = dict(status='retained-exact-evidence-copies', proposal_sha256=EXPECTED,
        source_files=rows, payload_count=len(rows), source_bytes=p['source_bytes'],
        scope=p['summary']['scope'], generated_files=GENERATED, bounds=BOUNDS,
        source_directory_memberships=p['complete_source_trees'],
        protected_original_archive=p['protected_results'], selected_archive_recovery=p['selected_archive_recovery'],
        selected_archive_sources=p['selected_archive_sources'],
        publisher=dict(source=publisher, retained_path='publication-copier.py'),
        originals_preserved=True, archive_payload_duplicated=False, git_mutations=False)
    generated = {'README.md':p['readme'].encode(), 'STATUS.md':p['status_document'].encode(),
        'summary.json':encoded(p['summary']), 'manifest.json':encoded(manifest),
        'publication-proposal.json':raw, 'publication-copier.py':publisher_raw}
    projected = p['source_bytes']+sum(len(data) for data in generated.values())
    require(all(len(data) <= BOUNDS['maximum_file_bytes'] for data in generated.values())
            and projected <= BOUNDS['maximum_publication_bytes'], 'full projected metadata and publication bound')
    # Complete readback of source closure precedes any output directory creation.
    check_trees(); check_metadata()
    for row in rows:
        read_file(row['source'], row)
    check_trees(); check_metadata(); protect_archive()
    outputs = []; output_dirs = {'.':None}
    with held_directory(DEST.parent) as (parent, check_parent):
        os.mkdir(DEST.name, 0o700, dir_fd=parent)
        root_fd = os.open(DEST.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            root_key = directory_key(os.fstat(root_fd)); output_dirs['.'] = root_key
            def check_root():
                require(directory_key(os.fstat(root_fd)) == root_key and
                    directory_key(os.stat(DEST.name, dir_fd=parent, follow_symlinks=False)) == root_key,
                    'exclusive destination root route changed')
                check_parent()

            def write(relative, data):
                require(len(outputs) < 127 and len(data) <= BOUNDS['maximum_file_bytes']
                        and sum(r['size'] for r in outputs)+len(data) <= BOUNDS['maximum_publication_bytes'],
                        'bounded complete output bytes')
                check_root(); parts = Path(relative).parts; fds = []; target = root_fd
                try:
                    for i, component in enumerate(parts[:-1]):
                        name = '/'.join(parts[:i+1])
                        if name not in output_dirs:
                            os.mkdir(component, 0o700, dir_fd=target)
                        child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=target)
                        fds.append(child); key = directory_key(os.fstat(child))
                        if name in output_dirs:
                            require(output_dirs[name] == key, 'output directory changed')
                        else:
                            output_dirs[name] = key
                        require(directory_key(os.stat(component, dir_fd=target, follow_symlinks=False)) == key,
                                'output directory route differs')
                        target = child
                    descriptor = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                         0o600, dir_fd=target)
                    with os.fdopen(descriptor, 'wb') as stream:
                        stream.write(data); stream.flush(); os.fsync(stream.fileno())
                    actual, out = read_file(DEST/relative)
                    require(actual == data and out['identity']['nlink'] == 1
                            and (out['identity']['dev'],out['identity']['ino']) not in
                                {(r['identity']['dev'],r['identity']['ino']) for r in rows},
                            'independent ordinary output bytes/identity')
                    out['relative'] = relative; outputs.append(out)
                    for descriptor in reversed(fds):
                        os.fsync(descriptor)
                    check_root()
                finally:
                    for descriptor in reversed(fds):
                        os.close(descriptor)

            for row in rows:
                write(row['destination'], read_file(row['source'], row)[0])
                read_file(row['source'], row)
            for name in GENERATED:
                write(name, generated[name])
            require(len(outputs) == 127 and sum(r['size'] for r in outputs) == projected,
                    'exact full output count and bytes')
            observed = membership(DEST)
            require({n for n,r in observed.items() if r['kind'] == 'file'} == {r['relative'] for r in outputs}
                    and {n for n,r in observed.items() if r['kind'] == 'directory'} == set(output_dirs),
                    'exact final output files and directories')
            for name, key in output_dirs.items():
                require(tuple(observed[name]['identity'][k] for k in ['dev','ino','mode']) == key,
                        'all output directory identities remain stable')
            for row in outputs:
                read_file(row['path'], row)
            for row in rows:
                read_file(row['source'], row)
            check_trees(); check_metadata(); protect_archive(); check_root()
            os.fsync(root_fd); os.fsync(parent)
        finally:
            os.close(root_fd)
    report = dict(status='verified-published-copies', started_at=started, finished_at=time.time(),
        publisher_pid=os.getpid(), publisher_parent_pid=os.getppid(), publisher=publisher,
        proposal=dict(path=str(PROPOSAL),sha256=EXPECTED), destination=str(DEST), files=outputs,
        file_count=len(outputs), total_bytes=projected, source_file_count=121, source_bytes=4465474,
        all_selected_closure_evidence_retained=True, complete_source_trees=p['complete_source_trees'],
        protected_original_archive=p['protected_results'], all5_original_archive_files_byte_and_identity_unchanged=True,
        selected241_payload_recovery='unchanged adjacent archive and exact member SHA map',
        source_identities_and_bytes_unchanged=True, full_output_readback=True, exact_output_directories=True,
        archive_payload_duplicated=False, workload_children=0, git_mutations=False)
    report_raw = encoded(report)
    require(len(report_raw) <= BOUNDS['maximum_file_bytes'], 'bounded publication report')
    with held_directory(REPORT.parent) as (parent, check):
        descriptor = os.open(REPORT.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(report_raw); stream.flush(); os.fsync(stream.fileno())
        require(read_file(REPORT)[0] == report_raw, 'full report readback')
        check(); os.fsync(parent)
    print(json.dumps(dict(report=str(REPORT),sha256=digest(report_raw),files=len(outputs),total_bytes=projected,
        manifest_sha256=digest(generated['manifest.json']))))


if __name__ == '__main__':
    main()
