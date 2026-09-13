#!/usr/bin/env python3
"""Repair the observed WorkerLocal/Arena identity mismatch without weakening checks."""
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('arena_upgrade_diagnostic', ROOT / 'experiments/hir-diagnostic-native/check.py')
diagnostic = importlib.util.module_from_spec(spec); sys.modules[spec.name] = diagnostic; spec.loader.exec_module(diagnostic)
engine, native = diagnostic.engine, diagnostic.native
require, sha, ordinary = engine.require, engine.sha, native.ordinary
CHECKPOINT = '8416694357ee7ac8ff8b1d3c262b61e7e1f52ca8'
PATCH_SHA = '485194f2f9e995b6ad1ee2c39d66d05deb776df7b6e26b22085925c28edd6671'
SOURCE_IDENTITY = 'a6cf8a739f3c7a29707bacb4f12ecb575700f72bc41004260f99951f85ecf13b'
NEW_TEST = 'candidate_identity_uses_worker_arena_and_rejects_wrapper_or_foreign_arena'
DIAGNOSTIC_OWNER = Path('/Users/danluu/dev/rust-interp-hir-diagnostic-native-20260913')
DIAGNOSTIC_WORK = DIAGNOSTIC_OWNER / '.work/hir-diagnostic-native-01'
DIAGNOSTIC_PLAN = DIAGNOSTIC_OWNER / 'experiments/hir-diagnostic-native/planned-diagnostic-01.json'
DIAGNOSTIC_PLAN_SHA = 'c79fd53d4678690835b2e7db33c14306cd7e5cea500a491c9a13c1b90d728452'
TERMINAL = DIAGNOSTIC_WORK / 'stages/run-01/receipt.json'
ARCHIVE = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-diagnostic-native-01')
ARCHIVE_HASHES = dict(archive='a214fd05b8ebc18538d052cb5502c53f99580d21ff89e0308b02b864ea93c32c',
    manifest='450a915c17517dc82bedb5b318146c3944fae2ea5d512ad957c03dde1f669ff8',
    summary='f38c566e11c3234afac9fc31921b92ce1e09c31ae4eaa7e9e51a2143bc6dcf0e')


def diagnostic_reference():
    paths = {k: str(ARCHIVE / n) for k,n in
             [('archive', 'evidence.tar.gz'), ('manifest', 'manifest.json'), ('summary', 'summary.json')]}
    require(all(sha(ordinary(paths[k])) == h for k,h in ARCHIVE_HASHES.items()), 'fixed diagnostic archive changed')
    manifest = json.loads(Path(paths['manifest']).read_bytes())
    required = {row['source']: row['sha256'] for row in manifest.values()}
    require(len(required) == len(manifest) == 250, 'complete diagnostic archive membership required')
    def saved(path):
        path = ordinary(path)
        require(required.get(str(path)) == sha(path), 'diagnostic raw source association changed')
        return json.loads(path.read_bytes())
    plan = saved(DIAGNOSTIC_PLAN)
    require(required[str(DIAGNOSTIC_PLAN)] == DIAGNOSTIC_PLAN_SHA
            and plan['previous']['source']['revision'] == diagnostic.SOURCE_REVISION
            and plan['previous']['plan_sha256'] == diagnostic.UPGRADE_PLAN_SHA
            and plan['build'] == diagnostic.BUILD and plan['probes'] == diagnostic.PROBES
            and plan['compile_command'] == diagnostic.compile_command(DIAGNOSTIC_WORK / 'fixture')
            and plan['diagnostic_only'] and not plan['native_qualified'] and not plan['executed_native_binary'],
            'diagnostic compiler route or qualification boundary changed')
    run = saved(TERMINAL)
    require(run['status'] == 'diagnostic-completed' and run['source_revision'] == diagnostic.SOURCE_REVISION
            and run['expected_plan_sha256'] == DIAGNOSTIC_PLAN_SHA
            and run['compiler_returncode'] == 0 and run['bootstrap_commands_passed'] == 1
            and run['identity_probes_passed'] == 3 and run['direct_compiler_commands_passed'] == 1
            and run['diagnostic_only'] and not run['native_qualified'] and not run['executed_native_binary'],
            'diagnostic result must not become native hit qualification')
    observation_path = TERMINAL.parent / 'observations.json'
    observation = saved(observation_path)
    require(required[str(observation_path)] == run['observation_sha256']
            and observation == run['observation'] and observation['records'] == 24
            and observation['state_counts'] == {'rejected-body-tree-cold-audit': 24},
            'observed cold-audit failure changed')
    environment = plan['previous']['old_plan']['environment']
    require('RUSTC_FORCE_RUSTC_VERSION' not in environment, 'diagnostic compiler identity was overridden')
    for stage, count in [('plan', 5), ('run', 20)]:
        path = DIAGNOSTIC_WORK / 'stages' / (stage + '-01') / 'receipt.json'
        row = saved(path)
        require(row['owner'] == str(DIAGNOSTIC_OWNER) and row['stage'] == stage
                and row['status'] == ('passed' if stage == 'plan' else 'diagnostic-completed')
                and len(row['commands']) == count
                and row.get('plan_sha256' if stage == 'plan' else 'expected_plan_sha256') == DIAGNOSTIC_PLAN_SHA,
                'exact diagnostic stage history required')
        for ref in row['commands']:
            child_path = ordinary(ref['path']); child = saved(child_path)
            require(child_path.is_relative_to(path.parent / 'commands')
                    and required[str(child_path)] == ref['sha256']
                    and child['status'] == 'finished' and child['returncode'] == 0
                    and child['command'] == ref['command'] and child['environment'] == environment,
                    'diagnostic child or environment changed')
            for stream in ['stdout', 'stderr']:
                output = child_path.parent / stream
                require(required.get(str(output)) == child[stream + '_sha256'] == sha(ordinary(output)),
                        'diagnostic raw output changed')
        outer = DIAGNOSTIC_OWNER / '.work/experiments' / ('hir-diagnostic-native-' + stage + '-supervisor-01')
        status = saved(outer / 'status.json')
        require(status['status'] == 'finished' and status['returncode'] == 0
                and status['child_pid'] == row['pid'] and status['supervisor_pid'] == row['parent_pid']
                and required.get(str(outer / 'plan.json')) == status['plan_sha256']
                and required.get(str(outer / 'command.log')) == status['log_sha256'],
                'diagnostic supervisor binding changed')
    return dict(paths=paths, hashes={paths[k]:h for k,h in ARCHIVE_HASHES.items()}, required=required,
                status='completed diagnostic; all24 cold audits rejected; native reuse unqualified')


def references():
    ref = diagnostic_reference()
    plan = json.loads(DIAGNOSTIC_PLAN.read_bytes())
    older = plan['previous']['historical_archives']
    require([r['hashes'][r['paths']['archive']] for r in older] == diagnostic.ARCHIVE_CHAIN,
            'diagnostic predecessor archive lineage changed')
    return [ref, *older]


def inputs():
    names = ['origin.json', 'capture.patch', 'patch.json', 'checkpoint-README.md']
    require(sorted(p.name for p in (HERE / 'inputs').iterdir()) == sorted(names), 'unknown arena-fix input')
    paths = [Path(__file__), HERE / 'README.md', ROOT / 'tests/test_hir_arena_identity_upgrade.py',
             *(HERE / 'inputs' / n for n in names), *map(Path, diagnostic.inputs())]
    files = {str(ordinary(p)):sha(p) for p in paths}
    for ref in references():
        files.update(ref['hashes'])
    return files


def checkpoint():
    origins = json.loads((HERE / 'inputs/origin.json').read_bytes())
    require(set(origins) == {'capture.patch', 'patch.json', 'checkpoint-README.md'}
            and all(row['git_revision'] == CHECKPOINT and sha(HERE / 'inputs' / name) == row['sha256']
                    for name,row in origins.items()), 'arena-fix snapshot identity changed')
    manifest = json.loads((HERE / 'inputs/patch.json').read_bytes())
    require(sha(HERE / 'inputs/capture.patch') == manifest['patch_sha256'] == PATCH_SHA
            and manifest['source_identity'] == SOURCE_IDENTITY and manifest['base_commit'] == engine.old.BASE
            and len(manifest['files']) == 25 and manifest['actual_cache_hit_path'] is True
            and manifest['cached_body_materialization'] is True and manifest['reuse_default'] is False
            and manifest['grammar_widened'] is False and manifest['replay_verification'] == 'always-on-tree-journal-poststate',
            'wrong arena-identity compiler checkpoint')
    previous, old_names = diagnostic.upgrade.checkpoint()
    names = sorted(re.findall(r'^\+\s*#\[test\]\n\+\s*fn ([a-z0-9_]+)',
                             (HERE / 'inputs/capture.patch').read_text(), re.M))
    require(names == sorted([*old_names, NEW_TEST]) and len(names) == len(set(names)) == 27
            and set(manifest['files']) == set(previous['files']), 'all26 old and new worker-arena control required')
    changed = {name for name in manifest['files'] if manifest['files'][name] != previous['files'][name]}
    require(changed == {'compiler/rustc_ast_lowering/src/body_cache/mod.rs',
                        'compiler/rustc_ast_lowering/src/body_cache/source_identity.rs'},
            'arena repair changed an unreviewed implementation file')
    return manifest, names


def stage_checkpoint():
    result = checkpoint()
    for ref in references():
        p = ref['paths']
        engine.verify_archive(p['archive'], p['manifest'], p['summary'], ref['required'])
    return result


def previous(terminal):
    require(Path(terminal) == TERMINAL, 'actual completed cold-audit diagnostic required')
    refs = references()
    prior = diagnostic.history(diagnostic.UPGRADE_WORK / 'stages/unit-01/receipt.json')
    require(prior['source']['revision'] == diagnostic.SOURCE_REVISION, 'qualified phase-checkpoint source changed')
    require(refs[1:] == prior['historical_archives'], 'selected-check and diagnostic histories disagree')
    native.verify_references(prior)
    return dict(status='diagnostic-completed-no-hits', terminal=str(terminal), source=prior['source'],
        old_manifest=diagnostic.upgrade.checkpoint()[0], old_plan=prior['old_plan'], old_plan_path=prior['old_plan_path'],
        files=prior['files'], historical_source=prior['historical_source'],
        historical_archives=refs,
        selected_check_passed=True, unit_controls_passed=26, native_hit_qualified=False,
        predecessor_checkpoint=diagnostic.CHECKPOINT, predecessor_plan_sha256=diagnostic.UPGRADE_PLAN_SHA)


def context():
    return engine.UpgradeContext(ROOT, HERE, ROOT / '.work/hir-arena-identity-upgrade-01', CHECKPOINT,
        inputs, previous, stage_checkpoint, tuple(diagnostic.upgrade.checkpoint()[1]), diagnostic.CURRENT_ARCHIVE_SHA)


if __name__ == '__main__':
    engine.execute(engine.arguments(__doc__), context=context())
