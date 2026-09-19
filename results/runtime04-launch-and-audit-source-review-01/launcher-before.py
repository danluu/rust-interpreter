"""Launch one reviewed runtime04 proposal and observe its detached supervisor to closure.

The launch digest is supplied only after concrete packet review. No provider,
compiler or controller starts before the unchanged fresh 24 GiB entry check.
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

HERE = Path(__file__).resolve().parent
ROOT = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
SOURCE = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/hir-options-hash/runtime-installation-04')
CAPACITY = dict(entry_gib=24,stop_gib=9,floor_gib=8,
                combined_namespace_bytes=14*2**30,evidence_bytes=256*2**20)
MAXIMUM_OBSERVATION_SECONDS = 1800
MAXIMUM_WRAPPER_SECONDS = 30


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    path=Path(path)
    require(path.resolve(strict=True)==path and path.is_file() and not path.is_symlink()
            and path.stat().st_size<=64*2**20,'ordinary bounded launcher input')
    before=path.stat()
    with path.open('rb') as stream:
        result=hashlib.file_digest(stream,'sha256').hexdigest()
    after=path.stat()
    require(all(getattr(before,'st_'+key)==getattr(after,'st_'+key)
                for key in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']),'launcher input changed')
    return result


def read(path):
    path=Path(path);digest=sha(path);data=path.read_bytes()
    require(len(data)<=64*2**20 and hashlib.sha256(data).hexdigest()==digest,'launcher JSON changed')
    return json.loads(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase',choices=['preflight','installation'],required=True)
    parser.add_argument('--launch-sha256',required=True)
    parser.add_argument('--launcher-sha256',required=True)
    args=parser.parse_args();expected=args.launch_sha256;phase=args.phase
    require(re.fullmatch('[a-f0-9]{64}',args.launcher_sha256)
            and sha(Path(__file__))==args.launcher_sha256,'exact independently reviewed launcher source required')
    packet=SOURCE/(phase+'-plan-01')
    LAUNCH=packet/'launch.json'
    WORK=ROOT/('.work/hir-options-hash-runtime-'+phase+'-launch-execution-04')
    OUTER=ROOT/('.work/experiments/hir-options-hash-runtime-'+phase+'-supervisor-04')
    CONTROLLER=ROOT/('.work/hir-options-hash-runtime-'+phase+'-04')
    require(Path.cwd() == ROOT and sys.dont_write_bytecode and not sys.flags.optimize,
            'fixed owner and unoptimized Python -B required')
    require(re.fullmatch('[a-f0-9]{64}', expected) and sha(LAUNCH) == expected,
            'reviewed launch digest required')
    proposal = read(LAUNCH)
    frozen = read(packet/'inputs.json')
    plan = read(packet/'plan.json')
    base = dict(path='/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/experiments/hir-options-hash-native-controls-03/inputs.json',
                sha256='8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d')
    integrity = frozen.get('file_table_integrity')
    require(frozen.get('file_table_base') == base and type(frozen.get('files')) is dict
            and base['path'] in frozen['files'] and len(frozen['files']) <= 180000
            and type(integrity) is dict and set(integrity) == {'sha256', 'count', 'total_bytes'}
            and type(integrity['count']) is int and len(frozen['files']) <= integrity['count'] <= 180000
            and type(integrity['total_bytes']) is int and 0 <= integrity['total_bytes'] <= 8 * 2**30
            and type(integrity['sha256']) is str and re.fullmatch('[a-f0-9]{64}', integrity['sha256']),
            'reviewed compact input representation required')
    python = str(Path(sys.executable).resolve(strict=True))
    command=[python,'-B',str(ROOT/'scripts/supervise_experiment.py'),'--run-id',OUTER.name,'--',
             python,'-B',str(SOURCE/'entry.py'),'--packet',str(packet),
             '--inputs-sha256',proposal['inputs_sha256'],
             '--snapshot-plan-sha256',proposal['snapshot_plan_sha256']]
    require(proposal['cwd']==str(ROOT) and proposal['command']==command and frozen['python']==python
            and plan['owner']==str(ROOT) and plan['phase']==phase and plan['work']==str(CONTROLLER)
            and plan['supervisor_work']==str(OUTER) and proposal['capacity']==plan['capacity']==CAPACITY,
            'exact runtime owner/phase/context/capacity required')
    require(sha(packet/'inputs.json')==proposal['inputs_sha256']
            and sha(packet/'plan.json')==frozen['plan_sha256']==proposal['plan_sha256']
            and sha(packet/'snapshot-plan.json')==proposal['snapshot_plan_sha256']
            and sha(SOURCE/'entry.py')==proposal['helper_sha256']==frozen['files'][str(SOURCE/'entry.py')]['sha256'],
            'reviewed runtime proposal and frozen entry changed')
    specification=packet/'specification.json'
    require(plan['specification']==dict(path=str(specification),sha256=sha(specification)),
            'exact runtime specification binding required')
    spec=read(specification)
    expected_children=2 if phase=='preflight' else len(spec['loader'])+5
    require(type(proposal['children']) is int and proposal['children']==len(plan['children'])==expected_children,
            'complete runtime probe/loader recipe required')
    require(proposal['environment']==frozen['launch_environment']==plan['launch_environment']==plan['environment'],
            'launch environment differs')
    require(all(not p.exists() and not p.is_symlink() for p in [WORK, OUTER, CONTROLLER]),
            'fresh launch and workload namespaces required')
    free = shutil.disk_usage(ROOT).free
    require(free >= 24 * 2**30, 'fresh 24 GiB required before controller or WORK')
    WORK.mkdir()
    source_bytes=Path(__file__).read_bytes()
    require(hashlib.sha256(source_bytes).hexdigest()==args.launcher_sha256,'launcher changed before source retention')
    with (WORK/'launcher.py').open('xb') as stream:
        stream.write(source_bytes);stream.flush();os.fsync(stream.fileno())
    require(sha(WORK/'launcher.py')==args.launcher_sha256,'retained launcher source differs')
    record = dict(status='starting', phase=phase, launch_path=str(LAUNCH), launch_sha256=expected,
                  retained_launcher_source=str(WORK/'launcher.py'),
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
