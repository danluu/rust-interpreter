"""Split one closed preservation archive without extracting or replacing it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
PLAN = Path(__file__).with_suffix('.plan.json')
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
BLOCK = 1024**2
START = time.monotonic()


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def stamp(s):
    return {key: getattr(s, 'st_' + key) for key in FIELDS}


def ordinary(path):
    require(path.is_absolute() and path.resolve(strict=True) == path,
            'indirect path: ' + str(path))
    value = stamp(path.lstat())
    require(stat.S_ISREG(value['mode']) and value['nlink'] == 1,
            'not an ordinary single-link file: ' + str(path))
    return value


def read(path, limit):
    before = ordinary(path)
    require(before['size'] <= limit, 'input size bound')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        require(stamp(os.fstat(stream.fileno())) == before, 'opened input changed')
        data = stream.read(limit + 1)
        require(len(data) == before['size'] and stamp(os.fstat(stream.fileno())) == before,
                'input changed while reading')
    require(ordinary(path) == before, 'input changed after reading')
    return data, dict(path=str(path), identity=before, bytes=len(data),
                      sha256=hashlib.sha256(data).hexdigest())


def write(path, data):
    require(len(data) <= 64 * BLOCK, 'output file bound')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def main(expected):
    raw, plan_ref = read(PLAN, 2 * BLOCK)
    require(plan_ref['sha256'] == expected, 'plan hash differs')
    plan = json.loads(raw)
    output = Path(plan['output'])
    require(output == ROOT/'results/runtime-exporter07-closed-cache-executable-preservation-chunks-01',
            'output route differs')
    require(not output.exists() and not output.is_symlink(), 'output already exists')
    require(plan['chunk_bytes'] == 64 * BLOCK and plan['extra_allocation_cap_bytes'] == 256 * BLOCK
            and plan['minimum_free_bytes'] == 16 * 1024**3
            and plan['chunk_sizes'] == [67108864, 54100644], 'resource policy differs')
    inputs = {}
    for name, row in plan['metadata'].items():
        data, actual = read(Path(row['path']), 32 * BLOCK)
        require(actual == row, 'metadata differs: ' + name)
        inputs[name] = data
    own, own_ref = read(Path(__file__), BLOCK)
    require(own_ref == plan['source'], 'packager source differs')
    manifest = json.loads(inputs['original-manifest.json'])
    parent = json.loads(inputs['retirement-parent.json'])
    receipt = json.loads(inputs['retirement-receipt.json'])
    review = json.loads(inputs['retirement-readback.json'])
    require(parent['status'] == 'finished' and parent['returncode'] == 0
            and parent['child_may_be_live'] is False and parent['retirement_verified'] is True,
            'retirement parent did not close passing')
    require(parent['receipt']['sha256'] == plan['metadata']['retirement-receipt.json']['sha256']
            and receipt['status'] == 'passed' and receipt['removed_files'] == 274
            and receipt['canonical_parent_lock_closed_at'] <= parent['finished_at']
            and receipt['pid'] == parent['child_pid'] and receipt['parent_pid'] == parent['parent_pid'],
            'retirement closure association differs')
    require(review['status'] == 'verified' and review['removed_files'] == 274
            and review['parent']['sha256'] == plan['metadata']['retirement-parent.json']['sha256']
            and review['receipt']['sha256'] == plan['metadata']['retirement-receipt.json']['sha256'],
            'independent retirement readback differs')
    archive = plan['archive']
    require(archive == manifest['archive'] and manifest['selected_files'] == 274
            and manifest['full_gzip_eof_crc'] is True and manifest['full_member_sha_and_eof'] is True,
            'original preservation association differs')
    source = Path(archive['path'])
    require(ordinary(source) == archive['identity'] and archive['bytes'] == 121209508,
            'archive stamp or size differs')
    created = []

    def guard():
        require(time.monotonic() - START < 180, 'packaging wall bound')
        require(shutil.disk_usage(ROOT).free > plan['minimum_free_bytes'], 'free space below 16 GiB')
        allocated = sum(p.lstat().st_blocks * 512 for p in created)
        allocated += sum(p.lstat().st_blocks * 512 for p in (output, output/'provenance') if p.exists())
        require(allocated + 2 * BLOCK <= plan['extra_allocation_cap_bytes'], 'extra allocation bound')

    guard()
    output.mkdir(mode=0o700)
    record = dict(status='started', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
                  source=own_ref, plan=plan_ref, compiler_calls=0, cache_walks=0,
                  extractions=0, deletions=0, original_retained=True, os_closure_observed=False)
    try:
        provenance = output/'provenance'
        provenance.mkdir(mode=0o700)
        for name, data in dict(inputs, **{'package.py': own, 'plan.json': raw}).items():
            path = provenance/name
            created.append(path)
            write(path, data)
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
        chunks = []
        total = 0
        complete = hashlib.sha256()
        with os.fdopen(fd, 'rb') as stream:
            require(stamp(os.fstat(stream.fileno())) == archive['identity'], 'archive changed before split')
            for index, size in enumerate(plan['chunk_sizes']):
                path = output/('evidence.tar.gz.part-' + str(index).zfill(3))
                fd_out = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                created.append(path)
                digest = hashlib.sha256()
                count = 0
                with os.fdopen(fd_out, 'wb') as destination:
                    while count < size:
                        guard()
                        block = stream.read(min(BLOCK, size - count))
                        require(bool(block), 'archive early EOF')
                        destination.write(block)
                        digest.update(block)
                        complete.update(block)
                        count += len(block)
                    destination.flush()
                    os.fsync(destination.fileno())
                chunks.append(dict(name=path.name, offset=total, bytes=count,
                                   sha256=digest.hexdigest(), identity=ordinary(path)))
                total += count
            require(stream.read(1) == b'' and stamp(os.fstat(stream.fileno())) == archive['identity'],
                    'archive EOF or stamp differs')
        require(total == archive['bytes'] and complete.hexdigest() == archive['sha256'],
                'archive complete hash differs')
        reconstructed = hashlib.sha256()
        for row in chunks:
            path = output/row['name']
            before = ordinary(path)
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as stream:
                count = 0
                digest = hashlib.sha256()
                while block := stream.read(BLOCK):
                    guard()
                    digest.update(block)
                    reconstructed.update(block)
                    count += len(block)
                require(stamp(os.fstat(stream.fileno())) == before, 'chunk changed during readback')
            require(count == row['bytes'] and digest.hexdigest() == row['sha256']
                    and ordinary(path) == before == row['identity'], 'chunk readback differs')
        require(reconstructed.hexdigest() == archive['sha256']
                and ordinary(source) == archive['identity'], 'reconstruction or original changed')
        for name, row in plan['metadata'].items():
            require(read(Path(row['path']), 32 * BLOCK)[1] == row, 'metadata changed after split')
            require(read(provenance/name, 32 * BLOCK)[0] == inputs[name], 'metadata copy differs')
        require(read(Path(__file__), BLOCK)[1] == own_ref and read(PLAN, 2 * BLOCK)[1] == plan_ref,
                'source or plan changed')
        result = dict(status='verified-lossless-chunks', original=archive, chunks=chunks,
                      ordered_count=len(chunks), reconstructed_bytes=total,
                      reconstructed_sha256=reconstructed.hexdigest(), original_retained_unchanged=True,
                      original_member_count=274, gzip_extraction_performed=False,
                      metadata=plan['metadata'], source=own_ref, plan=plan_ref)
        for name, data in [('manifest.json', encoded(result)), ('README.md',
            ('Two ordered parts reproduce the unchanged 274-file preservation archive.\n\n'
             '```sh\ncat evidence.tar.gz.part-000 evidence.tar.gz.part-001 > evidence.tar.gz\n'
             'shasum -a 256 evidence.tar.gz\n```\n\n'
             'Expected SHA-256: ' + archive['sha256'] + '\n'
             'Expected size: 121209508 bytes. The original archive remains retained.\n'
             'Historical metadata is copied under provenance; retirement passed separately.\n').encode())]:
            path = output/name
            created.append(path)
            write(path, data)
        guard()
        record.update(status='passed', original=archive, reconstructed_sha256=reconstructed.hexdigest(),
                      chunks=chunks, allocated_bytes_observed=sum(p.lstat().st_blocks * 512 for p in created))
    except BaseException as error:
        record.update(status='failed', error=repr(error))
        raise
    finally:
        record['finished_at'] = time.time()
        write(output/'record.json', encoded(record))
    print(json.dumps(dict(path=str(output), status='passed', chunk_count=len(chunks), bytes=total)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan-sha256', required=True)
    main(parser.parse_args().plan_sha256)
