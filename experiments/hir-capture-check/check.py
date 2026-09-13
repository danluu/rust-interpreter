#!/usr/bin/env python3
"""Limited, explicitly admitted check of the frozen capture-only compiler patch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'experiments/stable-cgu'))
from owned_stage import CANONICAL_LOCK, disk, require, run, sha, workload_lock, write

SOURCE = Path('/Users/danluu/dev/rustc-hir-capture-check-20260913')
DONOR = Path('/Users/danluu/dev/rustc-stable-mono-production-20260913')
BASE = '58e1e1f5311f4424ea81def4763081f6da62d9b3'
CHECKPOINT = '3f3e9c28704a7866f72ad0974336d79671714ae9'
BACKTRACE = 'd902726a1dcdc1e1c66f73d1162181b5423c645b'
UPSTREAM = 'cea272fa356e94bd2ee2cadf376630aa0683867a'
HOST = 'aarch64-apple-darwin'
LLVM = Path('/Users/danluu/dev/rust-interp-stable-cgu-20260913/.work/stable-cgu-compiler-setup-01/rust-dev-nightly-aarch64-apple-darwin.tar.xz')
ARCHIVES = {
    str(DONOR / 'build/cache/2026-08-30/rustc-beta-aarch64-apple-darwin.tar.xz'):
        '0c20c4730544923b2ba9ab4ccf98cd22db6759d1d6cc2e5b8c99662b953163ac',
    str(DONOR / 'build/cache/2026-08-30/rust-std-beta-aarch64-apple-darwin.tar.xz'):
        'd8f4620f3672cae11fdb841a86d44215aeba2e656244286056f7742e966797e3',
    str(DONOR / 'build/cache/2026-08-30/cargo-beta-aarch64-apple-darwin.tar.xz'):
        '473eed6c6004b83a306c4fcf34002560c292050a6c25247a8c1cbe3ad05b93b4',
    str(DONOR / 'build/cache/2026-08-30/rustfmt-nightly-aarch64-apple-darwin.tar.xz'):
        'fcc49f0698c09f8ff89ca044d0426dad2399da253d287c3aaabebf103b4a2820',
    str(DONOR / 'build/cache/2026-08-30/rustc-nightly-aarch64-apple-darwin.tar.xz'):
        '9d494a6b72761dee6ec3c0ec085d5b29838565ef45bbb67b097caf0aa4750304',
    str(LLVM): '0035445cb01c652999862c240d3c8ce663247abdc410482dde10f9e9c264bf8f',
}
COMMANDS = {
    'check': ['./x', 'check', '--stage', '1', 'compiler/rustc_ast_lowering', '--jobs', '2', '-vv'],
    'unit': ['./x', 'test', '--stage', '1', 'compiler/rustc_ast_lowering', '--jobs', '2', '-vv'],
}
STAGES = ['prepare', 'check', 'unit']
REQUIRED_TESTS = [
    'validates_s_relative_relocation_and_trait_presence',
    'rejects_forward_bind_duplicate_ast_and_counter_gaps',
    'rejects_prefix_aliases_body_prefixes_and_overflow',
    'honors_actual_item_local_id_sentinel_and_exclusive_end',
    'corrupt_truncated_wrong_key_and_hardlinked_old_inode',
]


def environment():
    require(not any(k.startswith(('LD_', 'DYLD_')) for k in os.environ), 'loader override present')
    allowed = ['PATH', 'HOME', 'USER', 'LOGNAME', 'TMPDIR', 'LANG', 'LC_ALL', 'SHELL',
               'CARGO_HOME', 'RUSTUP_HOME', 'SDKROOT', 'DEVELOPER_DIR', 'MACOSX_DEPLOYMENT_TARGET']
    env = {k: os.environ[k] for k in allowed if k in os.environ}
    env.update(CARGO_BUILD_JOBS='2', CARGO_INCREMENTAL='0', RUST_TEST_THREADS='2',
               CARGO_NET_OFFLINE='true', CARGO_TERM_COLOR='never')
    return env


def input_paths():
    names = ['origin.json', 'capture.patch', 'patch.json', 'bootstrap.toml']
    require(sorted(p.name for p in (HERE / 'inputs').iterdir()) == sorted(names), 'unknown checkpoint input')
    return [Path(__file__), HERE / 'README.md', *(HERE / 'inputs' / name for name in names),
            ROOT / 'experiments/stable-cgu/owned_stage.py', ROOT / 'scripts/supervise_experiment.py',
            ROOT / 'tests/test_hir_capture_check.py']


def configurations():
    paths = {Path(os.environ.get('CARGO_HOME', str(Path.home() / '.cargo'))) / n
             for n in ['config', 'config.toml']}
    # Pinned bootstrap.py:1062 and builder/cargo.rs:638 both set Cargo cwd to
    # SOURCE. Also guard the prospective build and selected manifest directories
    # explicitly; their absence must not become an untracked configuration.
    invocation_dirs = [SOURCE, SOURCE / 'build', SOURCE / 'src/bootstrap',
                       SOURCE / 'compiler/rustc', SOURCE / 'compiler/rustc_ast_lowering', ROOT]
    for parent in {p for directory in invocation_dirs for p in [directory, *directory.parents]}:
        paths.update(parent / '.cargo' / n for n in ['config', 'config.toml'])
    result = {}
    for path in sorted(paths):
        require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents),
                'Cargo configuration contains a symlink: ' + str(path))
        require(not path.exists() or path.is_file(), 'Cargo configuration is not an ordinary file')
        result[str(path)] = sha(path) if path.is_file() else None
    return result


def frozen_plan():
    origins = json.loads((HERE / 'inputs/origin.json').read_text())
    require(all(row['git_revision'] == CHECKPOINT and sha(HERE / 'inputs' / name) == row['sha256']
                for name, row in origins.items()), 'committed checkpoint bytes changed')
    manifest = json.loads((HERE / 'inputs/patch.json').read_text())
    require(manifest['base_commit'] == BASE and manifest['patch_sha256'] == sha(HERE / 'inputs/capture.patch')
            and manifest['actual_cache_hit_path'] is False, 'unexpected capture patch')
    return dict(schema_version=1, status='unexecuted limited check', owner=str(ROOT), source=str(SOURCE),
        donor=str(DONOR), base=BASE, checkpoint=CHECKPOINT, backtrace=BACKTRACE,
        run_id='hir-capture-check-01', stages=STAGES, commands=COMMANDS,
        canonical_lock=str(CANONICAL_LOCK), lock_wait_seconds=600, initial_free_gib=24,
        running_floor_gib=8, archives=ARCHIVES, environment=environment(),
        configurations=configurations(), inputs={str(p): sha(p) for p in sorted(input_paths())},
        python=dict(path=sys.executable, sha256=sha(sys.executable), version=sys.version),
        downloads='not authorized; exact archives seeded and Cargo offline',
        scope='compile and actual selected-crate unit tests only; no capture runtime or cache-hit qualification')


def inventory(command, source):
    entries = command(['git', 'ls-files', '--stage', '-z'], cwd=source)['stdout'].split('\0')
    files = {}
    for entry in filter(None, entries):
        info, name = entry.split('\t', 1)
        mode, object_id, stage = info.split()
        require(stage == '0', 'unmerged compiler index')
        path = source / name
        if mode == '160000':
            files[name] = dict(kind='gitlink', object=object_id)
        elif mode == '120000':
            require(path.is_symlink(), 'tracked symlink changed')
            files[name] = dict(kind='symlink', target=os.readlink(path))
        else:
            require(path.is_file() and not path.is_symlink(), 'tracked compiler file changed')
            files[name] = dict(kind='file', sha256=sha(path))
    return files


def execute(args):
    plan_path = args.plan.resolve(strict=True)
    require(plan_path.parent == HERE and not args.plan.is_symlink(), 'plan must be owned by this experiment')
    plan = json.loads(plan_path.read_text())
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.attempt), 'invalid fresh attempt')
    work = ROOT / '.work' / 'hir-capture-check-01'
    out = work / 'stages' / args.attempt
    out.mkdir(parents=True, exist_ok=False)
    receipt = dict(status='waiting', stage=args.stage, owner=str(ROOT), pid=os.getpid(),
        parent_pid=os.getppid(), started_at=time.time(), plan=str(plan_path), plan_sha256=sha(plan_path), commands=[])
    write(out / 'receipt.json', receipt)
    try:
        with workload_lock(CANONICAL_LOCK, 600):
            receipt.update(admitted_at=time.time(), free_bytes_before=disk(ROOT, 24 if args.stage == 'prepare' else 8))
            require(plan == frozen_plan(), 'frozen check plan, environment or helper inputs changed')
            require(all(Path(p).is_file() and not Path(p).is_symlink() and sha(p) == h
                        for p, h in ARCHIVES.items()), 'required offline archive changed or missing')
            completed_path = work / 'completed.json'
            completed = json.loads(completed_path.read_text()) if completed_path.exists() else {}
            require(set(completed) == set(STAGES[:STAGES.index(args.stage)]), 'limited stages out of order')
            for prior in completed.values():
                require(sha(prior['path']) == prior['sha256'] and
                        json.loads(Path(prior['path']).read_text())['status'] == 'passed', 'prior stage changed')
            env = plan['environment']
            def command(argv, cwd=SOURCE):
                require(plan == frozen_plan(), 'check inputs changed before child')
                directory = out / 'commands' / f'{len(receipt["commands"]):03d}'
                ref = dict(path=str(directory / 'receipt.json'), command=list(map(str, argv)))
                receipt['commands'].append(ref)
                write(out / 'receipt.json', receipt)
                try:
                    result = run(argv, cwd=cwd, env=env, out=directory, capacity_root=ROOT)
                finally:
                    if (directory / 'receipt.json').exists():
                        ref['sha256'] = sha(directory / 'receipt.json')
                        write(out / 'receipt.json', receipt)
                return dict(result, stdout=(directory / 'stdout').read_text(), stderr=(directory / 'stderr').read_text())

            if args.stage == 'prepare':
                require(not SOURCE.exists() and not SOURCE.is_symlink(), 'compiler destination already exists')
                require(command(['git', 'rev-parse', 'HEAD'], cwd=DONOR)['stdout'].strip() == BASE,
                        'donor compiler revision changed')
                command(['git', 'clone', '--no-hardlinks', '--no-checkout', str(DONOR), str(SOURCE)], cwd=ROOT)
                command(['git', 'checkout', '-b', 'hir-capture-check', BASE])
                require((SOURCE / '.git').is_dir() and not (SOURCE / '.git/objects/info/alternates').exists(),
                        'compiler clone shares Git objects')
                write(SOURCE / '.rust-interp-owned.json', dict(owner=str(ROOT), plan_sha256=sha(plan_path)))
                command(['git', 'clone', '--no-hardlinks', '--no-checkout', str(DONOR / 'library/backtrace'),
                         str(SOURCE / 'library/backtrace')])
                command(['git', 'checkout', '--detach', BACKTRACE], cwd=SOURCE / 'library/backtrace')
                require(not (SOURCE / 'library/backtrace/.git/objects/info/alternates').exists(),
                        'backtrace clone shares Git objects')
                manifest = json.loads((HERE / 'inputs/patch.json').read_text())
                for name, item in manifest['files'].items():
                    path = SOURCE / name
                    require(sha(path) == item['before_sha256'] if item['before_sha256'] else not path.exists(),
                            'capture base bytes differ: ' + name)
                command(['git', 'apply', '--check', str(HERE / 'inputs/capture.patch')])
                command(['git', 'apply', str(HERE / 'inputs/capture.patch')])
                require(all(sha(SOURCE / p) == item['after_sha256'] for p, item in manifest['files'].items()),
                        'capture replacement bytes differ')
                command(['git', 'add', '--', *manifest['files']])
                command(['git', 'commit', '-m', 'Add capture-only HIR body journal checkpoint'])
                shutil.copy2(HERE / 'inputs/bootstrap.toml', SOURCE / 'bootstrap.toml')
                for original, expected in ARCHIVES.items():
                    archive = Path(original)
                    target = (SOURCE / 'build/cache' / ('llvm-' + HOST + '-' + UPSTREAM + '-false') / archive.name
                              if archive == LLVM else SOURCE / 'build/cache/2026-08-30' / archive.name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(archive, target)
                    require(sha(target) == expected, 'seeded archive differs')
                state = dict(revision=command(['git', 'rev-parse', 'HEAD'])['stdout'].strip(),
                    files=inventory(command, SOURCE), backtrace_files=inventory(command, SOURCE / 'library/backtrace'),
                    config_sha256=sha(SOURCE / 'bootstrap.toml'), plan_sha256=sha(plan_path))
                write(work / 'source.json', state)
            else:
                state = json.loads((work / 'source.json').read_text())
                require(state['plan_sha256'] == sha(plan_path) and SOURCE.resolve(strict=True) == SOURCE,
                        'owned compiler source identity differs')
                def source_guard():
                    require((SOURCE / '.git').is_dir() and not (SOURCE / '.git').is_symlink()
                            and json.loads((SOURCE / '.rust-interp-owned.json').read_text()) ==
                                dict(owner=str(ROOT), plan_sha256=sha(plan_path))
                            and command(['git', 'rev-parse', 'HEAD'])['stdout'].strip() == state['revision']
                            and not command(['git', 'diff', 'HEAD', '--'])['stdout']
                            and command(['git', 'rev-parse', 'HEAD'], cwd=SOURCE / 'library/backtrace')['stdout'].strip() == BACKTRACE
                            and sha(SOURCE / 'bootstrap.toml') == state['config_sha256']
                            and inventory(command, SOURCE) == state['files']
                            and inventory(command, SOURCE / 'library/backtrace') == state['backtrace_files'],
                            'frozen compiler source changed')
                source_guard()
                result = command(COMMANDS[args.stage])
                source_guard()
                if args.stage == 'unit':
                    text = result['stdout'] + result['stderr']
                    require(all(re.search(r'test .*\b' + re.escape(name) + r' \.\.\. ok', text)
                                for name in REQUIRED_TESTS), 'required capture unit tests did not all run and pass')
                receipt['source_sha256'] = sha(work / 'source.json')
            require(plan == frozen_plan(), 'inputs changed during limited stage')
            receipt.update(status='passed', finished_at=time.time(), free_bytes_after=disk(ROOT))
            write(out / 'receipt.json', receipt)
            completed[args.stage] = dict(path=str(out / 'receipt.json'), sha256=sha(out / 'receipt.json'))
            write(completed_path, completed)
    except BaseException as error:
        receipt.update(status='failed', error=repr(error), finished_at=time.time())
        write(out / 'receipt.json', receipt)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-plan', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--stage', choices=STAGES)
    parser.add_argument('--attempt')
    args = parser.parse_args()
    if args.write_plan:
        require(not args.plan and not args.stage and not args.attempt and not args.write_plan.exists(),
                'plan destination must be fresh and planning has no execution stage')
        require(args.write_plan.is_absolute() and args.write_plan.parent.resolve(strict=True) == HERE,
                'plan must have an absolute owned destination')
        with workload_lock(CANONICAL_LOCK, 600):
            write(args.write_plan, frozen_plan())
    else:
        require(args.plan and args.stage and args.attempt, 'explicit reviewed plan, stage and fresh attempt required')
        execute(args)


if __name__ == '__main__':
    main()
