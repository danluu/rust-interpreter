"""Read-only bounded retention preparation for the closed published-prefix retirement."""
import ast
from collections import Counter
import json
import os
from pathlib import Path
import signal
import sys

import archive as a

R = a.OWNER
A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
H = R/'experiments/old-compiler-published-retirement-01'
W = R/'.work/old-compiler-published-retirement-01'
OLD = R/'.work/root-old-compiler-retirement-history-01'
LIVE = (R/'.work/compilers', X/'.work/hir-options-hash-compiler-01')


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2); stream.write('\n')


def main():
    assert Path.cwd() == R and sys.dont_write_bytecode and not sys.flags.optimize
    signal.alarm(600)
    for p in [a.HERE/'plan.json', a.HERE/'inputs.json', a.HERE/'launch.json', a.WORK, a.RESULT]:
        assert not p.exists() and not p.is_symlink()
    sources = {}

    def add(path):
        path = Path(path)
        assert not any(path.is_relative_to(root) for root in LIVE), 'live compiler payload excluded'
        assert path.resolve(strict=True) == path and path.is_file() and not path.is_symlink()
        assert path.stat().st_size <= 96*2**20
        sources[str(path)] = path
        assert len(sources) <= 1536 and sum(p.stat().st_size for p in sources.values()) < 384*2**20

    def tree(root):
        assert root.resolve(strict=True) == root and root.is_dir()
        count = 0
        for path in sorted(root.rglob('*')):
            count += 1; assert count <= 4096 and not path.is_symlink()
            if path.is_file(): add(path)
            else: assert path.is_dir()

    original = a.read(H/'plan-01/inputs.json')
    assert a.sha(H/'plan-01/inputs.json') == '0a65a1bb44207128051ea8186b28a93e3ad04043a9b866afb9d4ff6502074672'
    old_plan = a.read(H/'plan-01/plan.json')
    assert a.sha(H/'plan-01/plan.json') == original['plan_sha256']
    omitted = {}
    # Preserve all non-provider bytes and complete historical provider catalogs.
    # Do not re-run closed controller guards, especially historical consumer absences.
    for name, row in original['files'].items():
        path = Path(name)
        if any(path.is_relative_to(root) for root in LIVE):
            omitted[name] = row; continue
        assert a.identity(path) == row['identity'] and a.sha(path) == row['sha256'], name
        add(path)
    tree(H); tree(W); tree(OLD)
    tree(R/'.work/experiments/old-compiler-published-retirement-supervisor-01')
    tree(R/'.work/old-compiler-published-retirement-launch-01')
    for name in ['old-compiler-published-retirement-independent-verification-01.json',
                 'root-e48-packet-review-01.json', 'verify_old_compiler_published_retirement_01.py',
                 'launch_old_compiler_published_before_bounded_01.py',
                 'root-old-compiler-copy-comparison-preflight-failure-01.json',
                 'root-old-compiler-copy-comparison-preflight-failure-02.json',
                 'compare_retired_compiler_copies_01.py', 'compare_retired_compiler_copies_02.py',
                 'compare_retired_compiler_copies_03.py']:
        add(R/'.work'/name)
    for suffix in ['json', 'stdout', 'stderr']:
        add(R/'.work'/('old-compiler-published-retirement-preparation-01.'+suffix))
    for name in ['old-compiler-published-retirement-source-review-01.json',
                 'old-compiler-published-retirement-verifier-source-review-01.json']:
        add(O/'.work'/name)
    qualifications = [
        (A/'experiments/ruff-strict-cache-retirement-01/controls-01', A/'.work/ruff-strict-cache-retirement-controls-01',
         A/'.work/experiments/ruff-strict-cache-retirement-controls-supervisor-01', A/'.work/ruff-strict-cache-retirement-controls-launch-01',
         O/'.work/ruff-strict-cache-retirement-controls-independent-verification-01.json', 12),
        (O/'experiments/old-compiler-directory-mode-controls-01', O/'.work/old-compiler-directory-mode-controls-01',
         O/'.work/experiments/old-compiler-directory-mode-controls-supervisor-01', O/'.work/old-compiler-directory-mode-controls-launch-01',
         O/'.work/old-compiler-directory-mode-controls-independent-verification-01.json', 10)]
    qualification_freezes = {}
    for control, work, outer, launch, audit_path, count in qualifications:
        tree(control); tree(work); tree(outer); add(audit_path)
        for suffix in ['actual.json', 'stdout', 'stderr']: add(Path(str(launch)+'.'+suffix))
        freeze = a.read(control/'inputs.json'); qualification_freezes[str(control/'inputs.json')] = freeze
        for name, row in freeze['files'].items():
            path = Path(name); state = path.lstat()
            assert [state.st_dev, state.st_ino, state.st_mode, state.st_size,
                    state.st_mtime_ns, state.st_ctime_ns, state.st_nlink] == row['stamp']
            assert a.sha(path) == row['sha256']; add(path)
        audit = a.read(audit_path)
        assert audit['status'] == 'verified' and audit['controls'] == count
        assert audit['receipt_sha256'] == a.sha(work/'receipt.json') and audit['inputs_sha256'] == a.sha(control/'inputs.json')
    for name in ['archive.py', 'prepare.py', 'README.md']: add(a.HERE/name)
    for name in ['experiments/stable-cgu/owned_stage.py', 'scripts/supervise_experiment.py']: add(R/name)

    terminal = a.read(W/'receipt.json')
    audit_path = R/'.work/old-compiler-published-retirement-independent-verification-01.json'
    assert a.sha(audit_path) == 'e2cf2714c7bc507556169b8458f1a35a53d0336812ca2949839a18894867c5fa'
    audit = a.read(audit_path)
    assert audit['status'] == 'verified' and audit['receipt_sha256'] == a.sha(W/'receipt.json')
    for key, name in [('deleted_ledger_sha256','deleted.jsonl'), ('mode_ledger_sha256','directory-modes.jsonl'),
                      ('transition_sha256','transition.json'), ('writable_inventory_sha256','writable-inventory.json')]:
        assert audit[key] == a.sha(W/name)
    assert audit['inputs_sha256'] == a.sha(H/'plan-01/inputs.json')
    assert terminal['status'] == 'passed' and len(terminal['children']) == 2
    assert not Path(old_plan['root']).exists() and not Path(old_plan['root']).is_symlink()
    inventory = a.read(W/'admitted-inventory.json')
    def events(path, expected_names, kinds):
        counts = Counter(); sets = {key:set() for key in kinds}
        with path.open() as ledger:
            for line in ledger:
                assert len(line) <= 16384
                row = json.loads(line); kind = row['event']; name = row['relative']
                assert kind in sets and name in expected_names and name not in sets[kind]
                sets[kind].add(name); counts[kind] += 1
        assert all(names == expected_names for names in sets.values())
        assert counts == Counter({key:len(expected_names) for key in kinds})
    assert len(inventory) == 8389
    events(W/'deleted.jsonl',set(inventory),['intent','unlinked','validated'])
    mode_names = {name for name,row in inventory.items() if name != '.' and row['kind'] == 'directory'}
    assert len(mode_names) == 1405
    events(W/'directory-modes.jsonl',mode_names,['intent','applied','validated'])
    assert a.sha(W/'preserved-ready.json') == a.sha(H/'plan-01/preserved-ready.json') == audit['unique_ready_sha256']
    assert audit['unique_ready_sha256'] == 'ff93b6ae55e28406d6c88d0c1bc680f46ecae7f14014f54b83e84a8b34edaeda'
    assert a.sha(OLD/'evidence.tar.xz') == '97898061418b8a1f9e078e26418c9f45f14e566773f33af34c0425718c93b908'
    checks = {str(W/'receipt.json'):dict(status='passed',chmod_calls=1405,changed_files=0,changed_root=False,actual_readonly_probes=2),
        str(audit_path):dict(status='verified',retired_entries=8389,retired_files=6983,retired_directories=1406,
            ledger_events=25167,mode_ledger_events=4215,all_durable_events_replayed=True,
            full_historical_archive_members=52,full_xz_eof=True,chmod_calls=1405),
        str(qualifications[0][1]/'receipt.json'):dict(status='passed',controls_passed=12),
        str(qualifications[1][1]/'receipt.json'):dict(status='passed',controls_passed=10)}
    for name, expected in checks.items():
        actual = a.read(Path(name)); assert all(actual[key] == value for key,value in expected.items())
    members = {name.lstrip('/'):dict(source=name,bytes=p.stat().st_size,sha256=a.sha(p)) for name,p in sorted(sources.items())}
    histories = {str(H/'plan-01/inputs.json'):dict(sha256=a.sha(H/'plan-01/inputs.json'),files=len(original['files']))}
    histories.update({name:dict(sha256=a.sha(Path(name)),files=len(value['files'])) for name,value in qualification_freezes.items()})
    plan = dict(owner=str(R),members=members,historical_source_substitutions={},historical_freezes=histories,
        receipt_checks=checks,environment=old_plan['environment'],
        platform_context=list(os.uname()),platform_identity=[v for i,v in enumerate(os.uname()) if i!=1],
        canonical_lock=str(a.owned.CANONICAL_LOCK),wait_seconds=600,minimum_free_gib=9,
        executor=dict(path='/opt/homebrew/bin/python3',resolved=str(Path('/opt/homebrew/bin/python3').resolve(strict=True)),
                      route_identity=a.identity(Path('/opt/homebrew/bin/python3'))),
        children=0,archive_limit_bytes=64*2**20,maximum_logical_bytes=384*2**20,
        member_count=len(members),logical_bytes=sum(row['bytes'] for row in members.values()),
        excluded_live_provider_files=len(omitted),excluded_live_provider_bytes=sum(row['identity']['size'] for row in omitted.values()),
        exclusion_meaning='Live provider payloads are excluded; complete original frozen catalogs and the closed independent audit retain their historical association. Closed consumer absence observations are not ongoing absence requirements.',
        scope='Closed e48 published-prefix retirement: all8389 paths/25167 durable deletion events, all1405 directory mode changes/4215 events, unique ready bytes, two actual probes, bounded dispatcher/outer/terminal/full audit, exact12+10 helper qualification, prior partial retirement and52-member original XZ history. No workload or deletion runs here.')
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
        'old-compiler-published-retirement-evidence-supervisor-01','--','/opt/homebrew/bin/python3','-B',
        str(a.HERE/'archive.py'),'--inputs-sha256',a.sha(a.HERE/'inputs.json')]
    write(a.HERE/'launch.json',dict(command=command,cwd=str(R),environment=plan['environment'],review_required_before_execution=True))
    print(json.dumps(dict(members=len(members),logical_bytes=plan['logical_bytes'],inputs=len(files),
        plan_sha256=a.sha(a.HERE/'plan.json'),freeze_sha256=a.sha(a.HERE/'inputs.json'),
        launch_sha256=a.sha(a.HERE/'launch.json')),indent=2))


if __name__ == '__main__': main()
