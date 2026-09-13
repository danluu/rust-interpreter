"""Freeze source and controls sequentially; no benchmark lock or workload."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, time

root = Path(__file__).resolve().parents[2]
b = Path(__file__).resolve().parent
commands_path = b / 'local-export-qualification-commands.json'
commands = json.loads(commands_path.read_text())
assert Path.cwd() == root and commands['cwd'] == str(root)
assert list(sys.orig_argv) == commands['freeze']['command'], 'use the exact frozen freeze command'
assert [step['label'] for step in commands['freeze']['steps']] == ['source', 'controls']
receipt_path = b / 'local-export-input-freeze.json'
log_path = b / 'local-export-input-freeze.log'
assert not receipt_path.exists() and not log_path.exists() and not receipt_path.with_suffix('.json.tmp').exists(), 'preserve any previous freeze attempt'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(value):
    temporary = receipt_path.with_suffix('.json.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    temporary.replace(receipt_path)

record = dict(status='running', command=list(sys.orig_argv), executable=sys.executable,
              cwd=str(root), controller_pid=os.getpid(), controller_ppid=os.getppid(),
              started_at=time.time(), commands_sha256=sha(commands_path), steps=[],
              shared_lock_acquired=False, workloads_executed=False)
save(record)
try:
    with log_path.open('x') as log:
        for planned in commands['freeze']['steps']:
            assert sha(commands_path) == record['commands_sha256']
            step = dict(planned, cwd=str(root), controller_pid=os.getpid(), started_at=time.time())
            child = subprocess.Popen(step['command'], cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL)
            step['child_pid'] = child.pid
            record['steps'].append(step)
            try:
                save(record)
            finally:
                code = child.wait()
            step.update(returncode=code, finished_at=time.time())
            save(record)
            assert code == 0, 'freeze child failed: ' + step['label']
        log.flush(); os.fsync(log.fileno())
    record.update(status='passed', returncode=0, finished_at=time.time(),
                  outputs_sha256={name: sha(b / name) for name in [
                      'local-export-prebuild-source/source.json', 'local-export-prebuild-controls.json']},
                  log_sha256=sha(log_path))
except BaseException as error:
    record.update(status='failed', returncode=1, error=repr(error), finished_at=time.time())
    raise
finally:
    save(record)
print(json.dumps(dict(status=record['status'], commands=2, workloads_executed=False,
                     receipt=str(receipt_path)), indent=2))
