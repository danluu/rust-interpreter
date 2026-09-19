"""Launch the reviewed twenty-two-snapshot-control proposal and observe its detached supervisor to closure.

The exact launch digest is bound after concrete packet preparation and before separate launch review. No provider,
compiler or controller starts before the unchanged fresh 16 GiB entry check.
An observation timeout preserves the running task and reports it as unclosed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
HERE = ROOT/'experiments/bounded-proof-snapshot-controls-v2-01'
LAUNCH = HERE / 'launch.json'
WORK = ROOT / '.work/proof-snapshot-controls-v2-launch-execution-01'
OUTER = ROOT / '.work/experiments/bounded-proof-snapshot-controls-v2-supervisor-01'
CONTROLLER = ROOT / '.work/bounded-proof-snapshot-controls-v2-01'
MAXIMUM_OBSERVATION_SECONDS = 1800
MAXIMUM_WRAPPER_SECONDS = 30


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def main():
    expected = '8c3b162a55ee17468d4f722d2c9d9d970babc3ba09c4c4f53ad7078a081258f1'
    require(Path.cwd() == ROOT and sys.dont_write_bytecode and not sys.flags.optimize,
            'fixed owner and unoptimized Python -B required')
    require(re.fullmatch('[a-f0-9]{64}', expected) and sha(LAUNCH) == expected,
            'reviewed launch digest required')
    proposal = read(LAUNCH)
    frozen = read(HERE / 'inputs.json')
    python = str(Path(sys.executable).resolve(strict=True))
    command = [python, '-B', str(ROOT / 'scripts/supervise_experiment.py'),
               '--run-id', OUTER.name, '--', python, '-B', str(HERE / 'run.py'),
               '--inputs-sha256', proposal['inputs_sha256']]
    require(proposal['owner'] == str(ROOT) and proposal['command'] == command
            and frozen['python'] == python and proposal['expected_children'] == 1 and proposal['controls']==22,
            'exact reviewed one-child nine-control proposal required')
    require(sha(HERE / 'inputs.json') == proposal['inputs_sha256']
            and sha(HERE / 'run.py') == frozen['files'][str(HERE/'run.py')]['sha256'],
            'reviewed proposal/source bindings changed')
    require(proposal['environment'] == frozen['environment'], 'launch environment differs')
    require(all(not p.exists() and not p.is_symlink() for p in [WORK, OUTER, CONTROLLER]),
            'fresh launch and workload namespaces required')
    free = shutil.disk_usage(ROOT).free
    require(free >= 16 * 2**30, 'fresh 16 GiB required before controller or WORK')
    WORK.mkdir()
    record = dict(status='starting', launch_path=str(LAUNCH), launch_sha256=expected,
                  launcher_source_path=str(Path(__file__).resolve()),
                  launcher_source_sha256=sha(Path(__file__)),
                  launcher_pid=os.getpid(), launcher_parent_pid=os.getppid(),
                  launcher_identity=dict(source='in-process observation', pid=os.getpid(),
                      parent_pid=os.getppid(), pgid=os.getpgrp(), cwd=os.getcwd(), argv=sys.argv),
                  started_at=time.time(),
                  command=command, cwd=str(ROOT), environment=proposal['environment'],
                  entry_free_bytes=free, maximum_observation_seconds=MAXIMUM_OBSERVATION_SECONDS,
                  maximum_wrapper_seconds=MAXIMUM_WRAPPER_SECONDS,
                  wrapper_identity_limitation='Popen PID retained; no separate contemporaneous wrapper ps/cwd probe.')

    def save():
        with (WORK / 'record.staged').open('w') as stream:
            json.dump(record, stream, indent=2, sort_keys=True)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        (WORK / 'record.staged').replace(WORK / 'record.json')

    save()
    with (WORK / 'stdout').open('xb') as stdout, (WORK / 'stderr').open('xb') as stderr:
        child = subprocess.Popen(command, cwd=ROOT, env=proposal['environment'],
                                 stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                 start_new_session=True)
        try:
            record.update(status='wrapper-running', pid=child.pid)
            save()
        finally:
            try:
                code = child.wait(timeout=MAXIMUM_WRAPPER_SECONDS)
            except subprocess.TimeoutExpired:
                record.update(status='wrapper-observation-expired-task-not-signaled',
                              wrapper_may_be_live=True, observation_expired_at=time.time())
                save()
                raise RuntimeError('wrapper has not closed; owned task retained without process control')
            record.update(status='wrapper-finished-awaiting-terminal', launcher_returncode=code,
                          launcher_finished_at=time.time(), stdout_sha256=sha(WORK / 'stdout'),
                          stderr_sha256=sha(WORK / 'stderr'))
            save()
    require(code == 0, 'supervisor wrapper failed; retained history requires inspection')
    handoff = read(WORK / 'stdout')
    require(type(handoff['supervisor_pid']) is int and handoff['supervisor_pid'] > 0
            and handoff['directory'] == str(OUTER), 'wrapper supervisor handoff differs')
    record['supervisor_handoff'] = handoff
    save()
    started = time.monotonic()
    while time.monotonic() - started <= MAXIMUM_OBSERVATION_SECONDS:
        status = OUTER / 'status.json'
        if status.exists():
            terminal = read(status)
            require(terminal['command'] == command[6:] and terminal['cwd'] == str(ROOT),
                    'outer process association differs')
            require(terminal['supervisor_pid'] == handoff['supervisor_pid'],
                    'outer supervisor differs from actual wrapper handoff')
            if terminal['status'] in ['finished', 'supervisor failed']:
                now = time.time()
                record.update(status='terminal-observed', outer_sha256=sha(status),
                              outer_status=terminal['status'], terminal_observed_at=now,
                              finished_at=now, returncode=terminal.get('returncode'),
                              supervisor_pid=terminal['supervisor_pid'],
                              controller_pid=terminal.get('child_pid'))
                save()
                print(json.dumps(dict(path=str(WORK / 'record.json'), **{
                    k: record[k] for k in ['status', 'returncode', 'supervisor_pid', 'controller_pid']})))
                require(terminal['status'] == 'finished' and terminal['returncode'] == 0,
                        'actual supervisor did not finish successfully')
                return
        time.sleep(2)
    record.update(status='observation-expired-task-not-signaled', observation_expired_at=time.time())
    save()
    raise RuntimeError('actual terminal not observed within bound; task retained without process control')


if __name__ == '__main__':
    main()
