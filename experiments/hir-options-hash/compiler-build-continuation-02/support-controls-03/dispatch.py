"""One launch; wait for the supervisor launcher and retain its observed result."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import run


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--launch-sha256', required=True)
    args = parser.parse_args()
    assert Path.cwd() == run.OWNER
    path = run.HERE / 'launch.json'
    assert run.owned.sha(path) == args.launch_sha256
    launch = run.read(path)
    assert run.owned.sha(run.HERE / 'inputs.json') == launch['inputs_sha256']
    run.guard(run.read(run.HERE / 'inputs.json'))
    assert not run.WORK.exists() and not run.WORK.is_symlink()
    outer = run.OWNER / '.work/experiments/hir-options-hash-support-controls-supervisor-03'
    assert not outer.exists() and not outer.is_symlink()
    prefix = run.OWNER / '.work/hir-options-hash-support-controls-launch-03'
    record = Path(str(prefix) + '.actual.json')
    assert not record.exists()
    stdout = Path(str(prefix) + '.stdout'); stderr = Path(str(prefix) + '.stderr')
    actual = dict(status='starting', started_at=time.time(), launcher_pid=os.getpid(),
                  command=launch['command'], environment=launch['environment'], cwd=str(run.OWNER),
                  launch=str(path), launch_sha256=args.launch_sha256, stdout=str(stdout), stderr=str(stderr),
                  source_and_inputs_reviewed=True, launcher_wait_seconds=30)
    with record.open('x') as handle: json.dump(actual, handle, sort_keys=True, indent=2)
    with stdout.open('xb') as out, stderr.open('xb') as err:
        process = subprocess.Popen(launch['command'], cwd=run.OWNER, env=launch['environment'],
                                   stdin=subprocess.DEVNULL, stdout=out, stderr=err)
        actual.update(status='launcher-running', supervisor_launcher_pid=process.pid)
        run.owned.write(record, actual)
        try:
            code = process.wait(timeout=30)
            actual.update(status='launcher-finished', launcher_returncode=code, launcher_finished_at=time.time())
        except subprocess.TimeoutExpired:
            actual.update(status='launcher-wait-expired', launcher_wait_expired_at=time.time())
        finally:
            run.owned.write(record, actual)
    print(json.dumps(actual, indent=2))
    assert actual['status'] == 'launcher-finished' and actual['launcher_returncode'] == 0


if __name__ == '__main__': main()
