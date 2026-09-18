"""Read-only verification of a Cargo registry archive and its extracted tree."""
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(stream):
    result = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 ** 2), b''):
        result.update(block)
    return result.hexdigest()


def stamp(path):
    row = path.lstat()
    return row.st_dev, row.st_ino, row.st_mode, row.st_nlink, row.st_size, row.st_mtime_ns, row.st_ctime_ns


def regular(path):
    row = path.lstat()
    require(path.resolve(strict=True) == path and stat.S_ISREG(row.st_mode) and row.st_nlink == 1,
            'expected an ordinary unlinked file: ' + str(path))
    return row


def verify(archive, root, checksum, *, capacity=lambda: None):
    """Reject unexpected links, paths, duplicates, bytes, or tree membership.

    Cargo 797e8a9bc registry::unpack_package adds a root .cargo-ok containing
    {"v":1}; it changes selected mtimes, but not archived ordinary-file bytes.
    No extraction or repair is performed here.
    """
    archive, root = Path(archive), Path(root)
    require(root.resolve(strict=True) == root and root.is_dir(), 'nonordinary registry root')
    require(regular(archive).st_size <= 512 * 2**20, 'oversized registry archive')
    archive_stamp = stamp(archive)
    with archive.open('rb') as stream:
        require(digest(stream) == checksum, 'registry archive differs from Cargo.lock')
    members, directories, names, folded = {}, set(), set(), set()
    total = 0
    with tarfile.open(archive, 'r:gz') as stream:
        for member in stream:
            capacity()
            name = member.name.rstrip('/') if member.isdir() else member.name
            parts = name.split('/')
            require(parts and parts[0] == root.name and all(p not in ['', '.', '..'] for p in parts)
                    and '\\' not in name and '\x00' not in name and not PurePosixPath(name).is_absolute(),
                    'invalid registry archive path: ' + name)
            require(name not in names and name.casefold() not in folded, 'duplicate registry archive path')
            names.add(name)
            folded.add(name.casefold())
            require(len(names) <= 250000, 'registry archive member count exceeded')
            require(member.isfile() or member.isdir(), 'registry archive contains a link or special entry')
            relative = '/'.join(parts[1:])
            require(relative or member.isdir(), 'registry archive root is not a directory')
            if not relative:
                continue
            require(parts[-1] != '.cargo-ok', 'archive contains a Cargo-generated marker')
            for parent in PurePosixPath(relative).parents:
                if str(parent) != '.':
                    directories.add(str(parent))
            path = root / relative
            require(path.resolve(strict=True) == path, 'registry member traverses a link')
            if member.isdir():
                require(path.is_dir(), 'registry archive directory is missing')
                directories.add(relative)
                continue
            require(0 <= member.size <= 128 * 2**20, 'oversized registry member')
            total += member.size
            require(total <= 512 * 2**20, 'registry unpacked byte bound exceeded')
            row = regular(path)
            before = stamp(path)
            require(row.st_size == member.size, 'registry source size differs: ' + relative)
            with stream.extractfile(member) as source:
                archived = digest(source)
            with path.open('rb') as source:
                require(digest(source) == archived, 'registry source bytes differ: ' + relative)
            require(stamp(path) == before, 'registry source changed during verification')
            members[relative] = dict(bytes=member.size, sha256=archived,
                                     archive_mode=member.mode, extracted_mode=stat.S_IMODE(row.st_mode))
        # Read gzip through its trailer: a tar end marker alone does not check CRC.
        while stream.fileobj.read(1024 ** 2):
            pass
    marker = root / '.cargo-ok'
    require(regular(marker).st_size == 7 and marker.read_bytes() == b'{"v":1}', 'unexpected Cargo marker')
    actual_files, actual_dirs = set(), set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        capacity()
        for name in dirs:
            path = Path(directory) / name
            require(path.resolve(strict=True) == path and path.is_dir(), 'registry directory link')
            actual_dirs.add(str(path.relative_to(root)))
        for name in files:
            path = Path(directory) / name
            regular(path)
            actual_files.add(str(path.relative_to(root)))
    require(actual_files == set(members) | {'.cargo-ok'} and actual_dirs == directories,
            'registry tree membership differs from archive plus Cargo marker')
    require(stamp(archive) == archive_stamp, 'registry archive changed during verification')
    return dict(archive=str(archive), root=str(root), checksum=checksum, unpacked_bytes=total,
                members=members, directories=sorted(directories),
                cargo_marker=dict(bytes=7, sha256=hashlib.sha256(b'{"v":1}').hexdigest()))
