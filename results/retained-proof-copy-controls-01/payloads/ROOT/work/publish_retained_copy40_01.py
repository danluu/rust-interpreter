"""Publish exact closed pure-control evidence; never alter its sources."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import time

R = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
D = R/'results/retained-proof-copy-controls-01'
REPORT = R/'.work/retained-proof-copy40-publication-readback-01.json'
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
sha = lambda b: hashlib.sha256(b).hexdigest()
encode = lambda value: (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def identity(p):
    s = p.lstat()
    return {k: getattr(s, 'st_'+k) for k in FIELDS}


def read(p):
    before = identity(p)
    assert stat.S_ISREG(before['mode']) and p.resolve(strict=True) == p
    assert before['size'] <= 2*2**20
    with os.fdopen(os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as f:
        assert {k: getattr(os.fstat(f.fileno()), 'st_'+k) for k in FIELDS} == before
        data = f.read(2*2**20+1)
        assert len(data) == before['size']
        assert {k: getattr(os.fstat(f.fileno()), 'st_'+k) for k in FIELDS} == before
    assert identity(p) == before and p.resolve(strict=True) == p
    return data, before


def document(p):
    return json.loads(read(p)[0])


assert Path.cwd() == R and not D.exists() and not D.is_symlink() and not REPORT.exists()
audit_path = R/'.work/retained-proof-copy-controls-independent-verification-01.json'
assert sha(read(audit_path)[0]) == 'c803f6e6e663c3fc8a081829e3c07deb9098692206a91269c36b2fe6fc08290a'
audit = document(audit_path)
assert audit['status'] == 'verified' and audit['controls'] == 40
assert audit['compiler_calls'] == audit['provider_probes'] == audit['process_signals'] == 0
roots = [R/name for name in [
    'experiments/retained-proof-copy-references-01',
    'experiments/retained-proof-copy-controls-01',
    '.work/retained-proof-copy-controls-preparation-execution-01',
    '.work/retained-proof-copy-controls-launch-execution-01',
    '.work/experiments/retained-proof-copy-controls-supervisor-01',
    '.work/retained-proof-copy-controls-01',
    '.work/retained-proof-copy-controls-verification-execution-01',
]]
members = {}
selected = set()
for root in roots:
    assert root.resolve(strict=True) == root and root.is_dir()
    found = {}
    for p in [root, *sorted(root.rglob('*'))]:
        i = identity(p)
        assert stat.S_ISDIR(i['mode']) or stat.S_ISREG(i['mode'])
        assert p.resolve(strict=True) == p
        found[str(p.relative_to(root))] = i
        if stat.S_ISREG(i['mode']):
            selected.add(p)
    members[str(root)] = found

fixed = [audit_path, Path(__file__).resolve(),
    R/'.work/retained-proof-copy40-root-launch-review-01.json',
    R/'.work/prepare_retained_proof_copy_controls_01_once.py',
    O/'.work/retained-proof-copy40-independent-source-review-01.json',
    X/'.work/retained-proof-copy-references-source-self-review-01.json',
    X/'.work/retained-proof-copy40-harness-source-draft-01.json',
    X/'.work/retained-proof-copy40-packet-binding-source-01.json',
    X/'.work/retained-proof-copy-source-check-preflight-failure-01.json',
    X/'.work/runtime04-historical-copy-reference-design-01.json',
    R/'.work/completed-proof-snapshot-catalog-controls-independent-verification-01.json',
]
selected.update(fixed)
draft = document(X/'.work/retained-proof-copy40-harness-source-draft-01.json')
for name, row in draft['sources'].items():
    selected.update([Path(name), Path(row['source']), Path(row['diff']['path'])])
binding = document(X/'.work/retained-proof-copy40-packet-binding-source-01.json')
for name, row in binding['changes'].items():
    selected.update([Path(name), Path(row['before']['path']), Path(row['diff']['path'])])
source_review = document(X/'.work/retained-proof-copy-references-source-self-review-01.json')
selected.update(map(Path, source_review['diffs']))
for name in ['references.py', 'test_references.py', 'README.md']:
    selected.add(X/('.work/retained-proof-copy-'+name+'-before-partition-rebuild-01'))

files = []
contents = {}
for p in sorted(selected):
    data, stamp = read(p)
    label, base = next((label, base) for label, base in [('ROOT', R), ('X', X), ('O', O)] if p.is_relative_to(base))
    relative = 'payloads/'+label+'/'+str(p.relative_to(base)).replace('.work/', 'work/', 1)
    files.append(dict(path=str(p), relative=relative, identity=stamp, bytes=len(data), sha256=sha(data)))
    contents[relative] = data
assert len(files) <= 128 and len(contents) == len(files)
assert sum(r['bytes'] for r in files) <= 4*2**20
manifest = dict(status='exact-closed-pure-control-evidence', files=files, closed_trees=members,
    audit_sha256=sha(read(audit_path)[0]), controls=40, application_qualified=False,
    retirement_performed=False, allocation_credit_bytes=0, sources_preserved=True)
contents['manifest.json'] = encode(manifest)
contents['STATUS.md'] = (
    '# Status\n\nForty pure metadata tests passed once and were independently verified.\n'
    'The exact helper rejects unapproved missing inputs, forged historical records,\n'
    'owner/catalog mismatches, callback mutation and invented allocation credit.\n\n'
    'Audit: c803f6e6e663c3fc8a081829e3c07deb9098692206a91269c36b2fe6fc08290a.\n'
    'All 11 frozen inputs (833,424 bytes), raw results and process closure were checked.\n'
    'There were no compiler calls, provider probes, skipped tests or missing child cwd observations.\n\n'
    'These tests qualify metadata validation only. Actual runtime integration, full\n'
    'recovery verification and removal of duplicate evidence remain pending. No\n'
    'application performance or reclaimed storage is claimed. Prepared source\n'
    'READMEs and the initial drafts retain their original wording and bytes.\n'
).encode()
assert sum(map(len, contents.values())) <= 6*2**20
D.mkdir(mode=0o700)
for relative, data in contents.items():
    target = D/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    assert target.parent.resolve(strict=True) == target.parent
    with target.open('xb') as f:
        assert f.write(data) == len(data)
        f.flush(); os.fsync(f.fileno())
    assert read(target)[0] == data
assert {str(p.relative_to(D)) for p in D.rglob('*') if p.is_file()} == set(contents)
for row in files:
    data, stamp = read(Path(row['path']))
    assert stamp == row['identity'] and sha(data) == row['sha256']
for root, expected in members.items():
    p = Path(root)
    assert {str(q.relative_to(p)): identity(q) for q in [p, *sorted(p.rglob('*'))]} == expected
outputs = [dict(relative=n, bytes=len(data), sha256=sha(data)) for n, data in sorted(contents.items())]
for p in [D.parent, D, *sorted((p for p in D.rglob('*') if p.is_dir()), reverse=True)]:
    fd = os.open(p, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
report = dict(status='verified-full-publication-readback', finished_at=time.time(),
    destination=str(D), source_files=len(files), source_bytes=sum(r['bytes'] for r in files),
    outputs=outputs, output_files=len(outputs), output_bytes=sum(r['bytes'] for r in outputs),
    manifest_sha256=sha(contents['manifest.json']), sources_unchanged=True, git_mutations=False)
with REPORT.open('xb') as f:
    f.write(encode(report)); f.flush(); os.fsync(f.fileno())
print(json.dumps(dict(report=str(REPORT), sha256=sha(REPORT.read_bytes()),
    output_files=report['output_files'], output_bytes=report['output_bytes'])))
