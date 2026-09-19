"""Actual selected proc_macro library and eight public bridge integration tests."""
from pathlib import Path
import fcntl, hashlib, json, os, resource, shutil, subprocess, time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
HERE = Path(__file__).resolve().parent
WORK = ROOT / '.work/proc-macro-arena-bridge-01'
UNIT = ROOT / 'results/proc-macro-arena-crate-05'
FIXTURE = ROOT / 'experiments/proc-macro-arena-bridge-01/bridge.rs'
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
TC = Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    with (HERE / name).open('x') as f:
        json.dump(value, f, sort_keys=True, indent=2)
        f.write('\n')

def limits(cpu):
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

def run(label, command, cpu=120):
    record = dict(command=command, cwd=str(WORK), environment=environment,
        parent_pid=os.getpid(), parent_parent_pid=os.getppid(), started_at=time.time(),
        cpu_limit_seconds=cpu, file_limit_bytes=64 * 1024**2)
    with (HERE / (label + '.stdout')).open('xb') as out, (HERE / (label + '.stderr')).open('xb') as err:
        child = subprocess.Popen(command, cwd=WORK, env=environment, stdout=out,
            stderr=err, preexec_fn=lambda: limits(cpu), pass_fds=(lock.fileno(),))
        record.update(pid=child.pid, spawned_at=time.time())
        write(label + '-started.json', record)
        record['returncode'] = child.wait()
    record.update(status='closed', finished_at=time.time(),
        stdout_sha256=sha(HERE / (label + '.stdout')),
        stderr_sha256=sha(HERE / (label + '.stderr')))
    write(label + '-record.json', record)
    return record['returncode']

assert not WORK.exists() and not (HERE / 'source.json').exists()
assert sha(FIXTURE) == '715e31651259d8fc1b89f82f941e5f665f9e8964cfe96d38d3c0da4914efb195'
assert sha(UNIT / 'result.json') == '3650b6c5bd07ecf3ea75125131f967921fdc148d1af6aceef5a58c4e1624d60c'
unit = json.loads((UNIT / 'result.json').read_text())
source = json.loads((UNIT / 'source.json').read_text())
assert unit['status'] == 'passed' and unit['tests_passed'] == 13
source_pins = {str(UNIT / 'source' / name): row['sha256'] for name, row in source['actual_sources'].items()}
source_pins.update(source['dependency_sha256'])
source_pins[str(FIXTURE)] = sha(FIXTURE)
source_pins[str(TC / 'bin/rustc')] = source['compiler_sha256']
dependency = ROOT / '.work/proc-macro-arena-crate-05/librustc_literal_escaper.rlib'
source_pins[str(dependency)] = unit['dependency_binary_sha256']
for path, digest in source_pins.items():
    assert sha(Path(path)) == digest
assert LOCK.resolve(strict=True) == LOCK and LOCK.is_file()
assert shutil.disk_usage(ROOT).free >= 9 * 1024**3
WORK.mkdir()
(WORK / 'tmp').mkdir()
with (WORK / dependency.name).open('xb') as f:
    f.write(dependency.read_bytes())
with (HERE / 'bridge.rs').open('xb') as f:
    f.write(FIXTURE.read_bytes())
library = WORK / 'libproc_macro.rlib'
command = json.loads((UNIT / 'compile-record.json').read_text())['command']
test_index = command.index('--test')
command[test_index:test_index + 1] = ['--crate-type=rlib']
command[command.index('-o') + 1] = str(library)
command = ['rustc_literal_escaper=' + str(WORK / dependency.name)
           if p.startswith('rustc_literal_escaper=') else p for p in command]
command.extend(['-C', 'metadata=proc_macro_arena04_bridge01'])
fixture_command = [str(TC / 'bin/rustc'), '--sysroot', str(TC), '--edition=2024',
    '--test', str(HERE / 'bridge.rs'), '--extern', 'proc_macro=' + str(library),
    '-L', 'dependency=' + str(WORK), '-C', 'opt-level=0', '-C', 'debuginfo=0',
    '-Zbinary-dep-depinfo', '--emit=dep-info,link', '-o', str(WORK / 'bridge-tests')]
environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'TMPDIR': str(WORK / 'tmp')}
write('source.json', dict(source_pins=source_pins, library_source=str(UNIT / 'source'),
    unit_result_sha256=sha(UNIT / 'result.json'), runner_sha256=sha(Path(__file__)),
    standalone_library_only=True))
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
    library_rc = run('library', command)
    fixture_rc = run('fixture', fixture_command) if library_rc == 0 else None
    test_rc = None
    if fixture_rc == 0:
        depinfo = (WORK / 'bridge-tests.d').read_bytes()
        assert str(library).encode() in depinfo
        assert str(WORK / dependency.name).encode() in depinfo
        with (HERE / 'bridge-tests.d').open('xb') as f:
            f.write(depinfo)
        test_rc = run('tests', [str(WORK / 'bridge-tests'), '--test-threads=1'], 30)
    if test_rc == 0:
        assert 'test result: ok. 8 passed; 0 failed; 0 ignored;' in (HERE / 'tests.stdout').read_text()
    for path, digest in source_pins.items():
        assert sha(Path(path)) == digest
released = time.time()
passed = library_rc == fixture_rc == test_rc == 0
write('result.json', dict(status='passed' if passed else 'failed', library_returncode=library_rc,
    fixture_returncode=fixture_rc, test_returncode=test_rc, tests_passed=8 if passed else 0,
    canonical_lock_admitted_at=admitted, canonical_lock_released_at=released,
    library_sha256=sha(library) if library_rc == 0 else None,
    test_binary_sha256=sha(WORK / 'bridge-tests') if fixture_rc == 0 else None,
    standalone_library_only=True, compiler_distribution_qualified=False, benchmark=False))
print(json.dumps(dict(status='passed' if passed else 'failed', result_sha256=sha(HERE / 'result.json'))))
raise SystemExit(0 if passed else 1)
