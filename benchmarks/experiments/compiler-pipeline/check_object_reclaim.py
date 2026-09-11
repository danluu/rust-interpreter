#!/usr/bin/env python3
"""Check object-only reclamation against small owned files and live descriptors."""
import argparse
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from reclaim_workflow_objects import corpus_member, evidence, inventory, no_open_files, sha, validate_inventory
from workflow_io import write_json
from workspace_check_evidence import validate_identity, workspace_check


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    raw = ROOT / '.work/runs' / args.run_id
    out = ROOT / 'results' / args.run_id
    require(not raw.exists() and not out.exists(), 'run already exists')
    raw.mkdir()
    target = raw / 'target'
    target.mkdir()
    names = ['ordinary.o', 'executable.o', 'library.rlib', 'metadata.rmeta', 'program.rbc',
             'archive.a', 'native.dylib', 'query-cache.bin', 'executable', 'source.rs']
    for name in names:
        path = target / name
        path.write_bytes(('owned fixture: ' + name).encode())
        path.chmod(0o755 if name in ['executable.o', 'executable'] else 0o644)
    os.link(target / 'ordinary.o', target / 'ordinary-copy.o')
    os.link(target / 'ordinary.o', target / 'retained-link.rlib')
    plan = inventory(target)
    require([e['path'] for e in plan if e['remove']] == ['ordinary-copy.o', 'ordinary.o'],
            'non-object/executable selected for removal')
    validate_inventory(target, plan)
    no_open_files(target)
    rejected = []

    def rejects(label, operation):
        try:
            operation()
        except RuntimeError as error:
            rejected.append(dict(label=label, error=str(error)))
        else:
            raise RuntimeError('unsafe inventory accepted: ' + label)

    with (target / 'ordinary.o').open('rb'):
        rejects('open object', lambda: no_open_files(target))
    with (target / 'library.rlib').open('rb'):
        rejects('open retained library', lambda: no_open_files(target))
    (target / 'new.o').write_bytes(b'new')
    rejects('new file since inventory', lambda: validate_inventory(target, plan))
    (target / 'new.o').unlink()
    (target / 'symlink.o').symlink_to('ordinary.o')
    rejects('symlink object', lambda: inventory(target))
    (target / 'symlink.o').unlink()
    (target / 'alias-directory').symlink_to(raw, target_is_directory=True)
    rejects('symlink directory', lambda: inventory(target))
    (target / 'alias-directory').unlink()
    object_path = target / 'ordinary.o'
    original = object_path.read_bytes()
    object_path.write_bytes(b'x' * len(original))
    rejects('changed object', lambda: validate_inventory(target, plan))
    object_path.write_bytes(original)
    plan = inventory(target)
    retained = {e['path']: e['sha256'] for e in plan if not e['remove']}
    # Delete only two links to this test's own fixture object. A third link
    # with a retained library suffix must keep the same inode/content.
    for item in plan:
        if item['remove']:
            (target / item['path']).unlink()
    validate_inventory(target, plan, removed=True)
    require(all(sha(target / name) == digest for name, digest in retained.items()), 'retained file changed')
    require(len(rejected) == 6, 'missing rejection cases')
    corpus_id = 'resumable-bulk-heldout-retry-02'
    workflow_id = corpus_id + '-nushell-type-relations'
    report_path = ROOT / 'results' / workflow_id / 'summary.json'
    report = json.loads(report_path.read_text())
    corpus = json.loads((ROOT / 'results' / corpus_id / 'summary.json').read_text())
    corpus_member(corpus, corpus_id, workflow_id, report_path, report)
    changes = [
        ('changed report digest', lambda c: c['workflows'][0].update(report_sha256='0' * 64)),
        ('another report path', lambda c: c['workflows'][0].update(report='results/another/summary.json')),
        ('duplicate completed report', lambda c: c['workflows'].append(deepcopy(c['workflows'][0]))),
        ('missing completed report', lambda c: c['workflows'].clear()),
        ('wrong case project', lambda c: c['plan']['cases'][0].update(project='ruff')),
        ('wrong case workflow', lambda c: c['plan']['cases'][0].update(workflow='other')),
        ('wrong case label', lambda c: c['workflows'][0].update(label='other')),
    ]
    for label, change in changes:
        altered = deepcopy(corpus)
        change(altered)
        rejects(label, lambda: corpus_member(altered, corpus_id, workflow_id, report_path, report))
    require(len(rejected) == 13, 'missing corpus provenance rejections')
    workflow_checks = []
    for run_id, parent in [('lightweight-wrapper-pgrust-repeated-01', None), (workflow_id, corpus_id)]:
        checked_target, proofs, verified = evidence('workflow', run_id, parent)
        require(checked_target == ROOT / '.work/runs' / run_id / 'native', 'native workflow target differs')
        workflow_checks.append(dict(run_id=run_id, proof_files=len(proofs),
            primary_commands=verified['commands'], artifact_checks=verified['exact_artifact_hashes_verified']))
    host_checks = []
    for run_id in ['resumable-bulk-debug-01', 'resumable-bulk-release-01', 'lightweight-wrapper-release-01']:
        host_target, proofs, verified = workspace_check(run_id, sha)
        require(host_target == ROOT / '.work/diagnostic-builds' / run_id, 'host target differs')
        host_checks.append(dict(run_id=run_id, proof_files=len(proofs), verification=verified))
    run_id = 'resumable-bulk-debug-01'
    host_plan = json.loads((ROOT / '.work' / run_id / 'plan.json').read_text())
    host_status = json.loads((ROOT / '.work' / run_id / 'status.json').read_text())
    host_report = json.loads((ROOT / 'results' / run_id / 'summary.json').read_text())
    changes = [
        ('foreign check owner', lambda p, s, r: p.update(owner='/another/workspace')),
        ('another host target', lambda p, s, r: p.update(target='.work/interpreter-tools')),
        ('another source archive', lambda p, s, r: r.update(source_archive='.work/private')),
        ('running host check', lambda p, s, r: s.update(status='running')),
        ('failed host report', lambda p, s, r: r.update(status='failed')),
        ('changed host return code', lambda p, s, r: r.update(returncode=1)),
        ('changed frozen sources', lambda p, s, r: r.update(frozen_sources_unchanged=False)),
        ('another host report', lambda p, s, r: s.update(report='results/another')),
        ('performance target', lambda p, s, r: p.update(performance_measurement=True)),
        ('changed host command', lambda p, s, r: r['command'].append('--release')),
        ('another completed host command', lambda p, s, r: s['command'].__setitem__(
            s['command'].index('--target-dir') + 1, '/another/target')),
        ('another test log', lambda p, s, r: r.update(raw_log='.work/another/test.log')),
        ('missing frozen input', lambda p, s, r: r['frozen'].pop(next(iter(r['frozen'])))),
        ('zero passing tests', lambda p, s, r: r.update(workspace_passed=0)),
        ('incorrect test totals', lambda p, s, r: r.update(workspace_passed=r['workspace_passed'] + 1)),
        ('failed test target', lambda p, s, r: r['tests'][0].update(failed=1)),
    ]
    for label, change in changes:
        p, s, r = deepcopy(host_plan), deepcopy(host_status), deepcopy(host_report)
        change(p, s, r)
        rejects(label, lambda: validate_identity(run_id, p, s, r))
    rejects('unknown cleanup evidence kind', lambda: evidence('private', run_id))
    rejects('host check with corpus identity', lambda: evidence('workspace-check', run_id, 'some-corpus'))
    require(len(rejected) == 31, 'missing host qualification rejections')
    out.mkdir()
    write_json(out / 'summary.json', dict(status='passed', rejected=rejected,
        removable_objects=2, retained_files_verified=len(retained), compiler_cache_modified=False,
        real_corpus_provenance_verified=True, real_workflow_checks=workflow_checks, real_host_checks=host_checks,
        retained_hardlink_verified=True,
        raw=str(raw.relative_to(ROOT)), sources={str(p.relative_to(ROOT)): sha(p) for p in
            [Path(__file__), ROOT / 'scripts/reclaim_workflow_objects.py',
             ROOT / 'scripts/workspace_check_evidence.py', ROOT / 'scripts/workflow_io.py']}))
    print(json.dumps(dict(rejections=len(rejected), retained_files=len(retained))))


if __name__ == '__main__':
    main()
