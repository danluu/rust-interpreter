"""Publish a finite corrective note; original raw evidence stays in its capsule."""
import hashlib
import json
import stat
from pathlib import Path

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
OUT = ROOT / 'results/ruff-options-hash-diagnostic-attribution-01'


def stamp(s):
    return [s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size,
            s.st_mtime_ns, s.st_ctime_ns]


def read(path, digest=None):
    p = Path(path)
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_size <= 2 * 2**20
    b = p.read_bytes()
    assert len(b) == s.st_size and stamp(p.lstat()) == stamp(s)
    r = dict(path=str(p), bytes=len(b), sha256=hashlib.sha256(b).hexdigest(), stamp=stamp(s))
    assert digest is None or r['sha256'] == digest
    return b, r


def write(name, data):
    if not isinstance(data, bytes):
        data = (json.dumps(data, sort_keys=True, indent=2) + '\n').encode()
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as f:
        f.write(data)
    assert p.read_bytes() == data
    return dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


assert not OUT.exists()
attr_path = A / '.work/ruff-options-hash-strict-hir-event-attribution-01.json'
review_path = X / '.work/ruff-options-hash-diagnostic-attribution-independent-review-01.json'
attr_bytes, attr_ref = read(attr_path, 'ac1205993b6857afbcde0f7a23ffae2b2861f97944cf631b1e5f0879b0a4801a')
review_bytes, review_ref = read(review_path, 'd37b456bfee28e2b4a294f7a241c0d28e6fb7dd026418effaeaab04ced9a3fea')
attr, review = json.loads(attr_bytes), json.loads(review_bytes)
sources = [
    ('attribution.json', attr_ref), ('independent-review.json', review_ref),
    ('reviewer.py', review['reviewer_source']),
    ('event-semantics-source-review.json', dict(path=str(O / '.work/hir-event-semantics-independent-source-review-01.json'), sha256='e6a1cae415f3180c4818c77b1590006228aab01132c63d75bf8cdd2596537160')),
    ('original-eligibility-065d.json', attr['original_eligibility_unchanged']),
]
old = json.loads(read(attr['original_eligibility_unchanged']['path'], attr['original_eligibility_unchanged']['sha256'])[0])
sources.append(('sources/original-diagnostic-parser.py', old['parser_source']))
sources += [('sources/body_cache/' + name, row) for name, row in sorted(attr['compiler_sources'].items())]
sources.append(('publisher.py', dict(path=__file__)))
frozen = []
for name, row in sources:
    data, current = read(row['path'], row.get('sha256'))
    frozen.append((name, data, current))
assert len(frozen) == 13 and sum(len(data) for _, data, _ in frozen) < 2 * 2**20
archive_manifest_bytes, archive_manifest_ref = read(attr['archive_manifest']['path'], attr['archive_manifest']['sha256'])
archive_manifest = json.loads(archive_manifest_bytes)
OUT.mkdir()
members = [dict(**write(name, data), source=ref) for name, data, ref in frozen]
references = dict(original_capsule='results/ruff-options-hash-strict-01',
    manifest=archive_manifest_ref,
    archive=dict(path=str(Path(archive_manifest_ref['path']).parent / 'evidence.tar.gz'), **archive_manifest['files']['evidence.tar.gz']),
    original_member_count=840, referenced_member_count=len(review['archive_members_checked']),
    members=review['archive_members_checked'],
    verification_scope='The independent reader hashed the current 379 named raw/argv/receipt files and matched their frozen archive-manifest rows. This correction does not repeat the prior full gzip verification; the old capsule remains an explicit evidence dependency.')
members.append(write('evidence-references.json', references))
note = '''# Corrected diagnostic attribution

The strict run's **13,491 capture messages are not 13,491 newly executed captures**. The original eligibility report is retained unchanged as `original-eligibility-065d.json`; its count is a literal stderr-message total.

| Scope | Executed cold captures | Replayed capture messages | Current Ruff verified hits |
| --- | ---: | ---: | ---: |
| Initial cold candidate build | 2,921 (1,510 dependencies + 1,411 Ruff) | 0 | 0 |
| Each of seven warm candidate commands | 0 | 1,510 | 1,411 |
| All eight candidate commands | 2,921 | 10,570 | 9,877 |

In every warm history, the 1,510 capture messages follow Cargo `Fresh` dependency records and precede the sole `Running` record for Ruff. Their complete ordered stream matches the initial dependency capture stream byte for byte. All six wrapper records in each warm history are accounted for: one exported Ruff compilation and five native identity/file-name probes. The fresh Ruff invocation then reports 1,411 verified hits and no cold captures. The wrong-edit command retains its original expected exit code 1.

The independent review checks 383 saved files (21,313,326 bytes), including 379 exact members of the existing 840-member strict capsule and all 355 candidate wrapper argv records. It also checks eight off-arm stderr streams contain no HIR cache events. Full raw logs stay in `../ruff-options-hash-strict-01/evidence.tar.gz`; `evidence-references.json` names every required member and exact hash. The review includes selected line-numbered context without replacing the full raw evidence.

The source review confirms that a successful hit performs current input/key preparation and checked HIR reconstruction, then returns before cold lowering/capture. Event counts are not counts of distinct functions, and a hit does not mean zero work.

This is a corrective attribution of existing diagnostic evidence. No compiler or benchmark was rerun, no original source or proof was changed, and no timing or speedup is qualified. The older profile discussion and unmeasured optimization hypothesis retained in A's original attribution report are outside this capsule's independent attribution review.
'''
members.append(write('ERRATUM.md', note.encode()))
manifest = dict(status='published-corrective-diagnostic-attribution', performance_qualified=False,
                source_or_original_proof_mutated=False, member_count=len(members), members=members,
                payload_bytes=sum(row['bytes'] for row in members), external_evidence_dependency=references['manifest'])
manifest_row = write('manifest.json', manifest)
for row in members:
    data, current = read(OUT / row['path'], row['sha256'])
    assert len(data) == row['bytes']
for _, data, source in frozen:
    current_bytes, current = read(source['path'], source['sha256'])
    assert current_bytes == data and current['stamp'] == source['stamp']
assert read(archive_manifest_ref['path'], archive_manifest_ref['sha256'])[1]['stamp'] == archive_manifest_ref['stamp']
readback_row = write('READBACK.json', dict(status='verified', manifest=manifest_row,
    member_count=len(members), payload_bytes=manifest['payload_bytes'],
    all_copied_source_bytes_and_stamps_unchanged=True,
    all_members_full_eof_sha256=True, old_raw_archive_duplicated=False,
    old_raw_archive_reverified_in_this_publication=False, performance_qualified=False))
stage = sorted(str(OUT / row['path']) for row in members + [manifest_row, readback_row])
stage.append(str(OUT / 'STAGE.json'))
write('STAGE.json', dict(paths=sorted(stage), git_operations=False))
actual = sorted(str(p) for p in OUT.rglob('*') if p.is_file())
assert actual == sorted(stage)
print(json.dumps(dict(path=str(OUT), files=len(stage), payload_bytes=manifest['payload_bytes'],
                     manifest=manifest_row, readback=readback_row, stage=str(OUT / 'STAGE.json')), sort_keys=True))
