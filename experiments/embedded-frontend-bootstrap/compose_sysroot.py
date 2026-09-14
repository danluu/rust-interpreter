"""Fresh beta/private build sysroot; callable only by an admitted owned runner.

No subprocess, download, source discovery, or implicit current-sysroot overlay.
The caller proves the complete stamp against the successful native build, source
and runtime receipts, then supplies every approved ordinary input with its hash.
This module enforces exact membership/copy identity, not compiler compatibility.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile


POLICY = 'beta-private-build-sysroot-v1'
HOST = 'aarch64-apple-darwin'
SOURCE = Path('/Users/danluu/dev/rustc-hir-capture-check-20260913')
TREE = SOURCE / 'build' / HOST / 'stage1-rustc'
STAMP = TREE / HOST / 'release/.librustc-stamp'
BETA = {
    'rustc-beta-aarch64-apple-darwin.tar.xz': (
        '0c20c4730544923b2ba9ab4ccf98cd22db6759d1d6cc2e5b8c99662b953163ac', 'rustc'),
    'rust-std-beta-aarch64-apple-darwin.tar.xz': (
        'd8f4620f3672cae11fdb841a86d44215aeba2e656244286056f7742e966797e3',
        'rust-std-aarch64-apple-darwin'),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha_string(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'invalid SHA-256')
    return value


def relative(value):
    require(isinstance(value, str) and '\x00' not in value, 'invalid relative path')
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.parts and '..' not in path.parts
            and path.as_posix() == value, 'noncanonical relative path: ' + value)
    return path


def absolute(value):
    require(isinstance(value, str) and '\x00' not in value, 'invalid absolute path')
    path = Path(value)
    require(path.is_absolute() and '..' not in path.parts and str(path) == value,
            'noncanonical absolute path: ' + value)
    return path


def identity(info):
    return {name: getattr(info, 'st_' + name) for name in
            ('dev', 'ino', 'size', 'mode', 'nlink', 'mtime_ns', 'ctime_ns')}


def ordinary(path):
    path = absolute(str(path))
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and path.resolve(strict=True) == path,
            'input is not an ordinary canonical file: ' + str(path))
    return identity(info)


def stream_hash(stream, output=None, guard=None):
    require(output is None or callable(guard), 'copy requires a running capacity guard')
    result, size = hashlib.sha256(), 0
    for data in iter(lambda: stream.read(1024 * 1024), b''):
        result.update(data)
        size += len(data)
        if output is not None:
            guard()
            output.write(data)
            guard()
    return result.hexdigest(), size


def check_file(record, output=None, guard=None):
    """Capture immediately-before/after identity; copy to a fresh inode if asked."""
    path, expected = absolute(record['path']), sha_string(record['sha256'])
    before = ordinary(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        require(identity(os.fstat(stream.fileno())) == before, 'input replaced before read')
        actual, size = stream_hash(stream, output, guard)
        require(identity(os.fstat(stream.fileno())) == before, 'input changed while reading')
    require(ordinary(path) == before and actual == expected, 'input identity/hash changed: ' + str(path))
    require('size' not in record or record['size'] == size, 'input size differs')
    require('identity' not in record or record['identity'] == before, 'frozen inode identity differs')
    return dict(path=str(path), sha256=actual, size=size, identity=before)


def parse_stamp(data, host=HOST, target=HOST):
    """Match bootstrap add_to_sysroot h/t/s destinations without dropping entries."""
    require(host == HOST and target == HOST, 'this composition requires the pinned native host')
    require(data and data.endswith(b'\0'), 'empty or unterminated private stamp')
    result, paths, destinations = [], set(), set()
    for raw in data[:-1].split(b'\0'):
        require(len(raw) > 1 and raw[:1] in (b'h', b't', b's'), 'invalid stamp dependency tag')
        source = absolute(raw[1:].decode('utf-8', errors='strict'))
        # Both ordinary host proc-macro outputs and target compiler outputs are
        # admitted. Other roots require a separate source-reviewed recipe.
        require(any(source.is_relative_to(root) for root in
                    (TREE / 'release', TREE / HOST / 'release')), 'stamp input escapes build roots')
        tag = raw[:1].decode()
        triple = host if tag == 'h' else target
        directory = PurePosixPath('lib/rustlib') / triple / 'lib'
        if tag == 's':
            directory /= 'self-contained'
        destination = str(directory / source.name)
        require(str(source) not in paths and destination not in destinations,
                'duplicate stamp source or destination')
        paths.add(str(source))
        destinations.add(destination)
        result.append(dict(tag=tag, source=str(source), destination=destination))
    return result


def add_row(rows, destination, record):
    relative(destination)
    require(destination.startswith('lib/'), 'composition writes only lib subtree')
    require(destination not in rows, 'composition destination collision: ' + destination)
    # Also reject a file occupying an ancestor of another output.
    require(not any(destination.startswith(old + '/') or old.startswith(destination + '/')
                    for old in rows), 'composition file/directory collision')
    rows[destination] = record


def add_archive_copies(rows, copies):
    """Add explicit destinations for original archive members, never aliases."""
    originals = dict(rows)
    for copy in copies:
        require(set(copy) == {'source_destination', 'destination'}, 'invalid archive copy fields')
        source, destination = copy['source_destination'], copy['destination']
        relative(source)
        require(source in originals and originals[source]['kind'] == 'archive',
                'archive copy requires an original archive member')
        add_row(rows, destination, dict(originals[source]))


def check_archive_copies(plan):
    """Every repeated member requires an explicit original-to-copy mapping."""
    copies = plan.get('archive_copies', [])
    destinations = [copy['destination'] for copy in copies]
    require(len(destinations) == len(set(destinations)), 'duplicate archive copy destination')
    originals = {path: row for path, row in plan['files'].items() if path not in destinations}
    add_archive_copies(originals, copies)
    require(originals == plan['files'], 'archive copy mapping differs from planned files')
    members = set()
    for path, row in plan['files'].items():
        if row['kind'] != 'archive' or path in destinations:
            continue
        key = (row['path'], row['member'])
        require(key not in members, 'repeated archive member lacks explicit copy mapping')
        members.add(key)


def archive_rows(record, rows):
    """Hash the complete archive; select the component's entire lib subtree.

    Selected symlinks/hardlinks are rejected, even when an apparent target is
    present. No archive path is extracted or followed by tarfile.
    """
    checked = check_file(record)
    name = Path(record['path']).name
    require(name in BETA and record['sha256'] == BETA[name][0], 'unrecognized beta archive')
    prefix = name[:-len('.tar.xz')] + '/' + BETA[name][1] + '/'
    selected, members, seen = 0, [], set()
    with tarfile.open(record['path'], 'r:xz') as archive:
        for member in archive:
            path = member.name.rstrip('/') if member.isdir() else member.name
            relative(path)
            require(path not in seen, 'duplicate archive member')
            seen.add(path)
            in_lib = path.startswith(prefix + 'lib/')
            members.append(dict(name=member.name, size=member.size, mode=member.mode,
                                type=member.type.decode('ascii'), linkname=member.linkname,
                                selected=in_lib and not member.isdir()))
            if not in_lib or member.isdir():
                continue
            require(member.isfile() and not member.issparse(), 'nonordinary beta library member')
            require(member.mode & ~0o777 == 0, 'special beta file mode')
            with archive.extractfile(member) as stream:
                sha, size = stream_hash(stream)
            require(size == member.size, 'truncated beta library member')
            add_row(rows, path[len(prefix):], dict(kind='archive', path=record['path'],
                member=member.name, sha256=sha, size=size, mode=member.mode))
            selected += 1
    require(selected > 0, 'beta archive has no selected library payload')
    require(check_file(checked) == checked, 'beta archive changed during selection')
    return dict(file=checked, members=members, selected_files=selected)


def check_crate_names(rows):
    """Bootstrap forbids ambiguous rustc_* crate versions except rustc_hash."""
    stems = {}
    for destination in rows:
        path = PurePosixPath(destination)
        if str(path.parent) != f'lib/rustlib/{HOST}/lib':
            continue
        stem = path.name.split('.', 1)[0]
        if 'rustc_' not in stem or 'rustc_hash' in stem:
            continue
        crate = stem.split('-', 1)[0]
        require(crate not in stems or stems[crate] == stem, 'ambiguous private crate: ' + crate)
        stems[crate] = stem


def inspect_inputs(*, archives, stamp, approved_private_files, build_compiler,
                   runtime_source_commit, runtime_driver, proofs, archive_copies=()):
    """Read/hash only explicit inputs; caller supplies separately qualified proofs.

    approved_private_files is a path -> {sha256,size} map covering EVERY stamp
    path, proved by the outer runner against native005/current source/runtime.
    proofs is its exact source/build/archive/qualification metadata file list.
    Nothing here infers producer ownership from a filename or a favorable glob.
    """
    require(re.fullmatch('[0-9a-f]{40}', runtime_source_commit), 'invalid runtime source commit')
    require(set(Path(x['path']).name for x in archives) == set(BETA) and len(archives) == 2,
            'require exactly both pinned beta archives')
    require(absolute(stamp['path']) == STAMP, 'wrong private build stamp')
    require(proofs, 'outer producer/source qualification proofs are required')
    proof_records = [check_file(x) for x in proofs]
    require(len({x['path'] for x in proof_records}) == len(proof_records), 'duplicate proof')
    build, driver, stamp_record = check_file(build_compiler), check_file(runtime_driver), check_file(stamp)
    data = Path(stamp['path']).read_bytes()
    require(digest(data) == stamp_record['sha256'], 'stamp changed before parsing')
    entries = parse_stamp(data)
    require({x['source'] for x in entries} == set(approved_private_files),
            'approved producer map differs from complete stamp membership')
    rows = {}
    archive_records = [archive_rows(x, rows) for x in archives]
    add_archive_copies(rows, archive_copies)
    private = []
    for entry in entries:
        original = approved_private_files[entry['source']]
        require(set(original) == {'sha256', 'size'}, 'private approval requires exact hash and size')
        record = check_file(dict(path=entry['source'], **original))
        require(record['identity']['mode'] & 0o7000 == 0, 'special private file mode')
        add_row(rows, entry['destination'], dict(kind='private', path=record['path'],
                sha256=record['sha256'], size=record['size'],
                mode=stat.S_IMODE(record['identity']['mode'])))
        private.append(dict(**entry, file=record))
    # Bootstrap checks this invocation's stamped crates, not all preexisting
    # beta std transitive dependencies; preserve that exact boundary.
    check_crate_names({path: row for path, row in rows.items() if row['kind'] == 'private'})
    driver_destination = f'lib/rustlib/{HOST}/lib/' + Path(driver['path']).name
    require(driver_destination in rows and rows[driver_destination]['kind'] == 'private'
            and rows[driver_destination]['sha256'] == driver['sha256'],
            'stamped link driver is not the qualified runtime driver')
    metadata = str(PurePosixPath(driver_destination).with_suffix('.rmeta'))
    require(metadata in rows and rows[metadata]['kind'] == 'private', 'driver metadata missing')
    require(any(re.fullmatch(f'lib/rustlib/{HOST}/lib/libstd-[^.]+[.]rlib', path)
                and row['kind'] == 'archive' for path, row in rows.items()), 'beta libstd missing')
    result = dict(schema_version=1, policy=POLICY, host=HOST,
        build_compiler=build, runtime_source_commit=runtime_source_commit,
        runtime_driver=driver, archives=archive_records, stamp=stamp_record,
        stamp_hex=data.hex(), private=private, proofs=proof_records, files=rows,
        producer_qualification='required from outer runner; no inference by compositor',
        compiler_compatibility='unqualified')
    if archive_copies:
        result['archive_copies'] = [dict(copy) for copy in archive_copies]
    check_archive_copies(result)
    recheck_inputs(result)
    return result


def recheck_inputs(plan):
    for record in [plan['build_compiler'], plan['runtime_driver'], plan['stamp'],
                   *plan['proofs'], *(x['file'] for x in plan['archives']),
                   *(x['file'] for x in plan['private'])]:
        require(check_file(record) == record, 'frozen composition input changed')


def write_new(path, data, guard):
    guard()
    with path.open('xb') as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    guard()


def output_inventory(root):
    files = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'output contains symlink')
        if path.is_dir():
            continue
        before = ordinary(path)
        with path.open('rb') as stream:
            sha, size = stream_hash(stream)
        require(ordinary(path) == before and before['nlink'] == 1, 'output is changed/shared')
        files[str(path.relative_to(root))] = dict(sha256=sha, size=size,
            mode=stat.S_IMODE(before['mode']), identity=before)
    return files


def assemble(plan, *, expected_plan_sha256, destination, evidence, capacity_guard):
    """Copy only a frozen plan. Both outputs must be fresh siblings/independent.

    Outer owned_stage provides canonical lock, process/source guards and failure
    receipt. Its required capacity_guard runs around every copy and every MiB
    written, enforcing the admitted running floor throughout assembly. Partial
    files are deliberately retained on any failure.
    Metadata lives outside B, so its exhaustive manifest has no self-reference.
    """
    require(digest(encoded(plan)) == sha_string(expected_plan_sha256), 'composition plan hash differs')
    require(plan['schema_version'] == 1 and plan['policy'] == POLICY, 'wrong composition policy')
    check_archive_copies(plan)
    require(callable(capacity_guard), 'assembly requires a running capacity guard')
    destination, evidence = absolute(str(destination)), absolute(str(evidence))
    require(destination != evidence and not destination.is_relative_to(evidence)
            and not evidence.is_relative_to(destination), 'sysroot/evidence paths overlap')
    for path in (destination, evidence):
        require(not path.exists() and not path.is_symlink()
                and path.parent.resolve(strict=True) == path.parent, 'output must be fresh under ordinary parent')
    # No output files or directories precede all frozen input rechecks.
    recheck_inputs(plan)
    capacity_guard()
    destination.mkdir()
    evidence.mkdir()
    write_new(evidence / 'composition-plan.json', encoded(plan), capacity_guard)
    # Preserve all explicitly approved small metadata payloads, not source tree
    # or dependency binaries. Original paths/hashes remain in the plan.
    (evidence / 'proofs').mkdir()
    proof_copies = []
    for index, record in enumerate(plan['proofs']):
        capacity_guard()
        copy = evidence / 'proofs' / f'{index:03}.bin'
        with copy.open('xb') as output:
            check_file(record, output, capacity_guard)
            output.flush()
            os.fsync(output.fileno())
        copied = check_file(dict(path=str(copy), sha256=record['sha256'], size=record['size']))
        require(copied['identity']['nlink'] == 1, 'proof copy unexpectedly shares an inode')
        proof_copies.append(dict(original=record, copy=copied))
        capacity_guard()
    archive_by_path = {x['file']['path']: x for x in plan['archives']}
    for archive_path in archive_by_path:
        selected = {}
        for path, row in plan['files'].items():
            if row['kind'] == 'archive' and row['path'] == archive_path:
                selected.setdefault(row['member'], []).append((path, row))
        with tarfile.open(archive_path, 'r:xz') as archive:
            for member in archive:
                if member.name not in selected:
                    continue
                for path, row in selected.pop(member.name):
                    require(member.isfile() and not member.issparse() and member.size == row['size']
                            and member.mode == row['mode'], 'archive member changed')
                    target = destination / relative(path)
                    capacity_guard()
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(member) as source, target.open('xb') as output:
                        sha, size = stream_hash(source, output, capacity_guard)
                        output.flush()
                        os.fsync(output.fileno())
                    require(sha == row['sha256'] and size == row['size'], 'archive copy hash differs')
                    target.chmod(row['mode'])
                    capacity_guard()
        require(not selected, 'selected archive files missing')
    for item in plan['private']:
        row, path = item['file'], destination / relative(item['destination'])
        capacity_guard()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as output:
            check_file(row, output, capacity_guard)
            output.flush()
            os.fsync(output.fileno())
        path.chmod(stat.S_IMODE(row['identity']['mode']))
        capacity_guard()
    actual = output_inventory(destination)
    expected = {path: {k: row[k] for k in ('sha256', 'size', 'mode')}
                for path, row in plan['files'].items()}
    require({path: {k: row[k] for k in ('sha256', 'size', 'mode')}
             for path, row in actual.items()} == expected, 'complete output inventory differs')
    recheck_inputs(plan)
    manifest = dict(schema_version=1, build_compiler_sha256=plan['build_compiler']['sha256'],
        runtime_source_commit=plan['runtime_source_commit'], sysroot=str(destination), host=HOST,
        files={path: row['sha256'] for path, row in actual.items()})
    write_new(evidence / 'output-inventory.json', encoded(actual), capacity_guard)
    write_new(evidence / 'proof-copies.json', encoded(proof_copies), capacity_guard)
    write_new(evidence / 'private-sysroot.json', encoded(manifest), capacity_guard)
    result = dict(schema_version=1, status='assembled-unqualified', policy=POLICY,
        composition_plan_sha256=expected_plan_sha256, files=len(actual),
        copied_bytes=sum(x['size'] for x in actual.values()),
        proof_copies_sha256=digest(encoded(proof_copies)),
        output_inventory_sha256=digest(encoded(actual)),
        private_sysroot_manifest_sha256=digest(encoded(manifest)),
        compatibility_probes_run=False, compiler_builds_run=False)
    write_new(evidence / 'assembly-complete.json', encoded(result), capacity_guard)
    return result
