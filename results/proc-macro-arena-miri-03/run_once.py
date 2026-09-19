"""One isolated offline Miri sysroot setup and two actual Arena test runs."""
from pathlib import Path
import fcntl, hashlib, json, os, resource, shutil, subprocess, time, tomllib, traceback

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
RESULT = Path(__file__).resolve().parent
WORK = ROOT / '.work/proc-macro-arena-miri-01'
SOURCE = ROOT / 'experiments/proc-macro-arena-reuse-03'
TOOLS = ROOT / '.work/proc-macro-miri-tools-01'
TC = Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin')
LIB = TC / 'lib/rustlib/src/rust/library'
REGISTRY = Path('/Users/danluu/.cargo/registry')
REGISTRY_ID = 'index.crates.io-1949cf8c6b5b557f'
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
GIB = 1024**3
ACTIVE = {'addr2line', 'adler2', 'cfg-if', 'getopts', 'gimli', 'hashbrown', 'libc',
          'memchr', 'miniz_oxide', 'object', 'rustc-demangle', 'rustc-literal-escaper'}
PINS = {
    SOURCE / 'patched/arena.rs': '8466807f8c6602cdb20d81995ef50f26e8e1eeb48a97847825cd5b61a10c469b',
    SOURCE / 'arena_unit_tests.rs': '14710e15921895bed5e67055099682f54b6af861c0717e6dd2b6c4a770fe5aad',
    TOOLS / 'bin/cargo-miri': '6c1aa401a93c5b56a99b6481bb469ea4e412f1115b0215f0e55bf905bd2b127f',
    TOOLS / 'bin/miri': '8f20c45b352ceffd3495a23c90b62653ee46a671979e66a264ebcb4c6a25105f',
}

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

def run(label, command, cpu):
    record = {'command': command, 'cwd': str(WORK), 'environment': environment,
              'parent_pid': os.getpid(), 'parent_parent_pid': os.getppid(),
              'started_at': time.time(), 'free_bytes_before': gate(),
              'cpu_limit_seconds_per_process': cpu, 'file_limit_bytes': 512 * 1024**2,
              'capacity_observations_are_posthoc_checks': True}
    with (RESULT / (label + '.stdout')).open('xb') as out, (RESULT / (label + '.stderr')).open('xb') as err:
        child = subprocess.Popen(command, cwd=WORK, env=environment, stdout=out, stderr=err,
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
    if record['returncode'] != 0:
        raise RuntimeError(f'{label} closed with exit {record["returncode"]}')
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
for name in ['tmp', 'cargo-home', 'sysroot']:
    (WORK / name).mkdir()
for parent in [WORK, *WORK.parents]:
    assert not any((parent / '.cargo' / n).exists() for n in ['config', 'config.toml']), str(parent)
environment = {
    'PATH': str(TC / 'bin') + ':/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C', 'LC_ALL': 'C',
    'TMPDIR': str(WORK / 'tmp'), 'CARGO_HOME': str(WORK / 'cargo-home'),
    'CARGO_NET_OFFLINE': 'true', 'CARGO_BUILD_JOBS': '1',
    'CARGO': str(TC / 'bin/cargo'), 'MIRI': str(TOOLS / 'bin/miri'),
    'MIRI_HOST_SYSROOT': str(TC), 'MIRI_LIB_SRC': str(LIB),
    'MIRI_SYSROOT': str(WORK / 'sysroot'), 'DYLD_LIBRARY_PATH': str(TC / 'lib'),
}
source_paths = [*PINS, TC / 'bin/rustc', TC / 'bin/cargo', LIB / 'Cargo.lock',
                LIB / 'Cargo.toml', TC / 'lib/rustlib/multirust-channel-manifest.toml',
                TOOLS / 'download.json', TOOLS / 'extraction.json', Path(__file__)]
before = {str(p): row(p) for p in source_paths}
save('source.json', before)
save('started.json', {'status': 'started', 'parent_pid': os.getpid(), 'started_at': time.time(),
                     'canonical_lock': str(LOCK), 'maximum_lock_wait_seconds': 600,
                     'environment': environment, 'work': str(WORK)})
commands = []
checker_passed = {'stacked-borrows': False, 'tree-borrows': False}
admitted = None
released = None
failure = None
try:
    packages = [p for p in tomllib.loads((LIB / 'Cargo.lock').read_text())['package']
                if p.get('source', '').startswith('registry+')]
    seed = []
    def copy(rel, expected=None):
        source = REGISTRY / rel
        data = source.read_bytes()
        if expected is not None:
            assert hashlib.sha256(data).hexdigest() == expected, str(source)
        target = WORK / 'cargo-home/registry' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f:
            f.write(data)
        assert sha(target) == sha(source)
        seed.append({'source': row(source), 'destination': row(target)})
    copy(Path('index') / REGISTRY_ID / 'config.json')
    for package in packages:
        name = package['name']
        index = (name[:2] + '/' + name[2:4] + '/' + name if len(name) >= 4 else
                 '3/' + name[0] + '/' + name if len(name) == 3 else str(len(name)) + '/' + name)
        copy(Path('index') / REGISTRY_ID / '.cache' / index)
        if name in ACTIVE:
            copy(Path('cache') / REGISTRY_ID / (name + '-' + package['version'] + '.crate'), package['checksum'])
    assert len(seed) == 44
    save('offline-seed.json', {'files': seed, 'registry_packages': 31,
                             'darwin_archive_packages': sorted(ACTIVE), 'network_permitted': False})
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
        run('rustc-version', [str(TC / 'bin/rustc'), '-vV'], 120)
        run('setup', [str(TOOLS / 'bin/cargo-miri'), 'miri', 'setup', '--target', 'aarch64-apple-darwin', '-v'], 600)
        base = [str(TOOLS / 'bin/miri'), '--sysroot', str(WORK / 'sysroot'), '--test', '--edition=2024']
        target = [str(SOURCE / 'arena_unit_tests.rs'), '--', '--test-threads=1']
        for label, flags in [('stacked-borrows', []), ('tree-borrows', ['-Zmiri-tree-borrows'])]:
            run(label, base + flags + target, 180)
            assert 'test result: ok. 9 passed; 0 failed; 0 ignored;' in (RESULT / (label + '.stdout')).read_text()
            checker_passed[label] = True
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
    result = {'status': 'passed' if failure is None and unchanged else 'failed',
              'finished_at': time.time(), 'canonical_lock_admitted_at': admitted,
              'canonical_lock_released_at': released, 'sources_unchanged': unchanged,
              'setup_passed': any(c['command'][0].endswith('cargo-miri') and c['returncode'] == 0 for c in commands),
              'completed_commands': len(commands), 'arena_tests_per_checker': 9,
              'stacked_borrows_passed': checker_passed['stacked-borrows'],
              'tree_borrows_passed': checker_passed['tree-borrows'],
              'workspace_usage': disk_usage(WORK), 'free_bytes_after': shutil.disk_usage(ROOT).free,
              'compiler_integration': False, 'interner_tests_run': 0, 'benchmark': False,
              'network_permitted': False, 'failure': failure}
    save('result.json', result)
    manifest = {p.name: row(p) for p in sorted(RESULT.iterdir()) if p.is_file()}
    save('manifest.json', manifest)
    print(json.dumps({'status': result['status'], 'result_sha256': sha(RESULT / 'result.json'),
                      'work': str(WORK), 'usage': result['workspace_usage']}), flush=True)
    if result['status'] != 'passed':
        raise SystemExit(1)
