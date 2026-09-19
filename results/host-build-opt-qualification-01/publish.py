from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
PLAN = HERE/'host-build-opt-publication-plan-01.json'
assert hashlib.sha256(PLAN.read_bytes()).hexdigest() == 'f2ea3920996043c9d97b5930902f8eb7562f9fac676feaccc44518aa6b29c24e'
plan = json.loads(PLAN.read_text())
OUT = Path(plan['destination'])


def stamp(p):
    s = p.lstat()
    return [s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns]


def original(row):
    p = Path(row['path'])
    assert stamp(p) == row['identity']
    b = p.read_bytes()
    assert len(b) == row['bytes'] and hashlib.sha256(b).hexdigest() == row['sha256']
    assert stamp(p) == row['identity']


def trees():
    for row in plan['trees']:
        p = Path(row['path'])
        assert stamp(p)[:3] == row['root_identity']
        assert sorted(str(q.relative_to(p)) for q in p.rglob('*')) == row['entries']


def ref(p):
    b = p.read_bytes()
    return dict(path=str(p.relative_to(OUT)),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))


assert len(plan['files']) == plan['file_count'] <= plan['maximum_files']
assert sum(r['bytes'] for r in plan['files']) == plan['payload_bytes'] <= plan['maximum_payload_bytes']
assert not OUT.exists()
trees()
for row in plan['files']:
    original(row)
OUT.mkdir()
for row in plan['files']:
    destination = OUT/row['destination']
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(row['path'],destination)
    assert ref(destination)['sha256'] == row['sha256']
shutil.copy2(PLAN,OUT/'plan.json')
shutil.copy2(__file__,OUT/'publish.py')
status = '''This finite snapshot retains host-build-opt source development and native qualification.

Fixture02 PASSED under the original native Cargo/rustc: four normal closed commands, two profile_contract tests, 22 recorded Cargo compiler invocations and eight build-script profile observations. The native test and macro execution preserve enabled debug assertions and overflow checks while host optimization changes 0 to3 and target optimization remains1. Exact ordinary 16-source before/after and copied fixture checks passed. Original ten pure tests and five later saved-argv parser tests passed in separate evidence directories.

Fixture01 remains FAILED: its host0 Cargo/test succeeded, then the validator rejected the ordinary valueless -C prefer-dynamic. Host3 did not start. Its original sources, raw failure, normal parent closure, traces and profile records remain separate. Successor02 changed only parsing and fresh output/manifest routes.

The Cargo profile is an explicit policy, not a transparent optimization. Build-script OPT_LEVEL changes, both target crate metadata IDs change, and all three selected-test extern file hashes change between0/3. No RBCs or Ruff opt3 results were produced by this fixture. Application source/test/diagnostic and complete bytecode equality remain required before any performance interpretation. This snapshot makes no speedup, fastest-configuration, holdout or final-latency claim.

The30-second command/256MiB output thresholds are observed failure thresholds. Breaches retain normal wait without signaling and can exceed the timer; they are not hard wall limits or atomic disk quotas. The passing result recorded about8MiB allocated output. Compiler argv adapters exec in place; the root's actual normal parent closure and Cargo waits are retained, without claiming separately observed OS waits for each rustc adapter.

All210 payloads are finite source/text evidence. Provider binaries, fixture target binaries, caches and broader target directories are not copied. Only six exact saved--extern products were hashed during independent readback; their metadata/digests are retained. Historical source/profile memos keep external references and are not relabeled as new qualifications. Source-only handoffs retain their historical wording; this STATUS records the later actual outcomes.
'''
(OUT/'STATUS.md').write_text(status)
metadata = [ref(OUT/n) for n in ['plan.json','publish.py','STATUS.md']]
manifest = dict(policy='host-build-opt-finite-qualification-publication-v1',
    payloads=plan['files'],metadata=metadata,payload_count=plan['file_count'],payload_bytes=plan['payload_bytes'])
(OUT/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
expected = {r['destination'] for r in plan['files']} | {r['path'] for r in metadata} | {'manifest.json'}
assert {str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file()} == expected
for row in plan['files']:
    original(row)
    assert ref(OUT/row['destination'])['sha256'] == row['sha256']
trees()
readback = dict(status='passed',manifest=ref(OUT/'manifest.json'),
    exact_originals_and_copies=plan['file_count'],payload_bytes=plan['payload_bytes'],
    exact_final_file_membership=sorted(expected),original_trees_unchanged=len(plan['trees']),
    binary_payloads_copied=False)
(OUT/'readback.json').write_text(json.dumps(readback,sort_keys=True,indent=2)+'\n')
stage = dict(capsule_files=sorted(str(p) for p in OUT.rglob('*') if p.is_file())+[str(OUT/'staging-paths.json')],
             original_source_files=plan['original_source_staging'],
             note='Use explicit paths, including fixture/target source files ignored by default discovery.')
(OUT/'staging-paths.json').write_text(json.dumps(stage,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(directory=str(OUT),manifest=ref(OUT/'manifest.json'),
    readback=ref(OUT/'readback.json'),staging=ref(OUT/'staging-paths.json'))))
