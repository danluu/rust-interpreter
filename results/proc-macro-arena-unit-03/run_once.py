"""Compile and execute the actual Arena tests once with an installed nightly."""
from pathlib import Path
import fcntl, hashlib, json, os, resource, shutil, subprocess, time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'experiments/proc-macro-arena-reuse-03'
WORK = ROOT / '.work/proc-macro-arena-unit-03'
TOOLCHAIN = Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin')
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
EXPECTED = {
    'patched/arena.rs': '8466807f8c6602cdb20d81995ef50f26e8e1eeb48a97847825cd5b61a10c469b',
    'arena_unit_tests.rs': '14710e15921895bed5e67055099682f54b6af861c0717e6dd2b6c4a770fe5aad',
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    with (HERE / name).open('x') as output:
        json.dump(value, output, sort_keys=True, indent=2)
        output.write('\n')

def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

def run(label, command):
    record = dict(command=command, cwd=str(WORK), environment=environment,
                  parent_pid=os.getpid(), parent_parent_pid=os.getppid(),
                  started_at=time.time(), cpu_limit_seconds=120,
                  file_size_limit_bytes=64 * 1024**2)
    with (HERE / (label + '.stdout')).open('xb') as stdout, (HERE / (label + '.stderr')).open('xb') as stderr:
        child = subprocess.Popen(command, cwd=WORK, env=environment, stdout=stdout,
                                 stderr=stderr, preexec_fn=limits, pass_fds=(lock.fileno(),))
        record.update(pid=child.pid, spawned_at=time.time())
        write(label + '-started.json', record)
        # CPU/file limits are inherited; this runner never signals a process.
        record['returncode'] = child.wait()
    record.update(status='closed', finished_at=time.time(),
                  stdout_sha256=sha(HERE / (label + '.stdout')),
                  stderr_sha256=sha(HERE / (label + '.stderr')))
    write(label + '-record.json', record)
    assert record['returncode'] == 0, record
    return record

assert not WORK.exists()
assert not (HERE / 'source.json').exists()
for name, expected in EXPECTED.items():
    assert sha(SOURCE / name) == expected
assert LOCK.resolve(strict=True) == LOCK and LOCK.is_file()
assert shutil.disk_usage(ROOT).free >= 9 * 1024**3
WORK.mkdir()
(WORK / 'tmp').mkdir()
environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'TMPDIR': str(WORK / 'tmp')}
write('source.json', dict(source=str(SOURCE), source_sha256=EXPECTED,
    rustc_path=str(TOOLCHAIN / 'bin/rustc'), rustc_sha256=sha(TOOLCHAIN / 'bin/rustc'),
    channel_manifest_sha256=sha(TOOLCHAIN / 'lib/rustlib/multirust-channel-manifest.toml'),
    runner_sha256=sha(Path(__file__)), started_at=time.time(), free_bytes=shutil.disk_usage(ROOT).free))
with LOCK.open('r+') as lock:
    deadline = time.monotonic() + 600
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise TimeoutError('canonical workload lock wait exceeded 600 seconds')
            time.sleep(0.25)
    admitted = time.time()
    run('version', [str(TOOLCHAIN / 'bin/rustc'), '-vV'])
    run('compile', [str(TOOLCHAIN / 'bin/rustc'), '--sysroot', str(TOOLCHAIN),
        '--test', '--edition=2024', '-C', 'debuginfo=0', '-C', 'opt-level=0',
        str(SOURCE / 'arena_unit_tests.rs'), '-o', str(WORK / 'arena-tests')])
    binary_sha = sha(WORK / 'arena-tests')
    run('tests', [str(WORK / 'arena-tests'), '--test-threads=1'])
    output = (HERE / 'tests.stdout').read_text()
    assert 'test result: ok. 9 passed; 0 failed; 0 ignored;' in output
    for name, expected in EXPECTED.items():
        assert sha(SOURCE / name) == expected
released = time.time()
write('result.json', dict(status='passed', arena_tests=9, interner_tests_run=0,
    compiler_integration=False, benchmark=False, miri=False, binary_sha256=binary_sha,
    canonical_lock_admitted_at=admitted, canonical_lock_released_at=released,
    free_bytes_after=shutil.disk_usage(ROOT).free))
print(json.dumps(dict(status='passed', arena_tests=9, result_sha256=sha(HERE / 'result.json'))))
