"""Explicit frozen-link checks; ordinary saved-file Access remains unchanged.

Ancestor links are current audit observations, never retroactive frozen rows.
The caller authenticates ``rows`` and supplies its unchanged strict frozen-file
reader. Every resolved regular file is checked by that reader while all route
descriptors remain held. Directory targets receive metadata-only checks.
"""
import copy
import os
from pathlib import PurePosixPath
import re
import stat

FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
STAMP_FIELDS = ('dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink')
MAX_LINKS = 40
MAX_STEPS = 512
MAX_ROWS = 16000


def require(value, message):
    if not value:
        raise RuntimeError(message)


def path(value):
    require(type(value) is str and value.startswith('/') and not value.startswith('//')
        and value != '/' and str(PurePosixPath(value)) == value
        and '..' not in PurePosixPath(value).parts and len(os.fsencode(value)) <= 4096
        and not any(ord(c) < 32 or ord(c) == 127 for c in value), 'canonical declared absolute route')
    return value


def stamp(info):
    return {key: getattr(info, 'st_'+key) for key in FIELDS}


def route(info):
    # Match the qualified ordinary reader: unrelated ancestor membership/time
    # changes are allowed; held directory inode/type/mode changes are not.
    return dict(dev=info.st_dev, ino=info.st_ino, mode=info.st_mode)


def target(value):
    require(type(value) is str and 0 < len(os.fsencode(value)) <= 4096
        and not any(ord(c) < 32 or ord(c) == 127 for c in value), 'bounded explicit link text')
    require(not value.startswith('//'), 'ambiguous double-root link target')
    return value


def frozen_row(row):
    require(type(row) is dict and set(row) == {'stamp','target','resolved'}, 'exact frozen link row')
    values = row['stamp']
    require(type(values) is list and len(values) == 7
        and all(type(v) is int and v >= 0 for v in values)
        and values[1] > 0 and values[6] > 0 and stat.S_ISLNK(values[2]), 'typed frozen symlink stamp')
    target(row['target']); path(row['resolved'])


class FrozenLinks:
    def __init__(self, rows, *, read_file, guard=lambda: None):
        require(type(rows) is dict and len(rows) <= MAX_ROWS, 'bounded declared links')
        self.rows = copy.deepcopy(rows)
        for name, row in self.rows.items():
            path(name); frozen_row(row)
        self.read_file = read_file
        self.guard = guard
        self.checked = {}

    def verify(self, name):
        name = path(name)
        require(name in self.rows, 'undeclared frozen link')
        row = copy.deepcopy(self.rows[name]); self.guard()
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
        root = os.open('/', flags); descriptors = [root]
        stack = [('', root)]; directories = []; links = []; edges = []; leaf_seen = False
        parts = PurePosixPath(name).parts[1:]
        pending = [(part, i == len(parts)-1) for i, part in enumerate(parts)]
        terminal = None; resolved = None
        try:
            steps = 0
            while pending:
                steps += 1; self.guard()
                require(steps <= MAX_STEPS, 'bounded link expansion steps')
                part, declared_leaf = pending.pop(0)
                if part in ('', '.'):
                    continue
                if part == '..':
                    require(len(stack) > 1, 'link target traversed above filesystem root')
                    stack.pop(); continue
                parent = stack[-1][1]
                before = os.stat(part, dir_fd=parent, follow_symlinks=False)
                current = '/'+'/'.join([p for p, _ in stack[1:]]+[part])
                if stat.S_ISLNK(before.st_mode):
                    text = target(os.readlink(part, dir_fd=parent))
                    identity = stamp(before)
                    require(stamp(os.stat(part, dir_fd=parent, follow_symlinks=False)) == identity,
                            'link changed during initial observation')
                    links.append(dict(path=current, identity=identity, target=text, frozen_leaf=declared_leaf))
                    require(len(links) <= MAX_LINKS, 'bounded link expansion count')
                    edges.append(('link', parent, part, identity, text))
                    if declared_leaf:
                        require(not leaf_seen and [identity[k] for k in STAMP_FIELDS] == row['stamp']
                            and text == row['target'], 'frozen leaf identity/text differs')
                        leaf_seen = True
                    if text.startswith('/'):
                        stack = [('', root)]
                    expanded = text.split('/')
                    require(len(expanded)+len(pending) <= MAX_STEPS, 'bounded pending link components')
                    pending = [(part, False) for part in expanded]+pending
                    continue
                require(not declared_leaf, 'frozen leaf is not a symlink')
                if stat.S_ISDIR(before.st_mode):
                    descriptor = os.open(part, flags, dir_fd=parent); descriptors.append(descriptor)
                    key = route(before)
                    require(route(os.fstat(descriptor)) == key, 'directory changed during open')
                    directories.append(dict(path=current, identity=key))
                    edges.append(('directory', parent, part, descriptor, key))
                    stack.append((part, descriptor))
                else:
                    require(not pending and stat.S_ISREG(before.st_mode), 'target must end at ordinary file or directory')
                    descriptor = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                    descriptors.append(descriptor)
                    terminal = stamp(os.fstat(descriptor))
                    require(terminal == stamp(before), 'target file changed during open')
                    edges.append(('file', parent, part, descriptor, terminal)); resolved = current
            if terminal is None:
                descriptor = stack[-1][1]; terminal = stamp(os.fstat(descriptor))
                require(stat.S_ISDIR(terminal['mode']), 'ordinary final directory')
                resolved = '/'+'/'.join(p for p, _ in stack[1:])
            require(leaf_seen and resolved == row['resolved'], 'exact frozen resolved route differs')
            file_proof = None
            if stat.S_ISREG(terminal['mode']):
                # The callback must remain the existing strictly scoped, ordinary
                # frozen-file reader; it is never passed an alias pathname.
                file_proof = copy.deepcopy(self.read_file(resolved))
                require(type(file_proof) is dict and set(file_proof) == {'identity','size','sha256'}
                    and type(file_proof['identity']) is dict and set(file_proof['identity']) == set(FIELDS)
                    and all(type(v) is int for v in file_proof['identity'].values())
                    and file_proof['identity'] == terminal and type(file_proof['size']) is int
                    and file_proof['size'] == terminal['size'] and type(file_proof['sha256']) is str
                    and re.fullmatch('[0-9a-f]{64}', file_proof['sha256']) is not None,
                    'strict frozen target-file proof differs')
            self.guard()
            require(stamp(os.fstat(descriptor)) == terminal, 'resolved endpoint changed during verification')
            for kind, parent, part, held, expected in edges:
                named = os.stat(part, dir_fd=parent, follow_symlinks=False)
                if kind == 'link':
                    require(stamp(named) == held and os.readlink(part, dir_fd=parent) == expected,
                            'ancestor or leaf link changed during verification')
                elif kind == 'directory':
                    require(route(named) == expected and route(os.fstat(held)) == expected,
                            'held ancestor directory route changed during verification')
                else:
                    require(stamp(named) == expected and stamp(os.fstat(held)) == expected,
                            'resolved file changed during verification')
            observation = dict(policy='explicit-frozen-link-current-route-v1',path=name,frozen_row=row,
                current_ancestor_observations=dict(directories=directories,links=links),
                resolved_identity=terminal,resolved_file=file_proof,
                ancestors_were_in_original_freeze=False)
            require(name not in self.checked or self.checked[name] == observation,
                    'frozen link route changed after its first audit observation')
            self.checked.setdefault(name, copy.deepcopy(observation))
            return copy.deepcopy(observation)
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def recheck(self):
        # Snapshot keys so a rejected change cannot replace the first evidence.
        for name in list(self.checked):
            self.verify(name)
        return copy.deepcopy(self.checked)
