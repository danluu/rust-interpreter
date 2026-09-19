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
D = R/'results/runtime-prerequisite-controls-04'
REPORT = R/'.work/runtime52-publication-readback-01.json'
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
audit_path = R/'.work/runtime-prerequisite-controls-independent-verification-04.json'
assert sha(read(audit_path)[0]) == '4cb7aa612c5ae53ada77dd41db870adb5b8dfa742005aa297dd483fca9531dcc'
audit = document(audit_path)
assert audit['status'] == 'verified' and audit['controls'] == 52
assert audit['compiler_calls'] == audit['provider_probes'] == audit['process_signals'] == 0
roots = [X/'experiments/hir-options-hash/runtime-installation-04', *[R/name for name in [
    'experiments/runtime-prerequisite-controls-04',
    '.work/runtime-prerequisite-controls-preparation-execution-04',
    '.work/runtime-prerequisite-controls-launch-execution-04',
    '.work/experiments/runtime-prerequisite-controls-supervisor-04',
    '.work/runtime-prerequisite-controls-04',
    '.work/runtime-prerequisite-controls-verification-execution-04',
]]]
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
    R/'.work/runtime52-root-launch-review-01.json',
    R/'.work/runtime04-root-integration-source-review-01.json',
    R/'.work/prepare_runtime_prerequisite_controls_04_once.py',
    R/'.work/prepare_runtime_prerequisite_controls_04_once.diff',
    X/'.work/runtime04-source-self-review-01.json',
    X/'.work/runtime04-from-03-source-01.diff',
    X/'.work/runtime04-controls-harness-source-review-01.json',
    X/'.work/runtime04-controls-packet-binding-source-01.json',
    X/'.work/runtime04-required-live-metadata-assessment-01.json',
    A/'.work/runtime04-controls-harness-independent-source-review-01.json',
    A/'.work/runtime04-controls-packet-chain-independent-review-01.json',
    A/'.work/runtime04-copy-bootstrap-source-review-01.json',
    O/'.work/runtime04-reader-independent-source-review-01.json',
    R/'.work/retained-proof-copy-controls-independent-verification-01.json',
]
selected.update(fixed)
for stem in ['launch_runtime_prerequisite_controls_04_bounded',
             'verify_runtime_prerequisite_controls_04','execute_runtime_prerequisite_controls_audit_04']:
    for suffix in ['.py','.unbound-01.py','.from-actual40.diff','.packet-binding.diff']:
        selected.add(R/'.work'/(stem+suffix))
for name in ['run','child','prepare']:
    selected.add(R/'.work'/('runtime04-controls-'+name+'.py.diff'))
    selected.add(R/'experiments/retained-proof-copy-controls-01'/(name+'.py'))
for name in ['launch_retained_proof_copy_controls_01_bounded.py',
             'verify_retained_proof_copy_controls_01.py','execute_retained_proof_copy_controls_audit_01.py',
             'prepare_retained_proof_copy_controls_01_once.py']:
    selected.add(R/'.work'/name)

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
    audit_sha256=sha(read(audit_path)[0]), controls=52, application_qualified=False,
    retirement_performed=False, allocation_credit_bytes=0, sources_preserved=True)
contents['manifest.json'] = encode(manifest)
contents['STATUS.md'] = '# Status\n\nAll 52 runtime reader tests passed once and were independently verified: 37 prerequisite/factory/continuation cases and 15 copy-selection/collector/admission cases. The original 21 test methods remain unchanged.\n\nAudit: 4cb7aa612c5ae53ada77dd41db870adb5b8dfa742005aa297dd483fca9531dcc. All 16 frozen inputs (934,802 bytes), exact raw names and process closure were checked. No skips, compiler calls or provider probes occurred.\n\nThese are synthetic metadata tests. The full runtime reader rehearsal against the saved compiler evidence, duplicate-copy retirement, runtime installation and application timing remain pending. No files were retired and no space credit is claimed here. Current file APIs reject historical copies; production requires a separate retirement audit and actual absence of the selected 21 paths.\n\nOriginal source-review documents retain their historical unrun wording and exact bytes. They do not override the actual test status recorded here.\n'.encode()

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
