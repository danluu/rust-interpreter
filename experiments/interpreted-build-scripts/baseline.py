#!/usr/bin/env python3
"""Native-only, instrumented correctness baseline for the local build-script fixture."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
WORK = ROOT / '.work/interpreted-build-scripts-native-01'
FIXTURE = HERE / 'fixture'
APP = WORK / 'fixture'
HOST = 'aarch64-apple-darwin'
TOOLCHAIN = Path.home() / '.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin'
RUSTC, CARGO = TOOLCHAIN / 'bin/rustc', TOOLCHAIN / 'bin/cargo'
REVISION = 'cea272fa356e94bd2ee2cadf376630aa0683867a'
TESTS = ['tests::cargo_directives_reach_compilation', 'tests::generated_file_matches_current_helper_and_inputs',
         'tests::proc_macro_uses_its_actual_dependency_mode']
EDITABLE = ['app/build.rs', 'helper/src/lib.rs', 'app/input.txt']
OUTPUTS = ['generated.rs', 'history.txt', 'context.txt', 'before-unsupported.txt', 'child-version.txt']
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'experiments/stable-cgu'))
from owned_stage import CANONICAL_LOCK, disk, require, run, sha, workload_lock, write
from workflow_io import SourceEdit
from custom_cargo_libraries import library_closure, library_state, platform_identity
from toolchain_lookup import _stamp


def ordinary(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path and path.is_file() and not path.is_symlink(),
            'nonordinary file: ' + str(path))
    return path


def identity(path):
    path = Path(path); before = _stamp(path)
    value = dict(path=str(path), stamp=before, sha256=sha(path))
    require(_stamp(path) == before, 'input changed while hashing')
    return value


def inventory(root, excluded=()):
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'fixture/inventory contains symlink')
        if path.is_file() and path not in excluded:
            result[str(path.relative_to(root))] = sha(path)
    return result


def inputs():
    files = [Path(__file__), HERE / 'BASELINE.md', HERE / 'README.md', ROOT / 'tests/test_interpreted_build_scripts_baseline.py',
             ROOT / 'scripts/supervise_experiment.py', ROOT / 'scripts/workflow_io.py',
             ROOT / 'scripts/custom_cargo_libraries.py', ROOT / 'scripts/custom_compiler.py',
             ROOT / 'scripts/toolchain_lookup.py', ROOT / 'experiments/stable-cgu/owned_stage.py',
             *[p for p in FIXTURE.rglob('*') if p.is_file()]]
    return {str(ordinary(p)): sha(p) for p in files}


def environment():
    # Explicit small allowlist; inherited compiler/profile/loader credentials or
    # interpreter settings never enter the ordinary Cargo child environment.
    env = {k: os.environ[k] for k in ['HOME', 'USER', 'LOGNAME', 'TMPDIR', 'LANG', 'LC_ALL', 'LC_CTYPE'] if k in os.environ}
    env.update(PATH=str(Path(sys.executable).resolve().parent) + ':/usr/bin:/bin:/usr/sbin:/sbin',
        RUSTC=str(RUSTC), RUSTUP_TOOLCHAIN='nightly-2026-09-08', CARGO_HOME=str(WORK / 'cargo-home'),
        CARGO_TERM_COLOR='never', CARGO_NET_OFFLINE='true', RUSTC_WRAPPER=str(Path(__file__).resolve()),
        RUSTC_WORKSPACE_WRAPPER='', PYTHONDONTWRITEBYTECODE='1')
    return env


def configurations():
    dirs = [ROOT, APP, APP / 'app', APP / 'helper', APP / 'macros']
    paths = {p / '.cargo' / n for d in dirs for p in [d, *d.parents] for n in ['config', 'config.toml']}
    paths.update(WORK / 'cargo-home' / n for n in ['config', 'config.toml'])
    for path in paths:
        require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents), 'configuration symlink')
        require(not path.exists(), 'unreviewed Cargo configuration: ' + str(path))
    return {str(p): None for p in sorted(paths)}


def cases():
    result = []
    def add(label, group='default', multiplier=3, value=11, seed=None, wrong=False, error=None):
        result.append(dict(label=label, group=group, multiplier=multiplier, input=value, seed=seed, wrong=wrong, error=error))
    add('original'); add('unchanged'); add('helper-five', multiplier=5)
    add('input-seventeen', multiplier=5, value=17); add('seed-four', multiplier=5, value=17, seed=4)
    add('restore'); add('wrong-generated-value', wrong=True); add('restore-wrong')
    for target in ['app/build.rs', 'helper/src/lib.rs']:
        for kind in ['type', 'borrow', 'const', 'panic']:
            add(target.split('/')[0] + '-' + kind, error=dict(target=target, kind=kind))
            add('restore-' + target.split('/')[0] + '-' + kind)
    add('shared-original', 'shared'); add('shared-helper-five', 'shared', multiplier=5); add('shared-restore', 'shared')
    add('unsupported-native', 'unsupported')
    require(len(result) == 28, 'fixed native command count')
    return result


def argv(case):
    command = [str(CARGO), 'test', '--manifest-path', str(APP / 'Cargo.toml'), '--package', 'ibs-fixture-app',
               '--lib', '--target', HOST, '--locked', '--offline', '--jobs', '2', '--message-format=json']
    if case['group'] != 'default':
        command += ['--features', {'shared': 'native-shared-helper', 'unsupported': 'unsupported-build-operation'}[case['group']]]
    return command


def sources(case, templates):
    result = {name: templates[name] for name in EDITABLE}
    old = b'input * 3 + seed'; require(result['helper/src/lib.rs'].count(old) == 1, 'helper edit anchor changed')
    result['helper/src/lib.rs'] = result['helper/src/lib.rs'].replace(old, f'input * {case["multiplier"]} + seed'.encode())
    result['app/input.txt'] = f'{case["input"]}\n'.encode()
    if case['wrong']:
        old = b'let value = ibs_fixture_helper::transform(input, seed);'
        require(result['app/build.rs'].count(old) == 1, 'wrong-value edit anchor changed')
        result['app/build.rs'] = result['app/build.rs'].replace(old, b'let value = ibs_fixture_helper::transform(input, seed) + 1;')
    if case['error']:
        error = case['error']; marker = b'// QUALIFICATION_ERROR_SLOT'
        require(result[error['target']].count(marker) == 1, 'error slot changed')
        result[error['target']] = result[error['target']].replace(marker, templates['controls/' + error['kind'] + '.rs'])
    return result


def compiler_wrapper():
    # Cargo supplies the exact public RUSTC as argv[1]. exec preserves stdout,
    # stderr and all inherited jobserver FDs. The record is an exec request,
    # not an invented post-exec/exit observation.
    require(sys.argv[1] == str(RUSTC), 'wrapper received a different compiler')
    directory = Path(os.environ['IBS_BASELINE_COMPILER_RECORDS'])
    require(directory.resolve(strict=True) == directory and directory.is_relative_to(WORK / 'commands'), 'unowned wrapper receipt')
    require(sha(RUSTC) == os.environ['IBS_BASELINE_RUSTC_SHA'] and sha(Path(__file__)) == os.environ['IBS_BASELINE_WRAPPER_SHA'],
            'recorded compiler/wrapper changed')
    path = directory / (str(os.getpid()) + '.json')
    require(not path.exists(), 'compiler record collision')
    record = dict(status='exec-request', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
                  cwd=os.getcwd(), argv=sys.argv[1:], environment=dict(os.environ), executable_sha256=sha(RUSTC))
    write(path, record)
    try:
        os.execv(str(RUSTC), sys.argv[1:])
    except BaseException as error:
        record.update(status='exec-failed', error=repr(error)); write(path, record); raise


def public_inputs(command):
    files = {str(p): identity(p) for p in [RUSTC, CARGO, Path(sys.executable).resolve()]}
    closures = {}
    def inspect(args, *, text):
        require(text is True and args[0] == '/usr/bin/otool', 'unexpected closure inspector')
        return command(args)['stdout']
    for path in [RUSTC, CARGO]:
        closure, state = library_closure(path, HOST, inspect=inspect)
        closures[str(path)] = dict(identity=closure, state=state)
        for item in closure['libraries']: files[item['logical']] = identity(Path(item['logical']))
    lib = TOOLCHAIN / 'lib/rustlib' / HOST / 'lib'
    std = inventory(lib)
    for name in std: files[str(lib / name)] = identity(lib / name)
    for crate in ['core', 'alloc', 'std', 'test', 'proc_macro']:
        require(any(n.startswith('lib' + crate + '-') and n.endswith('.rlib') for n in std), 'native std missing ' + crate)
    versions = {name: command(args)['stdout'] for name, args in [
        ('rustc_verbose', [str(RUSTC), '-vV']), ('rustc_version', [str(RUSTC), '--version']),
        ('sysroot', [str(RUSTC), '--print', 'sysroot']), ('cargo', [str(CARGO), '-Vv'])]}
    require('commit-hash: ' + REVISION in versions['rustc_verbose'] and 'host: ' + HOST in versions['rustc_verbose']
            and versions['sysroot'].strip() == str(TOOLCHAIN), 'wrong public compiler')
    return dict(versions=versions, files=files, closures=closures, std_root=str(lib), std=std, platform=platform_identity())


def guard_public(public, rehash=False):
    require(platform_identity() == public['platform'], 'system platform changed')
    for record in public['files'].values():
        require(_stamp(Path(record['path'])) == record['stamp'], 'public tool/std/library identity changed')
        if rehash: require(sha(record['path']) == record['sha256'], 'public tool/std/library content changed')
    for closure in public['closures'].values():
        require(library_state(closure['identity']) == closure['state'], 'public library search changed')
    lib = Path(public['std_root'])
    require(sorted(str(p.relative_to(lib)) for p in lib.rglob('*') if p.is_file()) == sorted(public['std']), 'native std inventory changed')


def cargo_records(stdout):
    records, text = [], []
    for line in stdout.splitlines():
        if line.startswith('{'):
            try: record = json.loads(line)
            except json.JSONDecodeError: text.append(line); continue
            if isinstance(record, dict) and 'reason' in record: records.append(record); continue
        text.append(line)
    return records, '\n'.join(text)


def outcomes(case, records, text, returncode):
    found = re.findall(r'^test (tests::[a-z_]+) \.\.\. (ok|FAILED)$', text, re.M)
    errors = [r['message'] for r in records if r.get('reason') == 'compiler-message' and r['message']['level'] == 'error']
    if case['error']:
        code = dict(type='E0308', borrow='E0499', const='E0080', panic='unconditional_panic')[case['error']['kind']]
        require(returncode == 101 and not re.search(r'^test \S+ \.\.\. ', text, re.M)
                and any((m.get('code') or {}).get('code') == code for m in errors),
                'uncalled compilation failure/test nonexecution mismatch')
    else:
        require(sorted(n for n, _ in found) == TESTS and not errors, 'exact three native tests/diagnostics differ')
        failed = [n for n, status in found if status == 'FAILED']
        require(failed == (['tests::generated_file_matches_current_helper_and_inputs'] if case['wrong'] else [])
                and returncode == (101 if case['wrong'] else 0), 'wrong native outcome')
    return dict(tests=found, compiler_errors=errors)


def app_record(row):
    return 'ibs-fixture-app@' in row.get('package_id', '')


def contained(path, target):
    path = ordinary(path); require(path.is_relative_to(target), 'Cargo artifact escaped owned target'); return path


def output_snapshot(out_dir):
    return {name: dict(sha256=sha(out_dir / name), stamp=_stamp(out_dir / name), text=(out_dir / name).read_text())
            for name in OUTPUTS if (out_dir / name).exists()}


def script_outputs(case, out_dir, target, before, version):
    require(out_dir.resolve(strict=True) == out_dir and out_dir.is_relative_to(target), 'unowned OUT_DIR')
    current = output_snapshot(out_dir)
    if case['error'] or case['label'] == 'unchanged':
        require(current == before, 'script effects occurred during compile failure or freshness reuse')
        return dict(files=current, actual_runs=0)
    require(all(n in current for n in ['generated.rs', 'history.txt', 'context.txt']), 'missing actual script outputs')
    seed = 3 if case['seed'] is None else case['seed']; value = case['input'] * case['multiplier'] + seed + int(case['wrong'])
    mode = 'native-shared' if case['group'] == 'shared' else 'script-only'
    generated = f'pub const GENERATED_VALUE: u64 = {value};\npub const GENERATED_INPUT: u64 = {case["input"]};\npub const GENERATED_SEED: u64 = {seed};\n'
    require(current['generated.rs']['text'] == generated, 'actual generated bytes differ')
    prefix = before.get('history.txt', {}).get('text', '')
    require(current['history.txt']['text'] == prefix + f'input={case["input"]};seed={seed};mode={mode};value={value}\n', 'actual script run count/history differs')
    context = dict(line.split('=', 1) for line in current['context.txt']['text'].splitlines())
    require(context == dict(OUT_DIR=str(out_dir), CARGO_MANIFEST_DIR=str(APP / 'app'), HOST=HOST, TARGET=HOST,
        PROFILE='debug', OPT_LEVEL='0', DEBUG='true', NUM_JOBS='2'), 'actual Cargo script context differs')
    directives = ['cargo::rerun-if-changed=build.rs', 'cargo:rerun-if-changed=input.txt',
        'cargo::rerun-if-env-changed=IBS_FIXTURE_SEED', 'cargo::rustc-check-cfg=cfg(ibs_seed_even)']
    if seed % 2 == 0: directives.append('cargo::rustc-cfg=ibs_seed_even')
    directives.append(f'cargo::rustc-env=IBS_GENERATED_CONTEXT=input={case["input"]};seed={seed};mode={mode}')
    require((out_dir.parent / 'output').read_text().splitlines() == directives, 'actual directive ordering differs')
    require((out_dir.parent / 'stderr').read_text() == f'build-script input={case["input"]} seed={seed} mode={mode} value={value}\n', 'actual script stderr differs')
    if case['group'] == 'unsupported':
        require(current['before-unsupported.txt']['text'] == 'script already executed\n'
                and current['child-version.txt']['text'] == version, 'actual subprocess marker/stdout differs')
    else: require('before-unsupported.txt' not in current and 'child-version.txt' not in current, 'unexpected subprocess effects')
    return dict(files=current, actual_runs=1, directives=directives, context=context,
        nested_child=(dict(pid=None, pid_observed=False, command=[str(RUSTC), '--version'],
        success_asserted_by_fixture=True, stdout=current['child-version.txt']['text'],
        stdout_sha256=current['child-version.txt']['sha256'],
        evidence='unchanged fixture Command::output result; no process ID is exposed') if case['group'] == 'unsupported' else None))


def arg_value(args, flag):
    for i, arg in enumerate(args):
        if arg == flag and i + 1 < len(args): return args[i + 1]
        if arg.startswith(flag + '='): return arg[len(flag) + 1:]
    return None


def externs(args):
    return {value.split('=', 1)[0]: value.split('=', 1)[1] for i, arg in enumerate(args)
            if arg == '--extern' and i + 1 < len(args) and '=' in (value := args[i + 1])}


def native_macro_proof(case, compiler, records, target):
    if case['error']: return dict(new_macro_execution_claim=False, compilation_rejected=True)
    artifacts = [r for r in records if r.get('reason') == 'compiler-artifact']
    macro_files = {str(p) for r in artifacts if r['target']['name'] == 'ibs_fixture_macros'
                   and r['target']['kind'] == ['proc-macro'] for p in r['filenames'] if Path(p).suffix == '.dylib'}
    require(len(macro_files) == 1, 'actual native macro Cargo artifact unavailable')
    dylib = contained(next(iter(macro_files)), target)
    macro = [r for r in compiler if arg_value(r['argv'], '--crate-name') == 'ibs_fixture_macros']
    app = [r for r in compiler if arg_value(r['argv'], '--crate-name') == 'ibs_fixture_app']
    require(len(app) <= 1 and len(macro) <= 1, 'ambiguous actual compiler routes')
    if app:
        require(arg_value(app[0]['argv'], '--target') == HOST
                and externs(app[0]['argv']).get('ibs_fixture_macros') == str(dylib),
                'application did not receive the actual native macro dylib')
    else: require(case['label'] == 'unchanged', 'changed application compiler route absent')
    if macro:
        require(arg_value(macro[0]['argv'], '--crate-type') == 'proc-macro'
                and arg_value(macro[0]['argv'], '--target') is None, 'macro compiler host route changed')
    if case['group'] != 'shared':
        require(not macro or 'ibs_fixture_helper' not in externs(macro[0]['argv']), 'default macro gained helper dependency')
        return dict(proc_macro=identity(dylib), compiler_pids=[r['pid'] for r in [*macro, *app]],
            compiled_macro=bool(macro), application_recompiled=bool(app),
            basis='actual native Cargo dylib and application extern when recompiled; unchanged macro assertion executed')
    helpers = [r for r in compiler if arg_value(r['argv'], '--crate-name') == 'ibs_fixture_helper'
               and arg_value(r['argv'], '--target') is None]
    require(len(macro) == len(app) == len(helpers) == 1, 'actual shared native compiler routes absent')
    require('link' in (arg_value(helpers[0]['argv'], '--emit') or '').split(','), 'helper omitted native link emission')
    helper = contained(externs(macro[0]['argv'])['ibs_fixture_helper'], target)
    require(helper.suffix == '.rlib', 'native macro received metadata-only helper')
    files = {str(p) for r in artifacts for p in r['filenames']}
    require(str(helper) in files, 'native helper extern lacks Cargo artifact association')
    return dict(helper=identity(helper), proc_macro=identity(dylib), compiler_pids=[helpers[0]['pid'], macro[0]['pid'], app[0]['pid']],
        basis='actual host link emission/rlib extern, native proc-macro dylib extern and executed unchanged macro assertion; helper may inline')


def case_environment(case, ordinal, env, public, frozen):
    result = dict(env, CARGO_TARGET_DIR=str(WORK / 'targets' / case['group']),
        IBS_BASELINE_COMPILER_RECORDS=str(WORK / 'commands' / f'{ordinal:03d}' / 'compiler'),
        IBS_BASELINE_RUSTC_SHA=public['files'][str(RUSTC)]['sha256'],
        IBS_BASELINE_WRAPPER_SHA=frozen[str(Path(__file__).resolve())])
    if case['seed'] is not None: result['IBS_FIXTURE_SEED'] = str(case['seed'])
    return result


def validate_plan(plan, frozen, env, configs):
    require(plan['schema_version'] == 1 and plan['owner'] == str(ROOT) and plan['work'] == str(WORK)
        and plan['inputs'] == frozen and plan['environment'] == env and plan['configurations'] == configs
        and plan['cases'] == cases() and plan['commands'] == [argv(c) for c in cases()] and plan['tests'] == TESTS
        and plan['fixture'] == inventory(FIXTURE) and plan['jobs'] == 2
        and plan['canonical_lock'] == str(CANONICAL_LOCK) and plan['lock_wait_seconds'] == 600
        and plan['wrapper_policy'] == 'exact-public-rustc-exec-recorder-v1' and plan['native_baseline_only'] is True
        and plan['interpreted_scripts'] is False and plan['performance_claim'] is False
        and plan['environments'] == [case_environment(c,i,env,plan['public'],frozen) for i,c in enumerate(cases())],
        'baseline fixed plan changed')


def freeze_sources(destination, frozen):
    records = {}
    for path, expected in frozen.items():
        data = ordinary(path).read_bytes()
        require(hashlib.sha256(data).hexdigest() == expected, 'source changed while freezing')
        copy = destination / path.lstrip('/')
        copy.parent.mkdir(parents=True, exist_ok=True)
        with copy.open('xb') as f: f.write(data)
        require(sha(copy) == expected, 'frozen source copy differs')
        records[path] = dict(copy=str(copy), sha256=expected, bytes=len(data))
    write(destination.parent / 'source-snapshots.json', records)
    return records


def main():
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('stage', choices=['plan', 'run'])
    parser.add_argument('--plan', type=Path, required=True); parser.add_argument('--plan-sha256')
    args = parser.parse_args(); work = ROOT / '.work' / ('interpreted-build-scripts-plan-01' if args.stage == 'plan' else WORK.name)
    work.mkdir(parents=True, exist_ok=False)
    receipt = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), commands=[],
        canonical_lock=str(CANONICAL_LOCK), lock_wait_seconds=600, native_baseline_only=True, interpreted_scripts=False, performance_claim=False)
    write(work / 'receipt.json', receipt)
    try:
        with workload_lock(CANONICAL_LOCK, 600):
            receipt.update(status='running', admitted_at=time.time(), free_bytes_before=disk(ROOT)); write(work / 'receipt.json', receipt)
            frozen, env, configs = inputs(), environment(), configurations()
            def guard(public=None, rehash=False):
                require(inputs() == frozen and configurations() == configs, 'frozen controller/fixture/configuration changed')
                if public: guard_public(public, rehash)
                disk(ROOT)
            frozen_sources = freeze_sources(work / 'sources', frozen)
            receipt['source_snapshots_sha256'] = sha(work / 'source-snapshots.json')
            write(work / 'receipt.json', receipt)
            def command(command, directory, child_env=env, cwd=ROOT, expected=(0,)):
                guard()
                ref = dict(path=str(directory / 'receipt.json'), command=command)
                receipt['commands'].append(ref); write(work / 'receipt.json', receipt)
                try:
                    result = run(command, cwd=cwd, env=child_env, out=directory, capacity_root=ROOT, expected=expected)
                finally:
                    if (directory / 'receipt.json').exists():
                        ref['sha256'] = sha(directory / 'receipt.json'); write(work / 'receipt.json', receipt)
                return dict(result, stdout=(directory / 'stdout').read_text(), stderr=(directory / 'stderr').read_text())
            if args.stage == 'plan':
                require(args.plan.is_absolute() and args.plan.parent == HERE and not args.plan.exists() and not args.plan_sha256, 'fresh owned plan required')
                public = public_inputs(lambda argv: command(argv, work / 'metadata' / f'{len(receipt["commands"]):03d}'))
                plan = dict(schema_version=1, owner=str(ROOT), work=str(WORK), fixture=inventory(FIXTURE), inputs=frozen,
                    environment=env, configurations=configs, public=public, cases=cases(), commands=[argv(c) for c in cases()],
                    environments=[case_environment(c,i,env,public,frozen) for i,c in enumerate(cases())],
                    wrapper_policy='exact-public-rustc-exec-recorder-v1', tests=TESTS, jobs=2, native_baseline_only=True,
                    interpreted_scripts=False, performance_claim=False, canonical_lock=str(CANONICAL_LOCK), lock_wait_seconds=600)
                guard(public, True); write(args.plan, plan); receipt.update(plan=str(args.plan), plan_sha256=sha(args.plan))
            else:
                require(args.plan.is_absolute() and args.plan.parent == HERE and re.fullmatch('[0-9a-f]{64}', args.plan_sha256 or '')
                        and sha(ordinary(args.plan)) == args.plan_sha256, 'reviewed plan required')
                plan = json.loads(args.plan.read_bytes())
                validate_plan(plan, frozen, env, configs)
                public = plan['public']; guard(public, True)
                shutil.copytree(FIXTURE, APP); (WORK / 'cargo-home').mkdir()
                templates = {n: (APP / n).read_bytes() for n in plan['fixture']}
                rows, previous = [], {}
                try:
                    with ExitStack() as stack:
                        editors = {n: stack.enter_context(SourceEdit(APP / n, templates[n])) for n in EDITABLE}
                        excluded = {e.backup for e in editors.values()}
                        for i, case in enumerate(cases()):
                            changed = sources(case, templates)
                            for n, payload in changed.items():
                                if editors[n].current != payload: editors[n].replace(payload)
                            expected_sources = {n: hashlib.sha256(changed.get(n, b)).hexdigest() for n, b in templates.items()}
                            require(inventory(APP, excluded) == expected_sources, 'copied fixture source changed')
                            guard(public); require(sha(args.plan) == args.plan_sha256, 'reviewed plan changed')
                            directory = WORK / 'commands' / f'{i:03d}'; compiler_dir = directory / 'compiler'; compiler_dir.mkdir(parents=True)
                            target = WORK / 'targets' / case['group']; child_env = plan['environments'][i]
                            prior = previous.get(case['group']); before = output_snapshot(Path(prior)) if prior else {}
                            actual = command(argv(case), directory / 'cargo', child_env, APP, (0, 101))
                            records, test_text = cargo_records(actual['stdout']); result = outcomes(case, records, test_text, actual['returncode'])
                            dirs = {r['out_dir'] for r in records if r.get('reason') == 'build-script-executed' and app_record(r)}
                            require(len(dirs) <= 1 and (dirs or prior), 'actual Cargo OUT_DIR unavailable or ambiguous')
                            out_dir = Path(next(iter(dirs)) if dirs else prior)
                            if prior: require(out_dir == Path(prior), 'same Cargo history changed OUT_DIR unexpectedly')
                            effects = script_outputs(case, out_dir, target, before, public['versions']['rustc_version'])
                            compiler = [json.loads(p.read_bytes()) for p in sorted(compiler_dir.glob('*.json'))]
                            require(all(r['status'] == 'exec-request' and r['argv'][0] == str(RUSTC)
                                and r['executable_sha256'] == public['files'][str(RUSTC)]['sha256']
                                and r['environment']['RUSTC'] == str(RUSTC)
                                and r['environment']['IBS_BASELINE_WRAPPER_SHA'] == frozen[str(Path(__file__).resolve())]
                                for r in compiler), 'compiler forwarding failed')
                            proof = native_macro_proof(case, compiler, records, target)
                            saved = {}
                            paths = {Path(p) for r in records if r.get('reason') == 'compiler-artifact' for p in r['filenames']}
                            paths.update(Path(r['executable']) for r in records if r.get('reason') == 'compiler-artifact' and r.get('executable'))
                            paths.update(out_dir / n for n in OUTPUTS if (out_dir / n).exists())
                            paths.update(out_dir.parent / n for n in ['output', 'stderr'] if (out_dir.parent / n).exists())
                            for path in sorted(paths):
                                contained(path, target); disk(ROOT); dest = directory / 'artifacts' / path.relative_to(target)
                                dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, dest)
                                require(sha(dest) == sha(path), 'artifact copy differs'); saved[str(path)] = dict(copy=str(dest), sha256=sha(dest))
                            require(inventory(APP, excluded) == expected_sources, 'fixture changed during Cargo command')
                            guard(public); previous[case['group']] = str(out_dir)
                            row = dict(ordinal=i, case=case, argv=argv(case), environment=child_env, sources=expected_sources,
                                outcome=result, cargo_records=records, script=effects, out_dir=str(out_dir), compiler=compiler,
                                native_macro_proof=proof, retained_artifacts=saved, process_receipt=str(directory / 'cargo/receipt.json'))
                            write(directory / 'result.json', row); rows.append(row); write(WORK / 'records.json', rows)
                finally:
                    receipt['sources_restored'] = inventory(APP) == plan['fixture']; write(work / 'receipt.json', receipt)
                require(receipt['sources_restored'] and len(rows) == 28, 'complete restored 28-command baseline required')
                guard(public, True); receipt.update(cargo_commands=28, successful_cases=19, compile_rejections=8, wrong_value_rejections=1,
                    records_sha256=sha(WORK / 'records.json'), plan_sha256=args.plan_sha256)
            receipt.update(status='passed', finished_at=time.time(), free_bytes_after=disk(ROOT)); write(work / 'receipt.json', receipt)
    except BaseException as error:
        receipt.update(status='failed', error=repr(error), finished_at=time.time()); write(work / 'receipt.json', receipt); raise


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == str(RUSTC): compiler_wrapper()
    else: main()
