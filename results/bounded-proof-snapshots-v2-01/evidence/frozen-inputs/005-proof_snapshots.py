"""Lossless bounded snapshots with explicit references to retained proof blobs.

The caller owns a frozen input list, fresh destination, admission and physical
evidence budget. It also binds the closed predecessor receipts, manifests and
audits authorizing each reuse row, and proves that all supplied evidence roots
are already counted by its aggregate monitor. This module does not infer that
authorization from an on-disk filename. No processes or provider probes run.

Measurement writes no files. Every logical input is checked, including aliases.
Stored and reused gzip blobs both receive full compressed and logical readback.
Old blobs are never modified, linked, moved or silently omitted from the proof.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import stat

BLOCK = 2**20
FIELDS = ('dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink')
LIMIT_NAMES = {'maximum_files', 'maximum_file_bytes', 'maximum_logical_bytes',
               'maximum_compressed_bytes', 'maximum_manifest_bytes'}
BLOB_FIELDS = {'filename', 'logical_sha256', 'logical_bytes', 'sha256', 'compressed_bytes'}
POLICY = 'bounded-gzip-proof-snapshots-v2'


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()


def identity(info):
    return {key: getattr(info, 'st_'+key) for key in FIELDS}


def normalize(records, limits):
    require(set(limits) == LIMIT_NAMES and all(type(v) is int and v > 0 for v in limits.values()),
            'positive explicit snapshot limits required')
    require(type(records) is list and 0 < len(records) <= limits['maximum_files'],
            'bounded nonempty snapshot inputs required')
    result = {}
    logical = 0
    for row in records:
        require(set(row) == {'path', 'sha256', 'size', 'identity'}, 'exact snapshot input fields required')
        name = row['path']
        require(type(name) is str, 'snapshot input path must be text')
        path = Path(name)
        require(path.is_absolute() and str(path) == name and '..' not in path.parts,
                'canonical absolute snapshot path required')
        require(name not in result and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None,
                'duplicate input or malformed source hash')
        require(type(row['size']) is int and 0 <= row['size'] <= limits['maximum_file_bytes'],
                'logical snapshot file bound exceeded')
        require(set(row['identity']) == set(FIELDS) and all(type(v) is int for v in row['identity'].values())
                and stat.S_ISREG(row['identity']['mode']) and row['identity']['size'] == row['size'],
                'ordinary complete snapshot identity required')
        logical += row['size']
        require(logical <= limits['maximum_logical_bytes'], 'logical snapshot total bound exceeded')
        result[name] = json.loads(json.dumps(row))
    return dict(sorted(result.items()))


def input_blocks(row, guard):
    path = Path(row['path']); expected = row['identity']
    guard()
    require(path.resolve(strict=True) == path and identity(path.lstat()) == expected,
            'snapshot input route or identity changed')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    digest = hashlib.sha256(); size = 0
    try:
        require(identity(os.fstat(fd)) == expected, 'opened snapshot input differs')
        while True:
            guard()
            block = os.read(fd, min(BLOCK, row['size'] - size + 1))
            if not block:
                break
            size += len(block)
            require(size <= row['size'], 'snapshot input grew')
            digest.update(block)
            yield block
        require(size == row['size'] and digest.hexdigest() == row['sha256'], 'snapshot input bytes changed')
        require(identity(os.fstat(fd)) == expected and identity(path.lstat()) == expected,
                'snapshot input changed during read')
    finally:
        os.close(fd)


class Sink:
    def __init__(self, limit, guard, output=None):
        self.limit, self.guard, self.output = limit, guard, output
        self.size = 0
        self.digest = hashlib.sha256()

    def write(self, value):
        self.guard()
        require(self.size + len(value) <= self.limit, 'compressed snapshot bound exceeded before write')
        if self.output is not None:
            require(self.output.write(value) == len(value), 'short compressed snapshot write')
        self.size += len(value); self.digest.update(value)
        return len(value)

    def flush(self):
        if self.output is not None:
            self.output.flush()

    def tell(self):
        return self.size


def compress(row, remaining, guard, output=None):
    sink = Sink(remaining, guard, output)
    with gzip.GzipFile(filename='', mode='wb', fileobj=sink, mtime=0, compresslevel=6) as stream:
        for block in input_blocks(row, guard):
            stream.write(block)
    return dict(filename=row['sha256']+'.gz', logical_sha256=row['sha256'], logical_bytes=row['size'],
                sha256=sink.digest.hexdigest(), compressed_bytes=sink.size)


def ordinary_route(path):
    """Reject symlink ancestors even when their spelling resolves back to itself."""
    require(path.is_absolute() and '..' not in path.parts and str(path) != '/',
            'ordinary absolute proof route required')
    for parent in reversed(path.parents):
        require(stat.S_ISDIR(parent.lstat().st_mode) and not parent.is_symlink(),
                'proof route has a nonordinary ancestor')
    require(path.resolve(strict=True) == path and not path.is_symlink(),
            'proof route differs from canonical path')


def normalize_reuse(reuse, evidence_roots, files, limits):
    reuse = [] if reuse is None else reuse
    evidence_roots = {} if evidence_roots is None else evidence_roots
    require(type(reuse) is list and len(reuse) <= limits['maximum_files'],
            'bounded explicit reuse list required')
    require(type(evidence_roots) is dict and len(evidence_roots) <= 32,
            'bounded explicit accounted evidence roots required')
    roots = {}
    for name, stamp in evidence_roots.items():
        require(type(name) is str and str(Path(name)) == name,
                'canonical evidence root spelling required')
        path = Path(name); ordinary_route(path)
        require(type(stamp) is dict and set(stamp) == set(FIELDS) and all(type(v) is int for v in stamp.values())
                and stat.S_ISDIR(stamp['mode']) and identity(path.lstat()) == stamp,
                'frozen ordinary evidence root required')
        require(not any(path == other or path in other.parents or other in path.parents
                        for other in map(Path, roots)), 'overlapping evidence roots')
        roots[name] = dict(stamp)
    wanted = {}
    for row in files.values():
        key = row['sha256']
        require(key not in wanted or wanted[key] == row['size'], 'inconsistent equal-hash source size')
        wanted[key] = row['size']
    result = {}; paths = set(); inodes = set(); used_roots = set()
    for row in reuse:
        require(type(row) is dict and set(row) == {'path', 'identity', 'blob', 'evidence_root'},
                'exact frozen reuse fields required')
        blob = row['blob']; stamp = row['identity']; name = row['path']; root = row['evidence_root']
        require(type(blob) is dict and set(blob) == BLOB_FIELDS, 'exact reused blob fields required')
        key = blob['logical_sha256']
        require(type(key) is str and re.fullmatch('[0-9a-f]{64}', key)
                and key in wanted and type(blob['logical_bytes']) is int
                and blob['logical_bytes'] == wanted[key]
                and blob['filename'] == key+'.gz', 'reused blob is not an exact selected logical payload')
        require(type(blob['sha256']) is str and re.fullmatch('[0-9a-f]{64}', blob['sha256'])
                and type(blob['compressed_bytes']) is int
                and 0 < blob['compressed_bytes'] <= limits['maximum_compressed_bytes'],
                'bounded exact reused compressed payload required')
        require(type(name) is str and str(Path(name)) == name and root in roots,
                'reused blob must name an explicit accounted root')
        path = Path(name); ordinary_route(path)
        require(Path(root) in path.parents and path.name == blob['filename'],
                'reused blob escapes its exact evidence root or filename')
        require(type(stamp) is dict and set(stamp) == set(FIELDS) and all(type(v) is int for v in stamp.values())
                and stat.S_ISREG(stamp['mode']) and stamp['nlink'] == 1
                and stamp['size'] == blob['compressed_bytes']
                and identity(path.lstat()) == stamp, 'exact frozen single-link reused blob required')
        inode = (stamp['dev'], stamp['ino'])
        require(key not in result and name not in paths and inode not in inodes,
                'ambiguous or duplicate physical reuse credit')
        result[key] = json.loads(json.dumps(row))
        paths.add(name); inodes.add(inode); used_roots.add(root)
    require(used_roots == set(roots), 'unused evidence root is outside exact reuse selection')
    return dict(sorted(result.items())), dict(sorted(roots.items()))


def verify_reference(row, roots, capacity_guard):
    path = Path(row['path']); root = Path(row['evidence_root'])
    capacity_guard(); ordinary_route(root); ordinary_route(path)
    require(identity(root.lstat()) == roots[str(root)] and identity(path.lstat()) == row['identity'],
            'frozen reused root or blob changed before readback')
    verify_blob(path, row['blob'], capacity_guard)
    ordinary_route(root); ordinary_route(path)
    require(identity(root.lstat()) == roots[str(root)] and identity(path.lstat()) == row['identity'],
            'frozen reused root or blob changed during readback')


def measure(records, limits, capacity_guard, *, reuse=None, evidence_roots=None):
    files = normalize(records, limits)
    references, roots = normalize_reuse(reuse, evidence_roots, files, limits)
    blobs = {}; storage = {}; total = 0; new = 0
    for row in files.values():
        key = row['sha256']
        if key in blobs:
            require(blobs[key]['logical_bytes'] == row['size'], 'inconsistent equal-hash source size')
            for _ in input_blocks(row, capacity_guard):
                pass
        elif key in references:
            reference = references[key]
            require(total + reference['blob']['compressed_bytes'] <= limits['maximum_compressed_bytes'],
                    'total compressed snapshot bound exceeded by reused payload')
            for _ in input_blocks(row, capacity_guard):
                pass
            verify_reference(reference, roots, capacity_guard)
            blobs[key] = reference['blob']; total += reference['blob']['compressed_bytes']
            storage[key] = dict(kind='reused', path=reference['path'])
        else:
            blob = compress(row, limits['maximum_compressed_bytes']-total, capacity_guard)
            blobs[key] = blob; total += blob['compressed_bytes']; new += blob['compressed_bytes']
            storage[key] = dict(kind='stored')
    for reference in references.values():
        verify_reference(reference, roots, capacity_guard)
    result = dict(policy=POLICY, limits=dict(limits), files=files,
                  blobs=dict(sorted(blobs.items())), logical_bytes=sum(row['size'] for row in files.values()),
                  unique_logical_bytes=sum(row['logical_bytes'] for row in blobs.values()),
                  compressed_bytes=total,
                  new_compressed_bytes=new, reused_compressed_bytes=total-new,
                  compressed_allocated_bytes=sum((row['compressed_bytes']+4095)//4096*4096 for row in blobs.values()),
                  new_compressed_allocated_bytes=sum((row['compressed_bytes']+4095)//4096*4096
                      for key, row in blobs.items() if storage[key]['kind'] == 'stored'),
                  storage=dict(sorted(storage.items())), reuse=references, evidence_roots=roots,
                  manifest_reservation_bytes=2*limits['maximum_manifest_bytes'])
    require(len(encoded(result)) <= limits['maximum_manifest_bytes'], 'snapshot projection manifest bound exceeded')
    return result


def verify_blob(path, blob, capacity_guard):
    path = Path(path); before = identity(path.lstat())
    require(path.resolve(strict=True) == path and stat.S_ISREG(before['mode']) and before['nlink'] == 1
            and before['size'] == blob['compressed_bytes'], 'ordinary exact compressed snapshot required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as raw:
        require(identity(os.fstat(raw.fileno())) == before, 'opened compressed snapshot differs')
        compressed = hashlib.sha256(); compressed_size = 0
        while True:
            capacity_guard()
            block = raw.read(min(BLOCK, blob['compressed_bytes']-compressed_size+1))
            if not block:
                break
            compressed_size += len(block)
            require(compressed_size <= blob['compressed_bytes'], 'compressed snapshot grew during readback')
            compressed.update(block)
        require(compressed_size == blob['compressed_bytes'] and compressed.hexdigest() == blob['sha256'],
                'compressed snapshot hash differs')
        raw.seek(0); logical = hashlib.sha256(); size = 0
        with gzip.GzipFile(fileobj=raw, mode='rb') as stream:
            while True:
                capacity_guard()
                block = stream.read(min(BLOCK, blob['logical_bytes']-size+1))
                if not block:
                    break  # Full gzip EOF verifies its trailer, CRC and any concatenated member.
                size += len(block)
                require(size <= blob['logical_bytes'], 'expanded snapshot bound exceeded')
                logical.update(block)
        require(size == blob['logical_bytes'] and logical.hexdigest() == blob['logical_sha256'],
                'snapshot full logical readback differs')
        require(identity(os.fstat(raw.fileno())) == before and identity(path.lstat()) == before,
                'compressed snapshot changed during readback')


def write_verified(records, destination, projection, limits, capacity_guard, *, reuse=None, evidence_roots=None):
    # Recompute all source bytes and the exact projection before destination creation.
    require(measure(records, limits, capacity_guard, reuse=reuse, evidence_roots=evidence_roots) == projection,
            'reviewed snapshot projection differs')
    destination = Path(destination)
    require(destination.is_absolute() and destination.parent.resolve(strict=True) == destination.parent
            and not destination.exists() and not destination.is_symlink(), 'fresh ordinary snapshot destination required')
    require(not any(Path(root) == destination or Path(root) in destination.parents
                    or destination in Path(root).parents for root in projection['evidence_roots']),
            'new snapshots cannot alter a frozen reused evidence root')
    capacity_guard(); destination.mkdir()
    written = set(); total = 0; new = 0; physical = {}
    for row in projection['files'].values():
        key = row['sha256']
        if key in written:
            for _ in input_blocks(row, capacity_guard):
                pass
            continue
        expected = projection['blobs'][key]
        if projection['storage'][key]['kind'] == 'reused':
            for _ in input_blocks(row, capacity_guard):
                pass
            verify_reference(projection['reuse'][key], projection['evidence_roots'], capacity_guard)
            physical[key] = projection['storage'][key]
            total += expected['compressed_bytes']; written.add(key)
            continue
        path = destination/expected['filename']
        with path.open('xb') as output:
            observed = compress(row, limits['maximum_compressed_bytes']-total, capacity_guard, output)
            output.flush(); os.fsync(output.fileno())
        require(observed == expected, 'written snapshot differs from reviewed projection')
        total += observed['compressed_bytes']; new += observed['compressed_bytes']; written.add(key)
        physical[key] = dict(kind='stored', path=str(path))
        verify_blob(path, expected, capacity_guard)
    require(set(os.listdir(destination)) == {row['filename'] for key, row in projection['blobs'].items()
                                            if projection['storage'][key]['kind'] == 'stored'},
            'snapshot directory membership differs')
    for row in projection['reuse'].values():
        verify_reference(row, projection['evidence_roots'], capacity_guard)
    require(total == projection['compressed_bytes'] and new == projection['new_compressed_bytes'],
            'stored/reused compressed accounting differs')
    result = dict(policy=projection['policy'], projection_sha256=hashlib.sha256(encoded(projection)).hexdigest(),
                  files={name:dict(path=physical[row['sha256']]['path'],
                                  sha256=row['sha256'], size=row['size'], encoding='gzip')
                         for name,row in projection['files'].items()},
                  blobs=projection['blobs'], storage=dict(sorted(physical.items())),
                  reuse=projection['reuse'], evidence_roots=projection['evidence_roots'],
                  compressed_bytes=total, new_compressed_bytes=new, reused_compressed_bytes=total-new,
                  full_logical_readback=True, full_gzip_eof=True)
    require(len(encoded(result)) <= limits['maximum_manifest_bytes'], 'snapshot result manifest bound exceeded')
    capacity_guard()
    return result
