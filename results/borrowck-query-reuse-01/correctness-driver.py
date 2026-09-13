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
target = root / '.work/borrowck-cache-target/debug'
modules = sys.argv[2:] or ['test_borrowck_cache', 'test_borrowck_cache_cargo']
assert all(module.split('.')[0] in ['test_borrowck_cache', 'test_borrowck_cache_cargo'] for module in modules)
command = [sys.executable, '-m', 'unittest', '-v', *modules]
record = dict(owner=str(root), supervisor_pid=os.getpid(), performance_measurement=False,
              status='waiting', command=command, source_commit=subprocess.check_output(
                  ['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
              binaries={name:hashlib.sha256((target/name).read_bytes()).hexdigest() for name in
                        ['rust-interp-mir-export', 'rust-interp-rustc-wrapper', 'rust-interp-vm']},
              tests={name:hashlib.sha256((root/'tests'/name).read_bytes()).hexdigest() for name in
                     ['test_borrowck_cache.py', 'test_borrowck_cache_cargo.py']})
(work / 'driver.py').write_bytes(Path(__file__).read_bytes())
def save():
    temporary = work / 'receipt.tmp'
    temporary.write_text(json.dumps(record, indent=2) + '\n')
    temporary.replace(work / 'receipt.json')
save()
env = {k: v for k, v in os.environ.items()
       if not k.startswith(('RUST_INTERP_', 'CARGO_PROFILE_'))
       and k not in ('RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                    'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR')}
env.update(RUST_INTERP_TEST_EXPORTER=str(target/'rust-interp-mir-export'),
           RUST_INTERP_TEST_VM=str(target/'rust-interp-vm'),
           RUST_INTERP_TEST_ARTIFACT_DIR=str(work/'fixtures'))
with (root / '.work/benchmark.lock').open('a') as lock:
    deadline = time.monotonic() + 1800
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                record['status'] = 'lock timeout; no commands run'
                save()
                raise SystemExit(75)
            print('Waiting for shared build/test lock.', flush=True)
            time.sleep(30)
    print('Acquired shared lock for compiler/Cargo correctness tests.', flush=True)
    with (work / 'tests.log').open('x') as log:
        child = subprocess.Popen(command, cwd=root/'tests', env=env, stdout=log, stderr=subprocess.STDOUT)
        record.update(status='running', child_pid=child.pid, identity=subprocess.check_output(
            ['ps', '-p', str(child.pid), '-o', 'pid,ppid,lstart,tty,command'], text=True))
        save()
        record['returncode'] = child.wait()
    record.update(status='passed' if record['returncode'] == 0 else 'failed',
                  log_sha256=hashlib.sha256((work/'tests.log').read_bytes()).hexdigest())
    save()
    print((work/'tests.log').read_text()[-25000:], flush=True)
    raise SystemExit(record['returncode'])
