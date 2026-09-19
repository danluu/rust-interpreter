"""Build actual proc_macro test crate against the matching installed libraries."""
from pathlib import Path
import fcntl, hashlib, json, os, resource, shutil, subprocess, time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
HERE = Path(__file__).resolve().parent
WORK = ROOT / '.work/proc-macro-arena-crate-05'
PLAN = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/proc-macro-arena04-whole-crate-plan-01.json')
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

assert sha(PLAN) == '992a5892d22eb5eb5c330cde45a9cd4cedc585850235ef0782f80ae80c43a348'
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
DEPENDENCY = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01/cargo-home/registry/src/index.crates.io-1949cf8c6b5b557f/rustc-literal-escaper-0.0.8/src/lib.rs')
assert sha(DEPENDENCY) == 'd79e2b634a4d25f44258c2a8afd854e1f87c967716fb564603feb89246c0f722'
with (HERE / 'literal-escaper.rs').open('xb') as output:
    output.write(DEPENDENCY.read_bytes())
dependencies = {}
for name, row in plan['stdlib_component_dependencies'].items():
    path = Path(row['path'])
    assert path.stat().st_size == row['bytes']
    digest = sha(path)
    assert digest == row.get('sha256', digest)
    dependencies[str(path)] = digest
command = [part.replace('<fresh-source>', str(HERE / 'source')).replace('<fresh-output>', str(WORK))
           for part in plan['proposed_command_argv']]
# The installed escaper is force-marked rustc_private. Compile its real source
# normally instead; the proc_macro source and all language checks stay intact.
for index in range(len(command) - 1, 0, -1):
    if command[index].startswith('rustc_literal_escaper='):
        assert command[index - 1] == '--extern'
        del command[index - 1:index + 1]
command.extend(['--extern', 'rustc_literal_escaper=' + str(WORK / 'librustc_literal_escaper.rlib')])
dependency_command = [command[0], '--crate-name', 'rustc_literal_escaper', '--edition=2021',
    '--crate-type=rlib', str(HERE / 'literal-escaper.rs'), '--target', 'aarch64-apple-darwin',
    '--sysroot', plan['installed_toolchain'], '-C', 'opt-level=0', '-C', 'debuginfo=0',
    '--emit=link', '-o', str(WORK / 'librustc_literal_escaper.rlib')]
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
    dependency_compiled = run('dependency', dependency_command)
    compiled = run('compile', command) if dependency_compiled == 0 else None
    tested = None
    if compiled == 0:
        tested = run('tests', [str(WORK / 'proc_macro_arena_tests'), '--test-threads=1'])
    if compiled == 0 and tested == 0:
        text = (HERE / 'tests.stdout').read_text()
        assert 'test result: ok. 13 passed; 0 failed; 0 ignored;' in text
        for names in plan['expected_unit_tests'].values():
            for name in names:
                assert text.count('::' + name + ' ... ok') == 1
    for name, row in rows.items():
        assert sha(Path(row['path'])) == sha(HERE / 'source' / name) == row['sha256']
    for path, digest in dependencies.items():
        assert sha(Path(path)) == digest
    assert sha(DEPENDENCY) == sha(HERE / 'literal-escaper.rs') == 'd79e2b634a4d25f44258c2a8afd854e1f87c967716fb564603feb89246c0f722'
released = time.time()
passed = compiled == 0 and tested == 0
write('result.json', dict(status='passed' if passed else 'failed', compile_returncode=compiled,
    test_returncode=tested, tests_passed=13 if passed else 0, arena_tests=10, interner_tests=3,
    dependency_returncode=dependency_compiled,
    dependency_source_sha256=sha(DEPENDENCY),
    dependency_binary_sha256=sha(WORK / 'librustc_literal_escaper.rlib') if dependency_compiled == 0 else None,
    prior_failed_result_sha256='ac82839d76178bc70cd3d218d01efeae86829be95f8f3b50d0b55af9066a331e',
    canonical_lock_admitted_at=admitted, canonical_lock_released_at=released,
    full_compiler_integration=False, benchmark=False, miri=False,
    binary_sha256=sha(WORK / 'proc_macro_arena_tests') if compiled == 0 else None,
    free_bytes_after=shutil.disk_usage(ROOT).free))
print(json.dumps(dict(status='passed' if passed else 'failed', result_sha256=sha(HERE / 'result.json'))))
raise SystemExit(0 if passed else 1)
