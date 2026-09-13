#!/usr/bin/env python3
"""Sequential, explicitly admitted source upgrade of the owned limited HIR check."""
import argparse
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HIRC = Path('/Users/danluu/dev/rust-interp-hir-capture-check-20260913')
OLD_WORK = HIRC / '.work/hir-capture-check-01'
SOURCE = Path('/Users/danluu/dev/rustc-hir-capture-check-20260913')
CHECKPOINT = '33f4c4e4b0675578f92f2442de92de8232f30eeb'
WORK = ROOT / '.work/hir-capture-upgrade-01'
sys.path.insert(0, str(ROOT / 'experiments/stable-cgu'))
from owned_stage import CANONICAL_LOCK, disk, require, run, sha, workload_lock, write
spec = importlib.util.spec_from_file_location('frozen_hir_check', HIRC / 'experiments/hir-capture-check/check.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
STAGES = ['apply', 'check', 'unit']


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inputs():
    paths = [Path(__file__), HERE / 'README.md', ROOT / 'tests/test_hir_capture_upgrade.py',
             ROOT / 'experiments/stable-cgu/owned_stage.py', ROOT / 'scripts/supervise_experiment.py']
    paths += sorted((HERE / 'inputs').iterdir())
    require(all(p.is_file() and not p.is_symlink() for p in paths), 'invalid upgrade input')
    return {str(p): sha(p) for p in paths}


def checkpoint():
    origins = json.loads((HERE / 'inputs/origin.json').read_text())
    require(all(v['git_revision'] == CHECKPOINT and sha(HERE / 'inputs' / p) == v['sha256']
                for p, v in origins.items()), 'new checkpoint bytes changed')
    manifest = json.loads((HERE / 'inputs/patch.json').read_text())
    patch = HERE / 'inputs/capture.patch'
    require(manifest['base_commit'] == old.BASE and sha(patch) == manifest['patch_sha256']
            and manifest['actual_cache_hit_path'] is False and manifest['cached_body_materialization'] is False,
            'upgrade is not the reviewed capture-only checkpoint')
    names = re.findall(r'^\+\s*#\[test\]\n\+\s*fn ([a-z0-9_]+)', patch.read_text(), re.M)
    require(len(names) == len(set(names)) == 20 and set(old.REQUIRED_TESTS) <= set(names),
            'checkpoint must retain all five original and all twenty named controls')
    for path in manifest['files']:
        require(not Path(path).is_absolute() and '..' not in Path(path).parts, 'invalid patch path')
    return manifest, sorted(names)


def terminal_state(completed, terminal):
    """A terminal failure authorizes repair, never a claim of prior qualification."""
    require('prepare' in completed, 'no completed original prepare')
    stage, status = terminal['stage'], terminal['status']
    if status == 'failed':
        require(stage in ['check', 'unit'] and set(completed) == {'prepare', *(['check'] if stage == 'unit' else [])},
                'failure is not the next original stage')
    else:
        require(status == 'passed' and stage == 'unit' and set(completed) == {'prepare', 'check', 'unit'},
                'successful prior history must include unit completion')
    return status


def previous(terminal_path):
    terminal_path = Path(terminal_path).resolve(strict=True)
    require(terminal_path.is_relative_to(OLD_WORK / 'stages') and terminal_path.name == 'receipt.json',
            'terminal receipt is outside the original history')
    source_path, completed_path = OLD_WORK / 'source.json', OLD_WORK / 'completed.json'
    state = json.loads(source_path.read_text())
    completed = json.loads(completed_path.read_text())
    terminal = json.loads(terminal_path.read_text())
    status = terminal_state(completed, terminal)
    plan_path = Path(terminal['plan'])
    plan = json.loads(plan_path.read_text())
    require(plan == old.frozen_plan() and state['plan_sha256'] == sha(plan_path)
            and terminal['plan_sha256'] == sha(plan_path), 'original frozen plan changed')
    files = {source_path, completed_path, plan_path, terminal_path, *map(Path, plan['inputs'])}
    stages = [terminal_path]
    for reference in completed.values():
        path = Path(reference['path'])
        require(sha(path) == reference['sha256'] and json.loads(path.read_text())['status'] == 'passed',
                'completed original receipt changed')
        stages.append(path)
    for stage_path in set(stages):
        files.add(stage_path)
        row = json.loads(stage_path.read_text())
        for command in row['commands']:
            receipt_path = Path(command['path'])
            require(sha(receipt_path) == command['sha256'], 'original child receipt changed')
            child = json.loads(receipt_path.read_text())
            require(child['status'] == 'finished', 'original child still active')
            files.add(receipt_path)
            for name in ['stdout', 'stderr']:
                path = receipt_path.parent / name
                require(sha(path) == child[name + '_sha256'], 'original child output changed')
                files.add(path)
    last = json.loads(Path(terminal['commands'][-1]['path']).read_text())
    if status == 'failed':
        require(last['command'] == old.COMMANDS[terminal['stage']] and last['returncode'] != 0,
                'repair requires an actual failed compiler command')
    old_manifest = json.loads((old.HERE / 'inputs/patch.json').read_text())
    # Old source bytes are verified live only before applying the upgrade.
    # Later phases rely on these exact archived bytes and the new source record.
    historical_source = {str(SOURCE / p): row['after_sha256'] for p, row in old_manifest['files'].items()}
    return dict(status=status, terminal=str(terminal_path), source=state,
                old_manifest=old_manifest, old_plan=plan, old_plan_path=str(plan_path),
                files={str(p): sha(p) for p in files}, historical_source=historical_source)


def verify_archive(archive, manifest_path, summary_path, required):
    manifest = json.loads(Path(manifest_path).read_text())
    summary = json.loads(Path(summary_path).read_text())
    require(summary['archive']['sha256'] == sha(archive), 'archive summary mismatch')
    required = dict(required)
    seen = set()
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar:
            require(member.isfile() and member.name not in seen and member.name in manifest,
                    'unexpected archive member')
            seen.add(member.name)
            item = manifest[member.name]
            data = tar.extractfile(member).read()
            require(len(data) == item['bytes'] and digest(data) == item['sha256'], 'archive member changed')
            source = item['source']
            require(member.name == source.lstrip('/') and Path(source).is_absolute()
                    and '..' not in Path(member.name).parts, 'archive source mapping mismatch')
            if source in required:
                require(item['sha256'] == required.pop(source), 'required historical bytes differ')
    require(seen == set(manifest) and not required, 'historical archive is incomplete')


def source_guard(state, command, old_plan_hash):
    require(SOURCE.resolve(strict=True) == SOURCE and (SOURCE / '.git').is_dir()
            and not (SOURCE / '.git').is_symlink()
            and json.loads((SOURCE / '.rust-interp-owned.json').read_text()) ==
                dict(owner=str(HIRC), plan_sha256=old_plan_hash), 'owned source marker changed')
    require(command(['git', 'rev-parse', 'HEAD'])['stdout'].strip() == state['revision']
            and not command(['git', 'diff', 'HEAD', '--'])['stdout']
            and sha(SOURCE / 'bootstrap.toml') == state['config_sha256']
            and old.inventory(command, SOURCE) == state['files']
            and command(['git', 'rev-parse', 'HEAD'], SOURCE / 'library/backtrace')['stdout'].strip() == old.BACKTRACE
            and old.inventory(command, SOURCE / 'library/backtrace') == state['backtrace_files'],
            'compiler source, index, backtrace or configuration changed')


def delta_file(path, before, after):
    if before == after:
        return b''
    header = f'diff --git a/{path} b/{path}\n'
    if before is None:
        header += 'new file mode 100644\n'
    elif after is None:
        header += 'deleted file mode 100644\n'
    lines = difflib.unified_diff((before or b'').decode().splitlines(True),
        (after or b'').decode().splitlines(True), '/dev/null' if before is None else 'a/' + path,
        '/dev/null' if after is None else 'b/' + path)
    return (header + ''.join(lines)).encode()


def checked_tests(text, original, added):
    for name in [*original, *added]:
        require(re.search(r'test .*\b' + re.escape(name) + r' \.\.\. ok', text),
                'required actual unit test missing: ' + name)


def load_plan(path, expected_hash, frozen, names):
    require(re.fullmatch('[0-9a-f]{64}', expected_hash or ''), 'reviewed plan SHA256 required')
    data = Path(path).read_bytes()
    require(digest(data) == expected_hash, 'reviewed upgrade plan changed')
    plan = json.loads(data)
    require(plan['owner'] == str(ROOT) and plan['source'] == str(SOURCE)
            and plan['inputs'] == frozen and plan['checkpoint'] == CHECKPOINT
            and plan['stages'] == STAGES and plan['commands'] == old.COMMANDS
            and plan['old_tests'] == old.REQUIRED_TESTS
            and plan['added_tests'] == sorted(set(names) - set(old.REQUIRED_TESTS))
            and (plan['initial_free_gib'], plan['running_floor_gib'], plan['capacity_stop_gib']) == (16, 8, 9),
            'upgrade plan changed fixed source, commands, tests or capacity policy')
    return plan


def execute(args):
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.attempt), 'fresh attempt name required')
    phase = 'plan' if args.write_plan else args.stage
    require(phase in ['plan', *STAGES], 'explicit upgrade phase required')
    output = WORK / 'stages' / args.attempt
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(status='waiting', stage=phase, owner=str(ROOT), pid=os.getpid(), parent_pid=os.getppid(),
                   started_at=time.time(), commands=[], canonical_lock=str(CANONICAL_LOCK), lock_wait_seconds=600,
                   expected_plan_sha256=args.plan_sha256)
    write(output / 'receipt.json', receipt)
    try:
        with workload_lock(CANONICAL_LOCK, 600):
            receipt.update(status='running', admitted_at=time.time(), free_bytes_before=disk(ROOT, 16))
            write(output / 'receipt.json', receipt)
            frozen = inputs()
            new_manifest, names = checkpoint()
            if phase == 'plan':
                require(args.write_plan.is_absolute() and args.write_plan.parent == HERE
                        and not args.write_plan.exists(), 'plan must be a fresh owned path')
                prior = previous(args.terminal)
                archive_paths = dict(archive=str(args.archive.resolve(strict=True)),
                    manifest=str(args.archive_manifest.resolve(strict=True)), summary=str(args.archive_summary.resolve(strict=True)))
                required = prior['files'] | prior['historical_source']
                verify_archive(archive_paths['archive'], archive_paths['manifest'], archive_paths['summary'], required)
                plan = None
            else:
                require(args.plan.resolve(strict=True).parent == HERE and not args.plan.is_symlink(), 'unexpected upgrade plan')
                plan = load_plan(args.plan, args.plan_sha256, frozen, names)
                prior, archive_paths, required = plan['previous'], plan['archive_paths'], plan['archive_required']
                require(all(sha(p) == h for p, h in plan['archive_hashes'].items()), 'historical archive changed')
                verify_archive(archive_paths['archive'], archive_paths['manifest'], archive_paths['summary'], required)
            old_plan_hash = sha(prior['old_plan_path'])
            env = prior['old_plan']['environment']
            def guard():
                require(inputs() == frozen and old.frozen_plan() == prior['old_plan']
                        and all(sha(p) == h for p, h in prior['files'].items()), 'frozen prerequisites changed')
                if phase != 'plan':
                    require(sha(args.plan) == args.plan_sha256, 'reviewed plan changed during execution')
            def command(argv, cwd=SOURCE):
                guard()
                if argv[0] == './x':
                    old.verify_archives(old.ARCHIVES)
                    old.verify_copied_archives()
                directory = output / 'commands' / f'{len(receipt["commands"]):03d}'
                ref = dict(path=str(directory / 'receipt.json'), command=list(map(str, argv)))
                receipt['commands'].append(ref)
                write(output / 'receipt.json', receipt)
                try:
                    result = run(argv, cwd=cwd, env=env, out=directory, capacity_root=ROOT)
                finally:
                    if (directory / 'receipt.json').exists():
                        ref['sha256'] = sha(directory / 'receipt.json')
                        write(output / 'receipt.json', receipt)
                return dict(result, stdout=(directory / 'stdout').read_text(), stderr=(directory / 'stderr').read_text())
            guard()
            old.verify_archives(old.ARCHIVES)
            old.verify_copied_archives()
            if phase == 'plan':
                source_guard(prior['source'], command, old_plan_hash)
                # Only the affected union of ordinary text files is materialized
                # here. This is not a compiler checkout, bootstrap, or Cargo target.
                scratch = output / 'delta-inputs'
                scratch.mkdir()
                command(['git', 'init', '--quiet', str(scratch)], ROOT)
                paths = sorted(set(prior['old_manifest']['files']) | set(new_manifest['files']))
                before, base = {}, {}
                for name in paths:
                    item = new_manifest['files'].get(name, prior['old_manifest']['files'].get(name))
                    current = SOURCE / name
                    before[name] = current.read_bytes() if current.exists() else None
                    old_item = prior['old_manifest']['files'].get(name)
                    expected = old_item['after_sha256'] if old_item else item['before_sha256']
                    require((digest(before[name]) if before[name] is not None else None) == expected, 'old delta input changed')
                    if item['before_sha256']:
                        data = command(['git', 'show', old.BASE + ':' + name])['stdout'].encode()
                        require(digest(data) == item['before_sha256'], 'base patch input changed')
                        target = scratch / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(data)
                        base[name] = data
                command(['git', 'apply', '--check', str(HERE / 'inputs/capture.patch')], scratch)
                command(['git', 'apply', str(HERE / 'inputs/capture.patch')], scratch)
                after_hashes, delta = {}, bytearray()
                for name in paths:
                    path = scratch / name
                    after = path.read_bytes() if path.exists() else None
                    expected = new_manifest['files'][name]['after_sha256'] if name in new_manifest['files'] else prior['old_manifest']['files'][name]['before_sha256']
                    require((digest(after) if after is not None else None) == expected, 'new delta input changed')
                    after_hashes[name] = expected
                    delta.extend(delta_file(name, before[name], after))
                delta_path = output / 'upgrade.patch'
                delta_path.write_bytes(delta)
                command(['git', 'apply', '--check', '--index', str(delta_path)])
                source_guard(prior['source'], command, old_plan_hash)
                plan = dict(schema_version=1, owner=str(ROOT), source=str(SOURCE), checkpoint=CHECKPOINT,
                    inputs=frozen, previous=prior, archive_paths=archive_paths, archive_required=required,
                    archive_hashes={p:sha(p) for p in archive_paths.values()},
                    delta=str(delta_path), delta_sha256=sha(delta_path), after_hashes=after_hashes,
                    before_hashes={p:digest(b) if b is not None else None for p,b in before.items()},
                    old_tests=old.REQUIRED_TESTS, added_tests=sorted(set(names)-set(old.REQUIRED_TESTS)),
                    stages=STAGES, commands=old.COMMANDS, initial_free_gib=16, running_floor_gib=8,
                    capacity_stop_gib=9, compiler_downloads='unchanged constrained original policy')
                write(args.write_plan, plan)
            else:
                completed_path = WORK / 'completed.json'
                completed = json.loads(completed_path.read_text()) if completed_path.exists() else {}
                require(set(completed) == set(STAGES[:STAGES.index(phase)]), 'upgrade stages out of order')
                for ref in completed.values():
                    require(sha(ref['path']) == ref['sha256'] and json.loads(Path(ref['path']).read_text())['status'] == 'passed', 'upgrade predecessor changed')
                require(sha(plan['delta']) == plan['delta_sha256'], 'reviewed delta changed')
                if phase == 'apply':
                    source_guard(prior['source'], command, old_plan_hash)
                    command(['git', 'apply', '--check', '--index', plan['delta']])
                    command(['git', 'apply', '--index', plan['delta']])
                    for name, expected in plan['after_hashes'].items():
                        path = SOURCE / name
                        require((sha(path) if path.exists() else None) == expected, 'applied source differs')
                    command(['git', 'commit', '-m', 'Upgrade HIR capture to checked prepared values'])
                    state = dict(revision=command(['git', 'rev-parse', 'HEAD'])['stdout'].strip(),
                        parent=prior['source']['revision'], files=old.inventory(command, SOURCE),
                        backtrace_files=prior['source']['backtrace_files'], config_sha256=prior['source']['config_sha256'],
                        plan_sha256=sha(args.plan))
                    require(command(['git', 'rev-parse', 'HEAD^'])['stdout'].strip() == state['parent'], 'source parent changed')
                    write(WORK / 'source.json', state)
                else:
                    state = json.loads((WORK / 'source.json').read_text())
                    require(state['plan_sha256'] == sha(args.plan), 'upgrade source record changed')
                    source_guard(state, command, old_plan_hash)
                    result = command(plan['commands'][phase])
                    if phase == 'unit':
                        checked_tests(result['stdout'] + result['stderr'], plan['old_tests'], plan['added_tests'])
                source_guard(state, command, old_plan_hash)
                receipt['source_record_sha256'] = sha(WORK / 'source.json')
            guard()
            old.verify_archives(old.ARCHIVES)
            old.verify_copied_archives()
            receipt.update(status='passed', finished_at=time.time(), free_bytes_after=disk(ROOT),
                           plan_sha256=sha(args.write_plan or args.plan))
            write(output / 'receipt.json', receipt)
            if phase != 'plan':
                completed[phase] = dict(path=str(output / 'receipt.json'), sha256=sha(output / 'receipt.json'))
                write(completed_path, completed)
    except BaseException as error:
        receipt.update(status='failed', error=repr(error), finished_at=time.time())
        write(output / 'receipt.json', receipt)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-plan', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--plan-sha256')
    parser.add_argument('--stage', choices=STAGES)
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--terminal', type=Path)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--archive-manifest', type=Path)
    parser.add_argument('--archive-summary', type=Path)
    args = parser.parse_args()
    if args.write_plan:
        require(not args.plan and not args.plan_sha256 and not args.stage and all([args.terminal,args.archive,args.archive_manifest,args.archive_summary]), 'explicit prior evidence required')
    else:
        require(args.plan and args.plan_sha256 and args.stage and not any([args.terminal,args.archive,args.archive_manifest,args.archive_summary]), 'use the reviewed plan hash for execution')
    execute(args)


if __name__ == '__main__':
    main()
