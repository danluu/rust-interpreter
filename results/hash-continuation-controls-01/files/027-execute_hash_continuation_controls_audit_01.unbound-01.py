"""One authorized read-only actual70 audit after observed passing outer closure."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
SOURCE = ROOT/'.work/verify_hash_continuation_controls_01.py'
EXPECTED = None  # Bind only the final reviewed actual70 auditor source digest.
E = ROOT/'.work/hash-continuation-controls-verification-execution-01'
H = ROOT/'experiments/hash-continuation-controls-01'
P = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_bytes())
assert type(EXPECTED) is str and len(EXPECTED) == 64, 'unbound audit-executor draft; no evidence reads'
assert Path.cwd() == ROOT and sys.dont_write_bytecode and not sys.flags.optimize
assert Path(sys.executable).resolve(strict=True) == P and sha(SOURCE) == EXPECTED
assert not E.exists() and not E.is_symlink()
assert not (ROOT/'.work/hash-continuation-controls-independent-verification-01.json').exists()
terminal = read(ROOT/'.work/hash-continuation-controls-01/receipt.json')
outer = read(ROOT/'.work/experiments/hash-continuation-controls-supervisor-01/status.json')
launch = read(ROOT/'.work/hash-continuation-controls-launch-execution-01/record.json')
assert terminal['status'] == 'passed' and terminal['controls_passed'] == 70
assert outer['status'] == 'finished' and outer['returncode'] == 0
assert launch['status'] == 'terminal-observed' and launch['returncode'] == 0
E.mkdir(mode=0o700)
(E/'source.py').write_bytes(SOURCE.read_bytes())
(E/'execution.py').write_bytes(Path(__file__).read_bytes())
environment = read(H/'inputs.json')['environment']
command = [str(P), '-B', str(SOURCE)]
record = dict(status='starting', started_at=time.time(), parent_pid=os.getpid(),
    command=command, cwd=str(ROOT), environment=environment, source_sha256=EXPECTED,
    execution_source_sha256=sha(__file__),
    mode='one authorized independent read-only actual70 verification; no test or provider calls',
    identity_limitation='Popen PID and in-process parent retained; no extra identity probes or signals.')

def save():
    with (E/'record.staged').open('w') as stream:
        json.dump(record, stream, sort_keys=True, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    (E/'record.staged').replace(E/'record.json')

save()
resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
resource.setrlimit(resource.RLIMIT_FSIZE, (256*1024, 256*1024))
try:
    with (E/'stdout').open('xb') as stdout, (E/'stderr').open('xb') as stderr:
        child = subprocess.Popen(command, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                                 stdout=stdout, stderr=stderr)
        record.update(status='running', pid=child.pid)
        publication_error = None
        try:
            save()
        except BaseException as error:
            publication_error = repr(error)
        try:
            code = child.wait(timeout=120)
        except subprocess.TimeoutExpired:
            record.update(status='unresolved-live-child-not-signaled', observation_finished_at=time.time(),
                          publication_error=publication_error)
            save()
            raise
    record.update(status='finished', returncode=code, finished_at=time.time(),
                  stdout_sha256=sha(E/'stdout'), stderr_sha256=sha(E/'stderr'))
    if publication_error is not None:
        record['publication_error'] = publication_error
    save()
    assert code == 0 and not (E/'stderr').read_bytes() and publication_error is None
    assert sha(SOURCE) == EXPECTED == sha(E/'source.py')
    record['verified_output'] = read(E/'stdout'); save()
    print(json.dumps(record, sort_keys=True))
except BaseException as error:
    record['execution_error'] = repr(error); save(); raise
