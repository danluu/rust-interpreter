#!/usr/bin/env python3
"""Qualify independent CoW artifact replacement on owned synthetic files."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import artifact_clones as clones
from reclaim_workflow_objects import identifier, sha
from verify_repeated_workflow import require
from workflow_io import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    run = identifier(args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw, out = [ROOT / parent / run for parent in ['.work/runs', 'results']]
        require(not raw.exists() and not out.exists(), 'qualification already exists')
        raw.mkdir()
        sources = {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), ROOT / 'scripts/artifact_clones.py']}
        data = bytes(range(256)) * 4096

        def pair(label):
            folder = raw / label
            folder.mkdir()
            a, b = folder / 'source.rbc', folder / 'destination.rbc'
            for p, mode in [(a, 0o600), (b, 0o640)]:
                p.write_bytes(data)
                p.chmod(mode)
                os.utime(p, ns=(1600000000000000000, 1600000000123456789))
            return a, b, clones.inspect(a), clones.inspect(b)

        a, b, ai, bi = pair('independence')
        result = clones.replace_duplicate(a, b, ai, bi)
        require(result['inode'] not in [ai['inode'], bi['inode']] and
                all(result[k] == bi[k] for k in ['bytes', 'uid', 'gid', 'mode', 'mtime_ns', 'sha256']),
                'published clone differs')
        with b.open('r+b') as stream:
            stream.write(b'changed destination')
        require(a.read_bytes() == data, 'destination write changed source')
        changed_b = b.read_bytes()
        with a.open('r+b') as stream:
            stream.seek(4096)
            stream.write(b'changed source')
        require(b.read_bytes() == changed_b, 'source write changed destination')
        rejected = []

        def reject(label, call):
            try:
                call()
            except (RuntimeError, OSError):
                rejected.append(label)
            else:
                raise RuntimeError('invalid clone operation accepted: ' + label)

        a, b, ai, bi = pair('input-validation')
        reject('wrong-hash', lambda: clones.inspect(a, '0' * 64))
        reject('same-path', lambda: clones.replace_duplicate(a, a, ai, ai))
        reject('different-digest', lambda: clones.replace_duplicate(a, b, ai, dict(bi, sha256='0' * 64)))
        reject('different-device', lambda: clones.replace_duplicate(a, b, ai, dict(bi, device=-1)))
        reject('reviewed-inode-changed', lambda: clones.replace_duplicate(a, b, ai, dict(bi, inode=-1)))
        for label, create in [
                ('symlink', lambda p: p.symlink_to(a)),
                ('fifo', os.mkfifo), ('directory', lambda p: p.mkdir()),
                ('hardlink', lambda p: os.link(a, p)),
                ('empty', lambda p: p.write_bytes(b''))]:
            p = raw / label
            create(p)
            reject(label, lambda p=p: clones.inspect(p))
            if label == 'hardlink':
                p.unlink()
        for label, mutate in [
                ('setuid', lambda p: p.chmod(0o4600)),
                ('xattr', lambda p: subprocess.run(['/usr/bin/xattr', '-w', 'test.rust-interp', 'owned', str(p)], check=True)),
                ('acl', lambda p: subprocess.run(['/bin/chmod', '+a', 'everyone deny write', str(p)], check=True))]:
            a, b, ai, bi = pair(label)
            mutate(b)
            reject(label, lambda: clones.inspect(b))
        a, b, ai, bi = pair('growth')
        with b.open('r+b') as stream:
            stream.truncate(clones.MAX_BYTES + 1)
        reject('oversize', lambda: clones.inspect(b))
        a, b, ai, bi = pair('stale-source')
        a.write_bytes(b'changed source')
        reject('source-changed', lambda: clones.replace_duplicate(a, b, ai, bi))
        require(b.read_bytes() == data, 'stale source changed destination')
        a, b, ai, bi = pair('stale-destination')
        b.write_bytes(b'changed destination')
        reject('destination-changed', lambda: clones.replace_duplicate(a, b, ai, bi))
        require(b.read_bytes() == b'changed destination', 'stale destination was replaced')
        for label, target in [('clone-failure', 'clone_fd'), ('publication-failure', 'os.replace')]:
            a, b, ai, bi = pair(label)
            with patch('artifact_clones.' + target, side_effect=OSError('injected failure')):
                reject(label, lambda: clones.replace_duplicate(a, b, ai, bi))
            require(clones.same(a.stat(), ai) and clones.same(b.stat(), bi) and
                    a.read_bytes() == data and b.read_bytes() == data and
                    sorted(p.name for p in b.parent.iterdir()) == ['destination.rbc', 'source.rbc'],
                    'failed clone modified originals or left a temporary')
        require(all(sha(ROOT / p) == digest for p, digest in sources.items()), 'qualification source changed')
        out.mkdir()
        write_json(out / 'summary.json', dict(status='passed', independent_writes_both_directions=True,
            ownership_permissions_mtime_bytes_preserved=True, rejections=rejected, sources_sha256=sources,
            raw=str(raw.relative_to(ROOT)), note='Owned synthetic files only. No production artifacts modified. Inode, ctime and birth time intentionally differ; no ordinary-copy or hardlink fallback.'))
        print(json.dumps(dict(status='passed', rejections=len(rejected))))


if __name__ == '__main__':
    main()
