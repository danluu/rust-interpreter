"""Read-only retention preparation for a closed, audited partial retirement."""
import ast
from collections import Counter
import json
import os
from pathlib import Path
import sys

import archive as a

R = a.OWNER
A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
H = R/'experiments/old-compiler-partial-retirement-01'
W = R/'.work/old-compiler-partial-retirement-01'
C = A/'experiments/ruff-strict-cache-retirement-01/controls-01'
CW = A/'.work/ruff-strict-cache-retirement-controls-01'
OLD = R/'.work/root-old-compiler-retirement-history-01'
LIVE = (R/'.work/compilers', X/'.work/hir-options-hash-compiler-01')


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2); stream.write('\n')


def main():
    assert Path.cwd() == R and sys.dont_write_bytecode and not sys.flags.optimize
    for p in [a.HERE/'plan.json', a.HERE/'inputs.json', a.HERE/'launch.json', a.WORK, a.RESULT]:
        assert not p.exists() and not p.is_symlink()
    sources = {}

    def add(path):
        path = Path(path)
        assert not any(path.is_relative_to(root) for root in LIVE), 'live compiler payload excluded'
        assert path.resolve(strict=True) == path and path.is_file() and not path.is_symlink()
        assert path.stat().st_size <= 96*2**20
        sources[str(path)] = path
        assert len(sources) <= 1536

    def tree(root):
        assert root.resolve(strict=True) == root and root.is_dir()
        for path in sorted(root.rglob('*')):
            assert not path.is_symlink()
            if path.is_file(): add(path)
            else: assert path.is_dir()

    original = a.read(H/'plan-01/inputs.json')
    assert a.sha(H/'plan-01/inputs.json') == '1787fd98a4a84c4f8721b584b45dece5e712ad7c92dc822c3025ca3413ad7194'
    old_plan = a.read(H/'plan-01/plan.json')
    assert a.sha(H/'plan-01/plan.json') == original['plan_sha256']
    omitted = {}
    # Retain every non-provider source/proof from the actual removal freeze.
    # Large live provider bytes remain only in its historical identity catalog.
    for name, row in original['files'].items():
        path = Path(name)
        if any(path.is_relative_to(root) for root in LIVE):
            omitted[name] = row
            continue
        assert a.identity(path) == row['identity'] and a.sha(path) == row['sha256'], name
        add(path)
    tree(H); tree(W); tree(OLD)
    tree(R/'.work/experiments/old-compiler-partial-retirement-supervisor-01')
    tree(R/'.work/old-compiler-partial-retirement-launch-01')
    for name in ['old-compiler-partial-retirement-independent-verification-01.json',
                 'root-old-compiler-partial-retirement-plan-review-01.json',
                 'root-old-compiler-copy-comparison-03.json',
                 'root-old-compiler-copy-comparison-preflight-failure-01.json',
                 'root-old-compiler-copy-comparison-preflight-failure-02.json',
                 'compare_retired_compiler_copies_01.py', 'compare_retired_compiler_copies_02.py',
                 'compare_retired_compiler_copies_03.py', 'verify_old_compiler_failure_archive_02.py',
                 'verify_old_compiler_partial_retirement_01.py', 'launch_old_compiler_partial_retirement_01.py']:
        add(R/'.work'/name)
    for stem in ['old-compiler-partial-retirement-preparation-01',
                 'old-compiler-partial-retirement-independent-verification-execution-01']:
        for suffix in ['json', 'stdout', 'stderr']: add(R/'.work'/(stem+'.'+suffix))
    tree(C); tree(CW); tree(A/'.work/experiments/ruff-strict-cache-retirement-controls-supervisor-01')
    for suffix in ['actual.json', 'stdout', 'stderr']:
        add(A/'.work'/('ruff-strict-cache-retirement-controls-launch-01.'+suffix))
    control_freeze = a.read(C/'inputs.json')
    for name, row in control_freeze['files'].items():
        path = Path(name); state = path.lstat()
        assert [state.st_dev, state.st_ino, state.st_mode, state.st_size,
                state.st_mtime_ns, state.st_ctime_ns, state.st_nlink] == row['stamp']
        assert a.sha(path) == row['sha256']; add(path)
    for name in ['ruff-strict-cache-retirement-controls-independent-verification-01.json',
                 'verify_ruff_strict_cache_controls_01.py',
                 'old-compiler-partial-retirement-source-review-01.json']:
        add(O/'.work'/name)
    for name in ['archive.py', 'prepare.py', 'README.md']: add(a.HERE/name)
    for name in ['experiments/stable-cgu/owned_stage.py', 'scripts/supervise_experiment.py']: add(R/name)

    terminal = a.read(W/'receipt.json')
    audit_path = R/'.work/old-compiler-partial-retirement-independent-verification-01.json'
    audit = a.read(audit_path)
    assert audit['status'] == 'verified' and audit['receipt_sha256'] == a.sha(W/'receipt.json')
    assert audit['deleted_ledger_sha256'] == a.sha(W/'deleted.jsonl')
    assert audit['transition_sha256'] == a.sha(W/'transition.json')
    assert audit['inputs_sha256'] == a.sha(H/'plan-01/inputs.json')
    assert terminal['status'] == 'passed' and len(terminal['children']) == 2
    assert not Path(old_plan['root']).exists() and not Path(old_plan['root']).is_symlink()
    inventory = a.read(W/'admitted-inventory.json')
    counts = Counter(); sets = {key:set() for key in ['intent','unlinked','validated']}
    with (W/'deleted.jsonl').open() as ledger:
        for line in ledger:
            assert len(line) <= 16384
            row = json.loads(line); kind = row['event']; name = row['relative']
            assert kind in sets and name in inventory and name not in sets[kind]
            sets[kind].add(name); counts[kind] += 1
    assert len(inventory) == 8388 and counts == Counter(intent=8388,unlinked=8388,validated=8388)
    assert all(names == set(inventory) for names in sets.values()) and audit['ledger_events'] == 25164
    assert a.sha(OLD/'evidence.tar.xz') == '97898061418b8a1f9e078e26418c9f45f14e566773f33af34c0425718c93b908'
    control_audit = a.read(O/'.work/ruff-strict-cache-retirement-controls-independent-verification-01.json')
    assert control_audit['status'] == 'verified' and control_audit['controls'] == 12
    assert control_audit['receipt_sha256'] == a.sha(CW/'receipt.json')
    assert control_audit['inputs_sha256'] == a.sha(C/'inputs.json')
    helper = str(A/'experiments/ruff-strict-cache-retirement-01/fd_remove.py')
    assert control_freeze['files'][helper]['sha256'] == a.sha(H/'fd_remove.py') == '0b154792e3b393bdc018a6ee4337347535be466db64aa3fa40cd6a3899be6041'
    checks = {str(W/'receipt.json'):dict(status='passed',chmod_calls=0,actual_readonly_probes=2),
        str(audit_path):dict(status='verified',retired_entries=8388,retired_files=6982,
            retired_directories=1406,ledger_events=25164,all_durable_events_replayed=True,
            full_historical_archive_members=52,full_xz_eof=True,chmod_calls=0),
        str(CW/'receipt.json'):dict(status='passed',controls_passed=12),
        str(R/'.work/root-old-compiler-copy-comparison-preflight-failure-01.json'):
            dict(status='failed-read-only',deletions=0,processes_started=0),
        str(R/'.work/root-old-compiler-copy-comparison-preflight-failure-02.json'):
            dict(status='failed-read-only',deletions=0,processes_started=0)}
    for name, expected in checks.items():
        actual = a.read(Path(name)); assert all(actual[key] == value for key,value in expected.items())
    members = {name.lstrip('/'):dict(source=name,bytes=p.stat().st_size,sha256=a.sha(p)) for name,p in sorted(sources.items())}
    plan = dict(owner=str(R),members=members,historical_source_substitutions={},
        historical_freezes={str(H/'plan-01/inputs.json'):dict(sha256=a.sha(H/'plan-01/inputs.json'),files=len(original['files'])),
                           str(C/'inputs.json'):dict(sha256=a.sha(C/'inputs.json'),files=len(control_freeze['files']))},
        receipt_checks=checks,environment=old_plan['environment'],
        platform_context=list(os.uname()),platform_identity=[v for i,v in enumerate(os.uname()) if i!=1],
        canonical_lock=str(a.owned.CANONICAL_LOCK),wait_seconds=600,minimum_free_gib=9,
        executor=dict(path='/opt/homebrew/bin/python3',resolved=str(Path('/opt/homebrew/bin/python3').resolve(strict=True)),
                      route_identity=a.identity(Path('/opt/homebrew/bin/python3'))),
        children=0,archive_limit_bytes=64*2**20,maximum_logical_bytes=384*2**20,
        member_count=len(members),logical_bytes=sum(row['bytes'] for row in members.values()),
        excluded_live_provider_files=len(omitted),excluded_live_provider_bytes=sum(row['identity']['size'] for row in omitted.values()),
        exclusion_meaning='Live compiler/provider payloads are not archived. Their exact historical rows remain in the retained original freeze; no removed path is represented as current.',
        scope='Closed single failed staging-prefix retirement: 8388 paths, full25164 durable events, two actual read-only children, launcher/outer/terminal/full independent audit. Original failed comparison attempts and52-member XZ history including verification failure retained. Exact actual12-fixture qualification and all non-provider source/proof inputs retained. No compiler/control/probe/deletion/process-control work runs here.')
    assert len(members) <= 1536 and plan['logical_bytes'] < 384*2**20
    write(a.HERE/'plan.json',plan)
    files = set(sources.values()) | {a.HERE/'plan.json',Path(sys.executable).resolve(strict=True)}
    frozen = {}
    for p in sorted(files):
        before=a.identity(p);digest=a.sha(p);assert a.identity(p)==before
        frozen[str(p)]=dict(identity=before,sha256=digest)
        if p.suffix=='.py':ast.parse(p.read_bytes(),filename=str(p))
    write(a.HERE/'inputs.json',dict(files=frozen))
    command=['/opt/homebrew/bin/python3','-B',str(R/'scripts/supervise_experiment.py'),'--run-id',
        'old-compiler-partial-retirement-evidence-supervisor-01','--','/opt/homebrew/bin/python3','-B',
        str(a.HERE/'archive.py'),'--inputs-sha256',a.sha(a.HERE/'inputs.json')]
    write(a.HERE/'launch.json',dict(command=command,cwd=str(R),environment=plan['environment'],review_required_before_execution=True))
    print(json.dumps(dict(members=len(members),logical_bytes=plan['logical_bytes'],inputs=len(files),
        plan_sha256=a.sha(a.HERE/'plan.json'),freeze_sha256=a.sha(a.HERE/'inputs.json'),
        launch_sha256=a.sha(a.HERE/'launch.json')),indent=2))


if __name__ == '__main__': main()
