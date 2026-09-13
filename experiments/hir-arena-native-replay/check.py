#!/usr/bin/env python3
"""Replay the existing complete rmake recipe with unabridged file-backed output."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
WORK = ROOT / '.work/hir-arena-native-replay-01'
NATIVE = Path('/Users/danluu/dev/rust-interp-hir-arena-native-20260913')
spec = importlib.util.spec_from_file_location('arena_replay_native', NATIVE / 'experiments/hir-arena-native/check.py')
arena = importlib.util.module_from_spec(spec); sys.modules[spec.name] = arena; spec.loader.exec_module(arena)
native, engine = arena.native, arena.engine
require, sha, write, ordinary = native.require, native.sha, native.write, native.ordinary
SOURCE, HOST = native.SOURCE, native.old.HOST
BUILD = SOURCE / 'build' / HOST
PLAN = NATIVE / 'experiments/hir-arena-native/planned-native-01.json'
PLAN_SHA = 'c30a65cfb2c00ce67bdbea27df460f248a3f9b4ae324333a590b1aaea5301819'
FAILED = NATIVE / '.work/hir-arena-native-01/stages/native-01'
FAILED_SHA = '075c9bb98df60bdfdbe9a466c88ecc774cc4844e6dbafbc9095e10beb1a9af37'
RECIPE = BUILD / 'test/run-make/hir-body-cache-capture/rmake'
FIXTURE = SOURCE / 'tests/run-make/hir-body-cache-capture/fixture.rs'
COMPILETEST = BUILD / 'stage1-tools-bin/compiletest'
STAGE0_LIB = BUILD / 'stage0/lib/rustlib' / HOST / 'lib'
CAPACITY = dict(initial_free_gib=16, capacity_stop_gib=9, running_floor_gib=8)


def recipe_environment(text, inherited):
    """The final executed compiletest command, followed by run_make.rs's env edits."""
    lines = [line for line in text.splitlines() if line.startswith('running: env ')
             and str(COMPILETEST) in line and '"--run-make-support-rlib"' in line]
    require(len(lines) == 1 and lines[0].endswith(' (failure_mode=Exit)'),
            'one final executed compiletest command required')
    tokens = shlex.split(lines[0][len('running: '):-len(' (failure_mode=Exit)')])
    require(tokens.pop(0) == 'env', 'compiletest env envelope changed')
    env = dict(inherited)
    while tokens[0] != str(COMPILETEST):
        value = tokens.pop(0)
        if value == '-u': env.pop(tokens.pop(0), None)
        else:
            require('=' in value, 'unknown compiletest env operation')
            key, value = value.split('=', 1); env[key] = value
    tokens.pop(0)
    boolean = {'--no-capture', '--optimize-tests', '--verbose', '--verbose-run-make-subprocess-output',
               '--with-std-remap-debuginfo', '--with-rustc-debug-assertions', '--with-std-debug-assertions',
               '--profiler-runtime', '--git-hash'}
    options, filters = {}, []
    while tokens:
        key = tokens.pop(0)
        if key in boolean: value = True
        elif key.startswith('--'):
            require(tokens, 'missing compiletest option value'); value = tokens.pop(0)
        else: filters.append(key); continue
        if key in options:
            require(key in {'--host-rustcflags', '--target-rustcflags'}, 'duplicate compiletest option')
        options.setdefault(key, []).append(value)
    one = lambda name: options[name][0]
    expected = {'--stage': '1', '--suite': 'run-make', '--mode': 'run-make', '--host': HOST,
        '--target': HOST, '--rustc-path': str(native.RUSTC), '--src-root': str(SOURCE),
        '--build-root': str(SOURCE / 'build'), '--compile-lib-path': str(native.SYSROOT / 'lib'),
        '--run-lib-path': str(native.SYSROOT / 'lib/rustlib' / HOST / 'lib'), '--jobs': '2',
        '--stage0-rustc-path': str(BUILD / 'stage0/bin/rustc')}
    require(all(options.get(k) == [v] for k, v in expected.items())
            and filters == ['hir-body-cache-capture'] and '--verbose-run-make-subprocess-output' in options
            and not any(k in options for k in ['--bless', '--target-linker', '--runner', '--remote-test-client']),
            'unexpected recipe route, filter, or execution option')
    require(env.get('RUSTC_BOOTSTRAP') == '1' and env.get('RUSTC_FORCE_RUSTC_VERSION') == 'compiletest'
            and 'CARGO' not in env, 'original compiletest environment differs')
    base = env['DYLD_LIBRARY_PATH'].split(':')
    require(base == [str(Path(one('--run-make-support-rmeta')).parent)], 'unexpected base dylib route')
    env.update(LD_LIB_PATH_ENVVAR='DYLD_LIBRARY_PATH', DYLD_LIBRARY_PATH=':'.join([*base, str(STAGE0_LIB)]),
        HOST_RUSTC_DYLIB_PATH=one('--compile-lib-path'), TARGET_EXE_DYLIB_PATH=one('--run-lib-path'),
        TARGET=HOST, PYTHON=one('--python'), SOURCE_ROOT=str(SOURCE), BUILD_ROOT=str(BUILD),
        RUSTC=one('--rustc-path'), LLVM_COMPONENTS=one('--llvm-components'), __BOOTSTRAP_JOBS=one('--jobs'),
        CC=one('--cc'), CXX=one('--cxx'), AR=one('--ar'), CC_DEFAULT_FLAGS=one('--cflags'), CXX_DEFAULT_FLAGS=one('--cxxflags'))
    for key, option in {'RUSTDOC': '--rustdoc-path', 'NODE': '--nodejs', 'LLVM_FILECHECK': '--llvm-filecheck',
                        'LLVM_BIN_DIR': '--llvm-bin-dir'}.items():
        if option in options: env[key] = one(option)
    for key, option in {'__RMAKE_VERBOSE_SUBPROCESS_OUTPUT': '--verbose-run-make-subprocess-output',
        '__RUSTC_DEBUG_ASSERTIONS_ENABLED': '--with-rustc-debug-assertions',
        '__STD_DEBUG_ASSERTIONS_ENABLED': '--with-std-debug-assertions',
        '__STD_REMAP_DEBUGINFO_ENABLED': '--with-std-remap-debuginfo'}.items():
        env.pop(key, None)
        if option in options: env[key] = '1'
    env.pop('RUSTFLAGS', None)
    return dict(environment=env, original_compiletest_command=lines[0], options=options)


def checked_replay(text):
    """Use real recipe success plus raw compiler observations, without a libtest footer."""
    require('TRUNCATED' not in text, 'truncated output')
    hits = re.findall(r'(?m)^\[hir-body-reuse\][^\n]*$', text)
    require(hits, 'no actual verified cache hits in direct recipe output')
    names = set()
    for line in hits:
        match = re.fullmatch(r'\[hir-body-reuse\] ([a-z0-9_]+) hit cache_hits=1 '
            r'verify_tree=1 verify_journal=1 verify_poststate=1 S=(0|[1-9][0-9]*) E=(0|[1-9][0-9]*)', line)
        require(match is not None and 0 < int(match[2]) < int(match[3]) <= 0xFFFF_FF00,
                'malformed actual hit or invalid ItemLocalId interval')
        names.add(match[1])
    required = {'anchor', 'add', 'method', 'double', 'shadow', 'generic', 'conditional', 'array_index',
        'uninitialized', 'raw', 'arithmetic', 'literals', 'unsafe_block', 'flow', 'early', 'field', 'choose'}
    require(required <= names, 'complete recipe hit roles absent')
    for state in ['cold-tree-and-journal-after-stock-lowering', 'same-tree-and-journal-after-stock-lowering']:
        require('[hir-body-capture] anchor ' + state in text, 'capture history evidence absent')
    for code in ['E0308', 'E0382', 'E0080', 'unconditional_panic', 'unused_variables']:
        require(code in text, 'raw uncalled error/lint evidence absent')
    for label in ['empty', 'nonempty']:
        for mode in ['ordinary', 'capture', 'reuse']:
            for outcome in ['positive', 'negative']:
                require('-Cincremental=override-' + label + '-' + mode + '-' + outcome in text,
                        'version override control output absent')
    return dict(actual_verified_hits=len(hits), actual_hit_names=sorted(names),
                complete_unchanged_recipe_returned_successfully=True)


def prerequisite():
    context = arena.context()
    plan = native.load_plan(PLAN, PLAN_SHA, context.read_inputs(), context.read_checkpoint()[1], context=context)
    require(context.read_history(plan['previous']['plan_sha256'], plan['previous']['terminal']) == plan['previous'],
            'successful all27 prerequisite changed')
    require(sha(ordinary(FAILED / 'receipt.json')) == FAILED_SHA, 'original failed native receipt changed')
    failed = json.loads((FAILED / 'receipt.json').read_bytes())
    require(failed['status'] == 'failed' and failed['error'] == "RuntimeError('no actual verified cache hit in retained native output')"
        and failed['expected_plan_sha256'] == PLAN_SHA and failed['source_revision'] == arena.SOURCE_REVISION
        and len(failed['commands']) == 21, 'wrong original native failure')
    files = {str(PLAN): PLAN_SHA, str(FAILED / 'receipt.json'): FAILED_SHA,
        **plan['inputs'], **plan['previous']['files'], **plan['archive_hashes']}
    for ref in plan['previous']['historical_archives']: files.update(ref['hashes'])
    outputs = {}
    for index, ref in enumerate(failed['commands']):
        path = FAILED / 'commands' / f'{index:03d}' / 'receipt.json'
        require(ref['path'] == str(path) and sha(ordinary(path)) == ref['sha256'], 'native child changed')
        row = json.loads(path.read_bytes())
        require(row['status'] == 'finished' and row['returncode'] == 0 and row['command'] == ref['command']
            and row['environment'] == plan['previous']['old_plan']['environment'], 'native command failed or changed')
        files[str(path)] = sha(path)
        outputs[index] = ''
        for name in ['stdout', 'stderr']:
            p = path.parent / name
            require(sha(ordinary(p)) == row[name + '_sha256'], 'native raw output changed')
            files[str(p)] = sha(p); outputs[index] += p.read_text()
    require(failed['commands'][5]['command'] == native.COMMANDS['build']
        and failed['commands'][14]['command'] == native.COMMANDS['option']
        and failed['commands'][20]['command'] == native.COMMANDS['native'], 'native command association changed')
    native.checked_option(outputs[14]); native.checked_result(outputs[20], 1)
    require('TRUNCATED, SHOWING THE FIRST 524288 BYTES' in outputs[20], 'original truncation evidence absent')
    outer = NATIVE / '.work/experiments/hir-arena-native-run-supervisor-01'
    status = json.loads(ordinary(outer / 'status.json').read_bytes())
    require(status['status'] == 'finished' and status['returncode'] != 0
        and status['child_pid'] == failed['pid'] and status['supervisor_pid'] == failed['parent_pid']
        and sha(ordinary(outer / 'plan.json')) == status['plan_sha256']
        and sha(ordinary(outer / 'command.log')) == status['log_sha256'], 'failed outer association changed')
    for name in ['status.json', 'plan.json', 'command.log', 'supervisor.log']:
        files[str(ordinary(outer / name))] = sha(outer / name)
    paths = [Path(__file__), HERE / 'README.md', HERE / 'compiletest-command.txt',
        ROOT / 'tests/test_hir_arena_native_replay.py',
        ROOT / 'scripts/supervise_experiment.py', FAILED / 'built-artifacts.json', FIXTURE,
        SOURCE / 'tests/run-make/hir-body-cache-capture/rmake.rs',
        *[SOURCE / ('src/tools/' + p) for p in ['compiletest/src/runtest/run_make.rs',
            'compiletest/src/read2.rs', 'compiletest/src/cli.rs', 'run-make-support/src/util.rs']]]
    for p in paths: files[str(ordinary(p))] = sha(p)
    route = recipe_environment(outputs[20], plan['previous']['old_plan']['environment'])
    return plan, files, route


def runtime_inputs(route):
    stage1 = native.artifacts()
    built = json.loads((FAILED / 'built-artifacts.json').read_bytes())
    require(all(stage1['files'].get(p) == row for p, row in built['files'].items())
        and stage1['source_links'] == built['source_links'], 'original built compiler/std changed')
    roots = [STAGE0_LIB, Path(route['environment']['DYLD_LIBRARY_PATH'].split(':')[0])]
    files = {}
    for root in roots:
        require(root.resolve(strict=True) == root and root.is_dir(), 'runtime root is not ordinary')
        for p in sorted(root.rglob('*')):
            require(not p.is_symlink(), 'runtime dependency symlink')
            if p.is_dir(): continue
            files[str(ordinary(p))] = sha(p)
    for p in [RECIPE, COMPILETEST, Path(route['options']['--run-make-support-rlib'][0])]:
        files[str(ordinary(p))] = sha(p)
    return dict(stage1=stage1, other_files=files, runtime_roots=list(map(str, roots)))


def execute(args):
    require(re.fullmatch('[a-z0-9-]+', args.attempt), 'invalid fresh attempt')
    out = WORK / 'stages' / args.attempt; out.mkdir(parents=True, exist_ok=False)
    record = dict(owner=str(ROOT), stage=args.stage, status='waiting', started_at=time.time(),
        pid=os.getpid(), parent_pid=os.getppid(), commands=[])
    write(out / 'receipt.json', record)
    try:
        with engine.workload_lock(engine.CANONICAL_LOCK, 600):
            record.update(status='running', admitted_at=time.time(), free_bytes_before=engine.disk(ROOT, 16 if args.stage == 'run' else 8))
            write(out / 'receipt.json', record)
            original, frozen, route = prerequisite()
            native.verify_references(original['previous'])
            engine.verify_archive(original['archive_paths']['archive'], original['archive_paths']['manifest'],
                original['archive_paths']['summary'], original['archive_required'])
            runtime = runtime_inputs(route)
            configurations = native.extra_configurations(root=ROOT)
            plan = dict(schema_version=1, owner=str(ROOT), source_revision=arena.SOURCE_REVISION,
                original_native_plan=str(PLAN), original_native_plan_sha256=PLAN_SHA,
                original_failed_receipt=str(FAILED / 'receipt.json'), original_failed_receipt_sha256=FAILED_SHA,
                inputs=frozen, runtime=runtime, route=route, command=[str(RECIPE)], cwd=str(WORK / 'rmake_out'),
                probes=native.PROBES, capacity=CAPACITY, configurations=configurations,
                canonical_lock=str(engine.CANONICAL_LOCK))
            if args.stage == 'run':
                require(args.plan.parent == HERE and re.fullmatch('[0-9a-f]{64}', args.plan_sha256 or ''), 'reviewed owned replay plan required')
                data = ordinary(args.plan).read_bytes()
                require(engine.digest(data) == args.plan_sha256 and json.loads(data) == plan, 'reviewed replay plan or inputs changed')
                record.update(plan=str(args.plan), expected_plan_sha256=args.plan_sha256)
            def guard():
                require(all(sha(ordinary(p)) == h for p, h in frozen.items()), 'frozen replay source/history changed')
                require(native.extra_configurations(root=ROOT) == configurations, 'Cargo configuration changed')
                if args.stage == 'run': require(sha(args.plan) == args.plan_sha256, 'reviewed replay plan changed')
                engine.disk(ROOT, 9)
            def command(argv, cwd=SOURCE, env=None):
                guard()
                directory = out / 'commands' / f'{len(record["commands"]):03d}'
                ref = dict(path=str(directory / 'receipt.json'), command=list(map(str, argv)))
                record['commands'].append(ref); write(out / 'receipt.json', record)
                try:
                    result = engine.run(argv, cwd=cwd, env=env or original['previous']['old_plan']['environment'],
                                        out=directory, capacity_root=ROOT)
                finally:
                    if (directory / 'receipt.json').exists(): ref['sha256'] = sha(directory / 'receipt.json')
                    write(out / 'receipt.json', record)
                guard()
                return dict(result, stdout=(directory / 'stdout').read_text(), stderr=(directory / 'stderr').read_text())
            def source_guard():
                engine.source_guard(original['previous']['source'], command, sha(original['previous']['old_plan_path']))
            source_guard()
            if args.stage == 'plan':
                require(args.write_plan.parent == HERE and not args.write_plan.exists(), 'fresh owned plan required')
                write(args.write_plan, plan); record.update(plan=str(args.write_plan), plan_sha256=sha(args.write_plan))
            else:
                cwd = Path(plan['cwd']); cwd.mkdir(exist_ok=False)
                shutil.copyfile(FIXTURE, cwd / 'fixture.rs')
                require(sha(cwd / 'fixture.rs') == sha(FIXTURE), 'fixture copy differs')
                probes = [command(argv) for argv in native.PROBES]
                require('commit-hash: ' + arena.SOURCE_REVISION in probes[0]['stdout']
                    and probes[1]['stdout'].strip() == str(native.SYSROOT)
                    and all(re.search(r'(?m)^\s*-Z\s+' + flag + r'=', probes[2]['stdout'])
                            for flag in ['hir-body-cache-capture', 'hir-body-cache-reuse']), 'actual compiler identity differs')
                result = command(plan['command'], cwd, route['environment'])
                observations = checked_replay(result['stdout'] + result['stderr'])
                require(sha(cwd / 'fixture.rs') == sha(cwd / 'input.rs') == sha(FIXTURE), 'recipe source not restored')
                write(out / 'observations.json', observations)
                source_guard()
                record.update(observations_sha256=sha(out / 'observations.json'),
                    actual_direct_recipe_passed=1, original_outer_native_status='failed',
                    original_build_passed=True, original_option_test_passed=1,
                    original_compiletest_recipe_passed=1, performance_claim=False)
            require(runtime_inputs(route) == runtime, 'compiler/std/recipe/support dependencies changed')
            guard()
            record.update(status='passed', finished_at=time.time(), free_bytes_after=engine.disk(ROOT))
            write(out / 'receipt.json', record)
    except BaseException as error:
        record.update(status='failed', error=repr(error), finished_at=time.time(), free_bytes_after=shutil.disk_usage(ROOT).free)
        write(out / 'receipt.json', record)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['plan', 'run'])
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--write-plan', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--plan-sha256')
    execute(parser.parse_args())
