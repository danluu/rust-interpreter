#!/usr/bin/env python3
"""In-place fixture-environment repair and rejection-phase diagnostic continuation.

This checkpoint diagnoses the rejected capture path; it does not claim a hit fix.
Compiler mutation requires a separately reviewed plan and explicit stage command.
"""
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
NATIVE = ROOT / 'experiments/hir-native-correctness/check.py'
spec = importlib.util.spec_from_file_location('fixture_env_native_history', NATIVE)
native = importlib.util.module_from_spec(spec); sys.modules[spec.name] = native; spec.loader.exec_module(native)
engine = native.engine
require, sha = engine.require, engine.sha
CHECKPOINT = '3b34821e313fc9ea68917897648c9322c4cca067'
PATCH_SHA = '211425be515befb15594afaf9a1e5338569e605bb5cc92d5d71f66fd5c1f6ed2'
SOURCE_IDENTITY = '1cffd7526fd7d5415407a8d8ec333f1eae5dc06239189f0121bc6455759fceaf'
PREVIOUS_REVISION = '3d7ad8282c5695196f4a4dcfd0bdceacac3f79b9'
PREVIOUS_PARENT = '9d21c2bae5edcfd6cae6e96f38731a740b7acc9e'
PREVIOUS_PLAN_SHA = 'f2aa7f68beaa755280a6268da0c26c978bad69dddd5129ea74ddc6366a4fc747'
PREVIOUS_SOURCE_SHA = 'e0e4aa5e7cccaa4e1833750eaa942901b888d8047de25e9d593b97101b7730d2'
PREVIOUS_ARCHIVE_SHA = '6c390653214092e920b6b3fb9e3b3e33ebf41521870170f7a0fff515511b5b14'
PRIMARY = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
FAILURE = PRIMARY / 'results/hir-native-correctness-failed-01'
FAILURE_HASHES = dict(archive='a5a6e0e5b2c49603baa0c4d6d2e51b40f57279ab5f4f4f82d75cad0240d3e58b',
    manifest='2030b23dc04344ebfc2b42fd39074cb90e48e010ac4d12c108a43fed62ae9b68',
    summary='a49fe2ac227ca04f8430e6e87e32648e7da2f6fc11208572bcae2b552906dfec')
FAILED_OWNER = Path('/Users/danluu/dev/rust-interp-hir-native-correctness-20260913')
FAILED_TERMINAL = FAILED_OWNER / '.work/hir-native-correctness-01/stages/native-01/receipt.json'
FAILED_PLAN = FAILED_OWNER / 'experiments/hir-native-correctness/planned-native-01.json'
FAILED_PLAN_SHA = '27977dafa0f59c7f9ee891b2e27ad3e75acfb8606411dd4ef2f0104e2e6cab81'


def failure_paths():
    return {key: str(FAILURE / name) for key, name in
            [('archive', 'evidence.tar.gz'), ('manifest', 'manifest.json'), ('summary', 'summary.json')]}


def failed_native_reference(summary, manifest):
    """Archive authority survives deliberate repairs to the old live harness."""
    require(summary['owner'] == str(FAILED_OWNER) and summary['driver_revision'] ==
            '8b83ddd79b1e5cd7c185b33d8bfc88466da90b1f' and summary['source_revision'] == PREVIOUS_REVISION
            and summary['parent_revision'] == PREVIOUS_PARENT and summary['checkpoint'] == native.CHECKPOINT
            and summary['plan'] == dict(path=str(FAILED_PLAN), sha256=FAILED_PLAN_SHA)
            and summary['archive']['sha256'] == FAILURE_HASHES['archive'] and summary['archive']['members'] == 203
            and len(manifest) == 203 and summary['capture_report_lines'] == summary['verified_cache_hit_lines'] == 0
            and summary['native_hit_qualified'] is False and summary['performance_claim'] is False,
            'failed native archive must preserve the actual same-source failure')
    require([(r['stage'], r['status'], r['commands']) for r in summary['stages']] ==
            [('plan', 'passed', 5), ('run', 'failed', 21)] and summary['stages'][1]['path'] == str(FAILED_TERMINAL)
            and summary['total_original_commands'] == 26 and summary['bootstrap_build_passed'] is True
            and summary['identity_probes_passed'] == 3 and summary['option_test']['passed'] == 1
            and summary['native_runmake']['passed'] == 0 and summary['native_runmake']['failed'] == 1,
            'partial native success must not become hit qualification')
    guard = summary['source_postguard']
    require(guard['status'] == 'passed' and guard['revision'] == PREVIOUS_REVISION and guard['parent'] == PREVIOUS_PARENT
            and guard['source_files'] == 62708 and guard['backtrace_files'] == 102
            and guard['all_tracked_content_verified_twice'] and guard['independent_postfailure_check']
            and guard['configuration_and_absences_verified'] and guard['original_and_copied_seed_archives_verified']
            and guard['source_mutations'] == 0, 'independent postfailure source proof required')
    required = {item['source']: item['sha256'] for item in manifest.values()}
    require(required.get(str(FAILED_PLAN)) == FAILED_PLAN_SHA
            and required.get(str(FAILED_TERMINAL)) == summary['stages'][1]['sha256']
            and required.get(str(native.READY_WORK / 'source.json')) == PREVIOUS_SOURCE_SHA
            and len(required) == len(manifest), 'native archive critical source/terminal binding changed')
    for name, row in native.checkpoint()[0]['files'].items():
        require(required.get(str(engine.SOURCE / name)) == row['after_sha256'],
                'failed native archive lacks original exact patched bytes')
    for ref in [summary['postfailure_stage1_artifacts'], summary['fixture_inventory']]:
        require(required.get(ref['path']) == ref['sha256'], 'postfailure artifact inventory missing')
    paths = failure_paths()
    return dict(paths=paths, hashes={paths[k]: h for k, h in FAILURE_HASHES.items()}, required=required,
                status='failed native run; selected compiler check and26 units passed separately')


def read_failure():
    paths = failure_paths()
    require(all(sha(native.ordinary(paths[k])) == h for k, h in FAILURE_HASHES.items()), 'fixed native failure archive changed')
    return failed_native_reference(json.loads(Path(paths['summary']).read_bytes()),
                                   json.loads(Path(paths['manifest']).read_bytes()))


def ready_history():
    prior = native.history(PREVIOUS_PLAN_SHA, native.READY_WORK / 'stages/unit-01/receipt.json')
    require(prior['source']['revision'] == PREVIOUS_REVISION and prior['source']['parent'] == PREVIOUS_PARENT
            and sha(native.READY_WORK / 'source.json') == PREVIOUS_SOURCE_SHA, 'actual ReadyHit source identity changed')
    return prior


def references():
    # The failed native archive also identifies the full prior324/314/318 chain;
    # the324 archive is supplied separately as this upgrade's immediate archive.
    failure = read_failure()
    summary = json.loads(Path(failure['paths']['summary']).read_bytes())
    old_refs = summary['historical_archives']
    require(len(old_refs) == 3 and old_refs[0]['hashes'][old_refs[0]['paths']['archive']] == PREVIOUS_ARCHIVE_SHA
            and old_refs[1]['hashes'][old_refs[1]['paths']['archive']] == native.COLD_ARCHIVE_SHA
            and old_refs[2]['hashes'][old_refs[2]['paths']['archive']] == native.FAILED_ARCHIVE_SHA,
            'original324/314/318 archive lineage changed')
    return [failure, *[dict(paths=r['paths'], hashes=r['hashes'], required=r['required']) for r in old_refs[1:]]]


def inputs():
    names = ['origin.json', 'capture.patch', 'patch.json', 'checkpoint-README.md']
    require(sorted(p.name for p in (HERE / 'inputs').iterdir()) == sorted(names), 'unknown fixture repair input')
    paths = [Path(__file__), HERE / 'README.md', ROOT / 'tests/test_hir_fixture_env_upgrade.py',
             *(HERE / 'inputs' / n for n in names), *map(Path, native.inputs())]
    files = {str(native.ordinary(p)): sha(p) for p in paths}
    # Archive bytes, not deliberately superseded old live parser files, bind
    # failed-native history before every child through unchanged engine.guard.
    for ref in references():
        files.update(ref['hashes'])
    require(all(sha(p) == h for p, h in files.items()), 'frozen fixture repair input changed')
    return files


def checkpoint():
    origins = json.loads((HERE / 'inputs/origin.json').read_text())
    require(set(origins) == {'capture.patch', 'patch.json', 'checkpoint-README.md'}
            and all(row['git_revision'] == CHECKPOINT and sha(HERE / 'inputs' / name) == row['sha256']
                    for name, row in origins.items()), 'fixture repair snapshot changed')
    manifest = json.loads((HERE / 'inputs/patch.json').read_text())
    require(sha(HERE / 'inputs/capture.patch') == manifest['patch_sha256'] == PATCH_SHA
            and manifest['source_identity'] == SOURCE_IDENTITY and manifest['base_commit'] == engine.old.BASE
            and len(manifest['files']) == 25 and manifest['actual_cache_hit_path'] is True
            and manifest['cached_body_materialization'] is True and manifest['reuse_default'] is False
            and manifest['grammar_widened'] is False and manifest['replay_verification'] == 'always-on-tree-journal-poststate',
            'wrong fixture-environment checkpoint')
    previous, names = native.checkpoint()
    new_names = sorted(re.findall(r'^\+\s*#\[test\]\n\+\s*fn ([a-z0-9_]+)',
                                             (HERE / 'inputs/capture.patch').read_text(), re.M))
    require(new_names == names and len(new_names) == 26 and set(manifest['files']) == set(previous['files']),
            'fixture repair must preserve all26 units and the25-file patch domain')
    changed = {name for name in manifest['files'] if manifest['files'][name] != previous['files'][name]}
    require(changed == {'tests/run-make/hir-body-cache-capture/rmake.rs',
                        'compiler/rustc_ast_lowering/src/body_cache/source_identity.rs',
                        'compiler/rustc_ast_lowering/src/body_cache/mod.rs'},
            'fixture/phase snapshot changed an unreviewed compiler implementation file')
    return manifest, new_names


def stage_checkpoint():
    value = checkpoint()
    for ref in references():
        p = ref['paths']; engine.verify_archive(p['archive'], p['manifest'], p['summary'], ref['required'])
    return value


def previous(terminal_path):
    require(Path(terminal_path) == FAILED_TERMINAL, 'exact failed native terminal required')
    failure = read_failure()
    require(sha(native.ordinary(terminal_path)) == failure['required'][str(FAILED_TERMINAL)], 'native terminal changed')
    prior = ready_history()
    manifest, names = native.checkpoint()
    return dict(status='failed-native', terminal=str(terminal_path), source=prior['source'], old_manifest=manifest,
        old_plan=prior['old_plan'], old_plan_path=prior['old_plan_path'], files=prior['files'],
        historical_source=prior['historical_source'], historical_archives=[failure, *prior['historical_archives']],
        selected_check_passed=True, unit_controls_passed=26, native_hit_qualified=False,
        predecessor_checkpoint=native.CHECKPOINT, predecessor_plan_sha256=PREVIOUS_PLAN_SHA)


def context():
    return engine.UpgradeContext(ROOT, HERE, ROOT / '.work/hir-fixture-env-upgrade-01', CHECKPOINT,
        inputs, previous, stage_checkpoint, tuple(native.checkpoint()[1]), PREVIOUS_ARCHIVE_SHA)


def main():
    engine.execute(engine.arguments(__doc__), context=context())

if __name__ == '__main__': main()
