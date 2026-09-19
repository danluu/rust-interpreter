"""Pure historical proof-copy references; never a filesystem or live identity API.

The caller authenticates the complete closed retention owner and qualified v2
catalog, verifies every selected gzip through full compressed and logical EOF,
and checks an independently qualified retirement before admitting absent copies.
This module validates typed metadata only. It grants no allocation credit.
"""
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
import stat

POLICY = 'historical-retained-proof-copy-references-v1'
MAXIMUM_FILES = 180000
MAXIMUM_COPIES = 256
MAXIMUM_BLOBS = 1024
MAXIMUM_FILE_BYTES = 64 * 2**20
MAXIMUM_COPY_BYTES = 512 * 2**20
MAXIMUM_DOCUMENT_BYTES = 64 * 2**20
IDENTITY = {'dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns'}
DIGEST = re.compile(r'[0-9a-f]{64}\Z')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode()


def clone(value):
    count = 0
    def visit(item, depth):
        nonlocal count
        count += 1
        require(depth <= 64 and count <= 4_000_000, 'bounded typed JSON required')
        kind = type(item)
        if kind is dict:
            require(all(type(k) is str for k in item), 'string object keys required')
            for child in item.values():
                visit(child, depth + 1)
        elif kind is list:
            for child in item:
                visit(child, depth + 1)
        elif kind is float:
            require(math.isfinite(item), 'finite JSON metadata required')
        else:
            require(kind in (str, int, bool, type(None)), 'ordinary JSON metadata required')
    visit(value, 0)
    raw = encoded(value)
    require(len(raw) <= MAXIMUM_DOCUMENT_BYTES, 'bounded metadata document required')
    return json.loads(raw)


def same(a, b):
    return encoded(a) == encoded(b)


def path(value):
    require(type(value) is str and value.startswith('/') and not value.startswith('//')
            and value != '/' and str(PurePosixPath(value)) == value
            and '..' not in PurePosixPath(value).parts and len(value.encode()) <= 4096
            and not any(ord(c) < 32 or ord(c) == 127 for c in value),
            'canonical absolute path required')
    return PurePosixPath(value)


def digest(value):
    require(type(value) is str and DIGEST.fullmatch(value) is not None, 'SHA-256 required')


def integer(value, maximum):
    require(type(value) is int and 0 <= value <= maximum, 'bounded exact integer required')


def identity(value, *, ordinary=True):
    require(type(value) is dict and set(value) == IDENTITY, 'seven identity fields required')
    require(all(type(v) is int and v >= 0 for v in value.values()), 'nonnegative integer identity required')
    require(value['ino'] > 0 and value['nlink'] > 0, 'positive inode and link count required')
    require((stat.S_ISREG if ordinary else stat.S_ISDIR)(value['mode']), 'ordinary identity kind required')


def file_row(row, *, proof_copy=False):
    require(type(row) is dict and set(row) == {'sha256', 'size', 'identity'}, 'exact file row required')
    digest(row['sha256']); integer(row['size'], 2**30); identity(row['identity'])
    require(row['identity']['size'] == row['size'], 'file identity size differs')
    if proof_copy:
        require(row['size'] <= MAXIMUM_FILE_BYTES and row['identity']['nlink'] == 1
                and row['identity']['mode'] & 0o111 == 0, 'single-link non-executable proof copy required')


def table(value):
    require(type(value) is dict and len(value) <= MAXIMUM_FILES, 'bounded file table required')
    for name, row in value.items():
        path(name); file_row(row)


def reference(value):
    require(type(value) is dict and set(value) == {'path', 'sha256'}, 'exact raw file reference required')
    path(value['path']); digest(value['sha256'])


def blob_row(row, current, roots):
    require(type(row) is dict and set(row) == {'path', 'identity', 'blob', 'evidence_root'},
            'exact qualified physical blob row required')
    p = path(row['path']); root = path(row['evidence_root'])
    require(str(root) in roots and p.parent == root, 'blob root not in qualified catalog')
    identity(row['identity']); require(row['identity']['nlink'] == 1, 'ordinary single-link gzip required')
    b = row['blob']
    require(type(b) is dict and set(b) == {'filename', 'logical_sha256', 'logical_bytes', 'sha256', 'compressed_bytes'},
            'exact v2 gzip descriptor required')
    digest(b['logical_sha256']); digest(b['sha256'])
    integer(b['logical_bytes'], MAXIMUM_FILE_BYTES); integer(b['compressed_bytes'], MAXIMUM_FILE_BYTES)
    require(b['compressed_bytes'] > 0 and b['filename'] == b['logical_sha256'] + '.gz'
            and p.name == b['filename'], 'gzip name or size differs')
    expected = dict(sha256=b['sha256'], size=b['compressed_bytes'], identity=row['identity'])
    file_row(expected)
    require(str(p) in current and same(current[str(p)], expected), 'qualified gzip is not a current physical input')


def build(*, retention, historical_files, current_files, qualified_catalog,
          approved_copies, required_live, copy_root, owner, validate_owner, validate_catalog):
    """Validate an explicit copy subset against closed metadata and live witnesses.

    Both callbacks must return exactly True after full role-specific readback.
    They receive independent copies. The returned structure has no file/identity
    resolver and never represents the historical path as currently present.
    """
    retention, old, current, catalog, approved, live, owner = map(clone,
        [retention, historical_files, current_files, qualified_catalog, approved_copies, required_live, owner])
    table(old); table(current)
    require(type(owner) is dict and set(owner) == {'source', 'evidence', 'receipt', 'audit', 'retention'},
            'explicit completed retention owner required')
    path(owner['source']); evidence = path(owner['evidence'])
    for key in ['receipt', 'audit', 'retention']:
        reference(owner[key])
    require(path(owner['receipt']['path']).parent == evidence
            and path(owner['retention']['path']).parent == evidence, 'owner proof is outside evidence root')
    root = path(copy_root)
    require(root.parent == evidence, 'one exact direct retained-copy root required')
    require(type(approved) is list and all(type(n) is str for n in approved) and 0 < len(approved) <= MAXIMUM_COPIES
            and approved == sorted(set(approved)), 'explicit sorted unique copy selection required')
    require(type(live) is list and all(type(n) is str for n in live) and len(live) <= MAXIMUM_FILES and live == sorted(set(live)),
            'complete sorted unique required-live paths required')
    for name in approved + live:
        path(name)
    chosen = set(approved)
    require(chosen.isdisjoint(live) and chosen.isdisjoint(current), 'historical copy must not be a live input')
    require(set(live) <= set(current), 'required live input disappeared')
    require(chosen <= set(old), 'historical copy missing from original table')
    require(all(name in current and same(row, current[name]) for name, row in old.items() if name not in chosen),
            'unselected original current input changed or disappeared')
    require(validate_owner(clone(owner), clone(retention)) is True, 'completed retention owner not authenticated')
    require(validate_catalog(clone(catalog)) is True, 'completed physical catalog not authenticated')
    require(type(retention) is dict and retention.get('status') == 'retained'
            and type(retention.get('files')) is list and len(retention['files']) <= 1024,
            'complete retained-inputs manifest required')
    integer(retention.get('logical_bytes'), MAXIMUM_COPY_BYTES)
    entries = {}; total = 0
    for row in retention['files']:
        require(type(row) is dict and set(row) == {'source', 'retained', 'sha256', 'bytes'}, 'exact retention row required')
        source = path(row['source']); copy = path(row['retained']); digest(row['sha256']); integer(row['bytes'], MAXIMUM_FILE_BYTES)
        require(copy.parent == root and not source.is_relative_to(root) and str(copy) not in entries,
                'retention path, source or duplicate differs')
        entries[str(copy)] = row; total += row['bytes']
    require(total == retention['logical_bytes'] and chosen <= set(entries), 'complete retention bytes/selection differs')
    require(type(catalog) is dict and catalog.get('policy') in
            ['completed-proof-snapshot-catalog-v1', 'closed-failed-proof-snapshot-catalog-v2'], 'qualified v2 catalog required')
    records, roots = catalog.get('records'), catalog.get('evidence_roots')
    require(type(records) is list and 0 < len(records) <= MAXIMUM_BLOBS and type(roots) is dict,
            'bounded complete physical catalog required')
    for name, row in roots.items():
        path(name); identity(row, ordinary=False)
    by_digest = {}; seen = set(); inodes = set()
    for row in records:
        blob_row(row, current, roots)
        inode = (row['identity']['dev'], row['identity']['ino'])
        require(row['path'] not in seen and inode not in inodes, 'duplicate physical path or inode')
        seen.add(row['path']); inodes.add(inode)
        by_digest.setdefault(row['blob']['logical_sha256'], row)
    result = {}; witnesses = {}
    for name in approved:
        row = old[name]; file_row(row, proof_copy=True); entry = entries[name]
        require(entry['sha256'] == row['sha256'] and entry['bytes'] == row['size'], 'retained historical bytes differ')
        require(entry['source'] in current and entry['source'] not in chosen, 'original source must remain current')
        source = current[entry['source']]
        require(source['sha256'] == row['sha256'] and source['size'] == row['size'], 'current original source bytes differ')
        require(row['sha256'] in by_digest, 'historical copy lacks a qualified gzip witness')
        witness = by_digest[row['sha256']]
        require(witness['blob']['logical_bytes'] == row['size'] and witness['path'] not in chosen,
                'historical logical size or physical witness differs')
        result[name] = dict(kind='historical-proof-copy', original_record=row, retention_entry=entry,
                            current_source=dict(path=entry['source'], **source), witness=witness)
        witnesses[witness['path']] = witness
    return clone(dict(policy=POLICY, owner=owner, copy_root=str(root), records=result,
        witnesses=dict(sorted(witnesses.items())), historical_files=len(result),
        historical_logical_bytes=sum(r['original_record']['size'] for r in result.values()),
        original_file_table_sha256=hashlib.sha256(encoded(old)).hexdigest(),
        current_physical_files=len(current), new_physical_payload_bytes=0,
        retirement_authorized=False, allocation_credit_bytes=0))


def partition(references, *, retention, historical_files, current_files, qualified_catalog,
              approved_copies, required_live, copy_root, owner, validate_owner, validate_catalog):
    """Reauthenticate a saved representation before returning old-table subsets.

    No caller can obtain a partition from a fabricated standalone proof: every
    call rebuilds with all context and both authentication callbacks. Returned
    current_files contains ONLY the original table's physical portion. Fresh
    current rows supplied to build are not part of that historical partition.
    """
    old, proof = clone(historical_files), clone(references)
    rebuilt = build(retention=retention, historical_files=old, current_files=current_files,
        qualified_catalog=qualified_catalog, approved_copies=approved_copies,
        required_live=required_live, copy_root=copy_root, owner=owner,
        validate_owner=validate_owner, validate_catalog=validate_catalog)
    require(same(proof, rebuilt), 'saved references differ from complete authenticated rebuild')
    records = rebuilt['records']
    physical = {name: row for name, row in old.items() if name not in records}
    historical = {name: row for name, row in old.items() if name in records}
    require(same(dict(sorted({**physical, **historical}.items())), old), 'complete logical union differs')
    return dict(current_files=physical, historical_files=historical)
