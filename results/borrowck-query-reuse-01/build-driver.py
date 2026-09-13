import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path(__file__).resolve().parent.parent
work = root / '.work' / sys.argv[1]
work.mkdir(exist_ok=False)
target = root / '.work/borrowck-cache-target'
env = {k: v for k, v in os.environ.items()
       if not k.startswith(('RUST_INTERP_', 'CARGO_PROFILE_'))
       and k not in ('RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                    'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR')}
env.update(CARGO_PROFILE_DEV_DEBUG='0', CARGO_PROFILE_TEST_DEBUG='0', CARGO_INCREMENTAL='0')
prefix = ['cargo', '+nightly-2026-09-08']
common = ['--locked', '--offline', '--jobs', '2', '--target-dir', str(target)]
commands = [
    prefix + ['test', *common, '--package', 'rust-interp-mir-export'],
    prefix + ['build', *common, '--package', 'rust-interp-mir-export', '--package', 'rust-interp-bytecode',
              '--bin', 'rust-interp-mir-export', '--bin', 'rust-interp-rustc-wrapper', '--bin', 'rust-interp-vm'],
    [sys.executable, '-m', 'unittest', '-v',
     'test_borrowck_cache_launcher', 'test_interpreter_build_metrics', 'test_workspace_cache',
     'test_isolated_launcher', 'test_cargo_targets', 'test_test_discovery', 'test_toolchain_lookup'],
    [sys.executable, '-m', 'unittest', '-v', 'test_borrowck_cache'],
]
if (root / 'tests/test_borrowck_cache_cargo.py').exists():
    commands[-1].append('test_borrowck_cache_cargo')
receipt = dict(owner=str(root), supervisor_pid=os.getpid(), performance_measurement=False,
               commands=commands, lock=str((root / '.work/benchmark.lock').resolve()), status='waiting',
               head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
               script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
def save():
    (work / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
save()
with (root / '.work/benchmark.lock').open('a') as lock:
    deadline = time.monotonic() + 1800
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                receipt['status'] = 'lock timeout; no commands run'
                save()
                raise SystemExit(75)
            print('Waiting for shared build/test lock; no peer workload changed.', flush=True)
            time.sleep(30)
    receipt['status'] = 'running'
    receipt['results'] = []
    save()
    print('Acquired shared build/test lock.', flush=True)
    for index, command in enumerate(commands):
        child_env = dict(env)
        cwd = root if index < 2 else root / 'tests'
        if index == 3:
            child_env.update(RUST_INTERP_TEST_EXPORTER=str(target / 'debug/rust-interp-mir-export'),
                             RUST_INTERP_TEST_VM=str(target / 'debug/rust-interp-vm'),
                             RUST_INTERP_TEST_ARTIFACT_DIR=str(work / 'fixtures'))
        print('Correctness command', index, command, flush=True)
        with (work / (str(index) + '.log')).open('x') as log:
            child = subprocess.Popen(command, cwd=cwd, env=child_env, stdout=log, stderr=subprocess.STDOUT)
            row = dict(command=command, child_pid=child.pid, cwd=str(cwd),
                       identity=subprocess.check_output(['ps', '-p', str(child.pid), '-o',
                                                        'pid,ppid,lstart,tty,command'], text=True))
            receipt['results'].append(row)
            save()
            row['returncode'] = child.wait()
        row['log_sha256'] = hashlib.sha256((work / (str(index) + '.log')).read_bytes()).hexdigest()
        save()
        print((work / (str(index) + '.log')).read_text()[-14000:], flush=True)
        if row['returncode']:
            receipt['status'] = 'failed'
            save()
            raise SystemExit(row['returncode'])
    receipt['status'] = 'passed'
    save()
