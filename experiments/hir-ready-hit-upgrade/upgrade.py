#!/usr/bin/env python3
"""Reviewed in-place 60d cold-audit to exclusive ReadyHit compiler continuation."""
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PREVIOUS_ROOT = Path('/Users/danluu/dev/rust-interp-hir-cold-audit-upgrade-20260913')
PREVIOUS_WORK = PREVIOUS_ROOT / '.work/hir-cold-audit-upgrade-01'
PREVIOUS_PLAN = PREVIOUS_ROOT / 'experiments/hir-cold-audit-upgrade/planned-upgrade-01.json'
PREVIOUS_PLAN_SHA = '04e5e73dc76f20a0b7e809fe5d4d38e9f5d35b9fbecc635e3d328bc4090934a2'
PREVIOUS_SOURCE_SHA = '54930b3f022397235f8606b346fcdd372b0b678307e04ddfdb864d74fafe8b6d'
PREVIOUS_REVISION = '9d21c2bae5edcfd6cae6e96f38731a740b7acc9e'
PREVIOUS_PARENT = '3c40bed885cee37e422be334d0e1b9403225f833'
PREVIOUS_CHECKPOINT = '60d5be4532b260f2aea03226f463dccc83391266'
PREVIOUS_ARCHIVE_SHA = '55061f25443157ef7ea125a1cad8920ce18d895f9c6f9a99d480df804b188f73'
REFERENCED_ARCHIVE = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-upgrade-check-failed-01')
REFERENCED_HASHES = {
    'archive': '53a8fa2fab9504a8dbef7a44fbe26bf094a254bf8443f0cda43c9fe35eacaf54',
    'manifest': '996f38f6bc8e50824f3c56924d08e8b54164537a4b80cd4674a7f49c5ad5cfad',
    'summary': 'f6a2271f8fece3fc199a4b64fb8fb5f2807554a9ec4472c7a825b1b9ca945b14',
}
CHECKPOINT = '5cd6acd3f50912cec5fb29375b130afa70506703'
PATCH_SHA = 'cca094ebc73f6cc7da9ea1660669a436a6900e5d9c307550435dbcd8784410f4'
SOURCE_IDENTITY = '50ecfb157fd227791b2dbb196c6c795d8c999a37017fed3be938c672a8a85818'
COLD = ROOT / 'experiments/hir-cold-audit-upgrade/upgrade.py'
spec = importlib.util.spec_from_file_location('ready_hit_cold_predecessor', COLD)
cold = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cold
spec.loader.exec_module(cold)
engine = cold.engine
require, sha = engine.require, engine.sha


def previous_tests():
    manifest, names = cold.checkpoint()
    require(len(names) == 22 and manifest['actual_cache_hit_path'] is False
            and manifest['cold_materialization_audit'] is True, 'all twenty-two cold controls required')
    return names


def inputs():
    names = ['origin.json', 'capture.patch', 'patch.json', 'checkpoint-README.md']
    require(sorted(p.name for p in (HERE / 'inputs').iterdir()) == sorted(names), 'unknown ReadyHit input')
    paths = [Path(__file__), HERE / 'README.md', ROOT / 'tests/test_hir_ready_hit_upgrade.py',
             *(HERE / 'inputs' / name for name in names), *map(Path, cold.inputs())]
    require(all(p.is_file() and not p.is_symlink() and p.resolve(strict=True) == p for p in paths),
            'invalid frozen ReadyHit source')
    return {str(p): sha(p) for p in sorted(set(paths))}


def checkpoint():
    origins = json.loads((HERE / 'inputs/origin.json').read_text())
    require(set(origins) == {'capture.patch', 'patch.json', 'checkpoint-README.md'}
            and all(row['git_revision'] == CHECKPOINT
                    and sha(HERE / 'inputs' / name) == row['sha256']
                    for name, row in origins.items()), 'ReadyHit checkpoint source changed')
    manifest = json.loads((HERE / 'inputs/patch.json').read_text())
    patch = HERE / 'inputs/capture.patch'
    require(manifest['base_commit'] == engine.old.BASE and len(manifest['files']) == 25
            and sha(patch) == manifest['patch_sha256'] == PATCH_SHA
            and manifest['source_identity'] == SOURCE_IDENTITY
            and manifest['actual_cache_hit_path'] is True
            and manifest['cached_body_materialization'] is True
            and manifest['cold_materialization_audit'] is True
            and manifest['reuse_default'] is False and manifest['grammar_widened'] is False
            and manifest['replay_verification'] == 'always-on-tree-journal-poststate',
            'successor is not the reviewed exclusive ReadyHit checkpoint')
    names = cold.named_tests(patch)
    require(len(names) == 26 and set(previous_tests()) <= set(names), 'all twenty-six controls required')
    for name in manifest['files']:
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'invalid ReadyHit patch path')
    return manifest, names


def predecessor_plan():
    require(sha(PREVIOUS_PLAN) == PREVIOUS_PLAN_SHA, 'cold-audit plan changed')
    return json.loads(PREVIOUS_PLAN.read_text())


def historical_reference(plan):
    paths = {key: str(REFERENCED_ARCHIVE / name) for key, name in
             [('archive', 'evidence.tar.gz'), ('manifest', 'manifest.json'), ('summary', 'summary.json')]}
    hashes = {paths[key]: expected for key, expected in REFERENCED_HASHES.items()}
    require(plan['archive_paths'] == paths and plan['archive_hashes'] == hashes
            and plan['archive_required'], 'cold history must retain its exact failed-predecessor archive')
    return dict(paths=paths, hashes=hashes, required=plan['archive_required'])


def stage_checkpoint():
    """Called by the unchanged engine only after canonical stage admission."""
    result = checkpoint()
    reference = historical_reference(predecessor_plan())
    require(all(sha(path) == expected for path, expected in reference['hashes'].items()),
            'referenced failed-history archive changed')
    # The immediate 314-member cold archive references the prior 318-member
    # payload. Recheck that exact payload and its required members separately;
    # do not pretend the old members are embedded in the new archive.
    paths = reference['paths']
    engine.verify_archive(paths['archive'], paths['manifest'], paths['summary'], reference['required'])
    return result


def predecessor_state(plan, source, completed, terminal):
    require(plan['owner'] == str(PREVIOUS_ROOT) and plan['checkpoint'] == PREVIOUS_CHECKPOINT
            and plan['commands'] == engine.old.COMMANDS
            and source['revision'] == PREVIOUS_REVISION and source['parent'] == PREVIOUS_PARENT
            and source['plan_sha256'] == PREVIOUS_PLAN_SHA,
            'wrong cold predecessor source or command identity')
    require(terminal['owner'] == str(PREVIOUS_ROOT)
            and terminal.get('plan_sha256', terminal.get('expected_plan_sha256')) == PREVIOUS_PLAN_SHA
            and terminal['stage'] == 'unit' and terminal['status'] == 'passed'
            and set(completed) == {'apply', 'check', 'unit'},
            'ReadyHit continuation requires the actual passing cold check and all units')
    return 'passed'


def previous(terminal_path):
    terminal_path = Path(terminal_path).resolve(strict=True)
    require(terminal_path == PREVIOUS_WORK / 'stages/unit-01/receipt.json',
            'terminal is not the completed cold unit receipt')
    require(sha(PREVIOUS_WORK / 'source.json') == PREVIOUS_SOURCE_SHA, 'cold source receipt changed')
    plan = predecessor_plan()
    source = json.loads((PREVIOUS_WORK / 'source.json').read_text())
    completed = json.loads((PREVIOUS_WORK / 'completed.json').read_text())
    terminal = json.loads(terminal_path.read_text())
    status = predecessor_state(plan, source, completed, terminal)
    require(sorted([*plan['old_tests'], *plan['added_tests']]) == previous_tests(),
            'cold predecessor control set changed')
    files = {PREVIOUS_PLAN, PREVIOUS_WORK / 'source.json', PREVIOUS_WORK / 'completed.json',
             terminal_path, Path(plan['delta']), *map(Path, plan['inputs'])}
    require(sha(plan['delta']) == plan['delta_sha256'], 'cold predecessor delta changed')
    for path, expected in plan['inputs'].items():
        require(sha(path) == expected, 'frozen cold input changed')
    # These earlier inputs are retained in the referenced archive, not copied
    # into the immediate cold archive. Keep the two required-member maps apart.
    for path, expected in plan['previous']['files'].items():
        require(sha(path) == expected, 'referenced predecessor input changed')
    stages = [Path(plan['delta']).parent / 'receipt.json']
    for name in engine.STAGES:
        ref = completed[name]
        path = Path(ref['path'])
        require(path == PREVIOUS_WORK / 'stages' / (name + '-01') / 'receipt.json'
                and sha(path) == ref['sha256'], 'cold completion reference changed')
        row = json.loads(path.read_text())
        require(row['stage'] == name and row['status'] == 'passed'
                and row['plan_sha256'] == PREVIOUS_PLAN_SHA
                and row['source_record_sha256'] == PREVIOUS_SOURCE_SHA, 'cold completion is invalid')
        stages.append(path)
    last_finish = 0
    for stage_path, phase, count in zip(stages, ['plan', *engine.STAGES], [23, 16, 11, 11], strict=True):
        files.add(stage_path)
        row = json.loads(stage_path.read_text())
        require(row['stage'] == phase and row['status'] == 'passed' and len(row['commands']) == count
                and row['started_at'] <= row['admitted_at'] <= row['finished_at']
                and row['admitted_at'] >= last_finish, 'cold stage order or count changed')
        last_finish = row['finished_at']
        for ref in row['commands']:
            path = Path(ref['path'])
            require(path.is_relative_to(stage_path.parent / 'commands') and sha(path) == ref['sha256'],
                    'cold child association changed')
            child = json.loads(path.read_text())
            require(child['status'] == 'finished' and child['command'] == ref['command']
                    and child['returncode'] == 0, 'cold child did not pass')
            files.add(path)
            for name in ['stdout', 'stderr']:
                output = path.parent / name
                require(sha(output) == child[name + '_sha256'], 'cold child output changed')
                files.add(output)
        supervisor = PREVIOUS_ROOT / '.work/experiments' / ('hir-cold-audit-upgrade-' + phase + '-supervisor-01')
        status_row = json.loads((supervisor / 'status.json').read_text())
        require(status_row['status'] == 'finished' and status_row['returncode'] == 0
                and status_row['child_pid'] == row['pid'], 'cold supervisor association changed')
        require(sha(supervisor / 'plan.json') == status_row['plan_sha256']
                and sha(supervisor / 'command.log') == status_row['log_sha256'], 'cold supervisor output changed')
        files.update(supervisor / name for name in ['status.json', 'plan.json', 'command.log', 'supervisor.log'])
    compiler_refs = [row for row in terminal['commands'] if row['command'] == engine.old.COMMANDS['unit']]
    require(len(compiler_refs) == 1, 'exactly one cold unit compiler command required')
    unit = Path(compiler_refs[0]['path']).parent
    output = (unit / 'stdout').read_text() + (unit / 'stderr').read_text()
    require('22 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out' in output,
            'all twenty-two actual cold unit controls required')
    engine.checked_tests(output, previous_tests(), [])
    manifest = json.loads((PREVIOUS_ROOT / 'experiments/hir-cold-audit-upgrade/inputs/patch.json').read_text())
    require(manifest == cold.checkpoint()[0], 'cold patch differs from the frozen source')
    base = plan['previous']
    require(engine.old.frozen_plan() == base['old_plan'], 'original source/environment recipe changed')
    return dict(status=status, terminal=str(terminal_path), source=source, old_manifest=manifest,
        old_plan=base['old_plan'], old_plan_path=base['old_plan_path'],
        predecessor_checkpoint=PREVIOUS_CHECKPOINT, predecessor_plan_sha256=PREVIOUS_PLAN_SHA,
        historical_archives=[historical_reference(plan)], files={str(p): sha(p) for p in files},
        historical_source={str(engine.SOURCE / p): row['after_sha256'] for p, row in manifest['files'].items()})


def context():
    return engine.UpgradeContext(ROOT, HERE, ROOT / '.work/hir-ready-hit-upgrade-01',
        CHECKPOINT, inputs, previous, stage_checkpoint, tuple(previous_tests()), PREVIOUS_ARCHIVE_SHA)


def main():
    engine.execute(engine.arguments(__doc__), context=context())


if __name__ == '__main__':
    main()
