"""Independent finite chunk/closure readback and exact closed-evidence copies."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import stat
import time

Q = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
D = Q/'results/runtime-exporter07-closed-cache-executable-preservation-chunks-01'
OLD = Q/'results/runtime-exporter07-closed-cache-executable-preservation-01'
EXEC = Q/'.work/runtime-exporter07-preservation-chunks-execution-01'
WORK = X/'.work/runtime-exporter07-cache-executable-retirement-01'
SOURCE = Q/'experiments/runtime-exporter07-cache-executable-retirement-01'
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
BLOCK = 1024**2


def identity(path):
    return {k: getattr(path.lstat(), 'st_' + k) for k in FIELDS}


def ref(path, combined=None):
    before = identity(path)
    assert path.resolve(strict=True) == path and stat.S_ISREG(before['mode']) and before['nlink'] == 1
    assert before['size'] <= 128 * BLOCK
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    digest = hashlib.sha256()
    count = 0
    with os.fdopen(fd, 'rb') as stream:
        assert {k: getattr(os.fstat(stream.fileno()), 'st_' + k) for k in FIELDS} == before
        while block := stream.read(BLOCK):
            digest.update(block)
            if combined is not None:
                combined.update(block)
            count += len(block)
        assert {k: getattr(os.fstat(stream.fileno()), 'st_' + k) for k in FIELDS} == before
    assert identity(path) == before and count == before['size']
    return dict(path=str(path), identity=before, bytes=count, sha256=digest.hexdigest())


def load(path):
    row = ref(path)
    assert row['bytes'] <= 4 * BLOCK
    return json.loads(path.read_bytes()), row


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def dump(path, value):
    write(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


def main():
    assert shutil.disk_usage(Q).free > 16 * 1024**3
    manifest, manifest_ref = load(D/'manifest.json')
    assert manifest_ref['sha256'] == '89ac263c478d1de4e3ad23d83ce76479c13a96c916bacc107e2912c995e6b28b'
    parent, parent_ref = load(EXEC/'record.json')
    child, child_ref = load(D/'record.json')
    assert parent_ref['sha256'] == '6ec46cd53efce1e09dd2c2d7250733fbcc7bfa05575a45ee8ed54bd8dcbe6553'
    assert parent['status'] == 'finished' and parent['returncode'] == 0 and parent['child_may_be_live'] is False
    assert parent['child_pid'] == child['pid'] == 68505 and parent['parent_pid'] == child['parent_pid'] == 67787
    assert parent['started_at'] <= child['started_at'] <= child['finished_at'] <= parent['finished_at']
    assert child['status'] == 'passed' and child['os_closure_observed'] is False
    assert parent['argv'][-1] == manifest['plan']['sha256'] and parent['cwd'] == str(Q)
    assert (EXEC/'stderr').read_bytes() == b''
    stdout = json.loads((EXEC/'stdout').read_bytes())
    assert stdout == dict(path=str(D), status='passed', chunk_count=2, bytes=121209508)
    combined = hashlib.sha256()
    chunks = []
    offset = 0
    for row in manifest['chunks']:
        current = ref(D/row['name'], combined)
        assert current['sha256'] == row['sha256'] and current['bytes'] == row['bytes'] <= 64 * BLOCK
        assert current['identity'] == row['identity'] and row['offset'] == offset
        offset += current['bytes']
        chunks.append(current)
    assert len(chunks) == 2 and offset == 121209508 and combined.hexdigest() == manifest['original']['sha256']
    original = ref(Path(manifest['original']['path']))
    assert original == manifest['original']
    for name, expected in manifest['metadata'].items():
        assert ref(Path(expected['path'])) == expected
        copied = ref(D/'provenance'/name)
        assert (copied['bytes'], copied['sha256']) == (expected['bytes'], expected['sha256'])
    for name, expected in [('package.py', manifest['source']), ('plan.json', manifest['plan'])]:
        assert ref(Path(expected['path'])) == expected
        copied = ref(D/'provenance'/name)
        assert (copied['bytes'], copied['sha256']) == (expected['bytes'], expected['sha256'])
    initial = {str(p.relative_to(D)) for p in D.rglob('*') if p.is_file()}
    expected_initial = {'manifest.json', 'record.json', 'README.md', *(p.name for p in map(Path, [r['path'] for r in chunks])),
                        *('provenance/' + n for n in manifest['metadata']), 'provenance/package.py', 'provenance/plan.json'}
    assert initial == expected_initial and len(initial) == 13
    plan, _ = load(SOURCE/'plan.json')
    review, review_ref = load(X/'.work/runtime-exporter07-cache-executable-retirement-independent-readback-01.json')
    assert review_ref['sha256'] == '857d8ba6a4c1a041c0f77764a7a8cc6f376f28f877c378012228313fc6a949e1'
    checked = {row['path']: row for row in review['checked_evidence']}
    pairs = []
    for folder, relative in [(EXEC, 'package-execution'),
            (Q/'.work/runtime-exporter07-cache-executable-retirement-execution-01', 'retirement-execution'),
            (SOURCE, 'retirement-source'), (WORK, 'retirement-output'),
            (X/'.work/runtime-exporter07-cache-executable-preservation-execution-01', 'preservation-execution')]:
        files = sorted(p for p in folder.rglob('*') if p.is_file())
        assert len(files) <= 64 and sum(p.lstat().st_size for p in files) < 8 * BLOCK
        pairs += [(p, D/'provenance'/relative/p.relative_to(folder)) for p in files]
    for field in ('remover', 'owned_stage'):
        row = plan[field]
        p = Path(row['path'])
        assert ref(p)['sha256'] == row['file']['sha256']
        pairs.append((p, D/'provenance'/'retirement-source'/(field + '.py')))
    for name in ('selection.json', 'started.json'):
        pairs.append((OLD/name, D/'provenance'/'preservation-metadata'/name))
    old_record, _ = load(OLD/'record.json')
    pairs.append((Path(old_record['source']['path']), D/'provenance'/'preservation-source.py'))
    retirement_parent, _ = load(Q/'.work/runtime-exporter07-cache-executable-retirement-execution-01/record.json')
    pairs.append((Path(retirement_parent['source']['path']), D/'provenance'/'retirement-parent.py'))
    pairs.append((Path(__file__), D/'provenance'/'independent-reader.py'))
    copies = []
    for source, destination in pairs:
        row = ref(source)
        assert row['bytes'] < 8 * BLOCK
        if str(source) in checked:
            assert row == checked[str(source)]
        elif str(source) in plan['frozen_files']:
            expected = plan['frozen_files'][str(source)]
            assert row['identity'] == expected['identity'] and row['sha256'] == expected['sha256']
        data = source.read_bytes()
        assert hashlib.sha256(data).hexdigest() == row['sha256'] and identity(source) == row['identity']
        write(destination, data)
        saved = ref(destination)
        assert saved['bytes'] == row['bytes'] and saved['sha256'] == row['sha256']
        copies.append(dict(source=row, destination=str(destination.relative_to(D))))
    payloads = [ref(p) for p in sorted(D.rglob('*')) if p.is_file()]
    assert sum(p['bytes'] for p in payloads) < 256 * BLOCK
    publication = dict(status='complete-finite-publication', original_manifest=manifest_ref,
        original_archive_retained=original, copied_sources=copies,
        payloads=[dict(relative=str(Path(p['path']).relative_to(D)), **p) for p in payloads],
        payload_count=len(payloads), payload_bytes=sum(p['bytes'] for p in payloads),
        excluded=['Original cache trees and provider payloads', 'Reconstructed gzip file'],
        original_preservation_member_claim='Original exact274 metadata retained; independent current pass checks lossless compressed bytes only, without extraction.')
    dump(D/'publication-manifest.json', publication)
    exact = {row['relative'] for row in publication['payloads']} | {'publication-manifest.json'}
    assert {str(p.relative_to(D)) for p in D.rglob('*') if p.is_file()} == exact
    for row in payloads:
        assert ref(Path(row['path'])) == row
    allocated = sum(p.lstat().st_blocks * 512 for p in D.rglob('*')) + D.lstat().st_blocks * 512
    assert allocated + BLOCK < 256 * BLOCK and ref(Path(original['path'])) == original
    report = dict(status='verified', checked_at=time.time(), parent=parent_ref, child=child_ref,
        normal_wait_closed=True, parent_pid=67787, child_pid=68505,
        chunks=chunks, reconstructed_bytes=offset, reconstructed_sha256=combined.hexdigest(),
        original_retained_unchanged=original, publication_manifest=ref(D/'publication-manifest.json'),
        exact_payload_members=sorted(exact), payload_files_before_this_readback=len(exact),
        final_files_including_this_readback=len(exact)+1,
        allocated_bytes_before_readback=allocated, copied_proof_files=len(copies),
        no_cache_walks=True, no_extraction=True, no_benchmark_or_provider_calls=True,
        reader=ref(Path(__file__)))
    dump(D/'independent-readback.json', report)
    files = sorted(p for p in D.rglob('*') if p.is_file())
    assert len(files) == report['final_files_including_this_readback']
    stage = A/'.work/runtime-exporter07-preservation-chunks-stage-paths-01.txt'
    write(stage, ''.join(str(p.relative_to(Q))+'\n' for p in files).encode())
    print(json.dumps(dict(status='verified', report=ref(D/'independent-readback.json'),
                         manifest=ref(D/'publication-manifest.json'), stage_list=ref(stage),
                         files=len(files), logical_bytes=sum(p.stat().st_size for p in files))))


if __name__ == '__main__':
    main()
