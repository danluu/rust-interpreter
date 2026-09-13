#!/usr/bin/env python3
"""Reviewed in-place 33f prepared-value to 60d cold-audit compiler continuation."""
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PREVIOUS_ROOT = Path('/Users/danluu/dev/rust-interp-hir-upgrade-20260913')
PREVIOUS_WORK = PREVIOUS_ROOT / '.work/hir-capture-upgrade-01'
PREVIOUS_PLAN = PREVIOUS_ROOT / 'experiments/hir-capture-upgrade/planned-upgrade-01.json'
PREVIOUS_PLAN_SHA = '463bc86d99ec036de27e31fa892e8d080b31b51fe35e29bfa6c93cd7da4342cc'
PREVIOUS_SOURCE_SHA = '922df6cccb6acd88cfc7796957729fc2360dca685e4b21927394061d43324551'
PREVIOUS_REVISION = '3c40bed885cee37e422be334d0e1b9403225f833'
PREVIOUS_PARENT = '7c1a064b649c0e7610c557a2c98f5f3e2fc8ed27'
PREVIOUS_CHECKPOINT = '33f4c4e4b0675578f92f2442de92de8232f30eeb'
PREVIOUS_ARCHIVE_SHA = '53a8fa2fab9504a8dbef7a44fbe26bf094a254bf8443f0cda43c9fe35eacaf54'
CHECKPOINT = '60d5be4532b260f2aea03226f463dccc83391266'
PATCH_SHA = '3f09136b6e962c282d87f6a6c84afc895266a8c9f81aa55688c49ac98f624b03'
SOURCE_IDENTITY = '9ec60c2dea9e2c30a30c868dcf17afa030ecaa267d56f17bbfe5e36e5f60515f'
ENGINE = ROOT / 'experiments/hir-capture-upgrade/upgrade.py'
spec = importlib.util.spec_from_file_location('hir_successor_engine', ENGINE)
engine = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = engine
spec.loader.exec_module(engine)
require, sha = engine.require, engine.sha


def named_tests(patch):
    names = re.findall(r'^\+\s*#\[test\]\n\+\s*fn ([a-z0-9_]+)', patch.read_text(), re.M)
    require(len(names) == len(set(names)), 'duplicate checkpoint control')
    return sorted(names)


def previous_tests():
    manifest, names = engine.checkpoint()
    require(len(names) == 20 and manifest['actual_cache_hit_path'] is False,
            'the predecessor must retain all twenty prepared-value controls')
    return names


def inputs():
    names = ['origin.json', 'capture.patch', 'patch.json', 'checkpoint-README.md']
    require(sorted(p.name for p in (HERE / 'inputs').iterdir()) == sorted(names), 'unknown successor input')
    paths = [Path(__file__), HERE / 'README.md', ROOT / 'tests/test_hir_cold_audit_upgrade.py',
             *(HERE / 'inputs' / name for name in names)]
    # The engine and its original default controls/inputs are part of this
    # successor's source freeze. The actual earlier worktree stays unchanged.
    paths += list(map(Path, engine.inputs()))
    require(all(p.is_file() and not p.is_symlink() and p.resolve(strict=True) == p for p in paths),
            'invalid frozen continuation source')
    return {str(p): sha(p) for p in sorted(set(paths))}


def checkpoint():
    origins = json.loads((HERE / 'inputs/origin.json').read_text())
    require(set(origins) == {'capture.patch', 'patch.json', 'checkpoint-README.md'}
            and all(row['git_revision'] == CHECKPOINT
                    and sha(HERE / 'inputs' / name) == row['sha256']
                    for name, row in origins.items()), 'cold checkpoint source changed')
    manifest = json.loads((HERE / 'inputs/patch.json').read_text())
    patch = HERE / 'inputs/capture.patch'
    require(manifest['base_commit'] == engine.old.BASE and len(manifest['files']) == 24
            and sha(patch) == manifest['patch_sha256'] == PATCH_SHA
            and manifest['source_identity'] == SOURCE_IDENTITY
            and manifest['actual_cache_hit_path'] is False
            and manifest['cached_body_materialization'] is False
            and manifest['cold_materialization_audit'] is True,
            'successor is not the reviewed warning-fixed cold audit')
    names = named_tests(patch)
    require(len(names) == 22 and set(previous_tests()) <= set(names), 'all twenty-two controls required')
    for name in manifest['files']:
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'invalid successor patch path')
    return manifest, names


def predecessor_state(plan, source, completed, terminal):
    """Only a real terminal check failure or complete selected-crate history."""
    require(plan['owner'] == str(PREVIOUS_ROOT) and plan['checkpoint'] == PREVIOUS_CHECKPOINT
            and plan['commands'] == engine.old.COMMANDS
            and source['revision'] == PREVIOUS_REVISION and source['parent'] == PREVIOUS_PARENT
            and source['plan_sha256'] == PREVIOUS_PLAN_SHA,
            'wrong predecessor source or command identity')
    require(terminal['owner'] == str(PREVIOUS_ROOT)
            and terminal.get('plan_sha256', terminal.get('expected_plan_sha256')) == PREVIOUS_PLAN_SHA,
            'terminal receipt is not bound to the predecessor plan')
    stage, status = terminal['stage'], terminal['status']
    if status == 'failed':
        require(stage in ['check', 'unit'] and set(completed) ==
                {'apply', *(['check'] if stage == 'unit' else [])}, 'nonterminal predecessor failure')
    else:
        require(status == 'passed' and stage == 'unit' and set(completed) == {'apply', 'check', 'unit'},
                'passing predecessor history must include all unit controls')
    return status


def previous(terminal_path):
    terminal_path = Path(terminal_path).resolve(strict=True)
    require(terminal_path.is_relative_to(PREVIOUS_WORK / 'stages')
            and terminal_path.name == 'receipt.json', 'terminal is outside the predecessor history')
    require(sha(PREVIOUS_PLAN) == PREVIOUS_PLAN_SHA
            and sha(PREVIOUS_WORK / 'source.json') == PREVIOUS_SOURCE_SHA, 'predecessor records changed')
    plan = json.loads(PREVIOUS_PLAN.read_text())
    source = json.loads((PREVIOUS_WORK / 'source.json').read_text())
    completed = json.loads((PREVIOUS_WORK / 'completed.json').read_text())
    terminal = json.loads(terminal_path.read_text())
    status = predecessor_state(plan, source, completed, terminal)
    require(sorted([*plan['old_tests'], *plan['added_tests']]) == previous_tests(),
            'predecessor control set changed')
    files = {PREVIOUS_PLAN, PREVIOUS_WORK / 'source.json', PREVIOUS_WORK / 'completed.json',
             terminal_path, Path(plan['delta']), *map(Path, plan['inputs'])}
    require(sha(plan['delta']) == plan['delta_sha256'], 'predecessor delta changed')
    for path, expected in (plan['previous']['files'] | plan['inputs']).items():
        require(sha(path) == expected, 'frozen predecessor input changed')
        files.add(Path(path))
    # The plan-generation receipt is part of the parent proof as well as its
    # apply/check histories. Its output delta lives in the same stage folder.
    stages = {terminal_path, Path(plan['delta']).parent / 'receipt.json'}
    for name, ref in completed.items():
        path = Path(ref['path'])
        require(path.is_relative_to(PREVIOUS_WORK / 'stages') and sha(path) == ref['sha256'],
                'predecessor completion reference changed')
        receipt = json.loads(path.read_text())
        require(receipt['status'] == 'passed' and receipt['stage'] == name
                and receipt['plan_sha256'] == PREVIOUS_PLAN_SHA, 'predecessor completion is invalid')
        if name == 'apply':
            require(receipt['source_record_sha256'] == PREVIOUS_SOURCE_SHA, 'applied source identity changed')
        stages.add(path)
    for stage_path in stages:
        files.add(stage_path)
        row = json.loads(stage_path.read_text())
        for ref in row['commands']:
            path = Path(ref['path'])
            require(path.is_relative_to(stage_path.parent / 'commands') and sha(path) == ref['sha256'],
                    'predecessor child association changed')
            child = json.loads(path.read_text())
            require(child['status'] == 'finished' and child['command'] == ref['command'],
                    'predecessor child is not the recorded completed command')
            files.add(path)
            for name in ['stdout', 'stderr']:
                output = path.parent / name
                require(sha(output) == child[name + '_sha256'], 'predecessor child output changed')
                files.add(output)
    compiler_refs = [row for row in terminal['commands']
                     if row['command'] == engine.old.COMMANDS[terminal['stage']]]
    require(len(compiler_refs) == 1, 'exactly one terminal compiler command required')
    last_path = Path(compiler_refs[0]['path'])
    last = json.loads(last_path.read_text())
    require(((last['returncode'] != 0 and compiler_refs[0] == terminal['commands'][-1])
             if status == 'failed' else (last['returncode'] == 0)),
            'terminal result does not match the actual compiler child')
    if status == 'passed':
        engine.checked_tests((last_path.parent / 'stdout').read_text() +
                             (last_path.parent / 'stderr').read_text(), previous_tests(), [])
    manifest_path = PREVIOUS_ROOT / 'experiments/hir-capture-upgrade/inputs/patch.json'
    manifest = json.loads(manifest_path.read_text())
    require(manifest == engine.checkpoint()[0], 'predecessor patch differs from the frozen source')
    base = plan['previous']
    require(engine.old.frozen_plan() == base['old_plan'], 'original source/environment recipe changed')
    return dict(status=status, terminal=str(terminal_path), source=source, old_manifest=manifest,
        old_plan=base['old_plan'], old_plan_path=base['old_plan_path'],
        predecessor_checkpoint=PREVIOUS_CHECKPOINT, predecessor_plan_sha256=PREVIOUS_PLAN_SHA,
        files={str(p): sha(p) for p in files},
        historical_source={str(engine.SOURCE / p): row['after_sha256'] for p, row in manifest['files'].items()})


def context():
    return engine.UpgradeContext(ROOT, HERE, ROOT / '.work/hir-cold-audit-upgrade-01',
        CHECKPOINT, inputs, previous, checkpoint, tuple(previous_tests()), PREVIOUS_ARCHIVE_SHA)


def main():
    engine.execute(engine.arguments(__doc__), context=context())


if __name__ == '__main__':
    main()
