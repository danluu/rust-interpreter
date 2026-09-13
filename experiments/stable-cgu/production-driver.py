#!/usr/bin/env python3
"""Staged owned production compiler setup/build; planning starts no workloads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time
import tomllib

from owned_stage import (CANONICAL_LOCK, bootstrap_source_links, disk, inventory,
                         require, run, sha, workload_lock, write)

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HOST = 'aarch64-apple-darwin'
BASE = '73a11f167216d3955c277ed47f9b8cc68208105b'
UPSTREAM = 'cea272fa356e94bd2ee2cadf376630aa0683867a'
BACKTRACE = 'd902726a1dcdc1e1c66f73d1162181b5423c645b'
LLVM_SHA = '0035445cb01c652999862c240d3c8ce663247abdc410482dde10f9e9c264bf8f'
SOURCE = Path('/Users/danluu/dev/rustc-stable-mono-production-20260913')
DONOR = Path('/Users/danluu/dev/rustc-stable-cgu-20260913')
LLVM = Path('/Users/danluu/dev/rust-interp-stable-cgu-20260913/.work/stable-cgu-compiler-setup-01/rust-dev-nightly-aarch64-apple-darwin.tar.xz')
PUBLIC = Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin')
PUBLIC_LIBRARY = PUBLIC / 'lib/rustlib/src/rust/library'
OLD_COMPARISON = Path('/Users/danluu/dev/rust-interp-stable-cgu-20260913/.work/stable-cgu-compiler-setup-01/rust-src-comparison.json')
STAGES = ['prepare', 'freeze-source', 'stage1', 'stage1-controls', 'stage2',
          'option-hash', 'stage2-controls', 'dist', 'package', 'native-controls', 'strip-controls', 'complete']
ALLOWANCE = dict(prepare=28, **{'freeze-source': 2, 'stage1': 20, 'stage1-controls': 2,
    'stage2': 10, 'option-hash': 2, 'stage2-controls': 2, 'dist': 6, 'package': 6,
    'native-controls': 1, 'strip-controls': 1, 'complete': 0})
ARCHIVES = {
    'rustc-beta-' + HOST + '.tar.xz': '0c20c4730544923b2ba9ab4ccf98cd22db6759d1d6cc2e5b8c99662b953163ac',
    'rust-std-beta-' + HOST + '.tar.xz': 'd8f4620f3672cae11fdb841a86d44215aeba2e656244286056f7742e966797e3',
    'cargo-beta-' + HOST + '.tar.xz': '473eed6c6004b83a306c4fcf34002560c292050a6c25247a8c1cbe3ad05b93b4',
    'rustfmt-nightly-' + HOST + '.tar.xz': 'fcc49f0698c09f8ff89ca044d0426dad2399da253d287c3aaabebf103b4a2820',
    'rustc-nightly-' + HOST + '.tar.xz': '9d494a6b72761dee6ec3c0ec085d5b29838565ef45bbb67b097caf0aa4750304',
}
COMMANDS = {
    'stage1': ['./x', 'build', '--stage', '1', 'compiler/rustc', 'library', '--jobs', '2', '-vv'],
    'stage1-controls': ['./x', 'test', '--stage', '1', 'tests/codegen-units/partitioning',
        'tests/run-make/stable-mono-cgu-partitioning', '--jobs', '2', '-vv'],
    'stage2': ['./x', 'build', '--stage', '2', 'compiler/rustc', 'library', '--jobs', '2', '-vv'],
    'option-hash': ['./x', 'test', '--stage', '2', 'compiler/rustc_interface',
        '--test-args', 'test_unstable_options_tracking_hash', '--jobs', '2', '-vv'],
    'stage2-controls': ['./x', 'test', '--stage', '2', 'tests/codegen-units/partitioning',
        'tests/run-make/stable-cgu-partitioning', 'tests/run-make/stable-mono-cgu-partitioning', '--jobs', '2', '-vv'],
    'dist': ['./x', 'dist', '--stage', '2', 'rustc-dev', 'rust-std', '--jobs', '2', '-vv'],
}


def environment():
    require(not any(k.startswith(('LD_', 'DYLD_')) for k in os.environ), 'loader overrides are unsupported')
    # Verbose bootstrap commands may print their environment. Pass only ordinary
    # build inputs, never the caller's unrelated credentials or service tokens.
    allowed = ['PATH', 'HOME', 'USER', 'LOGNAME', 'TMPDIR', 'LANG', 'LC_ALL', 'SHELL',
               'CARGO_HOME', 'RUSTUP_HOME', 'SDKROOT', 'DEVELOPER_DIR', 'MACOSX_DEPLOYMENT_TARGET']
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env.update(CARGO_BUILD_JOBS='2', CARGO_INCREMENTAL='0', RUST_TEST_THREADS='2',
               CARGO_NET_OFFLINE='true', CARGO_TERM_COLOR='never')
    return env


def input_paths():
    paths = [Path(__file__).resolve(), HERE / 'owned_stage.py', HERE / 'package-owned.py',
        HERE / 'native-entry-controls.py', HERE / 'strip-controls.py',
        HERE / 'bootstrap-production-source-paths.toml', HERE / 'mono-production-admission.json',
        HERE / 'MONO-PRODUCTION-ADMISSION.md',
        HERE / 'PRODUCTION-DRIVER.md', ROOT / 'tests/test_owned_compiler_stage.py', OLD_COMPARISON,
        ROOT / 'experiments/stable-mono-cgu/rustc.patch',
        ROOT / 'experiments/stable-mono-cgu/source-identity.json']
    paths += sorted((ROOT / 'scripts').glob('*.py'))
    return paths


def prepare_plan(args):
    require(args.output.is_absolute() and not args.output.exists(), 'plan output must be fresh and absolute')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = args.output.with_suffix('.process.json')
    require(not receipt_path.exists(), 'plan inventory attempt already exists')
    receipt = dict(supervisor_pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
        action='source-only plan inventory; no compiler or build', status='waiting',
        lock=str(CANONICAL_LOCK), lock_wait_seconds=600, output=str(args.output))
    write(receipt_path, receipt)
    try:
        with workload_lock(CANONICAL_LOCK, 600):
            receipt.update(status='admitted', admitted_at=time.time())
            write(receipt_path, receipt)
            _prepare_plan(args)
            receipt.update(status='passed', plan_sha256=sha(args.output), finished_at=time.time())
            write(receipt_path, receipt)
    except BaseException as error:
        receipt.update(status='failed', finished_at=time.time(), error_type=type(error).__name__, error=str(error))
        write(receipt_path, receipt)
        raise


def _prepare_plan(args):
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid run identity')
    require(not SOURCE.exists() and not SOURCE.is_symlink(), 'fresh compiler destination already exists')
    require(args.output.is_absolute() and not args.output.exists(), 'plan output must be fresh and absolute')
    inputs = {str(path): sha(path) for path in input_paths()}
    admission = json.loads((HERE / 'mono-production-admission.json').read_text())
    require(inputs[str(HERE / 'bootstrap-production-source-paths.toml')] == admission['bootstrap_sha256']
            and inputs[str(ROOT / 'experiments/stable-mono-cgu/rustc.patch')] == admission['mono_patch_sha256'],
            'reviewed configuration or patch changed')
    plan = dict(schema_version=1, kind='owned-staged-production-compiler', status='planned; not executed',
        owner=str(ROOT), run_id=args.run_id, source=str(SOURCE), donor=str(DONOR), host=HOST,
        base_commit=BASE, upstream_commit=UPSTREAM, backtrace_commit=BACKTRACE,
        source_commit=None, source_commit_rule='actual commit after exact patch and focused formatting',
        lock=str(CANONICAL_LOCK), lock_wait_seconds=600, initial_free_gib=36, running_floor_gib=8,
        stage_allowances_gib=ALLOWANCE, stages=STAGES, bootstrap_commands=COMMANDS,
        llvm=dict(path=str(LLVM), sha256=LLVM_SHA), rust_src_component=public_component(),
        stage0_archives={str(DONOR / 'build/cache/2026-08-30' / name): digest for name, digest in ARCHIVES.items()},
        inputs=inputs, interpreter_source_revision=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        python=dict(executable=sys.executable, sha256=sha(sys.executable), version=sys.version),
        environment=environment(), retry='explicit fresh attempt; no failure deletion or sample replacement',
        downloads='none requested; seed exact archives, Cargo offline; unexpected bootstrap download is a failed setup assumption',
        compiler_policy='both partitioning options default off while building compiler/native std',
        package='first production composition, complete stage2 components and exact source; native/strip controls mandatory',
        qualification='compiler package only; separate strict interpreter36 and measured27 still required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, plan)
    print(json.dumps(dict(plan=str(args.output), sha256=sha(args.output), status=plan['status'])))


def public_component():
    """Pin actual public distributed source, including its explicit vendoring."""
    require(PUBLIC_LIBRARY.resolve(strict=True) == PUBLIC_LIBRARY, 'public rust-src library is indirect')
    files = {name: proof['sha256'] for name, proof in inventory(PUBLIC_LIBRARY).items()}
    metadata = {name: sha(PUBLIC / 'lib/rustlib' / name)
                for name in ['manifest-rust-src', 'components', 'rust-installer-version']}
    old = json.loads(OLD_COMPARISON.read_text())
    require(old['source_commit'] == BASE and not old['mismatched'] and not old['backtrace']['mismatched']
            and metadata == old['installed_component_metadata'], 'public component provider identity changed')
    for name, digest in old['checked'].items():
        require(files[name.removeprefix('library/')] == digest, 'public tracked library source changed')
    for name, digest in old['backtrace']['checked'].items():
        require(files['backtrace/' + name] == digest, 'public backtrace source changed')
    return dict(path=str(PUBLIC_LIBRARY), files=files, installer_metadata=metadata,
                prior_comparison_sha256=sha(OLD_COMPARISON))


def source_inventory(command, source):
    records = command(['git', 'ls-files', '--stage', '-z'], cwd=source)['stdout'].split('\0')
    files, links, gitlinks = {}, {}, {}
    for record in records:
        if not record:
            continue
        fields, name = record.split('\t', 1)
        mode, object_id, stage = fields.split()
        require(stage == '0', 'unmerged compiler source')
        path = source / name
        if mode == '160000':
            gitlinks[name] = object_id
        elif mode == '120000':
            require(path.is_symlink(), 'tracked source symlink changed type')
            links[name] = os.readlink(path)
        else:
            require(path.is_file() and not path.is_symlink(), 'tracked source is missing or indirect')
            files[name] = sha(path)
    return dict(files=files, symlinks=links, gitlinks=gitlinks)


def check_frozen(command, source, frozen):
    require(source.resolve(strict=True) == source and (source / '.git').is_dir(),
            'owned compiler source became indirect')
    require(json.loads((source / '.rust-interp-owned.json').read_text())['owner'] == str(ROOT),
            'compiler source owner changed')
    require(command(['git', 'rev-parse', 'HEAD'], cwd=source)['stdout'].strip() == frozen['source_commit'],
            'frozen compiler commit changed')
    require(not command(['git', 'diff', 'HEAD', '--'], cwd=source)['stdout'], 'frozen compiler source changed')
    require(source_inventory(command, source) == frozen['inventory'], 'frozen source inventory changed')
    backtrace = source / 'library/backtrace'
    require(command(['git', 'rev-parse', 'HEAD'], cwd=backtrace)['stdout'].strip() == BACKTRACE
            and not command(['git', 'diff', 'HEAD', '--'], cwd=backtrace)['stdout'], 'backtrace source changed')
    require(source_inventory(command, backtrace) == frozen['backtrace'], 'backtrace inventory changed')
    require(sha(source / 'bootstrap.toml') == frozen['config_sha256'], 'bootstrap configuration changed')


def execute_stage(args):
    plan_path = args.plan.resolve(strict=True)
    plan = json.loads(plan_path.read_text())
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', plan['run_id'])
            and plan['schema_version'] == 1 and plan['kind'] == 'owned-staged-production-compiler'
            and plan['base_commit'] == BASE and plan['upstream_commit'] == UPSTREAM
            and plan['backtrace_commit'] == BACKTRACE and plan['host'] == HOST
            and plan['source_commit'] is None and plan['lock_wait_seconds'] == 600
            and plan['llvm'] == dict(path=str(LLVM), sha256=LLVM_SHA)
            and plan['stage0_archives'] == {str(DONOR / 'build/cache/2026-08-30' / name): digest
                                           for name, digest in ARCHIVES.items()},
            'plan pins or owned run identity differ')
    require(plan['owner'] == str(ROOT) and plan['source'] == str(SOURCE) and plan['donor'] == str(DONOR)
            and plan['stages'] == STAGES and plan['bootstrap_commands'] == COMMANDS
            and plan['stage_allowances_gib'] == ALLOWANCE and plan['lock'] == str(CANONICAL_LOCK)
            and plan['initial_free_gib'] == 36 and plan['running_floor_gib'] == 8,
            'staged plan identity or admission limits differ')
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.attempt), 'invalid fresh attempt identity')
    work = ROOT / '.work' / plan['run_id']
    out = work / 'stages' / args.attempt
    out.mkdir(parents=True, exist_ok=False)
    record = dict(schema_version=1, owner=str(ROOT), supervisor_pid=os.getpid(), parent_pid=os.getppid(),
        stage=args.stage, attempt=args.attempt, plan=str(plan_path), plan_sha256=sha(plan_path),
        source=str(SOURCE), started_at=time.time(), status='waiting', lock=plan['lock'], commands=[])
    write(out / 'receipt.json', record)
    completed_path = work / 'completed.json'
    try:
        with workload_lock(CANONICAL_LOCK, plan['lock_wait_seconds']) as lock_fd:
            record.update(status='admitted', admitted_at=time.time(),
                          free_bytes_before=disk(ROOT, 8 + ALLOWANCE[args.stage]))
            write(out / 'receipt.json', record)
            require(set(plan['inputs']) == set(map(str, input_paths()))
                    and all(sha(p) == h for p, h in plan['inputs'].items()), 'frozen driver or input changed')
            require(plan['environment'] == environment(), 'reviewed build environment changed')
            require(plan['python'] == dict(executable=sys.executable, sha256=sha(sys.executable), version=sys.version),
                    'reviewed supervisor Python changed')
            completed = json.loads(completed_path.read_text()) if completed_path.exists() else {}
            position = STAGES.index(args.stage)
            require(set(completed) == set(STAGES[:position]), 'stages must run exactly once in reviewed order')
            for stage, proof in completed.items():
                require(sha(proof['path']) == proof['sha256'], 'prior stage receipt changed')
                require(json.loads(Path(proof['path']).read_text())['status'] == 'passed', 'prior stage failed')
            env = plan['environment']
            def command(argv, cwd=SOURCE, expected=(0,), fds=()):
                directory = out / 'commands' / f'{len(record["commands"]):03d}'
                reference = dict(receipt=str(directory / 'receipt.json'), command=list(map(str, argv)), status='starting')
                record['commands'].append(reference)
                write(out / 'receipt.json', record)
                try:
                    item = run(argv, cwd=cwd, env=env, out=directory, capacity_root=ROOT,
                               expected=expected, pass_fds=fds)
                finally:
                    if (directory / 'receipt.json').exists():
                        retained = json.loads((directory / 'receipt.json').read_text())
                        reference.update(sha256=sha(directory / 'receipt.json'), status=retained['status'],
                                         returncode=retained.get('returncode'))
                        write(out / 'receipt.json', record)
                return item | dict(stdout=(directory / 'stdout').read_text(errors='strict'),
                                   stderr=(directory / 'stderr').read_text(errors='strict'))
            state_path = work / 'source.json'
            frozen = json.loads(state_path.read_text()) if state_path.exists() else None
            if args.stage not in ['prepare', 'freeze-source']:
                require(frozen is not None, 'compiler source is not frozen')
                check_frozen(command, SOURCE, frozen)
                record.update(source_revision=frozen['source_commit'], config_sha256=frozen['config_sha256'],
                              source_receipt_sha256=sha(state_path))
            if args.stage == 'prepare':
                require(not SOURCE.exists() and not SOURCE.is_symlink(), 'compiler destination is not fresh')
                for path, digest in plan['stage0_archives'].items():
                    require(sha(path) == digest, 'stage0 archive differs: ' + path)
                require(sha(plan['llvm']['path']) == plan['llvm']['sha256'] == LLVM_SHA, 'LLVM archive differs')
                command(['git', 'clone', '--no-hardlinks', '--no-checkout', str(DONOR), str(SOURCE)], cwd=ROOT)
                command(['git', 'checkout', '-b', 'stable-mono-production', BASE])
                require((SOURCE / '.git').is_dir() and not (SOURCE / '.git/objects/info/alternates').exists(),
                        'compiler clone shares Git object storage')
                marker = dict(owner=str(ROOT), plan_sha256=sha(plan_path), source=str(SOURCE), base_commit=BASE)
                write(SOURCE / '.rust-interp-owned.json', marker)
                command(['git', 'clone', '--no-hardlinks', '--no-checkout', str(DONOR / 'library/backtrace'),
                         str(SOURCE / 'library/backtrace')])
                command(['git', 'checkout', '--detach', BACKTRACE], cwd=SOURCE / 'library/backtrace')
                require(not (SOURCE / 'library/backtrace/.git/objects/info/alternates').exists(), 'shared backtrace objects')
                admission = json.loads((HERE / 'mono-production-admission.json').read_text())
                for path, digest in admission['reviewed_pinned_source_files'].items():
                    require(sha(SOURCE / path) == digest, 'pinned bootstrap source differs')
                identities = json.loads((ROOT / 'experiments/stable-mono-cgu/source-identity.json').read_text())
                patch = ROOT / 'experiments/stable-mono-cgu/rustc.patch'
                require(sha(patch) == identities['patch_sha256'] == admission['mono_patch_sha256'], 'patch differs')
                for item in identities['files']:
                    path = SOURCE / item['path']
                    require(sha(path) == item['base_sha256'] if item['base_sha256'] else not path.exists(),
                            'compiler patch base differs')
                command(['git', 'apply', '--check', str(patch)])
                command(['git', 'apply', str(patch)])
                require(all(sha(SOURCE / item['path']) == item['patched_sha256'] for item in identities['files']),
                        'patched compiler bytes differ')
                shutil.copy2(HERE / 'bootstrap-production-source-paths.toml', SOURCE / 'bootstrap.toml')
                stage0 = dict(line.split('=', 1) for line in (SOURCE / 'src/stage0').read_text().splitlines()
                              if '=' in line and not line.startswith('#'))
                for path, digest in plan['stage0_archives'].items():
                    name = Path(path).name
                    require(stage0['dist/2026-08-30/' + name] == digest, 'stage0 manifest archive differs')
                    destination = SOURCE / 'build/cache/2026-08-30' / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, destination)
                    require(sha(destination) == digest, 'seeded stage0 copy differs')
                destination = SOURCE / ('build/cache/llvm-' + HOST + '-' + UPSTREAM + '-false') / LLVM.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(LLVM, destination)
                require(sha(destination) == LLVM_SHA, 'seeded LLVM copy differs')
                for argv in [['/usr/bin/sw_vers'], ['xcrun', '--show-sdk-path'], ['xcrun', '--show-sdk-version'],
                             ['xcrun', 'clang', '--version'], ['xcrun', 'ld', '-version_details']]:
                    command(argv)
                record.update(base_revision=BASE, patched_files=identities['files'], marker=marker,
                              archive_sources=plan['stage0_archives'] | {str(LLVM): LLVM_SHA})
            elif args.stage == 'freeze-source':
                require(frozen is None, 'source is already frozen')
                marker = json.loads((SOURCE / '.rust-interp-owned.json').read_text())
                require(marker['owner'] == str(ROOT) and marker['plan_sha256'] == sha(plan_path), 'source ownership differs')
                identities = json.loads((ROOT / 'experiments/stable-mono-cgu/source-identity.json').read_text())
                files = [item['path'] for item in identities['files']]
                require(all(sha(SOURCE / item['path']) == item['patched_sha256'] for item in identities['files']),
                        'source changed before focused formatting')
                before = command(['git', 'diff', '--binary', BASE, '--'])['stdout']
                (out / 'pre-format.patch').write_text(before)
                check = command(['./x', 'fmt', '--check', *files], expected=(0, 1))
                if check['returncode']:
                    command(['./x', 'fmt', *files])
                    command(['./x', 'fmt', '--check', *files])
                changed = set(command(['git', 'diff', '--name-only', BASE, '--'])['stdout'].splitlines())
                require(changed <= set(files), 'focused formatting changed another source file')
                command(['git', 'add', '--', *files])
                command(['git', 'commit', '-m', 'Add stable per-MonoItem codegen placement to the production compiler'])
                revision = command(['git', 'rev-parse', 'HEAD'])['stdout'].strip()
                require(re.fullmatch('[0-9a-f]{40}', revision) and revision not in [BASE, UPSTREAM], 'new source commit missing')
                command(['git', 'merge-base', '--is-ancestor', BASE, revision])
                combined = command(['git', 'diff', '--binary', UPSTREAM, revision, '--'])['stdout']
                (work / 'combined-upstream.patch').write_text(combined)
                (work / 'mono-formatted.patch').write_text(command(['git', 'diff', '--binary', BASE, revision, '--'])['stdout'])
                frozen = dict(source_commit=revision, base_commit=BASE, upstream_commit=UPSTREAM,
                    config_sha256=sha(SOURCE / 'bootstrap.toml'), inventory=source_inventory(command, SOURCE),
                    backtrace=source_inventory(command, SOURCE / 'library/backtrace'),
                    combined_patch_sha256=sha(work / 'combined-upstream.patch'),
                    formatted_mono_patch_sha256=sha(work / 'mono-formatted.patch'))
                write(state_path, frozen)
                check_frozen(command, SOURCE, frozen)
                record.update(source_revision=revision, config_sha256=frozen['config_sha256'], source_receipt_sha256=sha(state_path))
            elif args.stage in COMMANDS:
                item = command(COMMANDS[args.stage])
                record['command'] = item['command']
                llvm_root = SOURCE / 'build' / HOST / 'ci-llvm'
                require((llvm_root / '.llvm-stamp').read_text() == UPSTREAM + 'false',
                        'bootstrap selected a different CI LLVM identity')
                record['llvm_stamp'] = dict(path=str(llvm_root / '.llvm-stamp'), sha256=sha(llvm_root / '.llvm-stamp'))
                artifact_roots = []
                if args.stage in ['stage2', 'option-hash', 'stage2-controls']:
                    artifact_roots = [SOURCE / 'build' / HOST / 'stage2']
                elif args.stage == 'dist':
                    artifact_roots = [SOURCE / 'build/tmp/tarball' / name / HOST / 'image'
                                      for name in ['rustc-dev', 'rust-std']]
                stage2_root = SOURCE / 'build' / HOST / 'stage2'
                record['artifact_inventories'] = {
                    str(path): inventory(path, source_checkout=SOURCE if path == stage2_root else None)
                    for path in artifact_roots}
                record['artifact_source_links'] = {
                    str(path): bootstrap_source_links(path, SOURCE)
                    for path in artifact_roots if path == stage2_root}
                record['returncode'] = 0
            elif args.stage == 'package':
                package_stage(command, work, out, completed, frozen, lock_fd, record, plan['rust_src_component'])
            elif args.stage in ['native-controls', 'strip-controls']:
                prefix = work / 'packaged-stage2-01'
                script = 'native-entry-controls.py' if args.stage == 'native-controls' else 'strip-controls.py'
                command([sys.executable, HERE / script, '--compiler', prefix / 'bin/rustc',
                    '--package-provenance', work / 'package-01/provenance.json', '--receipt', out / 'controls',
                    '--partitioning-policy', 'stable-mono-cgu', '--lock-fd', str(lock_fd),
                    '--lock-wait-seconds', '600'], cwd=ROOT, fds=(lock_fd,))
                result = json.loads((out / 'controls/result.json').read_text())
                require(result['status'] == 'passed', 'native/strip control failed')
                record['control_result'] = dict(path=str(out / 'controls/result.json'), sha256=sha(out / 'controls/result.json'))
            else:
                package = json.loads((work / 'package-01/receipt.json').read_text())
                prefix = Path(package['prefix'])
                require({p: v['sha256'] for p, v in inventory(prefix).items()} == package['files'], 'package changed during controls')
                record.update(package=str(prefix), provenance=str(work / 'package-01/provenance.json'),
                              final_compiler_qualification=False, next_gate='strict interpreter integration, then matched27 screen')
            if frozen is not None:
                check_frozen(command, SOURCE, frozen)
            record.update(status='passed', returncode=0, finished_at=time.time(), free_bytes_after=disk(ROOT))
            write(out / 'receipt.json', record)
            completed[args.stage] = dict(path=str(out / 'receipt.json'), sha256=sha(out / 'receipt.json'))
            write(completed_path, completed)
            print(json.dumps(dict(stage=args.stage, status='passed', receipt=str(out / 'receipt.json'))))
    except BaseException as error:
        record.update(status='failed', finished_at=time.time(), error_type=type(error).__name__, error=str(error))
        write(out / 'receipt.json', record)
        raise


def package_stage(command, work, out, completed, frozen, lock_fd, record, component):
    from importlib import import_module
    sys.path.insert(0, str(ROOT / 'scripts'))
    source_capability = import_module('std_mir_source_paths').source_capability
    capability = work / 'source-capability.json'
    write(capability, source_capability(frozen['source_commit']))
    rust_src = work / 'rust-src'
    require(not rust_src.exists(), 'first package source destination exists')
    require(public_component() == component, 'pinned public rust-src component changed')
    shutil.copytree(PUBLIC_LIBRARY, rust_src / 'library', symlinks=False)
    copied = inventory(rust_src)
    require({name.removeprefix('library/'): proof['sha256'] for name, proof in copied.items()}
            == component['files'], 'distributed library source copy differs')
    comparison = work / 'source-comparison.json'
    checked, missing = {}, []
    for name, digest in frozen['inventory']['files'].items():
        if name.startswith('library/'):
            if name in copied:
                require(copied[name]['sha256'] == digest == sha(SOURCE / name), 'new compiler library differs from distribution')
                checked[name] = digest
            else:
                missing.append(name)
    backtrace, backtrace_missing = {}, []
    for name, digest in frozen['backtrace']['files'].items():
        if 'library/backtrace/' + name in copied:
            require(copied['library/backtrace/' + name]['sha256'] == digest
                    == sha(SOURCE / 'library/backtrace' / name), 'new compiler backtrace differs from distribution')
            backtrace[name] = digest
        else:
            backtrace_missing.append(name)
    old = json.loads(OLD_COMPARISON.read_text())
    require(sorted(missing) == sorted(old['missing'])
            and sorted(backtrace_missing) == sorted(old['backtrace']['missing']), 'new distribution omissions differ')
    extras = {name: proof['sha256'] for name, proof in copied.items()
              if name not in checked and name.removeprefix('library/backtrace/') not in backtrace}
    require(all(name.startswith('library/vendor/') or name == 'library/.cargo/config.toml'
                for name in extras), 'unrecognized distribution-only source file')
    lock = tomllib.loads((rust_src / 'library/Cargo.lock').read_text())
    packages = {(p['name'], p['version']): p.get('checksum') for p in lock['package']}
    vendors = {}
    for directory in sorted((rust_src / 'library/vendor').iterdir()):
        require(directory.is_dir() and not directory.is_symlink(), 'invalid distributed vendor directory')
        checksum = json.loads((directory / '.cargo-checksum.json').read_text())
        manifest = tomllib.loads((directory / 'Cargo.toml').read_text())['package']
        require(checksum['package'] == packages[(manifest['name'], manifest['version'])],
                'distributed vendor package differs from library lockfile')
        actual = {name: proof['sha256'] for name, proof in inventory(directory).items()}
        require(actual == checksum['files'] | {'.cargo-checksum.json': sha(directory / '.cargo-checksum.json')},
                'distributed vendor file differs from Cargo checksum')
        vendors[directory.name] = dict(package=manifest['name'], version=manifest['version'],
                                       checksum=checksum['package'], checksum_file=sha(directory / '.cargo-checksum.json'))
    write(comparison, dict(source_commit=frozen['source_commit'], checked=checked, missing=missing, mismatched=[],
        backtrace=dict(checked=backtrace, missing=backtrace_missing, mismatched=[]),
        distributed_component=component, distribution_only=extras, vendor_packages=vendors,
        distribution_only_configuration={name: (rust_src / name).read_text() for name in extras
                                          if name == 'library/.cargo/config.toml'},
        vendor_provenance='pinned installed public rust-src component; full files and Cargo checksum/lock binding; no crate archive assertion'))
    archive = SOURCE / ('build/cache/llvm-' + HOST + '-' + UPSTREAM + '-false') / LLVM.name
    objcopy = SOURCE / 'build' / HOST / 'ci-llvm/bin/llvm-objcopy'
    member_name = 'rust-dev-nightly-' + HOST + '/rust-dev/bin/llvm-objcopy'
    with tarfile.open(archive, 'r:xz') as reader:
        member = reader.getmember(member_name)
        digest = hashlib.sha256(reader.extractfile(member).read()).hexdigest()
    require(sha(archive) == LLVM_SHA and sha(objcopy) == digest, 'native support tool differs from CI archive')
    proof = work / 'llvm-source-proof.json'
    write(proof, dict(schema_version=1, archive=str(archive), archive_sha256=LLVM_SHA, member=member_name,
        member_sha256=digest, files={str(objcopy): dict(size=objcopy.stat().st_size, sha256=digest)}))
    command([sys.executable, HERE / 'package-owned.py', '--first-production', '--source-capability', capability,
        '--source', SOURCE, '--stage2', SOURCE / 'build' / HOST / 'stage2',
        '--std-image', SOURCE / 'build/tmp/tarball/rust-std' / HOST / 'image',
        '--dev-image', SOURCE / 'build/tmp/tarball/rustc-dev' / HOST / 'image',
        '--rust-src', rust_src, '--source-comparison', comparison,
        '--build-receipt', completed['stage2-controls']['path'], '--original-build-receipt', completed['stage2']['path'],
        '--dist-receipt', completed['dist']['path'], '--patch', work / 'combined-upstream.patch',
        '--llvm-objcopy', objcopy, '--llvm-source-proof', proof, '--prefix', work / 'packaged-stage2-01',
        '--receipt', work / 'package-01', '--host', HOST, '--lock-fd', str(lock_fd),
        '--lock-wait-seconds', '600'], cwd=ROOT, fds=(lock_fd,))
    record['package_receipt'] = dict(path=str(work / 'package-01/receipt.json'), sha256=sha(work / 'package-01/receipt.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    plan = commands.add_parser('plan', help='write a source-only, unexecuted plan')
    plan.add_argument('--run-id', required=True)
    plan.add_argument('--output', type=Path, required=True)
    execute = commands.add_parser('run', help='admit exactly one reviewed stage')
    execute.add_argument('--plan', type=Path, required=True)
    execute.add_argument('--stage', choices=STAGES, required=True)
    execute.add_argument('--attempt', required=True)
    args = parser.parse_args()
    require(__debug__, 'run Python without -O')
    if args.action == 'plan':
        prepare_plan(args)
    else:
        execute_stage(args)


if __name__ == '__main__':
    main()
