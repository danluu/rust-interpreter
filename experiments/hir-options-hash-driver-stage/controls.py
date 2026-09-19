"""Source-only execution core for one compile and two real hash-driver runs.

No CLI or concrete plan is supplied. The enclosing future stage must first
freeze actual successful compiler, B3, native-role and run-make evidence. Its
check_inputs callback validates those prerequisites and every immutable input;
inspect_closure is a frozen, pure Mach-O inspector, never an executable probe.
"""
import hashlib
import os
from pathlib import Path
import re
import shlex

import loader_trace
import owned_driver


H = 'aarch64-apple-darwin'
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
N = X / '.work/hir-options-hash-compiler-01'
S = N / 'source'
D2 = S / 'build' / H / 'stage0'
E2 = S / 'build' / H / 'stage1'
B3 = N / 'beta-sysroot'
ARTIFACTS = N / 'hash-driver-01'
DRIVER = X / 'experiments/hir-options-hash/controls/driver.rs'
FIXTURE = X / 'experiments/hir-options-hash/controls/fixture.rs'
SOURCE_HASHES = {
    DRIVER: '3953c595bb37a6c05661d9a399599bf5529b6a847629d2e1aa4c47eb8314605b',
    FIXTURE: 'd7f59ad74eb839ba84ce5ef1e8493bdd6f36d0304f240c080582a17824bfbb3d',
}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def desired_commands(plan):
    """Derive the only three permitted workload rows from actual role bindings."""
    require(plan['roles'] == dict(build_compiler=str(D2), build_sysroot=str(B3),
                                 runtime_compiler=str(E2), application_sysroot=str(E2)),
            'compiler role substitution')
    pair = plan['ordered_driver_pair']
    require(type(pair) is list and len(pair) == 2, 'complete ordered extern pair required')
    dylib, rmeta = map(Path, pair)
    require(dylib.parent == rmeta.parent == B3 / 'lib/rustlib' / H / 'lib'
            and re.fullmatch(r'librustc_driver-[0-9a-f]+\.dylib', dylib.name)
            and rmeta == dylib.with_suffix('.rmeta'), 'unproved private driver pair')
    env = plan['environment']
    require(set(env) <= {'PATH', 'HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'TZ',
                         'TMPDIR', 'SDKROOT', 'PYTHONDONTWRITEBYTECODE', 'PYTHONNOUSERSITE',
                         '__CF_USER_TEXT_ENCODING'}, 'unadmitted build/runtime environment key')
    require(env.get('TMPDIR') == str(ARTIFACTS / 'tmp') and env.get('SDKROOT') == plan['sdk'],
            'explicit owned temporary directory and qualified SDK required')
    require(Path(plan['clang']).is_absolute() and Path(plan['sdk']).is_absolute(),
            'qualified absolute tool routes required')
    binary = ARTIFACTS / 'hash-control-driver'
    compile_argv = [str(D2 / 'bin/rustc'), '--sysroot=' + str(B3), '--edition=2024',
        '--crate-name=hash_cache_control_driver', '--print=link-args', str(DRIVER),
        '--extern', 'rustc_driver=' + pair[0], '--extern', 'rustc_driver=' + pair[1],
        '-Lnative=' + str(E2 / 'lib'), '-Clinker=' + plan['clang'],
        '-C', 'link-arg=-Wl,-rpath,' + str(E2 / 'lib'), '-o', str(binary)]
    rows = [dict(argv=compile_argv, cwd=str(S), environment=env | {'RUSTC_BOOTSTRAP': '1'})]
    for mode in ['serial', 'parallel']:
        rows.append(dict(argv=[str(binary), str(E2), str(ARTIFACTS / 'fixture.rs'),
                               str(ARTIFACTS / mode), mode], cwd=str(S),
                         environment=env | {'DYLD_PRINT_LIBRARIES': '1'}))
    return rows


def linker_observation(raw, plan):
    """Bind the actual printed linker executable and essential role arguments.

    Retain every parsed argument and environment field; these checks do not
    claim a whitelist of all platform linker options or an observed linker PID.
    The successful rustc child and final static/actual loaders are separate proof.
    """
    require(type(raw) is bytes and 0 < len(raw) <= 2**20 and raw.endswith(b'\n')
            and raw.count(b'\n') == 1, 'one complete printed linker command required')
    words = shlex.split(raw.decode('utf-8', errors='strict'))
    require(words[:1] == ['env'], 'unrecognized linker command form')
    words = words[1:]; removed, env = [], {}
    while words[:1] == ['-u']:
        require(len(words) >= 2 and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', words[1]),
                'invalid linker environment removal')
        removed.append(words[1]); words = words[2:]
    require(len(removed) == len(set(removed)), 'duplicate linker environment removal')
    while words and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*=.*', words[0], re.S):
        key, value = words.pop(0).split('=', 1)
        require(key not in env, 'duplicate printed linker environment')
        env[key] = value
    require(words and words[0] == plan['clang'], 'actual printed linker provider differs')
    def values(flag):
        return [words[i + 1] for i, value in enumerate(words[:-1]) if value == flag]
    require(values('-o') == [str(ARTIFACTS / 'hash-control-driver')]
            and values('-arch') == ['arm64'], 'actual linker output/architecture differs')
    require(words.count(plan['ordered_driver_pair'][0]) == 1
            and plan['ordered_driver_pair'][1] not in words,
            'actual linker did not use the candidate driver dylib')
    require(str(E2 / 'lib') in values('-L')
            and words.count('-Wl,-rpath,' + str(E2 / 'lib')) == 1,
            'actual linker runtime search/rpath differs')
    require(env.get('SDKROOT') == plan['sdk'], 'actual linker SDK differs')
    return dict(raw_sha256=hashlib.sha256(raw).hexdigest(), argv=words,
                environment=env, removed=removed, observation_only=True)


def execute(plan, *, evidence_root, canonical_fd, owned, monitor,
            check_inputs, inspect_closure):
    """Execute only after an enclosing stage admits/freeze-checks prerequisites.

    monitor is the explicit shared candidate-stage budget monitor. Its frozen
    evidence_roots include every compiler failure/continuation/B3/native/recipe/
    hash history. No extra driver process is used for metadata or warming.
    """
    evidence_root = Path(evidence_root)
    require(evidence_root.name.startswith('hir-options-hash-driver-'), 'hash evidence namespace required')
    require(evidence_root.resolve(strict=True) == evidence_root and evidence_root.is_dir(),
            'enclosing stage must create fresh ordinary evidence after admission')
    rows = desired_commands(plan)
    require(plan['children'] == rows, 'frozen driver workload rows differ')
    roots = list(map(Path, plan['evidence_roots']))
    with owned.workload_lock(owned.CANONICAL_LOCK, 600, inherited_fd=canonical_fd):
        pass
    check_inputs()
    owned.disk(N, 24)
    require(ARTIFACTS.parent.resolve(strict=True) == ARTIFACTS.parent
            and not ARTIFACTS.exists() and not ARTIFACTS.is_symlink(), 'fresh native hash outputs required')
    for source, expected in SOURCE_HASHES.items():
        require(source.resolve(strict=True) == source and digest(source) == expected,
                'unchanged hash driver/fixture source required')
    ARTIFACTS.mkdir(); (ARTIFACTS / 'tmp').mkdir()
    with (ARTIFACTS / 'fixture.rs').open('xb') as stream:
        stream.write(FIXTURE.read_bytes()); stream.flush(); os.fsync(stream.fileno())
    initial_fixture = digest(ARTIFACTS / 'fixture.rs')
    require(initial_fixture == SOURCE_HASHES[FIXTURE], 'fixture copy differs')
    for mode in ['serial', 'parallel']:
        (ARTIFACTS / mode).mkdir()
    def sample():
        return monitor.sample(evidence_root=evidence_root, evidence_roots=roots)
    require(monitor.rejection(sample()) is None, 'hash resource reservation rejected')
    compile_output = evidence_root / 'compile'
    compiled = monitor.run(rows[0]['argv'], cwd=S, environment=rows[0]['environment'],
        output=compile_output, canonical_fd=canonical_fd,
        evidence_root=evidence_root, evidence_roots=roots)
    require(compiled['status'] == 'finished' and compiled['returncode'] == 0,
            'hash driver compilation failed')
    require(all((compile_output / name).stat().st_size <= 2**20 for name in ['stdout', 'stderr']),
            'hash compilation output exceeds one MiB per stream')
    require(not (compile_output / 'stderr').read_bytes(), 'unexpected driver build diagnostic')
    link = linker_observation((compile_output / 'stdout').read_bytes(), plan)
    owned.write(evidence_root / 'linker-command.json', link)
    binary = ARTIFACTS / 'hash-control-driver'
    require(binary.resolve(strict=True) == binary and binary.is_file()
            and binary.stat().st_nlink == 1 and os.access(binary, os.X_OK), 'fresh ordinary driver binary required')
    closure = inspect_closure(binary)
    require(str(binary) in closure['files'], 'static executable proof missing')
    providers = {path: row for path, row in closure['files'].items() if path != str(binary)}
    require(providers == plan['runtime_private_providers'], 'generated driver private closure differs')
    allowed = set(closure['files'])
    owned.write(evidence_root / 'driver-loader-closure.json', closure)
    def guard():
        check_inputs()
        require(digest(ARTIFACTS / 'fixture.rs') == initial_fixture, 'driver fixture changed')
        require(all(digest(source) == expected for source, expected in SOURCE_HASHES.items()),
                'unchanged driver source changed')
        require(inspect_closure(binary) == closure, 'driver/provider static closure changed')
    results = []
    for row in rows[1:]:
        mode = row['argv'][-1]
        require(not list((ARTIFACTS / mode).iterdir()), 'fresh per-mode output directory required')
        output = evidence_root / mode
        receipt = owned_driver.run(row['argv'], cwd=S, environment=row['environment'], output=output,
            canonical_fd=canonical_fd, owned=owned, guard=guard,
            resource_observation=sample, resource_rejection=monitor.rejection)
        require(receipt['status'] == 'passed' and not receipt['child_may_be_live']
                and not receipt['probe_may_be_live'], 'failed driver prevents subsequent execution')
        proof = loader_trace.process(receipt, (output / 'stdout').read_bytes(),
            (output / 'stderr').read_bytes(), command=row['argv'], cwd=str(S),
            environment=row['environment'], allowed_private=allowed)
        owned.write(output / 'validated-readback.json', proof)
        results.append(dict(mode=mode, pid=receipt['pid'], receipt_sha256=digest(output / 'receipt.json'),
                            readback_sha256=digest(output / 'validated-readback.json')))
    require(len(results) == 2 and len({row['pid'] for row in results}) == 2,
            'two separate actual driver processes required')
    guard()
    require(monitor.rejection(sample()) is None, 'final hash resource observation rejected')
    return dict(status='hash-driver-core-completed-awaiting-stage-audit', compilation_count=1,
        driver_process_count=2, contexts_per_process=8, processes=results,
        compile_receipt_sha256=digest(compile_output / 'receipt.json'),
        binary_sha256=digest(binary), fixture_sha256=initial_fixture,
        linker_observation_sha256=digest(evidence_root / 'linker-command.json'),
        closure_sha256=digest(evidence_root / 'driver-loader-closure.json'),
        application_qualified=False, performance_measurement=False)
