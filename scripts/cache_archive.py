"""A bounded cache archive: one compressed payload per inode plus a manifest.

No ZIP member is extracted by name. Only validated manifest paths are created.
File bytes, permission bits, access/modification times and internal hardlinks
are preserved. Special files, external hardlinks, flags and xattrs are refused.
Inodes, ctimes, birth times and ACLs are not recreated by this format.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import zipfile

from verify_repeated_workflow import require

LIMIT_FILES = 500_000
LIMIT_MANIFEST = 128 * 1024 * 1024
LIMIT_BYTES = 1024**4
BLOCK = 1024 * 1024


def encoded(manifest):
    return (json.dumps(manifest, sort_keys=True, separators=(',', ':')) + '\n').encode()


def valid_path(name, *, root=False):
    require(isinstance(name, str) and len(name.encode()) <= 4096 and '\0' not in name, 'invalid manifest path')
    if name == '' and root:
        return
    path = PurePosixPath(name)
    require(bool(name) and bool(path.parts) and not path.is_absolute() and path.as_posix() == name and
            all(part not in ['.', '..'] for part in path.parts), 'noncanonical manifest path')


def information(path, directory=False):
    value = path.lstat()
    require((stat.S_ISDIR if directory else stat.S_ISREG)(value.st_mode), 'unsupported cache entry type')
    require(getattr(value, 'st_flags', 0) == 0, 'file flags are unsupported')
    result = dict(device=value.st_dev, inode=value.st_ino, mode=stat.S_IMODE(value.st_mode),
        atime_ns=value.st_atime_ns, mtime_ns=value.st_mtime_ns)
    if not directory:
        result.update(bytes=value.st_size, links=value.st_nlink)
    return result


def no_xattrs(target, paths):
    if hasattr(os, 'listxattr'):
        require(all(not os.listxattr(target / p, follow_symlinks=False) for p in paths),
                'extended attributes are unsupported')
    else:
        require(sys.platform == 'darwin', 'cannot inspect extended attributes on this platform')
        result = subprocess.run(['/usr/bin/xattr', '-r', str(target)], capture_output=True)
        require(result.returncode == 0 and not result.stdout and not result.stderr,
                'extended attributes are present or inspection failed')


@contextmanager
def checked_file(path, group):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        value = os.fstat(stream.fileno())
        require(stat.S_ISREG(value.st_mode) and value.st_dev == group['device'] and
                value.st_ino == group['inode'] and value.st_size == group['bytes'] and
                value.st_mtime_ns == group['mtime_ns'] and stat.S_IMODE(value.st_mode) == group['mode'],
                'cache file changed before reading')
        yield stream


def copy_hash(stream, output=None, limit=LIMIT_BYTES):
    digest, total = hashlib.sha256(), 0
    while True:
        chunk = stream.read(min(BLOCK, limit - total + 1))
        if not chunk:
            break
        total += len(chunk)
        require(total <= limit, 'payload exceeds its declared bound')
        digest.update(chunk)
        if output is not None:
            output.write(chunk)
    return total, digest.hexdigest()


def snapshot(target):
    require(target.resolve(strict=True) == target and target.is_dir(), 'noncanonical cache target')
    directories, files = [], []
    for parent, children, names in os.walk(target, followlinks=False):
        children.sort()
        parent = Path(parent)
        name = '' if parent == target else parent.relative_to(target).as_posix()
        valid_path(name, root=True)
        directories.append(dict(path=name, **information(parent, True)))
        for child in children:
            information(parent / child, True)
        files.extend(parent / name for name in names)
        require(len(files) + len(directories) <= LIMIT_FILES, 'too many cache entries')
    groups, inodes = [], {}
    for path in sorted(files):
        relative = path.relative_to(target).as_posix()
        valid_path(relative)
        info = information(path)
        key = info['device'], info['inode']
        if key in inodes:
            group = groups[inodes[key]]
            require(all(info[k] == group[k] for k in info if k != 'atime_ns'), 'hardlink metadata changed')
            group['paths'].append(relative)
        else:
            group = dict(member=f'data/{len(groups):08d}', paths=[relative], **info)
            with checked_file(path, group) as stream:
                size, digest = copy_hash(stream, limit=info['bytes'])
            require(size == info['bytes'], 'cache file was truncated while reading')
            group['sha256'] = digest
            inodes[key] = len(groups)
            groups.append(group)
    require(all(len(g['paths']) == g['links'] for g in groups), 'hardlinks outside this target are unsupported')
    result = dict(format='rust-interp-cache-zip-v1', directories=sorted(directories, key=lambda d: d['path']), groups=groups)
    validate(result)
    no_xattrs(target, [d['path'] for d in directories] + [p for g in groups for p in g['paths']])
    return result


def validate(manifest):
    require(manifest['format'] == 'rust-interp-cache-zip-v1', 'unsupported archive format')
    require(len(encoded(manifest)) <= LIMIT_MANIFEST, 'manifest too large')
    directories, groups = manifest['directories'], manifest['groups']
    require(directories and directories[0]['path'] == '', 'missing root directory')
    names, file_count, total = set(), 0, 0
    for item in directories:
        valid_path(item['path'], root=True)
        require(item['path'] not in names, 'duplicate archive path')
        names.add(item['path'])
    directory_names = set(names)
    for index, group in enumerate(groups):
        require(group['member'] == f'data/{index:08d}' and bool(group['paths']) and
                group['paths'] == sorted(group['paths']) and group['links'] == len(group['paths']), 'invalid payload group')
        require(isinstance(group['bytes'], int) and 0 <= group['bytes'] <= LIMIT_BYTES and
                isinstance(group['sha256'], str) and len(group['sha256']) == 64 and
                all(c in '0123456789abcdef' for c in group['sha256']), 'invalid payload size or digest')
        total += group['bytes']
        for name in group['paths']:
            valid_path(name)
            require(name not in names, 'duplicate archive path')
            names.add(name)
            file_count += 1
    require(file_count + len(directories) <= LIMIT_FILES and total <= LIMIT_BYTES, 'archive exceeds bounds')
    for name in names - {''}:
        parent = PurePosixPath(name).parent.as_posix()
        require(('' if parent == '.' else parent) in directory_names, 'missing or non-directory parent')
    for entry in [*directories, *groups]:
        require(type(entry['mode']) is int and 0 <= entry['mode'] <= 0o7777, 'invalid mode')
        for key in ['atime_ns', 'mtime_ns']:
            require(type(entry[key]) is int and -(1 << 63) <= entry[key] < 1 << 63, 'invalid timestamp')


def stable(manifest, *, restored=False):
    def metadata(entry):
        keys = ['mode', 'mtime_ns'] + ([] if restored else ['device', 'inode'])
        return {key: entry[key] for key in keys}
    return dict(directories=[dict(path=d['path'], **metadata(d)) for d in manifest['directories']],
        groups=[dict(paths=g['paths'], bytes=g['bytes'], sha256=g['sha256'], links=g['links'], **metadata(g))
                for g in manifest['groups']])


def unchanged(target, manifest, *, restored=False):
    require(stable(snapshot(target), restored=restored) == stable(manifest, restored=restored),
            'cache content, structure or metadata differs')


def write_archive(target, manifest, archive):
    validate(manifest)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as output:
        output.writestr('manifest.json', encoded(manifest))
        for group in manifest['groups']:
            with checked_file(target / group['paths'][0], group) as source:
                with output.open(group['member'], 'w', force_zip64=True) as destination:
                    size, digest = copy_hash(source, destination, group['bytes'])
            require(size == group['bytes'] and digest == group['sha256'], 'payload changed while archiving')
    with archive.open('rb') as stream:
        os.fsync(stream.fileno())


def members(archive, manifest):
    validate(manifest)
    expected = ['manifest.json'] + [g['member'] for g in manifest['groups']]
    require(archive.namelist() == expected, 'missing, extra, duplicated or reordered ZIP members')
    require(archive.getinfo('manifest.json').file_size <= LIMIT_MANIFEST and
            archive.read('manifest.json') == encoded(manifest), 'archive manifest differs')
    for group in manifest['groups']:
        info = archive.getinfo(group['member'])
        require(info.file_size == group['bytes'] and not info.is_dir() and not info.flag_bits & 1 and
                info.compress_type == zipfile.ZIP_DEFLATED, 'invalid ZIP payload metadata')


def verify_archive(path, manifest):
    with zipfile.ZipFile(path) as archive:
        members(archive, manifest)
        for group in manifest['groups']:
            with archive.open(group['member']) as stream:
                require(copy_hash(stream, limit=group['bytes']) == (group['bytes'], group['sha256']), 'archived payload differs')


def restore(path, manifest, destination):
    validate(manifest)
    require(not destination.exists() and not destination.is_symlink() and
            destination.parent.resolve(strict=True) == destination.parent, 'restore destination is not new and canonical')
    with zipfile.ZipFile(path) as archive:
        members(archive, manifest)
        destination.mkdir(mode=0o700)
        for directory in sorted(manifest['directories'][1:], key=lambda d: (len(PurePosixPath(d['path']).parts), d['path'])):
            (destination / directory['path']).mkdir(mode=0o700)
        for group in manifest['groups']:
            first = destination / group['paths'][0]
            with archive.open(group['member']) as source, first.open('xb') as output:
                size, digest = copy_hash(source, output, group['bytes'])
            require(size == group['bytes'] and digest == group['sha256'], 'restored payload differs')
            for name in group['paths'][1:]:
                os.link(first, destination / name)
            first.chmod(group['mode'])
            os.utime(first, ns=(group['atime_ns'], group['mtime_ns']))
        for directory in sorted(manifest['directories'], key=lambda d: len(PurePosixPath(d['path']).parts), reverse=True):
            target = destination / directory['path']
            target.chmod(directory['mode'])
            os.utime(target, ns=(directory['atime_ns'], directory['mtime_ns']))
    unchanged(destination, manifest, restored=True)
    # Verification reads can update atimes. Restore those recorded timestamps
    # after the reads, without promising preservation of filesystem identities.
    for group in manifest['groups']:
        os.utime(destination / group['paths'][0], ns=(group['atime_ns'], group['mtime_ns']))
    for directory in manifest['directories']:
        os.utime(destination / directory['path'], ns=(directory['atime_ns'], directory['mtime_ns']))


def read_file(path, manifest, name, maximum):
    valid_path(name)
    require(type(maximum) is int and 0 <= maximum <= BLOCK, 'inspection limit must be at most one MiB')
    matches = [g for g in manifest['groups'] if name in g['paths']]
    require(len(matches) == 1 and matches[0]['bytes'] <= maximum, 'file missing or exceeds inspection limit')
    group = matches[0]
    with zipfile.ZipFile(path) as archive:
        members(archive, manifest)
        data = archive.read(group['member'])
    require(len(data) == group['bytes'] and hashlib.sha256(data).hexdigest() == group['sha256'], 'inspected file differs')
    return data
