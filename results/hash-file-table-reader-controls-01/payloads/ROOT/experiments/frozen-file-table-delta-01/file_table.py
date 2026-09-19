"""Read-only, single-level representation of an authenticated frozen file table.

No payload discovery, mutation, process control, or provider invocation occurs.
Callers still verify all reconstructed files, links, absences and their own
selection/retention contracts. This module authenticates only the base catalog.
"""
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import PurePosixPath
import re
import stat

MAXIMUM_FILES = 180000
MAXIMUM_FILE_BYTES = 2**30
MAXIMUM_TOTAL_BYTES = 8 * 2**30
MAXIMUM_BASE_BYTES = 64 * 2**20
MAXIMUM_TABLE_BYTES = 64 * 2**20
MAXIMUM_DOCUMENT_BYTES = 64 * 2**20
MAXIMUM_JSON_DEPTH = 64
MAXIMUM_JSON_NODES = 4_000_000
MAXIMUM_PATH_BYTES = 4096
CHUNK_BYTES = 2**20
IDENTITY_FIELDS = ('dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink')
ROW_FIELDS = frozenset(('size', 'sha256', 'identity'))
REFERENCE_FIELDS = frozenset(('path', 'sha256'))
INTEGRITY_FIELDS = frozenset(('sha256', 'count', 'total_bytes'))
REPRESENTATION_FIELDS = frozenset(('file_table_base', 'file_table_integrity'))
_SHA = re.compile(r'[0-9a-f]{64}\Z')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    """Canonical typed JSON used for file_table_integrity.sha256 (with newline)."""
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')


def _bounded_encoded(value, maximum, guard):
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'),
                               ensure_ascii=True, allow_nan=False)
    chunks = []
    length = 1
    for index, chunk in enumerate(encoder.iterencode(value)):
        if index % 4096 == 0:
            guard()
        data = chunk.encode('utf-8')
        length += len(data)
        require(length <= maximum, 'canonical JSON exceeds bound')
        chunks.append(data)
    chunks.append(b'\n')
    return b''.join(chunks)


def _path(value):
    require(type(value) is str and value.startswith('/') and not value.startswith('//')
            and value != '/' and str(PurePosixPath(value)) == value
            and '..' not in PurePosixPath(value).parts
            and not any(ord(char) < 32 or ord(char) == 127 for char in value)
            and len(value.encode('utf-8')) <= MAXIMUM_PATH_BYTES,
            'canonical bounded absolute path required')
    return value


def _digest(value):
    require(type(value) is str and _SHA.fullmatch(value) is not None,
            'lowercase SHA-256 required')


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('nonfinite JSON constant: ' + value)


def _clone(value, guard):
    """Reject Python-only values and clone without retaining caller aliases."""
    nodes = 0

    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        require(nodes <= MAXIMUM_JSON_NODES and depth <= MAXIMUM_JSON_DEPTH,
                'bounded JSON structure required')
        if nodes % 4096 == 0:
            guard()
        kind = type(item)
        if kind is dict:
            require(all(type(key) is str for key in item), 'JSON object keys must be strings')
            for child in item.values():
                visit(child, depth + 1)
        elif kind is list:
            for child in item:
                visit(child, depth + 1)
        elif kind is float:
            require(math.isfinite(item), 'finite JSON number required')
        elif kind is str:
            require(len(item) <= MAXIMUM_DOCUMENT_BYTES, 'bounded JSON string required')
        else:
            require(kind in (int, bool, type(None)), 'JSON value required')

    guard()
    visit(value, 0)
    raw = _bounded_encoded(value, MAXIMUM_DOCUMENT_BYTES, guard)
    guard()
    return json.loads(raw, object_pairs_hook=_unique, parse_constant=_constant)


def _identity(value):
    require(type(value) is dict and set(value) == set(IDENTITY_FIELDS),
            'exact seven-field identity required')
    require(all(type(value[key]) is int and value[key] >= 0 for key in IDENTITY_FIELDS),
            'identity fields must be nonnegative integers')
    require(value['ino'] > 0 and value['nlink'] > 0 and stat.S_ISREG(value['mode']),
            'ordinary file identity required')


def _table(files, guard):
    require(type(files) is dict and len(files) <= MAXIMUM_FILES, 'bounded file table required')
    total = 0
    for index, (name, row) in enumerate(files.items()):
        if index % 1024 == 0:
            guard()
        _path(name)
        require(type(row) is dict and set(row) == ROW_FIELDS, 'exact file-row schema required')
        require(type(row['size']) is int and 0 <= row['size'] <= MAXIMUM_FILE_BYTES,
                'bounded integer file size required')
        _digest(row['sha256'])
        _identity(row['identity'])
        require(row['size'] == row['identity']['size'], 'file size differs from identity')
        total += row['size']
        require(total <= MAXIMUM_TOTAL_BYTES, 'total declared file bytes exceed bound')
    raw = _bounded_encoded(files, MAXIMUM_TABLE_BYTES, guard)
    guard()
    return dict(sha256=hashlib.sha256(raw).hexdigest(), count=len(files), total_bytes=total)


def _metadata(document, files):
    require(type(document) is dict and 'files' in document, 'freeze object and files required')
    require(type(document.get('links')) is dict and type(document.get('absent_paths')) is list
            and type(document.get('snapshot_inputs')) is list,
            'complete links, absences and snapshot selection required')
    for name in document['links']:
        _path(name)
    for key in ('absent_paths', 'snapshot_inputs'):
        names = document[key]
        for name in names:
            _path(name)
        require(len(names) == len(set(names)), 'duplicate ' + key)
    require(set(document['snapshot_inputs']) <= set(files), 'snapshot selection missing from full file table')
    require(not set(files) & set(document['links']), 'file and link paths overlap')
    require(not (set(files) | set(document['links'])) & set(document['absent_paths']),
            'present and absent paths overlap')


def _stamp(value):
    return {name: getattr(value, 'st_' + name) for name in IDENTITY_FIELDS}


def _directory_identity(value):
    return value.st_dev, value.st_ino, value.st_mode


def _unchanged_base(file_fd, before, parent, leaf, route):
    require(_stamp(os.fstat(file_fd)) == before
            and _stamp(os.stat(leaf, dir_fd=parent, follow_symlinks=False)) == before,
            'base changed during read or construction')
    for parent_fd, component, child, expected in route:
        require(_directory_identity(os.fstat(child)) == expected
                and _directory_identity(os.stat(component, dir_fd=parent_fd, follow_symlinks=False)) == expected,
                'base parent route changed during read or construction')


@contextmanager
def _base(reference, guard):
    """Read one ordinary base through a held, no-follow chain from filesystem root."""
    require(type(reference) is dict and set(reference) == REFERENCE_FIELDS,
            'exact base reference required')
    name = _path(reference['path'])
    _digest(reference['sha256'])
    components = PurePosixPath(name).parts[1:]
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory_fds = []
    route = []
    file_fd = None
    guard()
    try:
        directory_fds.append(os.open('/', directory_flags))
        for component in components[:-1]:
            parent = directory_fds[-1]
            child = os.open(component, directory_flags, dir_fd=parent)
            directory_fds.append(child)
            held = os.fstat(child)
            require(stat.S_ISDIR(held.st_mode), 'ordinary base parent required')
            route.append((parent, component, child, _directory_identity(held)))
        parent = directory_fds[-1]
        leaf = components[-1]
        before = _stamp(os.stat(leaf, dir_fd=parent, follow_symlinks=False))
        _identity(before)
        require(before['size'] <= MAXIMUM_BASE_BYTES, 'base JSON exceeds bound')
        file_fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        require(_stamp(os.fstat(file_fd)) == before, 'base changed before opening')
        blocks = []
        length = 0
        while True:
            guard()
            block = os.read(file_fd, min(CHUNK_BYTES, MAXIMUM_BASE_BYTES + 1 - length))
            if not block:
                break
            blocks.append(block)
            length += len(block)
            require(length <= MAXIMUM_BASE_BYTES, 'base grew beyond bound')
        raw = b''.join(blocks)
        require(length == before['size'], 'base size changed during read')
        _unchanged_base(file_fd, before, parent, leaf, route)
        require(hashlib.sha256(raw).hexdigest() == reference['sha256'], 'base SHA-256 differs')
        guard()
        try:
            document = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique, parse_constant=_constant)
        except (UnicodeError, RecursionError) as error:
            raise ValueError('invalid bounded base JSON') from error
        require(type(document) is dict and not REPRESENTATION_FIELDS & set(document),
                'nested, cyclic or partial base representation refused')
        document = _clone(document, guard)
        _table(document.get('files'), guard)
        _metadata(document, document['files'])
        require(name not in document['files'], 'base must not include its own file row')
        row = dict(size=len(raw), sha256=reference['sha256'], identity=before)
        yield document, row
        # No callback or caller code runs between this final check and closing
        # the anchored descriptors. Changes by a guard after the read refuse.
        _unchanged_base(file_fd, before, parent, leaf, route)
    finally:
        if file_fd is not None:
            os.close(file_fd)
        for descriptor in reversed(directory_fds):
            os.close(descriptor)


def split(full_document, *, base_path, base_sha256, guard=lambda: None):
    """Return an independent compact document; refuse missing/changed base rows."""
    full = _clone(full_document, guard)
    require(type(full) is dict and not REPRESENTATION_FIELDS & set(full),
            'already compact or partial representation refused')
    files = full.get('files')
    integrity = _table(files, guard)
    _metadata(full, files)
    reference = dict(path=_path(base_path), sha256=base_sha256)
    with _base(reference, guard) as (base, base_row):
        for index, (name, row) in enumerate(base['files'].items()):
            if index % 1024 == 0:
                guard()
            require(name in files and encoded(files[name]) == encoded(row),
                    'full table omitted or changed a base row: ' + name)
        require(reference['path'] in files and encoded(files[reference['path']]) == encoded(base_row),
                'exact current base-file row must remain in delta')
        full['files'] = {name: row for name, row in files.items() if name not in base['files']}
        full['file_table_base'] = reference
        full['file_table_integrity'] = integrity
        return full


def expand(compact_document, *, guard=lambda: None):
    """Return the complete independent freeze after authenticating the pinned base."""
    compact = _clone(compact_document, guard)
    require(type(compact) is dict and REPRESENTATION_FIELDS <= set(compact),
            'complete compact representation required')
    expected = compact['file_table_integrity']
    require(type(expected) is dict and set(expected) == INTEGRITY_FIELDS,
            'exact full-table integrity required')
    _digest(expected['sha256'])
    require(type(expected['count']) is int and 0 <= expected['count'] <= MAXIMUM_FILES
            and type(expected['total_bytes']) is int and 0 <= expected['total_bytes'] <= MAXIMUM_TOTAL_BYTES,
            'bounded integer integrity counters required')
    delta = compact.get('files')
    _table(delta, guard)
    reference = compact['file_table_base']
    with _base(reference, guard) as (base, base_row):
        require(not set(base['files']) & set(delta), 'base and delta file rows overlap')
        require(reference['path'] in delta and encoded(delta[reference['path']]) == encoded(base_row),
                'exact current base-file row must remain in delta')
        require(len(base['files']) + len(delta) <= MAXIMUM_FILES, 'expanded file count exceeds bound')
        files = base['files'] | delta
        require(encoded(_table(files, guard)) == encoded(expected), 'full file-table integrity differs')
        _metadata(compact, files)
        compact['files'] = files
        del compact['file_table_base']
        del compact['file_table_integrity']
        return compact
