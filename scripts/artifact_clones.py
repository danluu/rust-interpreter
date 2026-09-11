"""Replace identical plain artifact files with independent Darwin CoW clones.

Only file data sharing changes. Paths, bytes, ownership, permissions and mtime
are preserved; inode, ctime and birth time are not preserved. Rich metadata is
refused. There is no hardlink or ordinary-copy fallback.
"""
import ctypes
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import sys
import uuid

from verify_repeated_workflow import require

MAX_BYTES = 64 * 1024 * 1024


def metadata(path, *, directory=False):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path and
            not any(ord(c) < 32 for c in str(path)), 'noncanonical artifact path')
    info = path.lstat()
    require((stat.S_ISDIR if directory else stat.S_ISREG)(info.st_mode) and
            info.st_uid == os.geteuid() and getattr(info, 'st_flags', 0) == 0 and
            not info.st_mode & 0o6000, 'artifact type, owner or flags are unsupported')
    if not directory:
        require(info.st_nlink == 1 and 0 < info.st_size <= MAX_BYTES,
                'artifact must be a bounded file with one link')
    attrs = subprocess.run(['/usr/bin/xattr', str(path)], capture_output=True, text=True)
    acl = subprocess.run(['/bin/ls', '-lde', str(path)], capture_output=True, text=True)
    require(attrs.returncode == 0 and not attrs.stdout and not attrs.stderr and
            acl.returncode == 0 and not acl.stderr and len(acl.stdout.splitlines()) == 1 and
            '+' not in acl.stdout.split()[0], 'artifact attributes or ACLs are unsupported')
    return dict(device=info.st_dev, inode=info.st_ino, bytes=info.st_size,
                uid=info.st_uid, gid=info.st_gid, mode=stat.S_IMODE(info.st_mode),
                mtime_ns=info.st_mtime_ns, ctime_ns=info.st_ctime_ns, atime_ns=info.st_atime_ns)


def same(info, expected):
    return (stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
            getattr(info, 'st_flags', 0) == 0 and
            (info.st_dev, info.st_ino, info.st_size, info.st_uid, info.st_gid,
             stat.S_IMODE(info.st_mode), info.st_mtime_ns, info.st_ctime_ns) ==
            tuple(expected[k] for k in ['device', 'inode', 'bytes', 'uid', 'gid', 'mode', 'mtime_ns', 'ctime_ns']))


def open_checked(path, expected):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        require(same(os.fstat(fd), expected), 'artifact identity changed before opening')
    except BaseException:
        os.close(fd)
        raise
    return fd


def fd_hash(fd, expected):
    os.lseek(fd, 0, os.SEEK_SET)
    digest, total = hashlib.sha256(), 0
    while True:
        block = os.read(fd, min(1024 * 1024, expected['bytes'] - total + 1))
        if not block:
            break
        total += len(block)
        require(total <= expected['bytes'], 'artifact grew while reading')
        digest.update(block)
    require(total == expected['bytes'] and same(os.fstat(fd), expected), 'artifact changed while reading')
    return digest.hexdigest()


def inspect(path, expected_hash=None):
    info = metadata(path)
    fd = open_checked(path, info)
    try:
        digest = fd_hash(fd, info)
    finally:
        os.close(fd)
    require(same(Path(path).lstat(), info), 'artifact path changed during inspection')
    require(expected_hash is None or digest == expected_hash, 'artifact content differs from recorded execution')
    return dict(info, sha256=digest)


def clone_fd(source_fd, directory_fd, name):
    require(sys.platform == 'darwin', 'artifact cloning requires Darwin')
    libc = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    call = libc.fclonefileat
    call.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
    call.restype = ctypes.c_int
    if call(source_fd, directory_fd, os.fsencode(name), 0) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), name)


def replace_duplicate(source, destination, source_info, destination_info):
    source, destination = Path(source), Path(destination)
    require(source != destination and source_info['device'] == destination_info['device'] and
            source_info['inode'] != destination_info['inode'] and
            source_info['bytes'] == destination_info['bytes'] and
            source_info['sha256'] == destination_info['sha256'], 'files are not independent identical artifacts')
    # Clones inherit the destination directory ACL. Refuse rich metadata rather
    # than changing it or treating permission bits as a complete ACL description.
    parent = metadata(destination.parent, directory=True)
    current_source, current_destination = metadata(source), metadata(destination)
    require(all(current_source[k] == source_info[k] for k in source_info if k not in ['sha256', 'atime_ns']) and
            all(current_destination[k] == destination_info[k] for k in destination_info if k not in ['sha256', 'atime_ns']),
            'artifact metadata changed after review')
    temporary = destination.parent / ('.' + destination.name + '.clone-' + uuid.uuid4().hex)
    created = None
    with ExitStack() as stack:
        src_fd = open_checked(source, source_info)
        stack.callback(os.close, src_fd)
        dst_fd = open_checked(destination, destination_info)
        stack.callback(os.close, dst_fd)
        directory_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        stack.callback(os.close, directory_fd)

        def remove_temporary():
            if created is not None and temporary.exists():
                info = temporary.lstat()
                require((info.st_dev, info.st_ino) == created, 'temporary clone identity changed')
                temporary.unlink()

        stack.callback(remove_temporary)
        directory = os.fstat(directory_fd)
        require((directory.st_dev, directory.st_ino) == (parent['device'], parent['inode']), 'artifact directory changed')
        require(fd_hash(src_fd, source_info) == source_info['sha256'] and
                fd_hash(dst_fd, destination_info) == destination_info['sha256'], 'artifact content changed after review')
        clone_fd(src_fd, directory_fd, temporary.name)
        temp_stat = temporary.lstat()
        created = (temp_stat.st_dev, temp_stat.st_ino)
        temporary.chmod(destination_info['mode'])
        os.utime(temporary, ns=(destination_info['atime_ns'], destination_info['mtime_ns']), follow_symlinks=False)
        cloned = inspect(temporary, destination_info['sha256'])
        require(all(cloned[k] == destination_info[k] for k in ['bytes', 'uid', 'gid', 'mode', 'mtime_ns']) and
                cloned['inode'] not in [source_info['inode'], destination_info['inode']], 'clone metadata or independence differs')
        temp_fd = open_checked(temporary, cloned)
        try:
            os.fsync(temp_fd)
        finally:
            os.close(temp_fd)
        require(same(source.lstat(), source_info) and same(destination.lstat(), destination_info) and
                (destination.parent.stat().st_dev, destination.parent.stat().st_ino) ==
                (parent['device'], parent['inode']), 'artifact changed before atomic replacement')
        os.replace(temporary.name, destination.name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        created = None
        os.fsync(directory_fd)
        result = inspect(destination, destination_info['sha256'])
        require(result['inode'] == cloned['inode'] and same(source.lstat(), source_info),
                'published clone or original changed')
        return result
