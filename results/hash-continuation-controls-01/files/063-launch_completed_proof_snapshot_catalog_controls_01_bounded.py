"""Bounded wrapper/terminal observation; no process signals or identity probes."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
HERE = ROOT/'experiments/completed-proof-snapshot-catalog-controls-01'
LAUNCH = HERE/'launch.json'
EXPECTED = '685b17d1877aa7cbf1b9ed7af085040d70dd53b75d9a78e1fc7510eda2d8d233'
WORK = ROOT/'.work/completed-proof-snapshot-catalog-controls-launch-execution-01'
OUTER = ROOT/'.work/experiments/completed-proof-snapshot-catalog-controls-supervisor-01'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path.cwd() == ROOT and sys.dont_write_bytecode and not sys.flags.optimize
assert sha(LAUNCH) == EXPECTED
plan = json.loads(LAUNCH.read_bytes())
assert sha(HERE/'inputs.json') == plan['inputs_sha256'] and sha(HERE/'run.py') == plan['helper_sha256']
assert plan['owner'] == str(ROOT) and plan['controls'] == 33 and plan['expected_children'] == 1
assert shutil.disk_usage(ROOT).free >= 16*2**30
assert not WORK.exists() and not WORK.is_symlink() and not OUTER.exists() and not OUTER.is_symlink()
WORK.mkdir()
record = dict(status='starting', launcher_source_path=str(Path(__file__).resolve()), launcher_source_sha256=sha(__file__),
    launch_path=str(LAUNCH), launch_sha256=EXPECTED, started_at=time.time(), launcher_pid=os.getpid(),
    launcher_parent_pid=os.getppid(), command=plan['command'], cwd=str(ROOT), environment=plan['environment'],
    launcher_identity=dict(method='in-process', pid=os.getpid(), parent_pid=os.getppid(), pgid=os.getpgrp(),
                           cwd=str(Path.cwd()), argv=list(sys.argv)),
    wrapper_identity_limitation='Popen PID retained; no separate contemporaneous wrapper ps/cwd probe.')


def write():
    with (WORK/'record.staged').open('w') as stream:
        json.dump(record, stream, sort_keys=True, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    (WORK/'record.staged').replace(WORK/'record.json')


write()
with (WORK/'stdout').open('xb') as stdout, (WORK/'stderr').open('xb') as stderr:
    child = subprocess.Popen(plan['command'], cwd=ROOT, env=plan['environment'], stdin=subprocess.DEVNULL,
                             stdout=stdout, stderr=stderr, start_new_session=True)
    record.update(status='wrapper-running', pid=child.pid); write()
    try:
        code = child.wait(timeout=30)
    except subprocess.TimeoutExpired:
        record.update(status='wrapper-observation-expired-task-not-signaled', observation_finished_at=time.time()); write()
        raise
record.update(status='wrapper-finished', launcher_returncode=code, launcher_finished_at=time.time(),
              stdout_sha256=sha(WORK/'stdout'), stderr_sha256=sha(WORK/'stderr')); write()
assert code == 0 and not (WORK/'stderr').read_bytes()
handoff = json.loads((WORK/'stdout').read_bytes())
assert type(handoff['supervisor_pid']) is int and handoff['supervisor_pid'] > 0 and handoff['directory'] == str(OUTER)
record['supervisor_pid'] = handoff['supervisor_pid']; write()
deadline = time.monotonic()+900
while time.monotonic() < deadline:
    if (OUTER/'status.json').exists():
        outer = json.loads((OUTER/'status.json').read_bytes())
        assert outer['supervisor_pid'] == handoff['supervisor_pid'] and outer['cwd'] == str(ROOT)
        assert outer['command'] == plan['command'][6:]
        if outer['status'] == 'finished':
            record.update(status='terminal-observed', returncode=outer['returncode'], finished_at=outer['finished_at'],
                terminal_observed_at=time.time(), outer_sha256=sha(OUTER/'status.json'), controller_pid=outer['child_pid'])
            write(); print(json.dumps(record, sort_keys=True)); assert outer['returncode'] == 0
            break
    time.sleep(2)
else:
    record.update(status='observation-expired-task-not-signaled', observation_finished_at=time.time()); write()
    raise RuntimeError('actual terminal not observed within 900 seconds; task not signaled')
