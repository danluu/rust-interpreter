"""Read-only saved-audit callbacks with explicit physical and inspection scopes.

No constructors here import producer code, create outputs, or infer missing
historical bytes. Callers authenticate the prepared document and separately
qualified supplemental rows before constructing this access object.
"""
from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
MAX_FILES = 180000
MAX_FILE = 2**30
MAX_BYTES = 8*2**30
MAX_JSON = 64*2**20


def require(value, message):
    if not value:
        raise RuntimeError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False)+'\n').encode()


def same(left, right):
    return encoded(left) == encoded(right)


def path(value):
    name = os.fspath(value)
    require(type(name) is str and name.startswith('/') and not name.startswith('//')
            and name != '/' and str(PurePosixPath(name)) == name
            and '..' not in PurePosixPath(name).parts
            and len(name.encode()) <= 4096
            and not any(ord(c) < 32 or ord(c) == 127 for c in name),
            'canonical absolute declared path required')
    return Path(name)


def stamp(info):
    return {key: getattr(info, 'st_'+key) for key in FIELDS}


def typed_identity(value, kind=None):
    require(type(value) is dict and set(value) == set(FIELDS)
            and all(type(v) is int and v >= 0 for v in value.values())
            and value['ino'] > 0 and value['nlink'] > 0, 'exact seven-field identity required')
    if kind is not None:
        require({'file': stat.S_ISREG, 'directory': stat.S_ISDIR,
                 'link': stat.S_ISLNK}[kind](value['mode']), 'entry kind differs')


def file_row(row):
    require(type(row) is dict and set(row) == {'size', 'sha256', 'identity'}
            and type(row['size']) is int and 0 <= row['size'] <= MAX_FILE
            and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']),
            'exact bounded physical file row required')
    typed_identity(row['identity'], 'file')
    require(row['size'] == row['identity']['size'], 'physical size and identity differ')


def table(rows):
    require(type(rows) is dict and len(rows) <= MAX_FILES, 'bounded complete file table required')
    total = 0
    for name, row in rows.items():
        path(name); file_row(row); total += row['size']
    require(total <= MAX_BYTES, 'complete file-table byte cap exceeded')


def inspection_union(prepared, supplemental, *, historical_paths):
    """Preserve the original document and add separately authenticated file rows.

    The returned ``value`` is an inspection context, never a replacement
    prepared packet. Its non-file metadata, including snapshot_inputs, is
    byte-for-byte equal under typed canonical JSON. The report identifies only
    genuinely additional paths; an overlapping row must be exactly identical.
    Real prepared absences after qualified retirement remain unchanged. This
    pure union neither adds absences nor qualifies retirement; its caller must
    authenticate that actual retirement and check the named absences physically.
    """
    original, extra = copy.deepcopy(prepared), copy.deepcopy(supplemental)
    require(type(original) is dict and 'file_table_base' not in original
            and 'file_table_integrity' not in original, 'complete expanded prepared document required')
    table(original['files']); table(extra)
    historical = list(historical_paths)
    require(historical == sorted(set(historical)), 'sorted unique historical paths required')
    for name in historical:
        path(name)
    forbidden = set(historical)
    require(not forbidden & (set(original['files']) | set(extra)
            | set(original.get('snapshot_inputs', []))),
            'historical copy cannot be a physical input or selected payload')
    merged = copy.deepcopy(original['files'])
    added = {}
    for name, row in extra.items():
        if name in merged:
            require(same(merged[name], row), 'supplement cannot relabel a prepared row')
        else:
            merged[name] = row; added[name] = row
    table(merged)
    value = copy.deepcopy(original)
    value['files'] = copy.deepcopy(merged)
    require(same({k:v for k,v in value.items() if k != 'files'},
                 {k:v for k,v in original.items() if k != 'files'}), 'prepared metadata changed')
    return dict(value=value, prepared=original, supplemental=extra,
        report=dict(policy='separate-audit-inspection-union-v1',
            prepared_table_sha256=hashlib.sha256(encoded(original['files'])).hexdigest(),
            supplemental_table_sha256=hashlib.sha256(encoded(extra)).hexdigest(),
            inspection_table_sha256=hashlib.sha256(encoded(merged)).hexdigest(),
            prepared_files=len(original['files']), additional_files=len(added),
            additional_bytes=sum(row['size'] for row in added.values()),
            additional_paths=sorted(added), historical_paths=historical,
            prepared_packet_mutated=False, snapshot_selection_changed=False))


def route_key(info):
    # Ancestors can legitimately acquire unrelated children while this reader
    # runs. Their named inode/type/mode must remain the held route throughout.
    return info.st_dev, info.st_ino, info.st_mode


@contextmanager
def parent_descriptor(value):
    """Hold all no-follow directory descriptors until the caller has finished."""
    target = path(value)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
    descriptors = [os.open('/', flags)]
    links = []
    try:
        for name in target.parts[1:-1]:
            parent = descriptors[-1]
            named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            require(stat.S_ISDIR(named.st_mode), 'symlink or non-directory ancestor')
            child = os.open(name, flags, dir_fd=parent)
            descriptors.append(child)
            require(route_key(os.fstat(child)) == route_key(named), 'ancestor changed during open')
            links.append((parent, name, child, route_key(named)))
        yield descriptors[-1], target.name
        # No callbacks occur after this final held-route comparison.
        for parent, name, child, expected in links:
            require(route_key(os.fstat(child)) == expected
                    and route_key(os.stat(name, dir_fd=parent, follow_symlinks=False)) == expected,
                    'ancestor route changed during read')
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


class Access:
    """Strict physical reads and observed output inventories; no write API.

    ``files`` contains fully authenticated current/supplemental rows. Historical
    paths are rejected before any syscall. ``entries`` authorizes only explicit
    provider links/directories and snapshot directory identities. Output roots
    authorize actual closed evidence or a derived installation prefix; they
    never authorize a historical pathname. Every repeated read retains the first
    complete identity/hash, and recheck(full=True) reads all observed bytes again.
    """
    def __init__(self, files, *, historical_paths=(), entries=None,
                 output_roots=(), guard=lambda: None):
        table(files)
        self.files = copy.deepcopy(files)
        self.historical = frozenset(str(path(n)) for n in historical_paths)
        self.entries = copy.deepcopy(entries or {})
        for name, row in self.entries.items():
            path(name); typed_identity(row)
            require(stat.S_ISDIR(row['mode']) or stat.S_ISLNK(row['mode']),
                    'explicit metadata entry must be a directory or link')
        require(not self.historical & (set(self.files) | set(self.entries)),
                'historical path cannot be declared current')
        self.output_roots = tuple(path(root) for root in output_roots)
        require(len(set(self.output_roots)) == len(self.output_roots)
                and not any(a != b and a in b.parents for a in self.output_roots for b in self.output_roots),
                'output roots must be distinct and nonoverlapping')
        self.guard = guard
        self.checked = {}
        self.checked_entries = {}
        self.directories = {}

    def _scope(self, value, *, file=False, frozen=None):
        p = path(value); name = str(p)
        require(name not in self.historical, 'historical proof copy has no current-file API')
        current = name in self.files or (not file and name in self.entries)
        output = any(p == root or root in p.parents for root in self.output_roots)
        require((current if frozen is True else output if frozen is False else current or output),
                'undeclared saved-evidence path')
        return p

    def _remember(self, name, row):
        require(name not in self.checked or same(self.checked[name], row),
                'repeated read changed the first complete file observation')
        self.checked.setdefault(name, copy.deepcopy(row))

    def _read(self, value, *, collect=False, limit=MAX_FILE, frozen=None):
        require(type(limit) is int and 0 <= limit <= MAX_FILE, 'bounded explicit read limit')
        p = self._scope(value, file=True, frozen=frozen); name = str(p)
        self.guard(); pieces = []; total = 0; h = hashlib.sha256()
        with parent_descriptor(p) as (parent, leaf):
            before = stamp(os.stat(leaf, dir_fd=parent, follow_symlinks=False))
            typed_identity(before, 'file')
            require(before['size'] <= limit, 'saved file exceeds read bound')
            descriptor = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            with os.fdopen(descriptor, 'rb') as stream:
                require(same(stamp(os.fstat(stream.fileno())), before), 'leaf changed during open')
                while True:
                    chunk = stream.read(min(2**20, limit-total+1))
                    if not chunk:
                        break
                    total += len(chunk); require(total <= limit, 'saved file grew beyond bound')
                    h.update(chunk)
                    if collect:
                        pieces.append(chunk)
                    self.guard()
                # A final callback precedes every final leaf/ancestor check.
                self.guard()
                require(same(stamp(os.fstat(stream.fileno())), before), 'opened file changed during read')
            require(same(stamp(os.stat(leaf, dir_fd=parent, follow_symlinks=False)), before),
                    'named leaf changed during read')
            row = dict(size=total, sha256=h.hexdigest(), identity=before)
            require(total == before['size'], 'saved file length changed')
            if name in self.files:
                require(same(row, self.files[name]), 'frozen physical bytes/identity differ')
            self._remember(name, row)
        return b''.join(pieces) if collect else copy.deepcopy(row)

    def file(self, value):
        self._read(value, frozen=True)
        return path(value)

    def record(self, value):
        return dict(path=str(path(value)), **self._read(value))

    def sha(self, value, *, frozen=None):
        return self._read(value, frozen=frozen)['sha256']

    def read_bytes(self, value, *, frozen=None, limit=MAX_JSON):
        return self._read(value, collect=True, limit=limit, frozen=frozen)

    def read_json(self, value, *, frozen=None):
        def unique(pairs):
            result = {}
            for key, item in pairs:
                require(key not in result, 'duplicate saved JSON key')
                result[key] = item
            return result
        return json.loads(self.read_bytes(value, frozen=frozen), object_pairs_hook=unique,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))

    def identity(self, value):
        p = self._scope(value); name = str(p); self.guard()
        with parent_descriptor(p) as (parent, leaf):
            actual = stamp(os.stat(leaf, dir_fd=parent, follow_symlinks=False))
            typed_identity(actual)
            expected = self.files[name]['identity'] if name in self.files else self.entries.get(name)
            if expected is not None:
                require(same(actual, expected), 'declared entry identity differs')
            require(name not in self.checked_entries or same(self.checked_entries[name], actual),
                    'entry changed after first observation')
            self.checked_entries.setdefault(name, actual)
        return copy.deepcopy(actual)

    def directory_record(self, value):
        p = self._scope(value); name = str(p); self.guard()
        with parent_descriptor(p) as (parent, leaf):
            before = stamp(os.stat(leaf, dir_fd=parent, follow_symlinks=False)); typed_identity(before, 'directory')
            descriptor = os.open(leaf, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            try:
                require(same(stamp(os.fstat(descriptor)), before), 'directory changed during open')
                children = sorted(os.listdir(descriptor)); self.guard()
                require(same(stamp(os.fstat(descriptor)), before)
                        and same(stamp(os.stat(leaf, dir_fd=parent, follow_symlinks=False)), before),
                        'directory changed during listing')
            finally:
                os.close(descriptor)
            if name in self.entries:
                require(same(before, self.entries[name]), 'declared directory changed')
            row = dict(identity=before, children=children)
            require(name not in self.directories or same(self.directories[name], row),
                    'complete directory changed after first observation')
            self.directories.setdefault(name, row)
        return copy.deepcopy(row)

    def inventory(self, value):
        root = self._scope(value, frozen=False)
        result = {}; pending = [(root, '.')]; total = 0
        while pending:
            directory, relative = pending.pop()
            listing = self.directory_record(directory)
            result[relative] = dict(kind='directory', identity=listing['identity'])
            for name in listing['children']:
                require(type(name) is str and name not in ['.', '..'] and '/' not in name, 'ordinary inventory member')
                p = directory/name; label = str(p.relative_to(root)); observed = self.identity(p)
                if stat.S_ISDIR(observed['mode']):
                    pending.append((p, label))
                else:
                    typed_identity(observed, 'file')
                    row = self._read(p); total += row['size']
                    result[label] = dict(kind='file', identity=row['identity'], sha256=row['sha256'])
                require(len(result)+len(pending) <= MAX_FILES and total <= MAX_BYTES, 'complete inventory cap')
        # Repeat exact directory membership after every descendant payload read.
        for name, row in list(result.items()):
            if row['kind'] == 'directory':
                self.directory_record(root if name == '.' else root/name)
        return dict(sorted(result.items()))

    def recheck(self, *, full=True):
        for name in list(self.checked):
            if full:
                self._read(name)
            else:
                require(same(self.identity(name), self.checked[name]['identity']), 'observed file changed')
        for name in list(self.checked_entries):
            self.identity(name)
        for name in list(self.directories):
            self.directory_record(name)
