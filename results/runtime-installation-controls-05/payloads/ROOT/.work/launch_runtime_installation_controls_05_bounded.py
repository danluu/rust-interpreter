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
HERE = ROOT/'experiments/runtime-installation-controls-05'
LAUNCH = HERE/'launch.json'
EXPECTED = 'f4b6f2b3bb6688e7f65f21d7b0f4196f09dc0ec4d54cb7866012afa6048b0077'
WORK = ROOT/'.work/runtime-installation-controls-launcher-05'
OUTER = ROOT/'.work/experiments/runtime-installation-controls-supervisor-05'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path.cwd() == ROOT and sys.dont_write_bytecode and not sys.flags.optimize
assert type(EXPECTED) is str and len(EXPECTED) == 64, 'actual prepared launch pin required'
assert sha(LAUNCH) == EXPECTED
plan = json.loads(LAUNCH.read_bytes())
assert sha(HERE/'inputs.json') == plan['inputs_sha256'] and sha(HERE/'run.py') == plan['helper_sha256']
assert plan['owner'] == str(ROOT) and plan['controls'] == 25 and plan['expected_children'] == 1
assert shutil.disk_usage(ROOT).free >= 10*2**30
assert not WORK.exists() and not WORK.is_symlink() and not OUTER.exists() and not OUTER.is_symlink()
WORK.mkdir()
record = dict(status='starting', launcher_source_path=str(Path(__file__).resolve()), launcher_source_sha256=sha(__file__),
    launch_path=str(LAUNCH), launch_sha256=EXPECTED, started_at=time.time(), launcher_pid=os.getpid(),
    launcher_parent_pid=os.getppid(), command=plan['command'], cwd=str(ROOT), environment=plan['environment'],
    launcher_identity=dict(method='in-process', pid=os.getpid(), parent_pid=os.getppid(), pgid=os.getpgrp(),
                           cwd=str(Path.cwd()), argv=list(sys.argv)),
    wrapper_identity_limitation='Popen PID retained; no separate contemporaneous wrapper ps/cwd probe.',
    observation_errors=[], disk_samples=[], actual_task_may_be_live=False)


def write():
    with (WORK/'record.staged').open('w') as stream:
        json.dump(record, stream, sort_keys=True, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    (WORK/'record.staged').replace(WORK/'record.json')


def observe_save():
    try:
        write()
    except BaseException as error:
        record['observation_errors'].append(dict(stage='publication', error=repr(error), time=time.time()))


write()
with (WORK/'stdout').open('xb') as stdout, (WORK/'stderr').open('xb') as stderr:
    child = subprocess.Popen(plan['command'], cwd=ROOT, env=plan['environment'], stdin=subprocess.DEVNULL,
                             stdout=stdout, stderr=stderr, start_new_session=True)
    deadline = time.monotonic()+30
    record.update(status='wrapper-running', pid=child.pid, actual_task_may_be_live=True)
    observe_save()
    while True:
        try:
            code = child.wait(timeout=min(1, max(.001, deadline-time.monotonic())))
            break
        except subprocess.TimeoutExpired:
            try:
                record['disk_samples'].append(dict(time=time.time(), free_bytes=shutil.disk_usage(ROOT).free))
            except BaseException as error:
                record['observation_errors'].append(dict(stage='disk-sample', error=repr(error), time=time.time()))
            observe_save()
            if time.monotonic() >= deadline:
                code = None
                record.update(status='wrapper-observation-expired-task-not-signaled',
                    observation_finished_at=time.time(), wrapper_returncode=child.returncode,
                    wrapper_may_be_live=child.returncode is None)
                observe_save()
                break
    if code is None:
        raise RuntimeError('bounded wrapper observation expired; no signal or closure claim')
# Preserve actual wait closure before any post-wait byte or disk observation.
record.update(status='wrapper-finished', launcher_returncode=code, launcher_finished_at=time.time(),
              wrapper_may_be_live=False)
observe_save()
for stream in ['stdout', 'stderr']:
    try:
        record[stream+'_sha256'] = sha(WORK/stream)
    except BaseException as error:
        record['observation_errors'].append(dict(stage='wrapper-'+stream+'-hash', error=repr(error), time=time.time()))
observe_save()
assert code == 0 and not (WORK/'stderr').read_bytes()
handoff = json.loads((WORK/'stdout').read_bytes())
assert type(handoff['supervisor_pid']) is int and handoff['supervisor_pid'] > 0 and handoff['directory'] == str(OUTER)
record['supervisor_pid'] = handoff['supervisor_pid']; observe_save()
deadline = time.monotonic()+900
while time.monotonic() < deadline:
    if (OUTER/'status.json').exists():
        outer = json.loads((OUTER/'status.json').read_bytes())
        assert outer['supervisor_pid'] == handoff['supervisor_pid'] and outer['cwd'] == str(ROOT)
        assert outer['command'] == plan['command'][6:]
        if outer['status'] == 'finished':
            record.update(status='terminal-observed', returncode=outer['returncode'], finished_at=outer['finished_at'],
                terminal_observed_at=time.time(), controller_pid=outer['child_pid'], actual_task_may_be_live=False)
            observe_save()
            try:
                record['outer_sha256'] = sha(OUTER/'status.json')
            except BaseException as error:
                record['observation_errors'].append(dict(stage='actual-outer-hash', error=repr(error), time=time.time()))
            observe_save()
            print(json.dumps(record, sort_keys=True))
            assert outer['returncode'] == 0
            assert not record['observation_errors'], 'observation/publication error; actual closure retained'
            assert all(sample['free_bytes'] >= 9*2**30 for sample in record['disk_samples']), 'observed live floor violation'
            break
    time.sleep(2)
else:
    record.update(status='observation-expired-task-not-signaled', observation_finished_at=time.time(), actual_task_may_be_live=True); observe_save()
    raise RuntimeError('actual terminal not observed within 900 seconds; task not signaled')
