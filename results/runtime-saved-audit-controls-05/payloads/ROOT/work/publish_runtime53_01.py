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
D = R/'results/runtime-saved-audit-controls-05'
REPORT = R/'.work/runtime53-publication-readback-01.json'
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
audit_path = R/'.work/runtime-saved-audit-controls-independent-verification-05.json'
assert sha(read(audit_path)[0]) == '8eab665dd1cd8107ff203056decf12b54c5f0724e3332fe5f6ccdf6f61a54333'
audit = document(audit_path)
assert audit['status'] == 'verified' and audit['controls'] == 53
assert audit['compiler_calls'] == audit['provider_probes'] == audit['process_signals'] == 0
roots = [R/name for name in [
    'experiments/runtime-saved-audit-controls-05',
    '.work/runtime-saved-audit-controls-preparation-execution-05',
    '.work/runtime-saved-audit-controls-launch-execution-05',
    '.work/experiments/runtime-saved-audit-controls-supervisor-05',
    '.work/runtime-saved-audit-controls-05',
    '.work/runtime-saved-audit-controls-verification-execution-05',
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

A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
fixed = [audit_path, Path(__file__).resolve(),
    R/'.work/runtime-saved-audit-controls05-actual-preparation-root-review-01.json',
    R/'.work/runtime-saved-audit-controls-05-from-actual52.diff',
    R/'.work/prepare_runtime_saved_audit_controls_05_from_actual52.diff',
    O/'.work/runtime-saved-audit-controls05-harness-independent-source-review-01.json',
    O/'.work/runtime-saved-audit-controls05-preparation-independent-source-review-02.json',
    O/'.work/runtime-saved-audit-controls05-packet-independent-review-01.json',
    O/'.work/runtime05-audit-io-independent-source-review-02.json',
]
fixed.extend(R/'experiments/hir-options-hash-runtime-audit-05'/name for name in
    ['reader.py','test_reader.py','audit_io.py','test_audit_io.py'])
selected.update(fixed)
for stem in ['prepare_runtime_saved_audit_controls_05_once',
             'launch_runtime_saved_audit_controls_05_bounded',
             'verify_runtime_saved_audit_controls_05','execute_runtime_saved_audit_controls_audit_05']:
    selected.update((R/'.work').glob(stem+'.*'))
for name in ['runtime05-reader-before-blob-schema-01.py','runtime05-reader-blob-schema-correction-01.diff',
             'runtime05-before-retired-absences-01-audit_io.py','runtime05-before-retired-absences-01-test_audit_io.py',
             'runtime05-retired-absence-correction-01.diff','runtime05-before-inspection-alias-fix-01-audit_io.py',
             'runtime05-before-inspection-alias-fix-01-test_audit_io.py','runtime05-inspection-alias-correction-01.diff']:
    selected.add(A/'.work'/name)

files = []
contents = {}
for p in sorted(selected):
    data, stamp = read(p)
    label, base = next((label, base) for label, base in [('ROOT', R), ('X', X), ('O', O), ('A', A)] if p.is_relative_to(base))
    relative = 'payloads/'+label+'/'+str(p.relative_to(base)).replace('.work/', 'work/', 1)
    files.append(dict(path=str(p), relative=relative, identity=stamp, bytes=len(data), sha256=sha(data)))
    contents[relative] = data
assert len(files) <= 128 and len(contents) == len(files)
assert sum(r['bytes'] for r in files) <= 4*2**20
manifest = dict(status='exact-closed-pure-control-evidence', files=files, closed_trees=members,
    audit_sha256=sha(read(audit_path)[0]), controls=53, application_qualified=False,
    retirement_performed=False, allocation_credit_bytes=0, sources_preserved=True)
contents['manifest.json'] = encode(manifest)
contents['STATUS.md'] = '# Status\n\nAll 53 saved-runtime reader and I/O controls passed once and were independently verified: 26 callback fixtures and 27 small file-I/O or input-union fixtures. No skips, compiler calls, provider probes or nested workload processes occurred.\n\nAudit: 8eab665dd1cd8107ff203056decf12b54c5f0724e3332fe5f6ccdf6f61a54333. All 12 frozen inputs (879,716 bytes), exact raw test names, process identity and terminal closure were checked. The four qualified sources are reader.py, test_reader.py, audit_io.py and test_audit_io.py from experiments/hir-options-hash-runtime-audit-05. Later orchestration source is not qualified by these fixtures.\n\nThese tests do not qualify the actual compiler/runtime or demonstrate faster application builds. The separate full saved-evidence Reader rehearsal02 failed on an omitted hash-stage launch file; its failed execution is preserved in results/runtime04-reader-rehearsal-02. Runtime installation and application timing remain pending. No files were retired and no space credit is claimed.\n\nSource-review and unbound-draft documents retain their historical wording and bytes. The actual tested status is recorded here.\n'.encode()

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
