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
D = R/'results/runtime-preflight-retry-controls-05'
REPORT = R/'.work/runtime-preflight-retry33-publication-readback-01.json'
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
audit_path = R/'.work/runtime-preflight-retry-controls-independent-verification-05.json'
assert sha(read(audit_path)[0]) == '65c10f5917dde90d0d03d7abd951e33c09ba076b401c6d0b00d9fbc046ff19a9'
audit = document(audit_path)
assert audit['status'] == 'verified' and audit['controls'] == 33
assert audit['compiler_calls'] == audit['provider_probes'] == audit['process_signals'] == 0
roots = [R/name for name in [
    'experiments/runtime-preflight-retry-controls-05',
    '.work/runtime-preflight-retry-controls-preparation-execution-05',
    '.work/runtime-preflight-retry-controls-launcher-05',
    '.work/experiments/runtime-preflight-retry-controls-supervisor-05',
    '.work/runtime-preflight-retry-controls-05',
    '.work/runtime-preflight-retry-controls-verification-execution-05',
    '.work/runtime-preflight-retry33-before-no-signals-01',
    '.work/runtime-preflight-retry33-before-actual-packet-binding-01',
    'results/runtime-preflight-retry-test-development-01',
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
    O/'.work/runtime-preflight05-test33-independent-source-review-01.json']
freeze = document(R/'experiments/runtime-preflight-retry-controls-05/inputs.json')
assert len(freeze['files']) == 19
for name, row in freeze['files'].items():
    p = Path(name)
    data, observed = read(p)
    expected_stamp = [observed[k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]
    assert row['stamp'] == expected_stamp and row['sha256'] == sha(data)
    fixed.append(p)
selected.update(fixed)
for base, patterns in [(R, ['runtime-preflight05-*', 'runtime-preflight-retry-controls-05-*.from-actual39.diff']),
                       (A, ['runtime-preflight-retry33-*.json', 'runtime-retry-test-*']),
                       (X, ['runtime-preflight05-*'])]:
    for pattern in patterns:
        selected.update(p for p in (base/'.work').glob(pattern) if p.is_file())
for name in ['prepare_runtime_preflight_retry_controls_05_once.py',
             'launch_runtime_preflight_retry_controls_05_bounded.py',
             'verify_runtime_preflight_retry_controls_05.py',
             'execute_runtime_preflight_retry_controls_audit_05.py']:
    selected.add(R/'.work'/name)
# Retain exact prior39 harness bytes underlying the narrow derivation diffs.
prior = document(A/'.work/runtime-preflight-retry33-harness-source-handoff-01.json')
for name, digest in prior['predecessors'].items():
    p = Path(name)
    assert sha(read(p)[0]) == digest
    selected.add(p)

files = []
contents = {}
for p in sorted(selected):
    data, stamp = read(p)
    label, base = next((label, base) for label, base in [('ROOT', R), ('X', X), ('O', O), ('A', A), ('SYSTEM', Path('/'))] if p.is_relative_to(base))
    relative = 'payloads/'+label+'/'+str(p.relative_to(base)).replace('.work/', 'work/', 1)
    files.append(dict(path=str(p), relative=relative, identity=stamp, bytes=len(data), sha256=sha(data)))
    contents[relative] = data
assert len(files) <= 128 and len(contents) == len(files)
assert sum(r['bytes'] for r in files) <= 4*2**20
manifest = dict(status='exact-closed-pure-control-evidence', files=files, closed_trees=members,
    audit_sha256=sha(read(audit_path)[0]), controls=33, application_qualified=False,
    retirement_performed=False, allocation_credit_bytes=0, sources_preserved=True,
    development_controls=33, development_is_frozen_qualification=False, input_files=19, input_bytes=1018181,
    compiler_qualified=False, runtime_qualified=False, performance_measurement=False)
contents['manifest.json'] = encode(manifest)
contents['STATUS.md'] = b'# Status\n\nAll 33 retry controls passed once in the frozen bounded harness and were independently verified: 19 saved owner fixtures, seven real temporary-file inherited-lock fixtures, and seven early Controller admission guards. There were no skipped tests, compiler calls, provider probes, nested workload processes, or explicit process signals.\n\nThe independent audit is 65c10f5917dde90d0d03d7abd951e33c09ba076b401c6d0b00d9fbc046ff19a9. It checked all 19 frozen inputs (1,018,181 bytes), exact raw test names, source identities, process records, and closed execution. Test PID 58379 ran beneath controller 23373 and supervisor 23323; the outer closed at 1789820054.7121742. The audit child 61588 closed with exit 0 under parent 60801. The source, packet, preparation, dispatcher, supervisor, tests, and independent audit are retained losslessly in payloads.\n\nAn earlier ordinary development run also passed 33 tests. Its result and raw output are retained separately under the development result path; it is not the frozen qualification proof. Unrun drafts, corrections, source reviews, and their historical wording are preserved. No failed controlled retry33 attempt occurred.\n\nThe retry policy has explicit owner05 routes and a 16 GiB preflight admission rule with 9 GiB stop and 8 GiB floor. The controls reject silently substituting the old 24 GiB preflight policy and preserve the installation policy separately. Lock cases use only owned temporary files with the real helper; the new wrapper observes preheld exclusion. This observation is not an atomic proof against concurrent ownership changes. The production entry retains its owning descriptor through the operation.\n\nThe original helper can acquire an unheld supplied descriptor; one test documents that actual legacy behavior. The new harness controller refuses os.kill and os.killpg through an audit hook before calling the unchanged helper. Existing child CPU and alarm bounds and helper wait/receipt handling remain intact.\n\nThese controls qualify the tested metadata and admission behavior. They do not qualify a runtime installation, compiler build, application workload, or performance claim. No production retry was run by this qualification. Original runtime04, startup39, and helper sources remain unchanged. Published byte copies have independent destination identities; manifest source identities describe the originals. manifest.json deliberately has no self-row.\n'

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
