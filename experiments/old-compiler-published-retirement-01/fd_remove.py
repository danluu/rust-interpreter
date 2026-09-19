"""Remove one admitted ordinary tree through held directory descriptors.

No discovery, chmod, processes or signal authority. The caller supplies the
complete frozen inventory, exact outer identity, capacity check and a precreated
ordinary empty ledger outside the root. It owns quiescence and preservation.
Internal hardlinks are allowed only when every alias is in this exact inventory.
Every unlink/rmdir has fsynced intent, completion, then validation observations.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import time

FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
MAX_LEDGER_BYTES = 192 * 2**20
MAX_EVENT_BYTES = 2**20


def require(value, message):
    if not value:
        raise RuntimeError(message)


def identity(info):
    return {key: getattr(info, 'st_' + key) for key in FIELDS}


def event(fd, value):
    """Publish one complete event through the caller-owned held ledger inode."""
    data = (json.dumps(value, sort_keys=True) + '\n').encode()
    require(len(data) <= MAX_EVENT_BYTES and os.fstat(fd).st_size + len(data) <= MAX_LEDGER_BYTES,
            'ledger write exceeds fixed bound')
    while data:
        count = os.write(fd, data)
        require(count > 0, 'ledger write made no progress')
        data = data[count:]
    os.fsync(fd)


def ledger_summary(path):
    """Report durable prefix honestly, including an incomplete final JSON write."""
    result = dict(intent=[], unlinked=[], validated=[], uncertain=[], readback_error=None)
    try:
        with Path(path).open('rb') as source:
            require(os.fstat(source.fileno()).st_size <= MAX_LEDGER_BYTES, 'ledger read exceeds fixed bound')
            while raw := source.readline(MAX_EVENT_BYTES + 1):
                require(len(raw) <= MAX_EVENT_BYTES and raw.endswith(b'\n'), 'incomplete ledger event')
                row = json.loads(raw)
                kind = row['event']; name = row['relative']
                require(kind in ('intent', 'unlinked', 'validated'), 'unknown ledger event')
                require(name not in result[kind], 'duplicate ledger event')
                require(kind == 'intent' or name in result['intent'], 'completion without intent')
                require(kind != 'validated' or name in result['unlinked'], 'validation without completion')
                result[kind].append(name)
    except BaseException as error:
        result['readback_error'] = repr(error)
    result['uncertain'] = [name for name in result['intent'] if name not in result['unlinked']]
    return result


def post_mutation(operation, before, after, parent_before, parent_after, parent, remaining):
    stable = ('dev', 'ino', 'mode', 'size', 'mtime_ns') if operation == 'unlink' else ('dev', 'ino', 'mode')
    require(all(after[key] == before[key] for key in stable), 'removed inode changed unexpectedly')
    if operation == 'unlink':
        require(after['nlink'] == before['nlink'] - 1, 'unexpected remaining file links')
    require(all(parent_after[key] == parent_before[key] for key in ('dev', 'ino', 'mode')),
            'mutation parent identity changed')
    require(set(os.listdir(parent)) == remaining, 'parent membership differs after mutation')


def remove_tree(root, rows, outer_expected, ledger, capacity):
    root = Path(root); ledger = Path(ledger)
    expected = json.loads(json.dumps(rows))
    require(root.is_absolute() and root.resolve(strict=True) == root, 'ordinary absolute root required')
    require(ledger.resolve(strict=True) == ledger and not ledger.is_relative_to(root), 'ledger route is inside root or indirect')
    require('.' in expected and len(expected) <= 100000, 'missing root or inventory exceeds bound')
    children = {}; groups = {}
    for name, row in expected.items():
        parts = PurePosixPath(name).parts
        require(name == '.' or (parts and not PurePosixPath(name).is_absolute() and '..' not in parts
                and str(PurePosixPath(name)) == name), 'invalid inventory path')
        before = row['identity']
        require(set(before) == set(FIELDS), 'incomplete identity')
        if row['kind'] == 'directory':
            require(stat.S_ISDIR(before['mode']) and before['mode'] & stat.S_IWUSR, 'directory is not ordinary user-writable')
            children[name] = set()
        else:
            require(row['kind'] == 'file' and stat.S_ISREG(before['mode']), 'special or linked path rejected')
            require(isinstance(row['sha256'], str) and len(row['sha256']) == 64, 'missing file digest')
            groups.setdefault((before['dev'], before['ino']), set()).add(name)
    require(expected['.']['kind'] == 'directory', 'root is not directory')
    for name in expected:
        if name != '.':
            parent = str(PurePosixPath(name).parent)
            require(parent in children, 'inventory parent missing')
            children[parent].add(PurePosixPath(name).name)
    for aliases in groups.values():
        first = expected[next(iter(aliases))]
        require(first['identity']['nlink'] == len(aliases) and
                all(expected[name] == first for name in aliases), 'outside hardlink or inconsistent internal alias')
    outer_fd = os.open(root.parent, DIRECTORY_FLAGS); root_fd = None; ledger_fd = None
    fst = lambda fd: identity(os.fstat(fd))
    at = lambda fd, name: identity(os.stat(name, dir_fd=fd, follow_symlinks=False))
    try:
        require(fst(outer_fd) == outer_expected, 'outer parent changed')
        require(at(outer_fd, root.name) == expected['.']['identity'], 'root route changed')
        root_fd = os.open(root.name, DIRECTORY_FLAGS, dir_fd=outer_fd)
        require(fst(root_fd) == expected['.']['identity'], 'opened root differs')
        outer_children = set(os.listdir(outer_fd))
        ledger_fd = os.open(ledger, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
        ledger_before = fst(ledger_fd)
        require(stat.S_ISREG(ledger_before['mode']) and ledger_before['nlink'] == 1 and
                ledger_before['size'] == 0 and identity(ledger.lstat()) == ledger_before,
                'ledger must be precreated empty ordinary single-link file')

        def root_binding():
            require(fst(outer_fd) == outer_expected and at(outer_fd, root.name) == expected['.']['identity']
                    and fst(root_fd) == expected['.']['identity'], 'root or outer binding changed')

        def parent_fd(name):
            root_binding(); fd = os.dup(root_fd); key = '.'
            try:
                for part in PurePosixPath(name).parts[:-1]:
                    require(fst(fd) == expected[key]['identity'], 'held ancestor changed')
                    child_key = part if key == '.' else key + '/' + part
                    require(expected[child_key]['kind'] == 'directory' and
                            at(fd, part) == expected[child_key]['identity'], 'ancestor route changed')
                    child = os.open(part, DIRECTORY_FLAGS, dir_fd=fd)
                    try:
                        require(fst(child) == expected[child_key]['identity'], 'opened ancestor differs')
                    except BaseException:
                        os.close(child); raise
                    os.close(fd); fd = child; key = child_key
                require(fst(fd) == expected[key]['identity'], 'mutation parent changed')
                return fd, key, PurePosixPath(name).name
            except BaseException:
                os.close(fd); raise

        # Reject unadmitted entries, aliases and stale identities before the first mutation.
        require(set(os.listdir(root_fd)) == children['.'], 'root membership differs')
        for name, row in sorted(expected.items()):
            if name == '.':
                continue
            capacity(); parent, key, basename = parent_fd(name)
            try:
                require(at(parent, basename) == row['identity'], 'inventory entry changed')
                if row['kind'] == 'directory':
                    child = os.open(basename, DIRECTORY_FLAGS, dir_fd=parent)
                    try:
                        require(fst(child) == row['identity'] and set(os.listdir(child)) == children[name],
                                'directory inventory differs')
                    finally:
                        os.close(child)
            finally:
                os.close(parent)

        def publish(row):
            capacity()
            event(ledger_fd, dict(row, time=time.time()))
            require(identity(ledger.lstat()) == fst(ledger_fd), 'ledger route changed after publication')

        def mutate(name, operation, parent, key, basename, fd):
            before = expected[name]['identity']; parent_before = outer_expected if key is None else expected[key]['identity']
            names = outer_children if key is None else children[key]
            require(fst(fd) == before and at(parent, basename) == before and fst(parent) == parent_before,
                    'entry or parent changed before intent')
            require(set(os.listdir(parent)) == names, 'pre-mutation membership differs')
            row = dict(relative=name, path=str(root if name == '.' else root / name), operation=operation,
                       before=before, parent_before=parent_before)
            if operation == 'unlink':
                row['sha256'] = expected[name]['sha256']
            publish(dict(row, event='intent'))
            require(fst(fd) == before and at(parent, basename) == before and fst(parent) == parent_before,
                    'entry changed after durable intent')
            if operation == 'unlink':
                os.unlink(basename, dir_fd=parent)
            else:
                os.rmdir(basename, dir_fd=parent)
            # Do not put capacity/identity checks before durable completion.
            event(ledger_fd, dict(row, event='unlinked', time=time.time()))
            after = fst(fd); parent_after = fst(parent); remaining = names - {basename}
            post_mutation(operation, before, after, parent_before, parent_after, parent, remaining)
            require(identity(ledger.lstat()) == fst(ledger_fd), 'ledger route changed after completion')
            if key is not None:
                children[key] = remaining; expected[key]['identity'] = parent_after
            del expected[name]
            alias_updates = {}
            if operation == 'unlink':
                aliases = groups[(before['dev'], before['ino'])]; aliases.remove(name)
                for alias in sorted(aliases):
                    alias_parent, _, alias_name = parent_fd(alias)
                    try:
                        require(at(alias_parent, alias_name) == after, 'remaining internal alias changed')
                        expected[alias]['identity'] = after; alias_updates[alias] = after
                    finally:
                        os.close(alias_parent)
            publish(dict(relative=name, operation=operation, event='validated', after=after,
                         parent_after=parent_after, aliases=alias_updates))

        for name in sorted(name for name, row in expected.items() if row['kind'] == 'file'):
            capacity(); parent, key, basename = parent_fd(name); fd = None
            try:
                row = expected[name]; before = row['identity']
                require(before['nlink'] == len(groups[(before['dev'], before['ino'])]), 'link count changed')
                require(at(parent, basename) == before, 'file identity changed')
                fd = os.open(basename, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
                require(fst(fd) == before, 'opened file differs')
                digest = hashlib.sha256(); size = 0
                while block := os.read(fd, min(8 * 2**20, before['size'] - size + 1)):
                    capacity(); size += len(block)
                    require(size <= before['size'], 'held file grew beyond admitted size')
                    digest.update(block)
                require(size == before['size'] and digest.hexdigest() == row['sha256'] and fst(fd) == before,
                        'held file bytes changed')
                mutate(name, 'unlink', parent, key, basename, fd)
            finally:
                if fd is not None:
                    os.close(fd)
                os.close(parent)
        for name in sorted([name for name in expected if name != '.'],
                           key=lambda value: (len(PurePosixPath(value).parts), value), reverse=True):
            capacity(); parent, key, basename = parent_fd(name); fd = None
            try:
                require(expected[name]['kind'] == 'directory', 'unexpected remaining file')
                fd = os.open(basename, DIRECTORY_FLAGS, dir_fd=parent)
                require(not children[name] and not os.listdir(fd), 'directory not empty')
                mutate(name, 'rmdir', parent, key, basename, fd)
                del children[name]
            finally:
                if fd is not None:
                    os.close(fd)
                os.close(parent)
        capacity(); root_binding()
        require(set(expected) == {'.'} and not children['.'] and not os.listdir(root_fd), 'root not empty')
        mutate('.', 'rmdir', outer_fd, None, root.name, root_fd)
        require(not expected and root.name not in os.listdir(outer_fd), 'removal incomplete')
        return dict(removed_entries=len(rows), files=sum(row['kind'] == 'file' for row in rows.values()),
                    directories=sum(row['kind'] == 'directory' for row in rows.values()), root_absent=True)
    finally:
        if ledger_fd is not None:
            os.close(ledger_fd)
        if root_fd is not None:
            os.close(root_fd)
        os.close(outer_fd)
