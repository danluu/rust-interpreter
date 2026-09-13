#!/usr/bin/env python3
"""Full native capture/reuse qualification of the worker-arena repair."""
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
WORK = ROOT / '.work/hir-arena-native-01'
spec = importlib.util.spec_from_file_location('native_arena_upgrade',
    ROOT / 'experiments/hir-arena-identity-upgrade/upgrade.py')
upgrade = importlib.util.module_from_spec(spec); sys.modules[spec.name] = upgrade; spec.loader.exec_module(upgrade)
native, engine = upgrade.native, upgrade.engine
require, sha, ordinary = engine.require, engine.sha, native.ordinary
UPGRADE = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
UPGRADE_WORK = UPGRADE / '.work/hir-arena-identity-upgrade-01'
UPGRADE_PLAN = UPGRADE / 'experiments/hir-arena-identity-upgrade/planned-upgrade-01.json'
PLAN_SHA = '01edd2672a7a0cbe850b9f6b38984b01ba4172d009417e9aaf40ae205cba9299'
SOURCE_REVISION = '7efc0d9484da82cd327deb3b48616f8ec81eaf8d'
SOURCE_RECORD_SHA = 'fd0cc030b76bce5f8733cce975c0bb1e00cf226ed495439e36d6e5bdb320e020'
# The completed check/all27 history is the immediate prerequisite, not any
# preceding diagnostic or selected-check archive.
CURRENT_ARCHIVE_SHA = 'ce5931c23ba0af5247f85848df64ef0735b14ae5ba0c1fd4ce1a080477b023ce'
CURRENT_ARCHIVE = UPGRADE / 'results/hir-arena-identity-check-01'
CURRENT_TEXT_HASHES = {
    str(CURRENT_ARCHIVE / 'manifest.json'): '65b7030506a1dd390ff856a6bf5a38497c0967c7396f438d2ccf68fa68dbac1a',
    str(CURRENT_ARCHIVE / 'summary.json'): '3196ec4d0c62fe5caa9f21fee2807f221b0856ee7ee820ea1e586ab6317081a0',
}
ARCHIVE_CHAIN = [upgrade.diagnostic.CURRENT_ARCHIVE_SHA, upgrade.ARCHIVE_HASHES['archive'],
                 *upgrade.diagnostic.ARCHIVE_CHAIN]


def checkpoint():
    manifest, names = upgrade.checkpoint()
    require(len(names) == 27 and upgrade.NEW_TEST in names,
            'all27 worker-arena and prior units are required')
    return manifest, names


def inputs():
    # The separate old PRIMARY paths in the completed history remain untouched;
    # this worktree supplies its own reviewed, default-preserving native engine.
    paths = [Path(__file__), HERE / 'README.md', ROOT / 'tests/test_hir_arena_native.py']
    require(all(sha(ordinary(p)) == h for p, h in CURRENT_TEXT_HASHES.items()),
            'completed arena archive summary or manifest changed')
    return {**upgrade.inputs(), **{str(ordinary(p)): sha(p) for p in paths}, **CURRENT_TEXT_HASHES}


def history(plan_hash, terminal_path):
    """Require actual successful arena check/all27, not its diagnostic predecessor."""
    require(plan_hash == PLAN_SHA and sha(ordinary(UPGRADE_PLAN)) == PLAN_SHA,
            'exact reviewed arena-upgrade plan required')
    plan = json.loads(UPGRADE_PLAN.read_bytes())
    state_path, completed_path = UPGRADE_WORK / 'source.json', UPGRADE_WORK / 'completed.json'
    require(sha(ordinary(state_path)) == SOURCE_RECORD_SHA, 'actual arena source receipt changed')
    state = json.loads(state_path.read_bytes())
    completed = json.loads(ordinary(completed_path).read_bytes())
    manifest, names = checkpoint()
    require(state['revision'] == SOURCE_REVISION and state['parent'] == upgrade.diagnostic.SOURCE_REVISION
            and state['plan_sha256'] == PLAN_SHA and state['config_sha256'] == native.CONFIG_SHA,
            'actual arena compiler source or bootstrap identity changed')
    require(plan['owner'] == str(UPGRADE) and plan['source'] == str(engine.SOURCE)
            and plan['checkpoint'] == upgrade.CHECKPOINT and plan['commands'] == engine.old.COMMANDS
            and plan['stages'] == ['apply', 'check', 'unit']
            and sorted([*plan['old_tests'], *plan['added_tests']]) == names
            and set(completed) == {'apply', 'check', 'unit'},
            'arena selected check and all27 unit history is incomplete')
    require(state['parent'] == plan['previous']['source']['revision']
            and all(state['files'].get(name) == dict(kind='file', sha256=row['after_sha256'])
                    for name, row in manifest['files'].items()), 'arena source differs from reviewed patch')
    references = [dict(paths=plan['archive_paths'], hashes=plan['archive_hashes'], required=plan['archive_required']),
                  *plan['previous']['historical_archives']]
    require(len(references) == len(ARCHIVE_CHAIN) == 6, 'six separate historical archives required')
    for ref, expected in zip(references, ARCHIVE_CHAIN, strict=True):
        require(ref['hashes'][ref['paths']['archive']] == expected and ref['required']
                and set(ref['hashes']) == set(ref['paths'].values()), 'fixed archive lineage changed')
    require(references[0]['required'] == (plan['previous']['files'] | plan['previous']['historical_source']),
            'immediate phase322 required source proof changed')
    archive_inputs = {r['paths']['archive']: r['hashes'][r['paths']['archive']] for r in references}
    require(all(plan['inputs'].get(p) in (None, h) for p, h in archive_inputs.items()),
            'archived input and historical reference disagree')
    text_inputs = {p: h for p, h in plan['inputs'].items() if p not in archive_inputs}
    files = {str(UPGRADE_PLAN): PLAN_SHA, str(state_path): SOURCE_RECORD_SHA,
             str(completed_path): sha(completed_path), str(ordinary(plan['delta'])): plan['delta_sha256'], **text_inputs}
    stages = {name: ordinary(ref['path']) for name, ref in completed.items()}
    require(ordinary(terminal_path) == stages['unit'], 'terminal must be actual arena unit completion')
    stages = {'plan': ordinary(Path(plan['delta']).parent / 'receipt.json'), **stages}
    last_finish = 0
    for name in ['plan', 'apply', 'check', 'unit']:
        stage_path = stages[name]
        require(stage_path.is_relative_to(UPGRADE_WORK / 'stages')
                and (name == 'plan' or sha(stage_path) == completed[name]['sha256']),
                'arena completion association changed')
        row = json.loads(stage_path.read_bytes())
        require(row['owner'] == str(UPGRADE) and row['stage'] == name and row['status'] == 'passed'
                and row['plan_sha256'] == PLAN_SHA
                and (name == 'plan' or row['source_record_sha256'] == SOURCE_RECORD_SHA),
                'arena stage did not pass against actual current source')
        require(row['started_at'] <= row['admitted_at'] <= row['finished_at']
                and row['admitted_at'] >= last_finish, 'arena stage order changed')
        last_finish = row['finished_at']
        attempt = re.fullmatch(re.escape(name) + r'-(\d+)', stage_path.parent.name)
        require(attempt is not None, 'unknown arena stage attempt')
        outer = UPGRADE / '.work/experiments' / ('hir-arena-identity-upgrade-' + name + '-supervisor-' + attempt[1])
        status = json.loads(ordinary(outer / 'status.json').read_bytes())
        require(status['status'] == 'finished' and status['returncode'] == 0 and status['child_pid'] == row['pid']
                and status['supervisor_pid'] == row['parent_pid']
                and sha(ordinary(outer / 'plan.json')) == status['plan_sha256']
                and sha(ordinary(outer / 'command.log')) == status['log_sha256'], 'arena outer supervisor changed')
        for part in ['status.json', 'plan.json', 'command.log', 'supervisor.log']:
            files[str(ordinary(outer / part))] = sha(outer / part)
        files[str(stage_path)] = sha(stage_path)
        matched = []
        for ref in row['commands']:
            path = ordinary(ref['path'])
            require(path.is_relative_to(stage_path.parent / 'commands') and sha(path) == ref['sha256'],
                    'arena child association changed')
            child = json.loads(path.read_bytes())
            require(child['status'] == 'finished' and child['returncode'] == 0 and child['command'] == ref['command']
                    and child['environment'] == plan['previous']['old_plan']['environment'],
                    'arena child failed or its invocation changed')
            files[str(path)] = sha(path)
            text = ''
            for output in ['stdout', 'stderr']:
                output_path = ordinary(path.parent / output)
                require(sha(output_path) == child[output + '_sha256'], 'arena child raw output changed')
                files[str(output_path)] = sha(output_path)
                text += output_path.read_text()
            if name in engine.old.COMMANDS and child['command'] == engine.old.COMMANDS[name]:
                require(child['cwd'] == str(engine.SOURCE), 'arena compiler cwd changed')
                matched.append(text)
        if name in engine.old.COMMANDS:
            require(len(matched) == 1, 'exactly one selected arena compiler command required')
            if name == 'unit':
                engine.checked_tests(matched[0], names, [])
                native.checked_result(matched[0], 27, unfiltered=True)
    require(all(sha(ordinary(p)) == h for p, h in files.items()), 'arena history input changed')
    require(engine.old.frozen_plan() == plan['previous']['old_plan'], 'original bootstrap/seed recipe changed')
    return dict(plan_sha256=PLAN_SHA, source=state, terminal=str(terminal_path), files=files,
        old_plan=plan['previous']['old_plan'], old_plan_path=plan['previous']['old_plan_path'],
        historical_archives=references,
        historical_source={str(engine.SOURCE / p): row['after_sha256'] for p, row in manifest['files'].items()})


def context():
    require(re.fullmatch('[0-9a-f]{64}', CURRENT_ARCHIVE_SHA or ''),
            'completed arena check/all27 archive has not been pinned')
    return native.NativeContext(ROOT, HERE, WORK, upgrade.CHECKPOINT, inputs, checkpoint, history,
                                CURRENT_ARCHIVE_SHA)


if __name__ == '__main__':
    native.execute(native.arguments(__doc__), context=context())
