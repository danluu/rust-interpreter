"""Lossless bounded proof snapshots; no processes, admission or provider probes.

The caller owns a frozen input list, fresh destination, admission and physical
evidence budget. Measurement writes no files. Every logical input is checked,
including duplicate payloads, and each written gzip is fully read back.
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


def measure(records, limits, capacity_guard):
    files = normalize(records, limits)
    blobs = {}; total = 0
    for row in files.values():
        key = row['sha256']
        if key in blobs:
            require(blobs[key]['logical_bytes'] == row['size'], 'inconsistent equal-hash source size')
            for _ in input_blocks(row, capacity_guard):
                pass
        else:
            blob = compress(row, limits['maximum_compressed_bytes']-total, capacity_guard)
            blobs[key] = blob; total += blob['compressed_bytes']
    result = dict(policy='bounded-gzip-proof-snapshots-v1', limits=dict(limits), files=files,
                  blobs=dict(sorted(blobs.items())), logical_bytes=sum(row['size'] for row in files.values()),
                  unique_logical_bytes=sum(row['logical_bytes'] for row in blobs.values()),
                  compressed_bytes=total,
                  compressed_allocated_bytes=sum((row['compressed_bytes']+4095)//4096*4096 for row in blobs.values()),
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


def write_verified(records, destination, projection, limits, capacity_guard):
    # Recompute all source bytes and the exact projection before destination creation.
    require(measure(records, limits, capacity_guard) == projection, 'reviewed snapshot projection differs')
    destination = Path(destination)
    require(destination.is_absolute() and destination.parent.resolve(strict=True) == destination.parent
            and not destination.exists() and not destination.is_symlink(), 'fresh ordinary snapshot destination required')
    capacity_guard(); destination.mkdir()
    written = set(); total = 0
    for row in projection['files'].values():
        key = row['sha256']
        if key in written:
            for _ in input_blocks(row, capacity_guard):
                pass
            continue
        expected = projection['blobs'][key]; path = destination/expected['filename']
        with path.open('xb') as output:
            observed = compress(row, limits['maximum_compressed_bytes']-total, capacity_guard, output)
            output.flush(); os.fsync(output.fileno())
        require(observed == expected, 'written snapshot differs from reviewed projection')
        total += observed['compressed_bytes']; written.add(key)
        verify_blob(path, expected, capacity_guard)
    require(set(os.listdir(destination)) == {row['filename'] for row in projection['blobs'].values()},
            'snapshot directory membership differs')
    result = dict(policy=projection['policy'], projection_sha256=hashlib.sha256(encoded(projection)).hexdigest(),
                  files={name:dict(path=str(destination/projection['blobs'][row['sha256']]['filename']),
                                  sha256=row['sha256'], size=row['size'], encoding='gzip')
                         for name,row in projection['files'].items()},
                  blobs=projection['blobs'], compressed_bytes=total,
                  full_logical_readback=True, full_gzip_eof=True)
    require(len(encoded(result)) <= limits['maximum_manifest_bytes'], 'snapshot result manifest bound exceeded')
    capacity_guard()
    return result
