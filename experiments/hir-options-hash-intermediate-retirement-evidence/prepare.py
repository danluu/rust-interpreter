"""Freeze the closed failed/fixture/successful retirement histories; no archive run."""
import ast
import json
import os
from pathlib import Path
import sys

import archive as a

H = a.OWNER / 'experiments/hir-options-hash-intermediate-retirement'
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')


def write(path, value):
    with path.open('x') as output:
        json.dump(value, output, sort_keys=True, indent=2); output.write('\n')


def main():
    assert Path.cwd() == a.OWNER and sys.dont_write_bytecode and not sys.flags.optimize
    for path in [a.HERE/'plan.json', a.HERE/'inputs.json', a.HERE/'launch.json', a.WORK, a.RESULT]:
        assert not path.exists() and not path.is_symlink()
    sources = {}; historical_freezes = {}; historical = {}
    for relative in ['plan-01/inputs.json', 'controls-01/inputs.json', 'plan-02/inputs.json']:
        path = H/relative; frozen = a.read(path)['files']
        historical_freezes[str(path)] = dict(sha256=a.sha(path), files=len(frozen))
        for name, row in frozen.items():
            assert name not in historical or historical[name]['sha256'] == row['sha256']
            historical[name] = row
    assert len(historical) == 177
    preserved = a.read(H/'preserved-consumer-03/manifest.json')['files']
    substitutions = {}
    for name, row in historical.items():
        source = Path(name)
        if source == X/'experiments/hir-options-hash/compiler-build-continuation-03/prepare.py':
            proof = preserved[name]; source = Path(proof['retained_path'])
            assert a.sha(source) == row['sha256'] == proof['sha256']
            substitutions[name] = dict(source=str(source), sha256=row['sha256'],
                reason='Exact old frozen preparer retained before later separately reviewed transition binding.')
        assert source.resolve(strict=True) == source and source.is_file() and a.sha(source) == row['sha256']
        sources[name] = source

    def add(path):
        assert path.resolve(strict=True) == path and path.is_file() and not path.is_symlink()
        assert path.stat().st_size <= 96 * 2**20
        assert str(path) not in sources or sources[str(path)] == path
        sources[str(path)] = path

    def tree(root):
        assert root.resolve(strict=True) == root and root.is_dir()
        for path in sorted(root.rglob('*')):
            assert not path.is_symlink()
            if path.is_file():
                add(path)
            else:
                assert path.is_dir()
            assert len(sources) <= 384

    tree(H)
    for stem in ['hir-options-hash-intermediate-retirement-01',
                 'hir-options-hash-intermediate-retirement-controls-01',
                 'hir-options-hash-intermediate-retirement-02']:
        tree(a.OWNER/'.work'/stem)
    for stem in ['hir-options-hash-intermediate-retirement-supervisor-01',
                 'hir-options-hash-intermediate-retirement-controls-supervisor-01',
                 'hir-options-hash-intermediate-retirement-supervisor-02']:
        tree(a.OWNER/'.work/experiments'/stem)
    for stem in ['hir-options-hash-intermediate-retirement-launch-01',
                 'hir-options-hash-intermediate-retirement-controls-launch-01',
                 'hir-options-hash-intermediate-retirement-launch-02']:
        for suffix in ['actual.json', 'stdout', 'stderr']:
            add(a.OWNER/'.work'/(stem+'.'+suffix))
    for name in ['hir-options-hash-intermediate-retirement-failure-verification-01.json',
                 'hir-options-hash-intermediate-retirement-partial-inventory-01.json',
                 'hir-options-hash-intermediate-retirement-controls-verification-01.json',
                 'hir-options-hash-intermediate-retirement-verification-02.json',
                 'verify_intermediate_retirement_failure_01.py', 'verify_intermediate_retirement_controls_01.py',
                 'verify_intermediate_retirement_02.py', 'launch_intermediate_retirement_01.py',
                 'launch_intermediate_retirement_controls_01.py', 'launch_intermediate_retirement_02.py',
                 'assess_intermediate_association_02.py', 'assess_intermediate_content_01.py']:
        add(a.OWNER/'.work'/name)
    for index in ['01', '02']:
        add(ROOT/'.work'/('root-intermediate-retirement-plan-verification-'+index+'.json'))
        add(X/'.work'/('hir-options-hash-intermediate-retirement-source-review-'+index+'.json'))
    for name in ['archive.py', 'prepare.py', 'README.md']:
        add(a.HERE/name)
    for name in ['experiments/stable-cgu/owned_stage.py', 'scripts/supervise_experiment.py']:
        add(a.OWNER/name)

    members = {name.lstrip('/'): dict(source=str(source), bytes=source.stat().st_size, sha256=a.sha(source))
               for name, source in sorted(sources.items())}
    checks = {
        str(a.OWNER/'.work/hir-options-hash-intermediate-retirement-01/receipt.json'):
            dict(status='failed', error="RuntimeError('directory identity changed during unlink')"),
        str(a.OWNER/'.work/hir-options-hash-intermediate-retirement-controls-01/receipt.json'):
            dict(status='passed', controls_passed=6),
        str(a.OWNER/'.work/hir-options-hash-intermediate-retirement-02/receipt.json'):
            dict(status='passed', retired_files=4645, combined_retired_files=4646, prior_partial_retired_files=1,
                 removed_directories=0, protected_providers_unchanged=True, uncertain_unlink_intents=[]),
        str(a.OWNER/'.work/hir-options-hash-intermediate-retirement-verification-02.json'):
            dict(status='verified', ledger_rows=13935, combined_retired_files=4646, successor_retired_files=4645,
                 all_protected_bytes_and_identities_unchanged=True,
                 all_remaining_membership_bytes_and_identities_match_ledger=True),
    }
    for name, expected in checks.items():
        actual = a.read(Path(name)); assert all(actual[key] == value for key, value in expected.items())
    environment = a.read(H/'plan-02/plan.json')['environment']
    plan = dict(owner=str(a.OWNER), members=members, historical_source_substitutions=substitutions,
        historical_freezes=historical_freezes, receipt_checks=checks, environment=environment,
        platform_context=list(os.uname()), platform_identity=[value for i,value in enumerate(os.uname()) if i != 1],
        canonical_lock=str(a.owned.CANONICAL_LOCK), wait_seconds=600, minimum_free_gib=9,
        executor=dict(path='/opt/homebrew/bin/python3', resolved=str(Path('/opt/homebrew/bin/python3').resolve(strict=True)),
                      route_identity=a.identity(Path('/opt/homebrew/bin/python3'))),
        children=0, archive_limit_bytes=64*2**20, maximum_logical_bytes=384*2**20,
        member_count=len(members), logical_bytes=sum(row['bytes'] for row in members.values()),
        scope='Completed first one-file partial failure, six fixture controls, and remaining4645 retirement. '
              'Full historical source/evidence, all13935 durable events and before/partial/remaining/protected proofs. '
              'Old snapshots and incomplete check stamps remain historical; removed compiler intermediates are '
              'represented by content hashes and actual source/tool/command provenance, without a byte-identical '
              'rebuild promise. No further cleanup, compiler, recipe or process-probe execution.')
    assert plan['member_count'] <= 384 and plan['logical_bytes'] < plan['maximum_logical_bytes']
    write(a.HERE/'plan.json', plan)
    files = set(sources.values()) | {a.HERE/'plan.json', Path(sys.executable).resolve(strict=True)}
    frozen = {}
    for path in sorted(files):
        assert path.resolve(strict=True) == path and path.is_file()
        before = a.identity(path); digest = a.sha(path); assert a.identity(path) == before
        frozen[str(path)] = dict(identity=before, sha256=digest)
        if path.suffix == '.py':
            ast.parse(path.read_bytes(), filename=str(path))
    write(a.HERE/'inputs.json', dict(files=frozen))
    command = ['/opt/homebrew/bin/python3', '-B', str(a.OWNER/'scripts/supervise_experiment.py'), '--run-id',
        'hir-options-hash-intermediate-retirement-evidence-supervisor-01', '--', '/opt/homebrew/bin/python3', '-B',
        str(a.HERE/'archive.py'), '--inputs-sha256', a.sha(a.HERE/'inputs.json')]
    write(a.HERE/'launch.json', dict(command=command, cwd=str(a.OWNER), environment=environment,
                                    review_required_before_execution=True))
    print(json.dumps(dict(members=len(members), logical_bytes=plan['logical_bytes'], inputs=len(files),
        plan_sha256=a.sha(a.HERE/'plan.json'), freeze_sha256=a.sha(a.HERE/'inputs.json'),
        launch_sha256=a.sha(a.HERE/'launch.json')), indent=2))


if __name__ == '__main__':
    main()
