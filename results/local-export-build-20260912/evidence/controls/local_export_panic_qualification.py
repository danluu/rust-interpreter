"""Bounded future panic-store correctness qualification; root executes only.

freeze is hash-only. run owns the established shared lock once; do not wrap it
in run_locked.py. finalize requires a separately written actual-MIR/data-flow
inspection. No latency or adoption result is produced.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
import traceback

ROOT = Path('/Users/danluu/dev/rust-interp-perf-20260912')
B = ROOT / '.work/build-general-20260912'
SCRIPT = B / 'local_export_panic_qualification.py'
PLAN = B / 'local-export-panic-plan.md'
INPUTS = B / 'local-export-panic-inputs.json'
FROZEN = B / 'local-export-panic-frozen.json'
RUN = ROOT / '.work/runs/local-export-panic-20260912-01'
FIXTURE = ROOT / 'tests/panic_store_fixture.rs'
INSPECTOR = B / 'panic-store-inspector'
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
BASELINE = 'eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d'
CANDIDATE = '14af97a36405cc925ce89529e5bc9ff2db9ecdbd0f8b816095ace66235fc4c75'
FIXTURE_SHA = '71ee4a3d817990ea243968be710f9d233450ea25cd0f5ab921055f2bd1651cc3'
VALUES = ['0', '1', '9223372036854775808', '18446744073709551615']
ENGINES = ['interpreter', 'jit']
COMMAND_COUNT = 90
MIN_FREE_BYTES = 4 * 1024**3
MAX_ARTIFACT = 64 * 1024**2


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path,
            'noncanonical proof path: ' + str(path))
    require(stat.S_ISREG(path.lstat().st_mode), 'nonregular proof: ' + str(path))
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(data)
    return digest.hexdigest()


def read(path):
    sha(path)
    return json.loads(Path(path).read_text())


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def bind(proofs, path, expected=None):
    path = Path(path)
    digest = sha(path)
    require(expected is None or digest == expected, 'hash differs: ' + str(path))
    require(str(path) not in proofs or proofs[str(path)] == digest,
            'proof changed: ' + str(path))
    proofs[str(path)] = digest


def verify(proofs):
    for path, digest in proofs.items():
        require(sha(path) == digest, 'frozen input changed: ' + path)


def spec(label, kind, command, *, extra_env=None, **metadata):
    return dict(label=label, kind=kind, command=list(map(str, command)),
                extra_env=extra_env or {}, **metadata)


def schedule(rustc, cargo, bundles):
    native = RUN / 'native'
    inspector = RUN / 'inspector-target/release/panic-store-inspector'
    jobs = [spec('build-inspector', 'build', [cargo, 'build', '--release', '--locked',
            '--offline', '--jobs', '2', '--manifest-path', INSPECTOR / 'Cargo.toml',
            '--target-dir', RUN / 'inspector-target']),
            spec('build-native', 'build', [rustc, FIXTURE, '--edition=2024', '-o', native])]
    for value in VALUES:
        for mode in ['observe', '0', '1']:
            jobs.append(spec('native-' + mode + '-' + value, 'native',
                             [native, mode, value], mode=mode, value=value))
    for inline in [False, True]:
        for arm in ['baseline', 'candidate']:
            tag = arm + ('-inline' if inline else '-plain')
            directory = RUN / tag
            exporter = Path(bundles[arm]['directory']) / 'rust-interp-mir-export'
            for diagnostic in [False, True]:
                suffix = 'mir' if diagnostic else 'primary'
                artifact = directory / (suffix + '.rbc')
                command = [exporter, FIXTURE, '--crate-name', 'panic_store_fixture',
                           '--edition=2024', '--emit=metadata', '-o', directory / (suffix + '.rmeta')]
                if diagnostic:
                    command += ['-Zdump-mir=store_then_panic',
                                '-Zdump-mir-dir=' + str(directory / 'mir')]
                env = dict(RUST_INTERP_OUTPUT=str(artifact), RUST_INTERP_ENTRY='rust_interp_entry',
                           RUST_INTERP_EXPORT_TEST='0', RUST_INTERP_DEMAND_BODIES='0',
                           RUST_INTERP_DEMAND_CACHE='0')
                if inline:
                    env['RUST_INTERP_INLINE_LEAVES'] = '1'
                jobs.append(spec(tag + '-' + suffix, 'export', command, extra_env=env,
                                 arm=arm, inline=inline, diagnostic=diagnostic, artifact=str(artifact)))
            jobs.append(spec(tag + '-inspect', 'inspect', [inspector, directory / 'primary.rbc'],
                             arm=arm, inline=inline, artifact=str(directory / 'primary.rbc')))
            for engine in ENGINES:
                for value in VALUES:
                    for mode in ['0', '1']:
                        command = [Path(bundles[arm]['directory']) / 'rust-interp-vm',
                                   '--engine', engine, '--instruction-limit', '1000000',
                                   directory / 'primary.rbc', mode, value]
                        jobs.append(spec(tag + '-' + engine + '-' + mode + '-' + value,
                                         'vm', command, arm=arm, inline=inline, engine=engine,
                                         mode=mode, value=value, artifact=str(directory / 'primary.rbc')))
    require(len(jobs) == COMMAND_COUNT and len({j['label'] for j in jobs}) == COMMAND_COUNT,
            'incorrect fixed schedule')
    return jobs


def freeze(args):
    require(not os.path.lexists(FROZEN) and not os.path.lexists(RUN), 'qualification already prepared')
    inputs = read(INPUTS)
    require(inputs['candidate_tool_key'] == CANDIDATE and inputs['baseline_tool_key'] == BASELINE,
            'wrong static tool identities')
    require(inputs['values'] == VALUES and inputs['commands'] == COMMAND_COUNT, 'static scope differs')
    proofs = dict(inputs['files'])
    verify(proofs)
    for path in [INPUTS, SCRIPT, PLAN]:
        bind(proofs, path)
    core_path = B / 'local-export-qualification.json'
    core = read(core_path)
    require(core['qualification_pass'] is True and core['tool_key'] == CANDIDATE
            and core['baseline_tool_key'] == BASELINE and core['frozen_baseline_runtime'] is True,
            'future core qualification did not pass')
    require(core['tests'] == {p: dict(passed=408, failed=0, ignored=1) for p in ['debug', 'release']}
            and core['full_validation']['completed_commands'] == 23727
            and core['raw_validation_records'] == 23727, 'core counts differ')
    for name, digest in core['proofs'].items():
        bind(proofs, ROOT / name, digest)
    bind(proofs, core_path)
    source = read(B / 'local-export-prebuild-source/source.json')
    require(source['tool_key'] == CANDIDATE and len(source['files']) == 146, 'wrong core source')
    for name, row in source['files'].items():
        bind(proofs, ROOT / name, row['sha256'])
    for name, digest in source['common_files'].items():
        bind(proofs, ROOT / name, digest)
    bind(proofs, FIXTURE, FIXTURE_SHA)
    bundles = {}
    for arm, receipt, key in [('baseline', 'owned-analysis-tools.json', BASELINE),
                              ('candidate', 'local-export-tools.json', CANDIDATE)]:
        bundle = read(B / receipt)
        require(bundle['tool_key'] == key, 'wrong selected tool bundle')
        for name, digest in bundle['binaries'].items():
            bind(proofs, Path(bundle['directory']) / name, digest)
        bind(proofs, B / receipt)
        bundles[arm] = bundle
    for name in ['rust-interp-vm', 'rust-interp-rustc-wrapper']:
        require(bundles['baseline']['binaries'][name] == bundles['candidate']['binaries'][name],
                'baseline runtime/wrapper differs')
    rustc, cargo = Path(args.rustc), Path(args.cargo)
    require(rustc.name == 'rustc' and cargo.name == 'cargo' and rustc.parent == cargo.parent
            and rustc.parent.name == 'bin'
            and rustc.parent.parent.name == 'nightly-2026-09-08-aarch64-apple-darwin',
            'use the exact installed pinned toolchain binaries, not rustup shims')
    bind(proofs, rustc)
    bind(proofs, cargo)
    python = Path(sys.executable).resolve(strict=True)
    bind(proofs, python)
    lock_source = read(B / 'panic-store-inspector-lock-source.json')
    require(lock_source['registry_versions_unchanged'] is True and lock_source['packages'] == 28,
            'inspector lock provenance differs')
    bind(proofs, lock_source['source'], lock_source['source_sha256'])
    bind(proofs, lock_source['output'], lock_source['output_sha256'])
    require(Path(lock_source['output']) == INSPECTOR / 'Cargo.lock', 'wrong inspector lock')
    jobs = schedule(rustc, cargo, bundles)
    write_new(FROZEN, dict(schema_version=1, status='frozen; no workload executed',
              controller_pid=os.getpid(), frozen_at=time.time(), cwd=str(ROOT),
              candidate_tool_key=CANDIDATE, baseline_tool_key=BASELINE, bundles=bundles,
              rustc=str(rustc), cargo=str(cargo), python=str(python), proofs=proofs, commands=jobs,
              common_mir_optimization_flags=[], diagnostic_only_flags=['-Zdump-mir=store_then_panic',
              '-Zdump-mir-dir=PER_ARM_DIRECTORY'], shared_lock=str(LOCK),
              minimum_free_bytes=MIN_FREE_BYTES, performance_measurement=False))


def clean_env(frozen):
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or name in [
                'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR',
                'CARGO_BUILD_TARGET', 'RUSTC_BOOTSTRAP', 'RUST_BACKTRACE', 'RUST_LIB_BACKTRACE']:
            env.pop(name)
    env.update(RUSTC=frozen['rustc'], RUSTUP_TOOLCHAIN='nightly-2026-09-08',
               CARGO_INCREMENTAL='0', CARGO_TERM_COLOR='never', RUST_BACKTRACE='0', LC_ALL='C')
    return env


def output(row, stream):
    path = Path(row[stream]['path'])
    require(sha(path) == row[stream]['sha256'], 'raw output changed')
    return path.read_bytes()


def outcome(row):
    return row['returncode'], output(row, 'stdout'), output(row, 'stderr')


def validate_records(frozen, records):
    require(len(records) == COMMAND_COUNT, 'incomplete command set')
    executables = dict(frozen['proofs'])
    for label, path in [('build-native', RUN / 'native'),
                        ('build-inspector', RUN / 'inspector-target/release/panic-store-inspector')]:
        receipt = read(RUN / (label + '.binary.json'))
        require(receipt['path'] == str(path) and receipt['build_label'] == label
                and receipt['build_record'] == next(r for r in records if r['spec']['label'] == label),
                'built executable receipt does not bind its command')
        bind(executables, path, receipt['sha256'])
    previous_finish = frozen['frozen_at']
    for row, planned in zip(records, frozen['commands']):
        require(row['spec'] == planned and row['cwd'] == str(ROOT), 'command schedule differs')
        require(row['executable_sha256'] == executables[planned['command'][0]],
                'command executable differs from frozen/built bytes')
        require(row['child_pid'] > 0 and row['child_pid'] != row['controller_pid']
                and previous_finish <= row['started_at'] <= row['finished_at'],
                'invalid command interval/identity')
        previous_finish = row['finished_at']
        code, stdout, stderr = outcome(row)
        require(b'internal compiler error' not in stderr, 'compiler ICE')
        kind, mode = planned['kind'], planned.get('mode')
        if kind in ['native', 'vm']:
            if mode != '1':
                require(code == 0 and stdout == (planned['value'] + '\n').encode(), 'normal/observe oracle failed')
                if mode == 'observe':
                    require(b'panic-store fixture' in stderr, 'native observer did not report panic')
                else:
                    require(stderr == b'', 'unexpected successful-run diagnostic')
            else:
                require(code == (101 if kind == 'native' else 1) and stdout == b'', 'uncaught panic outcome differs')
                require((b'panic-store fixture' if kind == 'native' else b'panic') in stderr,
                        'expected panic diagnostic missing')
        else:
            require(code == 0, 'build/export/inspector failed')
        if 'artifact' in planned:
            require(row['artifact']['path'] == planned['artifact']
                    and sha(planned['artifact']) == row['artifact']['sha256'], 'artifact binding differs')
    for inline in [False, True]:
        exports = [r for r in records if r['spec']['kind'] == 'export' and r['spec']['inline'] == inline]
        artifacts = [Path(r['spec']['artifact']).read_bytes() for r in exports]
        require(len(artifacts) == 4 and all(a == artifacts[0] for a in artifacts),
                'baseline/candidate or diagnostic bytecode differs')
        for engine in ENGINES:
            for value in VALUES:
                for mode in ['0', '1']:
                    pair = [r for r in records if r['spec']['kind'] == 'vm'
                            and all(r['spec'][k] == v for k, v in
                                    dict(inline=inline, engine=engine, value=value, mode=mode).items())]
                    require(len(pair) == 2 and outcome(pair[0]) == outcome(pair[1]),
                            'baseline/candidate output/error parity failed')
        for arm in ['baseline', 'candidate']:
            for value in VALUES:
                for mode in ['0', '1']:
                    pair = [r for r in records if r['spec']['kind'] == 'vm'
                            and all(r['spec'][k] == v for k, v in
                                    dict(inline=inline, arm=arm, value=value, mode=mode).items())]
                    require(len(pair) == 2 and outcome(pair[0]) == outcome(pair[1]), 'engine parity failed')


def execute(frozen, records):
    env = clean_env(frozen)
    executable_hashes = {}
    for job in frozen['commands']:
        require(shutil.disk_usage(ROOT).free >= MIN_FREE_BYTES, 'below fixed free-space reserve')
        require(sha(FIXTURE) == FIXTURE_SHA and sha(SCRIPT) == frozen['proofs'][str(SCRIPT)],
                'source/controller changed')
        executable = Path(job['command'][0])
        digest = sha(executable)
        expected = frozen['proofs'].get(str(executable), executable_hashes.get(str(executable)))
        require(expected is not None and digest == expected, 'unbound executable: ' + str(executable))
        if job['kind'] == 'export':
            Path(job['artifact']).parent.mkdir(exist_ok=True)
            require(not Path(job['artifact']).exists(), 'artifact already exists')
        row = dict(spec=job, cwd=str(ROOT), controller_pid=os.getpid(), started_at=time.time(),
                   executable_sha256=digest)
        out, err = RUN / (job['label'] + '.stdout'), RUN / (job['label'] + '.stderr')
        with out.open('xb') as stdout, err.open('xb') as stderr:
            child = subprocess.Popen(job['command'], cwd=ROOT, env=env | job['extra_env'],
                                     stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
            row['child_pid'] = child.pid
            write_new(RUN / (job['label'] + '.started.json'), row)
            try:
                row['returncode'] = child.wait()
            except BaseException:
                # Keep the shared lock until this exact owned child terminates.
                # Never signal a process or unlock around a still-running child.
                child.wait()
                raise
        row['finished_at'] = time.time()
        row['stdout'] = dict(path=str(out), sha256=sha(out))
        row['stderr'] = dict(path=str(err), sha256=sha(err))
        if 'artifact' in job and Path(job['artifact']).exists():
            path = Path(job['artifact'])
            require(0 < path.stat().st_size <= MAX_ARTIFACT, 'invalid artifact byte size')
            row['artifact'] = dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)
        records.append(row)
        with (RUN / 'commands.jsonl').open('a') as stream:
            stream.write(json.dumps(row, allow_nan=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        require((row['returncode'] == 0) == not_failure(job), 'unexpected command exit: ' + job['label'])
        if job['kind'] == 'build':
            path = RUN / ('native' if job['label'] == 'build-native' else 'inspector-target/release/panic-store-inspector')
            executable_hashes[str(path)] = sha(path)
            write_new(RUN / (job['label'] + '.binary.json'), dict(path=str(path), sha256=sha(path),
                       build_label=job['label'], build_record=row))
    validate_records(frozen, records)


def not_failure(job):
    return not (job['kind'] in ['native', 'vm'] and job['mode'] == '1')


def run(args):
    frozen = read(FROZEN)
    verify(frozen['proofs'])
    require(str(Path(sys.executable).resolve(strict=True)) == frozen['python'], 'Python launcher differs')
    require(frozen['commands'] == schedule(Path(frozen['rustc']), Path(frozen['cargo']), frozen['bundles']),
            'frozen schedule differs')
    require(not os.path.lexists(RUN), 'run directory already exists; do not retry workloads')
    require(1 <= args.attempt <= 9, 'invalid bounded lock attempt')
    if args.attempt > 1:
        previous = read(B / f'local-export-panic-attempt-{args.attempt - 1:02}.json')
        require(previous['status'] == 'unstarted-lock-timeout' and previous['frozen_sha256'] == sha(FROZEN),
                'only an unstarted shared-lock timeout can be retried')
    attempt_path = B / f'local-export-panic-attempt-{args.attempt:02}.json'
    require(not attempt_path.exists(), 'attempt already exists')
    attempt = dict(status='waiting for lock', controller_pid=os.getpid(), controller_ppid=os.getppid(),
                   started_at=time.time(), frozen_sha256=sha(FROZEN), command=sys.argv,
                   shared_lock=str(LOCK), workload_started=False)
    write_new(B / f'local-export-panic-attempt-{args.attempt:02}.started.json', attempt)
    records = []
    try:
        require(LOCK.resolve(strict=True) == LOCK and stat.S_ISREG(LOCK.lstat().st_mode), 'wrong shared lock')
        with LOCK.open('r+') as lock:
            deadline = time.monotonic() + 300
            while True:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        attempt['status'] = 'unstarted-lock-timeout'
                        raise TimeoutError('shared lock unavailable after 300 seconds; no workload started')
                    time.sleep(1)
            attempt['lock_acquired_at'] = time.time()
            verify(frozen['proofs'])
            require(not os.path.lexists(RUN) and shutil.disk_usage(ROOT).free >= MIN_FREE_BYTES,
                    'run namespace occupied or insufficient fixed reserve')
            RUN.mkdir()
            attempt['workload_started'] = True
            execute(frozen, records)
            verify(frozen['proofs'])
            artifacts = {}
            for tag in ['baseline-plain', 'candidate-plain', 'baseline-inline', 'candidate-inline']:
                dumps = sorted((RUN / tag / 'mir').glob('*.mir'))
                require(0 < len(dumps) <= 1000 and sum(p.stat().st_size for p in dumps) <= MAX_ARTIFACT,
                        'missing or excessive bounded MIR evidence')
                for path in dumps:
                    bind(artifacts, path)
            for path in sorted(RUN.glob('*')):
                if path.is_file():
                    bind(artifacts, path)
            for row in records:
                if 'artifact' in row:
                    bind(artifacts, row['artifact']['path'], row['artifact']['sha256'])
            bind(artifacts, RUN / 'inspector-target/release/panic-store-inspector')
            write_new(RUN / 'records.json', records)
            bind(artifacts, RUN / 'records.json')
            write_new(RUN / 'execution.json', dict(status='awaiting structural inspection',
                       completed_commands=len(records), frozen_sha256=sha(FROZEN), proofs=artifacts,
                       attempt=args.attempt,
                       bytecode_and_error_parity=True, native_oracles_passed=True,
                       structural_coverage_claimed=False, performance_measurement=False))
            attempt['status'] = 'awaiting structural inspection'
    except BaseException:
        if attempt['status'] != 'unstarted-lock-timeout':
            attempt['status'] = 'failed'
        attempt['exception'] = traceback.format_exc()
        raise
    finally:
        attempt['finished_at'] = time.time()
        attempt['completed_commands'] = len(records)
        write_new(attempt_path, attempt)


def finalize(args):
    frozen, execution = read(FROZEN), read(RUN / 'execution.json')
    verify(frozen['proofs'])
    require(str(Path(sys.executable).resolve(strict=True)) == frozen['python'], 'Python launcher differs')
    verify(execution['proofs'])
    require(execution['status'] == 'awaiting structural inspection'
            and execution['frozen_sha256'] == sha(FROZEN), 'wrong execution receipt')
    records = read(RUN / 'records.json')
    require([json.loads(line) for line in (RUN / 'commands.jsonl').read_text().splitlines()] == records,
            'raw record archives differ')
    validate_records(frozen, records)
    attempt_path = B / f"local-export-panic-attempt-{execution['attempt']:02}.json"
    attempt = read(attempt_path)
    require(attempt['status'] == 'awaiting structural inspection' and attempt['workload_started'] is True
            and attempt['frozen_sha256'] == sha(FROZEN) and attempt['completed_commands'] == COMMAND_COUNT
            and attempt['started_at'] <= attempt['lock_acquired_at'] <= records[0]['started_at']
            and records[-1]['finished_at'] <= attempt['finished_at']
            and all(row['controller_pid'] == attempt['controller_pid'] for row in records),
            'command sequence does not bind its terminal shared-lock attempt')
    inspection_path = Path(args.inspection)
    require(inspection_path.is_relative_to(B) or inspection_path.is_relative_to(RUN),
            'inspection report must be task-owned')
    report = read(inspection_path)
    require(report['schema_version'] == 1 and report['coverage_pass'] is True
            and report['execution_sha256'] == sha(RUN / 'execution.json')
            and report['frozen_sha256'] == sha(FROZEN) and report['fixture_sha256'] == FIXTURE_SHA,
            'inspection does not bind this actual run')
    require(report['reviewer'].strip() and report['method'] == 'explicit actual MIR and bytecode data-flow inspection',
            'explicit reviewed structural evidence required')
    cases = report['cases']
    expected = {(arm, inline) for arm in ['baseline', 'candidate'] for inline in [False, True]}
    require(len(cases) == 4 and all(type(c['inline']) is bool for c in cases)
            and {(c['arm'], c['inline']) for c in cases} == expected,
            'all four exports require structural inspection')
    proofs = dict(frozen['proofs']) | execution['proofs']
    for case in cases:
        tag = case['arm'] + ('-inline' if case['inline'] else '-plain')
        artifact = RUN / tag / 'primary.rbc'
        inspector_row = next(r for r in records if r['spec']['label'] == tag + '-inspect')
        json_path = Path(inspector_row['stdout']['path'])
        require(case['artifact_sha256'] == sha(artifact)
                and case['program_json_sha256'] == sha(json_path), 'inspection artifact identity differs')
        mir = case['mir']
        mir_path = Path(mir['path'])
        require(mir_path.parent == RUN / tag / 'mir' and str(mir_path) in execution['proofs'],
                'MIR witness not in this diagnostic export')
        bind(proofs, mir_path, mir['sha256'])
        text = mir_path.read_text()
        for field in ['function_signature', 'block_excerpt', 'dereference_assignment', 'panic_call']:
            require(isinstance(mir[field], str) and mir[field].strip() and mir[field] in text,
                    'MIR witness text is not present: ' + field)
        require(mir['dereference_assignment'] in mir['block_excerpt']
                and mir['panic_call'] in mir['block_excerpt']
                and mir['block_excerpt'].index(mir['dereference_assignment']) < mir['block_excerpt'].index(mir['panic_call']),
                'store and panic order not retained in block excerpt')
        for field in ['reachable_from_entry', 'same_basic_block', 'dereference_is_first_argument',
                      'stored_value_is_second_argument', 'not_panic_preparation',
                      'terminator_is_recognized_original_fndef', 'is_actual_instance_mir_body']:
            require(mir[field] is True, 'MIR coverage missing: ' + field)
        for field in ['instance_mir_stage_reason', 'recognized_definition', 'classifier_source_reason',
                      'reachability_reason', 'argument_mapping_reason']:
            require(isinstance(mir[field], str) and mir[field].strip(), 'missing inspection explanation: ' + field)
        classifier = (B / 'owned-analysis-source/crates/mir-export/src/lower.rs'
                      if case['arm'] == 'baseline' else ROOT / 'crates/mir-export/src/lower.rs')
        require(mir['classifier_source_path'] == str(classifier)
                and mir['classifier_source_sha256'] == frozen['proofs'][str(classifier)],
                'classification explanation is not bound to the selected compiler source')
        program = read(json_path)
        bytecode = case['bytecode']
        require(type(bytecode['function_index']) is int
                and 0 <= bytecode['function_index'] < len(program['functions']), 'invalid witness function index')
        function = program['functions'][bytecode['function_index']]
        require(function['name'] == bytecode['function_name'], 'wrong bytecode function')
        store_pc, trap_pc = bytecode['store_pc'], bytecode['trap_pc']
        require(type(store_pc) is int and type(trap_pc) is int
                and 0 <= store_pc < trap_pc < len(function['code']), 'invalid Store/Trap witness PCs')
        store, trap = function['code'][store_pc], function['code'][trap_pc]
        require(store == bytecode['store'] and set(store) == {'Store'} and store['Store']['size'] == 8
                and trap == bytecode['trap'] and set(trap) == {'Trap'}, 'actual Store/Trap witness differs')
        require(trap['Trap']['message'].startswith(mir['recognized_definition'] + ' at '),
                'witness Trap is not the identified recognized panic')
        for row in records:
            if (row['spec']['kind'] == 'vm' and row['spec']['arm'] == case['arm']
                    and row['spec']['inline'] == case['inline'] and row['spec']['mode'] == '1'):
                require(trap['Trap']['message'].encode() in output(row, 'stderr'),
                        'VM failure does not identify the witnessed panic Trap')
        for field in ['reachable_from_entry', 'store_executes_before_trap', 'address_is_destination_argument',
                      'value_is_value_argument', 'excludes_caller_initialization']:
            require(bytecode[field] is True, 'bytecode coverage missing: ' + field)
        require(bytecode['argument_and_control_flow_derivation'].strip(), 'missing explicit data-flow derivation')
        require(bytecode['trace'], 'missing data-flow operation trace')
        for step in bytecode['trace']:
            require(type(step['function_index']) is int
                    and 0 <= step['function_index'] < len(program['functions']), 'invalid trace function index')
            f = program['functions'][step['function_index']]
            require(type(step['pc']) is int and 0 <= step['pc'] < len(f['code'])
                    and f['code'][step['pc']] == step['operation'] and step['meaning'].strip(),
                    'data-flow trace does not reproduce actual operations')
    bind(proofs, inspection_path)
    bind(proofs, attempt_path)
    bind(proofs, B / f"local-export-panic-attempt-{execution['attempt']:02}.started.json")
    bind(proofs, FROZEN)
    bind(proofs, RUN / 'execution.json')
    write_new(B / 'local-export-panic-passed.json', dict(status='passed',
              candidate_tool_key=CANDIDATE, baseline_tool_key=BASELINE,
              completed_commands=COMMAND_COUNT, native_commands=12, vm_commands=64,
              export_commands=8, inspector_commands=4, build_commands=2,
              values=VALUES, engines=ENGINES, inline_leaves=[False, True],
              actual_mir_and_argument_directed_store_before_trap=True,
              bytecode_and_error_parity=True, proofs=proofs, performance_measurement=False,
              structural_method='explicit inspection; not an automated MIR semantic proof'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    prepare = modes.add_parser('freeze')
    prepare.add_argument('--rustc', required=True)
    prepare.add_argument('--cargo', required=True)
    runner = modes.add_parser('run')
    runner.add_argument('--attempt', type=int, default=1)
    final = modes.add_parser('finalize')
    final.add_argument('--inspection', required=True)
    args = parser.parse_args()
    require(Path.cwd() == ROOT, 'run from the isolated root worktree')
    {'freeze': freeze, 'run': run, 'finalize': finalize}[args.mode](args)


if __name__ == '__main__':
    main()
