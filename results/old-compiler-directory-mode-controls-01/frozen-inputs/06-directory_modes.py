"""Add owner write permission to admitted 0555 directories through held FDs.

The root must already be 0700. Files and the root are never chmod'ed. The caller
owns exact-tree selection, full byte verification, quiescence and preservation;
this helper validates complete membership and metadata before the first change.
Each change has durable intent, applied and validated records. A failed change
is retained for inspection, without rollback, deletion or automatic retry.
"""
import json
import os
from pathlib import Path, PurePosixPath
import stat
import time

import fd_remove as f

MAX_ENTRIES = 10000
MAX_LEDGER_BYTES = 8 * 2**20


def event(fd, row):
    data = (json.dumps(row, sort_keys=True) + '\n').encode()
    f.require(os.fstat(fd).st_size + len(data) <= MAX_LEDGER_BYTES, 'mode ledger bound')
    f.event(fd, row)


def post_mode(before, after):
    f.require(all(after[k] == before[k] for k in f.FIELDS if k not in ['mode', 'ctime_ns'])
              and after['mode'] == before['mode'] | stat.S_IWUSR,
              'directory changed beyond admitted owner-write mode')


def make_writable(root, rows, outer_expected, ledger, capacity):
    root, ledger = Path(root), Path(ledger)
    expected = json.loads(json.dumps(rows))
    f.require(root.is_absolute() and root.resolve(strict=True) == root, 'ordinary absolute root required')
    f.require(ledger.resolve(strict=True) == ledger and not ledger.is_relative_to(root),
              'ordinary external ledger required')
    f.require('.' in expected and len(expected) <= MAX_ENTRIES, 'bounded complete inventory required')
    children = {}
    for name, row in expected.items():
        parts = PurePosixPath(name).parts
        f.require(name == '.' or (parts and not PurePosixPath(name).is_absolute() and '..' not in parts
                  and str(PurePosixPath(name)) == name), 'invalid inventory path')
        before = row['identity']
        f.require(set(before) == set(f.FIELDS), 'complete identity required')
        if row['kind'] == 'directory':
            f.require(stat.S_ISDIR(before['mode']) and stat.S_IMODE(before['mode']) ==
                      (0o700 if name == '.' else 0o555), 'unadmitted directory mode')
            children[name] = set()
        else:
            f.require(row['kind'] == 'file' and stat.S_ISREG(before['mode']) and before['nlink'] == 1,
                      'ordinary single-link files required')
    f.require(expected['.']['kind'] == 'directory', 'directory root required')
    for name in expected:
        if name != '.':
            parent = str(PurePosixPath(name).parent)
            f.require(parent in children, 'inventory parent missing')
            children[parent].add(PurePosixPath(name).name)
    fst = lambda fd: f.identity(os.fstat(fd))
    at = lambda fd, name: f.identity(os.stat(name, dir_fd=fd, follow_symlinks=False))
    outer_fd = os.open(root.parent, f.DIRECTORY_FLAGS)
    root_fd = ledger_fd = None
    try:
        f.require(fst(outer_fd) == outer_expected and at(outer_fd, root.name) == expected['.']['identity'],
                  'outer/root binding changed')
        root_fd = os.open(root.name, f.DIRECTORY_FLAGS, dir_fd=outer_fd)
        f.require(fst(root_fd) == expected['.']['identity'], 'opened root differs')
        ledger_fd = os.open(ledger, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
        ledger_before = fst(ledger_fd)
        f.require(stat.S_ISREG(ledger_before['mode']) and ledger_before['nlink'] == 1
                  and ledger_before['size'] == 0 and f.identity(ledger.lstat()) == ledger_before,
                  'empty ordinary single-link ledger required')

        def binding():
            f.require(fst(outer_fd) == outer_expected and fst(root_fd) == expected['.']['identity']
                      and at(outer_fd, root.name) == expected['.']['identity'], 'root route changed')

        def parent_fd(name):
            binding(); fd = os.dup(root_fd); key = '.'
            try:
                for part in PurePosixPath(name).parts[:-1]:
                    f.require(fst(fd) == expected[key]['identity'], 'held ancestor changed')
                    key = part if key == '.' else key + '/' + part
                    f.require(at(fd, part) == expected[key]['identity'], 'ancestor route changed')
                    child = os.open(part, f.DIRECTORY_FLAGS, dir_fd=fd)
                    try:
                        f.require(fst(child) == expected[key]['identity'], 'opened ancestor differs')
                    except BaseException:
                        os.close(child); raise
                    os.close(fd); fd = child
                f.require(fst(fd) == expected[key]['identity'], 'held parent changed')
                return fd, key, PurePosixPath(name).name
            except BaseException:
                os.close(fd); raise

        def complete_metadata_check():
            binding()
            f.require(set(os.listdir(root_fd)) == children['.'], 'root membership differs')
            for name, row in sorted(expected.items()):
                if name == '.':
                    continue
                capacity(); parent, _, basename = parent_fd(name)
                try:
                    f.require(at(parent, basename) == row['identity'], 'inventory entry changed')
                    if row['kind'] == 'directory':
                        fd = os.open(basename, f.DIRECTORY_FLAGS, dir_fd=parent)
                        try:
                            f.require(fst(fd) == row['identity'] and set(os.listdir(fd)) == children[name],
                                      'directory membership differs')
                        finally:
                            os.close(fd)
                finally:
                    os.close(parent)

        def publish(row):
            capacity(); event(ledger_fd, dict(row, time=time.time()))
            f.require(f.identity(ledger.lstat()) == fst(ledger_fd), 'mode ledger route changed')

        complete_metadata_check()
        names = sorted(name for name in children if name != '.')
        for name in names:
            capacity(); parent, key, basename = parent_fd(name); fd = None
            try:
                fd = os.open(basename, f.DIRECTORY_FLAGS, dir_fd=parent)
                before = expected[name]['identity']; parent_before = expected[key]['identity']
                f.require(fst(fd) == before and at(parent, basename) == before
                          and fst(parent) == parent_before and set(os.listdir(fd)) == children[name],
                          'directory binding changed before intent')
                change = dict(relative=name, operation='fchmod-owner-write', before=before,
                              target_mode=0o755, parent_before=parent_before)
                publish(dict(change, event='intent'))
                binding()
                f.require(fst(fd) == before and at(parent, basename) == before
                          and fst(parent) == parent_before, 'directory binding changed after intent')
                os.fchmod(fd, 0o755)
                # Completion publication precedes every fallible postcondition.
                event(ledger_fd, dict(change, event='applied', time=time.time()))
                after = fst(fd)
                post_mode(before, after)
                f.require(at(parent, basename) == after and fst(parent) == parent_before
                          and set(os.listdir(fd)) == children[name], 'directory changed after mode update')
                expected[name]['identity'] = after
                publish(dict(relative=name, operation='fchmod-owner-write', event='validated', after=after))
            finally:
                if fd is not None:
                    os.close(fd)
                os.close(parent)
        complete_metadata_check()
        return expected, dict(changed_directories=len(names), chmod_calls=len(names),
                              changed_files=0, changed_root=False)
    finally:
        if ledger_fd is not None:
            os.close(ledger_fd)
        if root_fd is not None:
            os.close(root_fd)
        os.close(outer_fd)
