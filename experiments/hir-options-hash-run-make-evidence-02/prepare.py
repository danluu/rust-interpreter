"""Freeze already completed run-make source and evidence; no workload runs."""
import ast
import json
import os
from pathlib import Path
import sys

import archive as a

H = a.OWNER/'experiments/hir-options-hash-run-make-stage-02'
W = a.OWNER/'.work/hir-options-hash-run-make-01'
OUT = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01/run-make-01')


def write(path, value):
    with path.open('x') as output:
        json.dump(value, output, sort_keys=True, indent=2); output.write('\n')


def main():
    assert Path.cwd() == a.OWNER and sys.dont_write_bytecode and not sys.flags.optimize
    for path in [a.HERE/'plan.json', a.HERE/'inputs.json', a.HERE/'launch.json', a.WORK, a.RESULT]:
        assert not path.exists() and not path.is_symlink()
    sources = {}

    def add(path):
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

    old = a.read(H/'inputs.json')
    assert a.sha(H/'inputs.json') == '7ce058286d7531751b436b4855fb819e961a034b69d197e0c9b1468829f8973c'
    assert a.sha(H/'plan.json') == old['plan_sha256']
    for name, row in old['files'].items():
        path = Path(name); info = path.lstat()
        stamp = [info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink]
        assert stamp == row['stamp'] and a.sha(path) == row['sha256'], name
        add(path)
    assert len(old['files']) == 166
    tree(a.OWNER/'experiments/hir-options-hash-run-make-evidence-01')
    tree(H); tree(W); tree(a.OWNER/'.work/experiments/hir-options-hash-run-make-supervisor-01')
    output_inventory = a.read(W/'final-output-inventory.json')
    observed = {str(path.relative_to(OUT)) for path in OUT.rglob('*')}
    assert observed == set(output_inventory)
    for name, row in output_inventory.items():
        path = OUT/name
        assert path.resolve(strict=True) == path and not path.is_symlink()
        if row['kind'] == 'directory': assert path.is_dir()
        else:
            assert row['kind'] == 'file'
            info = path.lstat()
            assert [info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink] == row['stamp']
            assert a.sha(path) == row['sha256']
            add(path)
    for stem in ['hir-options-hash-run-make-launch-01', 'run-make-stage-02-discovery-01']:
        for suffix in ['actual.json', 'stdout', 'stderr']:
            add(a.OWNER/'.work'/(stem+'.'+suffix))
    for name in ['run-make-stage-02-discovery-01.source.json', 'run-make-stage-02-discovery-verification-01.json',
                 'hir-options-hash-run-make-independent-verification-01.json', 'verify_run_make_stage_02.py',
                 'prepare_run_make_stage_02_once.py', 'launch_run_make_stage_02_once.py',
                 'watch_run_make_capacity_01.py', 'run-make-capacity-wait-01.json']:
        add(a.OWNER/'.work'/name)
    for name in ['archive.py', 'prepare.py', 'README.md']: add(a.HERE/name)
    for name in ['experiments/stable-cgu/owned_stage.py', 'scripts/supervise_experiment.py']: add(a.OWNER/name)
    members = {name.lstrip('/'): dict(source=name, bytes=path.stat().st_size, sha256=a.sha(path))
               for name, path in sorted(sources.items())}
    checks = {
        str(W/'receipt.json'): dict(status='passed', recipe_compilations=1, recipe_executions=1,
                                   nested_commands=230, native_recipe_qualified=True,
                                   performance_measurement=False, application_qualified=False, hash_driver_qualified=False),
        str(W/'result.json'): dict(status='passed', compiler_commands=144, native_runs=86,
                                  expected_compiler_failures=39, recipe_compilations=1, recipe_executions=1),
        str(a.OWNER/'.work/hir-options-hash-run-make-independent-verification-01.json'):
            dict(status='verified', children=2, nested_commands=230, compiler_commands=144,
                 native_runs=86, expected_compiler_failures=39, source_restored=True,
                 loader_closures_recomputed=True, all_raw_and_proof_hashes_verified=True),
    }
    for name, expected in checks.items():
        actual = a.read(Path(name)); assert all(actual[key] == value for key, value in expected.items())
    environment = old['environment']
    plan = dict(owner=str(a.OWNER), members=members, historical_source_substitutions={},
        historical_freezes={str(H/'inputs.json'): dict(sha256=a.sha(H/'inputs.json'), files=166)},
        receipt_checks=checks, environment=environment,
        platform_context=list(os.uname()), platform_identity=[v for i,v in enumerate(os.uname()) if i != 1],
        canonical_lock=str(a.owned.CANONICAL_LOCK), wait_seconds=600, minimum_free_gib=9,
        executor=dict(path='/opt/homebrew/bin/python3', resolved=str(Path('/opt/homebrew/bin/python3').resolve(strict=True)),
                      route_identity=a.identity(Path('/opt/homebrew/bin/python3'))),
        children=0, archive_limit_bytes=64*2**20, maximum_logical_bytes=384*2**20,
        member_count=len(members), logical_bytes=sum(row['bytes'] for row in members.values()),
        output_inventory=dict(path=str(W/'final-output-inventory.json'), sha256=a.sha(W/'final-output-inventory.json'),
                              entries=len(output_inventory), files=sum(v['kind']=='file' for v in output_inventory.values())),
        scope='Exactly one D2 recipe compile and one unchanged E2 recipe execution; all 230 nested blocks '
              '(144 compiler, 86 native, 39 expected compiler failures), complete final outputs, raw streams, '
              'loader proofs, retained inputs and all 166 frozen source/proof files. Compiler prerequisite '
              'retains 25 successful logical and 26 actual commands across three owners, including the '
              'failed support attempt and unavailable historical cwd observations. Admission wait/discovery '
              'and actual independent audit are preserved. Provider binaries remain referenced by exact '
              'catalogs; no compiler, recipe, probe, cleanup or performance measurement runs here.')
    assert plan['member_count'] <= 1536 and plan['logical_bytes'] < plan['maximum_logical_bytes']
    write(a.HERE/'plan.json', plan)
    files = set(sources.values()) | {a.HERE/'plan.json', Path(sys.executable).resolve(strict=True)}
    frozen = {}
    for path in sorted(files):
        assert path.resolve(strict=True) == path and path.is_file()
        before = a.identity(path); digest = a.sha(path); assert a.identity(path) == before
        frozen[str(path)] = dict(identity=before, sha256=digest)
        if path.suffix == '.py': ast.parse(path.read_bytes(), filename=str(path))
    write(a.HERE/'inputs.json', dict(files=frozen))
    command = ['/opt/homebrew/bin/python3', '-B', str(a.OWNER/'scripts/supervise_experiment.py'), '--run-id',
        'run-make-qualification-retention-supervisor-01', '--', '/opt/homebrew/bin/python3', '-B',
        str(a.HERE/'archive.py'), '--inputs-sha256', a.sha(a.HERE/'inputs.json')]
    write(a.HERE/'launch.json', dict(command=command, cwd=str(a.OWNER), environment=environment,
                                   review_required_before_execution=True))
    print(json.dumps(dict(members=len(members), logical_bytes=plan['logical_bytes'], inputs=len(files),
        plan_sha256=a.sha(a.HERE/'plan.json'), freeze_sha256=a.sha(a.HERE/'inputs.json'),
        launch_sha256=a.sha(a.HERE/'launch.json')), indent=2))


if __name__ == '__main__': main()
