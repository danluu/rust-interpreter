"""Build actual proc_macro test crate against the matching installed libraries."""
from pathlib import Path
import fcntl, hashlib, json, os, resource, shutil, subprocess, time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
HERE = Path(__file__).resolve().parent
WORK = ROOT / '.work/proc-macro-arena-crate-03'
PLAN = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/proc-macro-arena03-whole-crate-feasibility-01.json')
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    with (HERE / name).open('x') as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write('\n')

def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

def run(label, command):
    record = dict(command=command, cwd=str(WORK), environment=environment,
        parent_pid=os.getpid(), parent_parent_pid=os.getppid(), started_at=time.time(),
        cpu_limit_seconds=120, file_size_limit_bytes=64 * 1024**2)
    with (HERE / (label + '.stdout')).open('xb') as out, (HERE / (label + '.stderr')).open('xb') as err:
        child = subprocess.Popen(command, cwd=WORK, env=environment, stdout=out,
            stderr=err, preexec_fn=limits, pass_fds=(lock.fileno(),))
        record.update(pid=child.pid, spawned_at=time.time())
        write(label + '-started.json', record)
        record['returncode'] = child.wait()
    record.update(status='closed', finished_at=time.time(),
        stdout_sha256=sha(HERE / (label + '.stdout')),
        stderr_sha256=sha(HERE / (label + '.stderr')))
    write(label + '-record.json', record)
    return record['returncode']

assert sha(PLAN) == 'b287feda40a7dda4b2e3ed3b308c4089847f2d325efa7c44aa99d2610e20d438'
plan = json.loads(PLAN.read_text())
assert not WORK.exists() and not (HERE / 'source').exists()
assert LOCK.resolve(strict=True) == LOCK and LOCK.is_file()
assert shutil.disk_usage(ROOT).free >= 9 * 1024**3
WORK.mkdir()
(WORK / 'tmp').mkdir()
(HERE / 'source').mkdir()
with (HERE / 'preparation-plan.json').open('xb') as output:
    output.write(PLAN.read_bytes())
rows = dict(plan['original_sources'])
rows.update(plan['patched_sources'])
assert len(rows) == 18
for name, row in rows.items():
    source = Path(row['path'])
    assert sha(source) == row['sha256']
    destination = HERE / 'source' / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as output:
        output.write(source.read_bytes())
    assert sha(destination) == row['sha256']
dependencies = {}
for name, row in plan['stdlib_component_dependencies'].items():
    path = Path(row['path'])
    assert path.stat().st_size == row['bytes']
    digest = sha(path)
    assert digest == row.get('sha256', digest)
    dependencies[str(path)] = digest
command = [part.replace('<fresh-source>', str(HERE / 'source')).replace('<fresh-output>', str(WORK))
           for part in plan['proposed_command_argv']]
environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'TMPDIR': str(WORK / 'tmp')}
write('source.json', dict(actual_sources=rows, dependency_sha256=dependencies,
    compiler_sha256=sha(Path(command[0])), runner_sha256=sha(Path(__file__))))
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
    compiled = run('compile', command)
    tested = None
    if compiled == 0:
        tested = run('tests', [str(WORK / 'proc_macro_arena_tests'), '--test-threads=1'])
    if compiled == 0 and tested == 0:
        text = (HERE / 'tests.stdout').read_text()
        assert 'test result: ok. 12 passed; 0 failed; 0 ignored;' in text
        for names in plan['expected_unit_tests'].values():
            for name in names:
                assert text.count('::' + name + ' ... ok') == 1
    for name, row in rows.items():
        assert sha(Path(row['path'])) == sha(HERE / 'source' / name) == row['sha256']
    for path, digest in dependencies.items():
        assert sha(Path(path)) == digest
released = time.time()
passed = compiled == 0 and tested == 0
write('result.json', dict(status='passed' if passed else 'failed', compile_returncode=compiled,
    test_returncode=tested, tests_passed=12 if passed else 0, arena_tests=9, interner_tests=3,
    canonical_lock_admitted_at=admitted, canonical_lock_released_at=released,
    full_compiler_integration=False, benchmark=False, miri=False,
    binary_sha256=sha(WORK / 'proc_macro_arena_tests') if compiled == 0 else None,
    free_bytes_after=shutil.disk_usage(ROOT).free))
print(json.dumps(dict(status='passed' if passed else 'failed', result_sha256=sha(HERE / 'result.json'))))
raise SystemExit(0 if passed else 1)
