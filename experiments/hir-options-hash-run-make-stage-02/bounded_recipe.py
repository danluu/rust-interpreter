"""Two-cwd adapter around the exact shared four-owner stage monitor.

Only process launch/receipt handling is local: allocation, refusal, owned stop
and failure draining all call the unchanged A-path monitor with explicit roots.
"""
import os
import resource
import subprocess
import time

from . import adapter
from . import support as s

monitor = adapter.monitor()
owned = monitor.owned


def run(command, *, cwd, environment, output, canonical_fd, evidence_roots, expected=(0,)):
    assert cwd in [s.S, s.OUT]
    assert output.is_relative_to(s.WORK) and output.parent.resolve(strict=True) == output.parent
    assert not any(part in ['.', '..'] for part in output.parts)
    context = dict(evidence_root=s.WORK, evidence_roots=tuple(evidence_roots))
    with owned.workload_lock(owned.CANONICAL_LOCK, 600, inherited_fd=canonical_fd):
        pass
    output.mkdir(exist_ok=False)
    initial = monitor.sample(**context)
    assert monitor.rejection(initial) is None, monitor.rejection(initial)
    record = dict(schema_version=1, status='starting', command=list(command), cwd=str(cwd),
        environment=environment, expected=list(expected), supervisor_pid=os.getpid(),
        parent_pid=os.getppid(), started_at=time.time(), samples=[initial],
        inherited_canonical_fd=canonical_fd, canonical_inode=os.fstat(canonical_fd).st_ino,
        shared_monitor_path=monitor.__file__)
    owned.write(output/'receipt.json', record)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    with (output/'stdout').open('xb') as stdout, (output/'stderr').open('xb') as stderr:
        child = subprocess.Popen(command, cwd=cwd, env=environment, stdout=stdout, stderr=stderr,
            start_new_session=True, pass_fds=(canonical_fd,))
        stop_requested = False
        try:
            record.update(status='running', pid=child.pid, identity=owned.identity(child.pid))
            owned.write(output/'receipt.json', record)
            while child.poll() is None:
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    observation = monitor.sample(**context)
                    record['samples'].append(observation)
                    owned.write(output/'receipt.json', record)
                    reason = monitor.rejection(observation)
                    if reason is not None:
                        owned.write(output/'budget-reason.json', dict(reason=reason, observation=observation,
                            child_pid=child.pid, process_group=child.pid))
                        monitor.stop_owned(child, record['identity'], output/'owned-stop.json', reason)
                        stop_requested = True
                        raise RuntimeError(reason)
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            record.update(status='finished', returncode=child.returncode,
                child_cpu=dict(user_seconds=after.ru_utime-before.ru_utime,
                               system_seconds=after.ru_stime-before.ru_stime))
            record['samples'].append(monitor.sample(**context))
            assert monitor.rejection(record['samples'][-1]) is None, monitor.rejection(record['samples'][-1])
            assert child.returncode in expected, 'unexpected run-make stage return code'
        except BaseException as error:
            record.update(status='failed', error=repr(error))
            monitor.drain_failed_child(child, record, output, stop_requested=stop_requested, **context)
            record['returncode'] = child.returncode
            raise
        finally:
            record['finished_at'] = time.time()
            stdout.flush(); stderr.flush()
            record['stdout_sha256'] = owned.sha(output/'stdout')
            record['stderr_sha256'] = owned.sha(output/'stderr')
            owned.write(output/'receipt.json', record)
    return record
