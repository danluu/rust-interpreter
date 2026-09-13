#!/usr/bin/env python3
"""Explicit recovery for plan02's rejected `x fmt <paths>` source-freeze step."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile
import time

from owned_stage import CANONICAL_LOCK, disk, require, run, sha, workload_lock, write

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
POLICY = 'owned-freeze-source-continuation-v1'


def read(path):
    return json.loads(Path(path).read_text())


def formatter_inventory(source, plan, original):
    """Check the existing extraction against both original, pinned components.

    Match download.rs's ordered component overlays, without extracting, repairing
    or downloading anything. The only generated file allowed is its exact stamp.
    """
    prefix = source / 'build' / original['host'] / 'rustfmt'
    require(prefix.resolve(strict=True) == prefix and prefix.is_dir(), 'missing ordinary formatter prefix')
    expected, archive_proofs = {}, []
    for specification in plan['formatter_archives']:
        path = Path(specification['path'])
        require(original['stage0_archives'][specification['original_path']] == specification['sha256']
                and sha(path) == specification['sha256'], 'pinned formatter archive changed')
        component = path.name.removesuffix('.tar.xz') + '/' + specification['component'] + '/'
        with tarfile.open(path, 'r:xz') as bundle:
            for member in bundle:
                if not member.name.startswith(component):
                    continue
                relative = member.name[len(component):].rstrip('/')
                if not relative:
                    continue
                require(not PurePosixPath(relative).is_absolute() and '..' not in PurePosixPath(relative).parts,
                        'invalid formatter archive path')
                if member.isdir():
                    value = dict(kind='directory')
                elif member.isfile():
                    digest = hashlib.sha256()
                    stream = bundle.extractfile(member)
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(block)
                    value = dict(kind='file', bytes=member.size, sha256=digest.hexdigest())
                elif member.issym():
                    value = dict(kind='symlink', link=member.linkname)
                else:
                    raise RuntimeError('unsupported formatter archive entry: ' + member.name)
                expected[relative] = value
                for parent in PurePosixPath(relative).parents:
                    if str(parent) != '.':
                        expected.setdefault(str(parent), dict(kind='directory'))
        archive_proofs.append(specification)
    stamp = b'nightly-2026-08-30'
    expected['.rustfmt-stamp'] = dict(kind='file', bytes=len(stamp), sha256=hashlib.sha256(stamp).hexdigest())
    actual = {}
    for path in sorted(prefix.rglob('*')):
        name = str(path.relative_to(prefix))
        item = path.lstat()
        if stat.S_ISLNK(item.st_mode):
            require(path.resolve(strict=True).is_relative_to(prefix), 'formatter link escapes its archive prefix')
            actual[name] = dict(kind='symlink', link=os.readlink(path))
        elif stat.S_ISDIR(item.st_mode):
            actual[name] = dict(kind='directory')
        else:
            require(stat.S_ISREG(item.st_mode), 'unsupported formatter extraction entry')
            actual[name] = dict(kind='file', bytes=item.st_size, sha256=sha(path))
    require(actual == expected, 'formatter extraction differs from pinned component overlays')
    require(os.access(prefix / 'bin/rustfmt', os.X_OK), 'pinned formatter is not executable')
    return dict(prefix=str(prefix), archives=archive_proofs, files=actual)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    require(__debug__, 'run Python without -O')
    path = args.plan.resolve(strict=True)
    plan = read(path)
    require(plan['policy'] == POLICY and plan['status'] == 'unexecuted continuation'
            and plan['owner'] == str(ROOT) and plan['runner_sha256'] == sha(Path(__file__)),
            'continuation plan/runner differs')
    original_path = Path(plan['original_plan']['path'])
    require(sha(original_path) == plan['original_plan']['sha256'], 'original plan changed')
    original = read(original_path)
    source = Path(original['source'])
    work = ROOT / '.work' / original['run_id']
    require(plan['attempt'] == 'freeze-source-continuation-01', 'unexpected recovery attempt')
    out = work / 'stages' / plan['attempt']
    out.mkdir(parents=True, exist_ok=False)
    record = dict(schema_version=1, owner=str(ROOT), supervisor_pid=os.getpid(), parent_pid=os.getppid(),
        stage='freeze-source', attempt=plan['attempt'], plan=str(original_path), plan_sha256=sha(original_path),
        source=str(source), started_at=time.time(), status='waiting', lock=str(CANONICAL_LOCK), commands=[],
        continuation=dict(policy=POLICY, plan=str(path), plan_sha256=sha(path),
            original_failure=plan['original_failure'], reason=plan['reason']))
    write(out / 'receipt.json', record)
    try:
        with workload_lock(CANONICAL_LOCK, original['lock_wait_seconds']):
            record.update(status='admitted', admitted_at=time.time(), free_bytes_before=disk(ROOT, 10))
            write(out / 'receipt.json', record)
            require(all(sha(Path(p)) == h for p, h in original['inputs'].items()), 'original frozen input changed')
            spec = importlib.util.spec_from_file_location('frozen_production_driver', HERE / 'production-driver.py')
            driver = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(driver)
            require(driver.ROOT == ROOT and driver.SOURCE == source
                    and set(original['inputs']) == set(map(str, driver.input_paths()))
                    and original['environment'] == driver.environment()
                    and original['python'] == dict(executable=sys.executable, sha256=sha(sys.executable), version=sys.version),
                    'original driver/environment/Python contract changed')
            completed_path, state_path = work / 'completed.json', work / 'source.json'
            completed = read(completed_path)
            require(completed == dict(prepare=plan['prepared_stage']) and not state_path.exists(),
                    'source is already frozen or preceding stage differs')
            require(not any((work / name).exists() for name in ['combined-upstream.patch', 'mono-formatted.patch']),
                    'source delta outputs already exist')
            for proof in [plan['prepared_stage'], plan['original_failure']]:
                require(sha(Path(proof['path'])) == proof['sha256'], 'retained stage receipt changed')
            failed = read(plan['original_failure']['path'])
            require(read(plan['prepared_stage']['path'])['status'] == 'passed'
                    and failed['stage'] == 'freeze-source' and failed['status'] == 'failed'
                    and failed['plan_sha256'] == record['plan_sha256'], 'recovery is not for the recorded formatting failure')
            for proof in failed['commands']:
                require(sha(Path(proof['receipt'])) == proof['sha256'], 'failed child receipt changed')
                child = read(proof['receipt'])
                for name in ['stdout', 'stderr']:
                    require(sha(Path(proof['receipt']).parent / name) == child[name + '_sha256'], 'failed child output changed')
            failure_text = (Path(failed['commands'][1]['receipt']).parent / 'stderr').read_text()
            require('path arguments are no longer accepted' in failure_text, 'original failure diagnosis differs')
            require(source.resolve(strict=True) == source and (source / '.git').is_dir()
                    and not (source / '.git/objects/info/alternates').exists(), 'source ownership/storage changed')
            require(read(source / '.rust-interp-owned.json') == read(plan['prepared_stage']['path'])['marker'],
                    'owned source marker changed')
            identities = read(ROOT / 'experiments/stable-mono-cgu/source-identity.json')
            files = [item['path'] for item in identities['files']]
            require(files == plan['files'] and len(files) == 6
                    and all(sha(source / item['path']) == item['patched_sha256'] for item in identities['files']),
                    'original six patched source files changed')
            require(sha(source / 'bootstrap.toml') == original['inputs'][str(HERE / 'bootstrap-production-source-paths.toml')],
                    'production bootstrap configuration changed')
            for name, expected in plan['pinned_recipe_sources'].items():
                require(sha(source / name) == expected, 'pinned formatter recipe source changed')
            formatter = formatter_inventory(source, plan, original)
            write(out / 'formatter-inventory.json', formatter)
            record['formatter_inventory_sha256'] = sha(out / 'formatter-inventory.json')

            def command(argv, cwd=source, expected=(0,)):
                directory = out / 'commands' / f'{len(record["commands"]):03d}'
                reference = dict(receipt=str(directory / 'receipt.json'), command=list(map(str, argv)), status='starting')
                record['commands'].append(reference)
                write(out / 'receipt.json', record)
                try:
                    item = run(argv, cwd=cwd, env=original['environment'], out=directory,
                               capacity_root=ROOT, expected=expected)
                finally:
                    if (directory / 'receipt.json').exists():
                        retained = read(directory / 'receipt.json')
                        reference.update(sha256=sha(directory / 'receipt.json'), status=retained['status'],
                                         returncode=retained.get('returncode'))
                        write(out / 'receipt.json', record)
                return item | dict(stdout=(directory / 'stdout').read_text(), stderr=(directory / 'stderr').read_text())

            require(command(['git', 'rev-parse', 'HEAD'])['stdout'].strip() == driver.BASE
                    and not command(['git', 'diff', '--cached', '--name-only'])['stdout'], 'source/index is not the prepared base')
            require(set(command(['git', 'diff', '--name-only', driver.BASE, '--'])['stdout'].splitlines()) <= set(files),
                    'another tracked source file changed before formatting')
            before = driver.source_inventory(command, source)
            write(out / 'source-before.json', before)
            (out / 'pre-format.patch').write_text(command(['git', 'diff', '--binary', driver.BASE, '--'])['stdout'])
            formatter_command = [str(source / 'build' / driver.HOST / 'rustfmt/bin/rustfmt'),
                '--config-path', str(source), '--edition', '2024', '--unstable-features', '--skip-children']
            require(formatter_command == plan['formatter_command'], 'standalone formatter recipe differs')
            if command([*formatter_command, '--check', *files], expected=(0, 1))['returncode']:
                command([*formatter_command, *files])
            command([*formatter_command, '--check', *files])
            after = driver.source_inventory(command, source)
            require(before['symlinks'] == after['symlinks'] and before['gitlinks'] == after['gitlinks']
                    and {p:h for p,h in before['files'].items() if p not in files}
                    == {p:h for p,h in after['files'].items() if p not in files}, 'formatter changed unrelated tracked source')
            require(formatter_inventory(source, plan, original) == formatter, 'formatter changed during use')
            command(['git', 'add', '--', *files])
            require(set(command(['git', 'diff', '--cached', '--name-only'])['stdout'].splitlines()) <= set(files),
                    'commit would include unrelated source')
            command(['git', 'commit', '-m', 'Add stable per-MonoItem codegen placement to the production compiler'])
            revision = command(['git', 'rev-parse', 'HEAD'])['stdout'].strip()
            require(re.fullmatch('[0-9a-f]{40}', revision) and revision not in [driver.BASE, driver.UPSTREAM], 'new source commit missing')
            command(['git', 'merge-base', '--is-ancestor', driver.BASE, revision])
            for name, base in [('combined-upstream.patch', driver.UPSTREAM), ('mono-formatted.patch', driver.BASE)]:
                require(not (work / name).exists(), 'source delta output already exists')
                (work / name).write_text(command(['git', 'diff', '--binary', base, revision, '--'])['stdout'])
            frozen = dict(source_commit=revision, base_commit=driver.BASE, upstream_commit=driver.UPSTREAM,
                config_sha256=sha(source / 'bootstrap.toml'), inventory=driver.source_inventory(command, source),
                backtrace=driver.source_inventory(command, source / 'library/backtrace'),
                combined_patch_sha256=sha(work / 'combined-upstream.patch'),
                formatted_mono_patch_sha256=sha(work / 'mono-formatted.patch'))
            driver.check_frozen(command, source, frozen)
            write(state_path, frozen)
            record.update(status='passed', returncode=0, source_revision=revision,
                config_sha256=frozen['config_sha256'], source_receipt_sha256=sha(state_path),
                finished_at=time.time(), free_bytes_after=disk(ROOT))
            write(out / 'receipt.json', record)
            completed['freeze-source'] = dict(path=str(out / 'receipt.json'), sha256=sha(out / 'receipt.json'))
            write(completed_path, completed)
            print(json.dumps(dict(stage='freeze-source', status='passed', continuation=POLICY, source_commit=revision)))
    except BaseException as error:
        record.update(status='failed', finished_at=time.time(), error_type=type(error).__name__, error=str(error))
        write(out / 'receipt.json', record)
        raise


if __name__ == '__main__':
    main()
