"""Real literal dependency metadata and both alias checkers over all thirteen actual proc_macro tests."""
from pathlib import Path
import fcntl, hashlib, json, os, resource, shutil, subprocess, time, tomllib, traceback

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
RESULT = Path(__file__).resolve().parent
WORK = ROOT / '.work/proc-macro-arena-crate-miri-03'
SOURCE = ROOT / 'results/proc-macro-arena-crate-05/source'
PLAN_PATH = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/.work/proc-macro-arena-whole-crate-miri-plan-03.json')
assert hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest() == '9ce144943feb0cdc71e3c24f097be77a6f827c414e7dc370bd73a42f02934b42'
PLAN = json.loads(PLAN_PATH.read_text())
SYSROOT = ROOT / '.work/proc-macro-arena-miri-02/sysroot'
TOOLS = ROOT / '.work/proc-macro-miri-tools-01'
TC = Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin')
LIB = TC / 'lib/rustlib/src/rust/library'
REGISTRY = Path('/Users/danluu/.cargo/registry')
REGISTRY_ID = 'index.crates.io-1949cf8c6b5b557f'
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
GIB = 1024**3
PINS = {Path(k): v for k, v in {'/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/Cargo.toml': 'f91d22525f86110eb784ba390dd389033b87e8f7841c071a7803a1c63121a990', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/bridge/arena.rs': 'a2b05d25db81e5703fa5872e4b7961774a961a3360c0420daf8d2c740e4e5fa2', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/bridge/buffer.rs': '858499925d66e8014bf779ded30d67718ce9fed9541442f4a81b799b7f302560', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/bridge/client.rs': 'fe5d6760d816a6f1f612d85107eed3a88d8929af93cb4309ababcd3e9b4565b2', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/bridge/closure.rs': '03453e29c27d9a3ffafe2455bee14d65815fa6c8df1e9d6cf131aacc2ef624a8', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/bridge/fxhash.rs': '43c95da90564aa359a25b5a567cb5da351f40092caa260c29d009b7e25c68647', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/bridge/handle.rs': 'cd7e0b6c7940f7ae9baad9c463e4bc3a77dd5db29922a2e988dfeef4230d5bde', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/bridge/mod.rs': 'cdcdf5e2d24471f06b59f2baa7f254c5160bc0acc25a06c535f8cb3872eeb83b', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/bridge/panic_message.rs': '56d2ceea35eaae7cf601a8029e5351b24a3ac56c3e3f4f4b2d4fd6d933aed971', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/bridge/rpc.rs': '611a26a3f2080a821a6921c1f0e74e734bf9cb9dd37891c82765f9755a6cf06c', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/bridge/selfless_reify.rs': 'ee921c120b8a72c6e1e0df5ec3d5b0662b5411c49673a7ceecbc37b421c76edd', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/bridge/server.rs': '1a6eb7d13e8af5b16e3fa7930e4ff2925bf861ec4b86e06df75595d01e9e8d3a', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/bridge/symbol.rs': '086c4712892a0377af36274941cce3585cf306290ebbb06158ccf4789bdbe3ba', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/diagnostic.rs': '8c84548915beeea0de620ac65ab93d89d124e19ac02632b080293b0c1c80cb8a', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/escape.rs': '66c6b2d053be4c6b8a63c508c475173322ea3a70e495018938ba5f93b8662dfd', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/lib.rs': '68237ec6a7a9a2d1dd7cd81e41ccb2996414df1891e4d8dba9e4f19a862c1f50', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/quote.rs': '87451d78d39b8de71a06744cb20b38cd415c38f621e41c9112b0cf005128d2b0', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/source/src/to_tokens.rs': '8d6dd0acef632336cf4b10319eb1f4a035a035b6bb4b0d3ba57aed11f917e48a', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/literal-escaper.rs': 'd79e2b634a4d25f44258c2a8afd854e1f87c967716fb564603feb89246c0f722', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/proc-macro-miri-tools-01/bin/miri': '8f20c45b352ceffd3495a23c90b62653ee46a671979e66a264ebcb4c6a25105f', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/result.json': '3650b6c5bd07ecf3ea75125131f967921fdc148d1af6aceef5a58c4e1624d60c', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-miri-05/result.json': 'a0a24195b2809ef100c422e1744da021d550d0e73fa41c51bd28ef166846674c', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/proc-macro-arena-miri-02/sysroot/lib/rustlib/aarch64-apple-darwin/lib/libcore-5f55620141d53a81.rlib': '9cc7c8be4e7984c2d29ce3fb55f73e2ea6ff5d714fb5f5c6375a191f524510c5', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/proc-macro-arena-miri-02/sysroot/lib/rustlib/aarch64-apple-darwin/lib/libcore-5f55620141d53a81.rmeta': 'adb271a81db50f61c6e280ac2b486bd64d82aa4a7b83065fbf83eedf1efeb5de', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/proc-macro-arena-miri-02/sysroot/lib/rustlib/aarch64-apple-darwin/lib/libstd-caac9ef6fc0b4c88.rlib': '0c991ddb3a32ae39905853acfd64fddb9977d389f9c6924536ec133af5ec5bad', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/proc-macro-arena-miri-02/sysroot/lib/rustlib/aarch64-apple-darwin/lib/libstd-caac9ef6fc0b4c88.rmeta': '6aef747cc57841a30e8e954cc047093bb92ab9f0f48f96547db3f5816a27a198', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-miri-01/literal-dependency-record.json': 'b531424333808c91535890860577e02b8730e11e071920b1720e29bccd9096ce', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-miri-01/manifest.json': '9e04cae5f33ec5b8c7a3c360f12e2736ae586fbc8a56d8a8a3a57cf4bc8c7d0b', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-miri-01/result.json': '12e596feba14cceedc554f99b660d80b3ce6f2672f3d64ce33bdc4328b92f132', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-miri-01/stacked-borrows-record.json': '80d02eef28be447b48d0acec8e4b33e3a8e23fa8943390e4d8e723141b8ca019', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-miri-01/tree-borrows-record.json': '3a2086f67f9ab0d218098e915ca770ed41c2002237d6b03c8fbb4359758a691b', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-miri-02/result.json': '386ec9c889c06529f50d1741cbf2908cd3159f9f7f633f324fcbd7a38032a3a3', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-miri-02/literal-dependency-record.json': '70342c17da72ca162ac1805703e751df12d2d5e8a61dda4b287d333437356b3b', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-miri-02/stacked-borrows-record.json': '6cfdb2b334916d03f099d71e89e9b28134a8e7734744a2a245a968a63f56a444', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-miri-02/tree-borrows-record.json': 'd49236280a833de9507bad883ff91fc5494a80701c88b99ffa3df209dcbee8db', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-miri-02/manifest.json': 'b8ed3ee224eb341951f867a778e2ef6b811792e0a0b9fd9388589c8c7404f134', '/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/.work/proc-macro-arena-whole-crate-miri-plan-03.json': '9ce144943feb0cdc71e3c24f097be77a6f827c414e7dc370bd73a42f02934b42', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/preparation-plan.json': '992a5892d22eb5eb5c330cde45a9cd4cedc585850235ef0782f80ae80c43a348', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-miri-04/setup-record.json': 'ccf4049e269b2b41457bf50032cea72ea1f517dff8688206c0d458fafa453c00', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-crate-05/compile-record.json': '9795a2f4af68ad1c17e10f15b760ab7b94b39803ebc294173c84f7fe9c78236a'}.items()}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def row(path):
    st = path.stat()
    return {'path': str(path), 'bytes': st.st_size, 'sha256': sha(path),
            'identity': [st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns]}

def save(name, value):
    with (RESULT / name).open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write('\n')

def disk_usage(path):
    files = [p for p in path.rglob('*') if p.is_file()]
    return {'files': len(files), 'logical_bytes': sum(p.stat().st_size for p in files),
            'allocated_bytes': sum(p.stat().st_blocks * 512 for p in files)}

def gate():
    free = shutil.disk_usage(ROOT).free
    if free < 16 * GIB:
        raise RuntimeError(f'fresh admission below 16 GiB: {free}')
    return free

def limits(cpu):
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    resource.setrlimit(resource.RLIMIT_FSIZE, (512 * 1024**2, 512 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

def run(label, command, cpu, additions):
    child_environment = dict(environment, **additions)
    record = {'command': command, 'cwd': str(WORK), 'environment': child_environment,
              'parent_pid': os.getpid(), 'parent_parent_pid': os.getppid(),
              'started_at': time.time(), 'free_bytes_before': gate(),
              'cpu_limit_seconds_per_process': cpu, 'file_limit_bytes': 512 * 1024**2,
              'capacity_observations_are_posthoc_checks': True}
    with (RESULT / (label + '.stdout')).open('xb') as out, (RESULT / (label + '.stderr')).open('xb') as err:
        child = subprocess.Popen(command, cwd=WORK, env=child_environment, stdout=out, stderr=err,
                                 preexec_fn=lambda: limits(cpu), pass_fds=(lock.fileno(),))
        record.update(pid=child.pid, spawned_at=time.time())
        save(label + '-started.json', record)
        low = record['free_bytes_before']
        observations = 0
        while child.poll() is None:
            low = min(low, shutil.disk_usage(ROOT).free)
            observations += 1
            time.sleep(1)
        record['returncode'] = child.wait()
    record.update(status='closed', finished_at=time.time(), minimum_observed_free_bytes=low,
                  capacity_observations=observations, free_bytes_after=shutil.disk_usage(ROOT).free,
                  stdout=row(RESULT / (label + '.stdout')), stderr=row(RESULT / (label + '.stderr')))
    save(label + '-record.json', record)
    commands.append(record)
    if min(low, record['free_bytes_after']) < 8 * GIB:
        raise RuntimeError(f'{label} observed free-space floor violation')
    if disk_usage(WORK)['allocated_bytes'] > 4 * GIB:
        raise RuntimeError(f'{label} exceeded planned 4 GiB workspace budget')
    return record

assert not WORK.exists()
assert not (RESULT / 'started.json').exists()
for path, expected in PINS.items():
    assert sha(path) == expected, str(path)
assert LOCK.is_file() and LOCK.resolve(strict=True) == LOCK
gate()
WORK.mkdir()
for name in ['tmp', 'cargo-home', 'deps']:
    (WORK / name).mkdir()
for parent in [WORK, *WORK.parents]:
    assert not any((parent / '.cargo' / n).exists() for n in ['config', 'config.toml']), str(parent)
environment = PLAN['environment']
assert 'MIRI_BE_RUSTC' not in environment

source_paths = [*PINS, *sorted(p for p in SYSROOT.rglob('*') if p.is_file()), TC / 'bin/rustc', TC / 'bin/cargo', LIB / 'Cargo.lock',
                LIB / 'Cargo.toml', TC / 'lib/rustlib/multirust-channel-manifest.toml',
                TOOLS / 'download.json', TOOLS / 'extraction.json', Path(__file__)]
before = {str(p): row(p) for p in source_paths}
save('source.json', before)
save('started.json', {'status': 'started', 'parent_pid': os.getpid(), 'started_at': time.time(),
                     'canonical_lock': str(LOCK), 'maximum_lock_wait_seconds': 600,
                     'environment': environment, 'work': str(WORK)})
commands = []
dependency_passed = False
dependency_outputs = None
checker_passed = {'stacked-borrows': False, 'tree-borrows': False}
admitted = None
released = None
failure = None
try:
    with LOCK.open('r+') as lock:
        deadline = time.monotonic() + 600
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('canonical lock wait exceeded 600 seconds')
                time.sleep(0.25)
        admitted = time.time()
        save('admission.json', {'admitted_at': admitted, 'free_bytes': gate(), 'parent_pid': os.getpid()})
        expected = json.loads((ROOT / 'results/proc-macro-arena-crate-05/preparation-plan.json').read_text())['expected_unit_tests']
        names = [name for group in expected.values() for name in group]
        assert len(names) == len(set(names)) == 13
        dependency = PLAN['commands'][0]
        record = run(dependency['label'], dependency['argv'], dependency['cpu_seconds'], dependency['environment_additions'])
        dependency_passed = record['returncode'] == 0
        if not dependency_passed:
            raise RuntimeError('literal dependency metadata compilation failed')
        metadata = WORK / 'deps/librustc_literal_escaper.rlib'
        assert metadata.is_file() and metadata.stat().st_size > 0
        dependency_outputs = {str(p): row(p) for p in sorted((WORK / 'deps').iterdir()) if p.is_file()}
        assert len(dependency_outputs) == 2 and any(p.endswith('.d') for p in dependency_outputs)
        save('dependency-outputs.json', dependency_outputs)
        for command in PLAN['commands'][1:]:
            assert command['environment_additions'] == {}
            label = command['label']
            record = run(label, command['argv'], command['cpu_seconds'], command['environment_additions'])
            raw = (RESULT / (label + '.stdout')).read_text()
            checker_passed[label] = (record['returncode'] == 0 and
                'test result: ok. 13 passed; 0 failed; 0 ignored;' in raw and
                all(raw.count('::' + name + ' ... ok') == 1 for name in names))
        assert dependency_outputs == {str(p): row(p) for p in sorted((WORK / 'deps').iterdir()) if p.is_file()}
    released = time.time()
except BaseException:
    failure = traceback.format_exc()
    with (RESULT / 'failure.txt').open('x') as f:
        f.write(failure)
finally:
    if admitted is not None and released is None:
        released = time.time()
    after = {str(p): row(p) for p in source_paths}
    save('source-after.json', after)
    unchanged = before == after
    result = {'status': 'passed' if failure is None and unchanged and len(commands) == 3 and dependency_passed and all(checker_passed.values()) else 'failed',
              'finished_at': time.time(), 'canonical_lock_admitted_at': admitted,
              'canonical_lock_released_at': released, 'sources_unchanged': unchanged,
              'reused_successful_sysroot': str(SYSROOT), 'both_checkers_observed': len(commands) == 3, 'dependency_passed': dependency_passed,
              'completed_commands': len(commands), 'tests_per_checker': 13, 'arena_tests_per_checker': 10, 'interner_tests_per_checker': 3,
              'stacked_borrows_passed': checker_passed['stacked-borrows'],
              'tree_borrows_passed': checker_passed['tree-borrows'],
              'workspace_usage': disk_usage(WORK), 'free_bytes_after': shutil.disk_usage(ROOT).free,
              'compiler_integration': False, 'interner_scope': 'actual original module with reviewed reset change', 'benchmark': False,
              'network_permitted': False, 'failure': failure}
    save('result.json', result)
    manifest = {p.name: row(p) for p in sorted(RESULT.iterdir()) if p.is_file()}
    save('manifest.json', manifest)
    print(json.dumps({'status': result['status'], 'result_sha256': sha(RESULT / 'result.json'),
                      'work': str(WORK), 'usage': result['workspace_usage']}), flush=True)
    if result['status'] != 'passed':
        raise SystemExit(1)
