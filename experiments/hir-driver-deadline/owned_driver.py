"""Source-only adapter for one fresh hash-driver process; no CLI or admission.

The future qualified stage supplies immutable provider guards, the aggregate
resource observation and the already-held canonical lock. This module alone
does not establish those prerequisites or authorize a real driver execution.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import deadline


def require(value, message):
    if not value:
        raise RuntimeError(message)


def check_identity(value, *, pid, parent, command, cwd):
    """Interpret the exact existing owned_stage.identity ps/lsof schema."""
    require(value['ps_returncode'] == value['cwd_returncode'] == 0,
            'identity probe failed')
    fields = value['ps'].split(None, 9)
    require(len(fields) == 10, 'incomplete ps identity')
    require([int(word) for word in fields[:3]] == [pid, parent, pid],
            'PID, parent or fresh process group differs')
    require(fields[8] == '??', 'new driver unexpectedly has a terminal')
    require(fields[9] == ' '.join(command), 'actual driver command differs')
    require(value['cwd'].splitlines() == [f'p{pid}', 'fcwd', 'n' + str(cwd)],
            'actual driver working directory differs')
    # The five lstart fields stay in the immutable original raw ps identity.
    return value


def prove_singleton(original, current, groups, *, pid, parent, command, cwd):
    """Refuse any extra group member, even an apparent descendant.

    The unchanged fixture uses embedded compiler calls ending after expansion;
    it needs no child process. A different process tree requires a new design.
    groups is the complete ps (pid, ppid, pgid) table, not a name-based selection.
    """
    check_identity(original, pid=pid, parent=parent, command=command, cwd=cwd)
    check_identity(current, pid=pid, parent=parent, command=command, cwd=cwd)
    require(current == original, 'original process identity changed')
    require(all(type(row) is tuple and len(row) == 3
                and all(type(value) is int for value in row) for row in groups),
            'malformed process table')
    require(len({row[0] for row in groups}) == len(groups), 'duplicate process table PID')
    members = [row for row in groups if row[2] == pid]
    require(members == [(pid, parent, pid)], 'driver group contains an unproved process')
    return dict(original=original, current=current, group=members)


def bounded_probe(command, *, cwd, environment, output, canonical_fd, owned):
    """Bound a read-only probe wait without implicitly killing on timeout.

    A timed-out probe keeps the inherited canonical FD; its unresolved receipt
    prevents a later stage from treating the controller return as completion.
    No probe process receives a signal from this adapter.
    """
    output.mkdir(exist_ok=False)
    record = dict(status='starting', command=list(command), cwd=str(cwd),
                  environment=environment, parent_pid=os.getpid(), started_at=time.time())
    owned.write(output / 'receipt.json', record)
    with (output / 'stdout').open('xb') as stdout, (output / 'stderr').open('xb') as stderr:
        child = subprocess.Popen(command, cwd=cwd, env=environment, stdout=stdout, stderr=stderr,
                                 start_new_session=True, pass_fds=(canonical_fd,))
        record.update(pid=child.pid, process_group=child.pid, terminal=None, status='running')
        try:
            owned.write(output / 'receipt.json', record)
            record['returncode'] = child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            record.update(status='unresolved-live-probe', controller_finished_at=time.time())
            owned.write(output / 'receipt.json', record)
            raise RuntimeError('read-only identity probe exceeded its finite wait; no signal sent')
        except BaseException as error:
            record.update(status='failed-probe', error=repr(error),
                          process_may_be_live=child.poll() is None, controller_finished_at=time.time())
            owned.write(output / 'receipt.json', record)
            raise
        record.update(status='finished', finished_at=time.time())
        stdout.flush(); stderr.flush()
    # Check sizes before any complete read/hash, including a fast oversized exit.
    require(all((output / name).stat().st_size <= 2**20 for name in ('stdout', 'stderr')),
            'identity probe output exceeds 1 MiB per stream')
    raw = {name: (output / name).read_bytes() for name in ('stdout', 'stderr')}
    record.update({name + '_sha256': hashlib.sha256(value).hexdigest() for name, value in raw.items()})
    owned.write(output / 'receipt.json', record)
    require(not raw['stderr'], 'unexpected identity probe diagnostic')
    return record['returncode'], raw['stdout'].decode('utf-8', errors='strict')


def run(command, *, cwd, environment, output, canonical_fd, owned,
        guard, resource_observation, resource_rejection):
    """Run one admitted driver row, retaining a bounded-wait terminal result.

    owned is the separately frozen existing owned_stage module. guard performs
    the future stage's full source/provider/input checks. Resource callbacks
    must cover the complete 14 GiB namespace, 256 MiB evidence and 9 GiB stop.
    Only exited/zero/error-free results can pass. Every caller must reject a
    failed or unresolved result and must not start the other process afterward.
    """
    command = list(command); cwd = Path(cwd); output = Path(output)
    require(len(command) == 5 and command[-1] in ('serial', 'parallel'),
            'expected one unchanged hash-driver command')
    require(all(type(word) is str for word in command), 'non-string command argument')
    require(all(Path(word).is_absolute() for word in command[:4]), 'absolute driver paths required')
    require(cwd.resolve(strict=True) == cwd and cwd.is_dir(), 'ordinary working directory required')
    require(output.parent.resolve(strict=True) == output.parent, 'ordinary evidence parent required')
    require(not output.exists() and not output.is_symlink(), 'fresh evidence path required')
    # Validate this exact open-file description; never reopen an independent lock
    # and claim it will remain held by a live driver after supervisor failure.
    with owned.workload_lock(owned.CANONICAL_LOCK, 600, inherited_fd=canonical_fd):
        pass
    guard()
    initial = resource_observation()
    require(resource_rejection(initial) is None, 'initial resource observation rejected')
    output.mkdir(); (output / 'probes').mkdir()
    parent = os.getpid()
    record = dict(status='starting', command=command, cwd=str(cwd), environment=environment,
                  supervisor_pid=parent, parent_pid=os.getppid(), started_at=time.time(),
                  samples=[initial], events=[], errors=[], probes=[], mode=command[-1],
                  real_driver_qualification=False)

    def save():
        owned.write(output / 'receipt.json', record)

    save()
    original = None

    def probe(argv):
        destination = output / 'probes' / f'{len(record["probes"]):03}'
        # Tracing belongs to the driver; it must not contaminate identity output.
        probe_environment = dict(environment)
        probe_environment.pop('DYLD_PRINT_LIBRARIES', None)
        try:
            return bounded_probe(argv, cwd=cwd, environment=probe_environment,
                                 output=destination, canonical_fd=canonical_fd, owned=owned)
        finally:
            path = destination / 'receipt.json'
            if path.exists():
                row = json.loads(path.read_bytes())
                record['probes'].append(dict(path=str(path), receipt=row))

    def inspect(pid):
        ps_code, ps = probe(['/bin/ps', '-p', str(pid), '-o',
                             'pid=,ppid=,pgid=,lstart=,tty=,command='])
        cwd_code, directory = probe(['/usr/sbin/lsof', '-a', '-p', str(pid), '-d', 'cwd', '-Fn'])
        return dict(ps=ps.strip(), ps_returncode=ps_code, cwd=directory, cwd_returncode=cwd_code)

    with (output / 'stdout').open('xb') as stdout, (output / 'stderr').open('xb') as stderr:
        started = time.monotonic()
        try:
            child = subprocess.Popen(command, cwd=cwd, env=environment, stdout=stdout, stderr=stderr,
                                     start_new_session=True, pass_fds=(canonical_fd,))
        except BaseException as error:
            record.update(status='failed', controller_finished_at=time.time(),
                          launch_error=repr(error), child_may_be_live=False)
            save()
            raise
        record.update(pid=child.pid, status='running', child_started_monotonic=started)
        try:
            original = check_identity(inspect(child.pid), pid=child.pid,
                                      parent=parent, command=command, cwd=cwd)
            record['identity'] = original
            save()
        except Exception as error:
            record['errors'].append(dict(operation='initial identity/publication', error=repr(error)))

        def heartbeat():
            try:
                row = resource_observation(); record['samples'].append(row)
                reason = resource_rejection(row)
                if any((output / name).stat().st_size > 2**20 for name in ('stdout', 'stderr')):
                    reason = reason or 'driver output exceeded observed 1 MiB per-stream limit'
                save()
                return reason or ('initial identity/publication failed' if record['errors'] else None)
            except Exception as error:
                record['errors'].append(dict(operation='resource observation/publication', error=repr(error)))
                return 'resource observation/publication failed'

        def publish(event):
            record['events'].append(event); save()

        def stop_owned(signum, reason):
            require(signum in (signal.SIGINT, signal.SIGKILL), 'unapproved stop signal')
            if child.poll() is not None:
                return False
            require(original is not None, 'no original identity; refusing signal')
            current = inspect(child.pid)
            code, table = probe(['/bin/ps', '-axo', 'pid=,ppid=,pgid='])
            require(code == 0, 'process-group table probe failed')
            groups = [tuple(map(int, line.split())) for line in table.splitlines() if line.strip()]
            proof = prove_singleton(original, current, groups, pid=child.pid, parent=parent,
                                    command=command, cwd=cwd)
            require(os.getpgid(child.pid) == child.pid, 'owned process group changed')
            # Retain proof before any signal. Publication failure refuses it.
            owned.write(output / ('owned-stop-' + signum.name + '.json'),
                        dict(reason=reason, signal=signum.name, time=time.time(), **proof))
            if child.poll() is None:
                os.killpg(child.pid, signum)
                return True
            return False

        waited = deadline.monitor(child, heartbeat=heartbeat, stop_owned=stop_owned,
                                  publish=publish, started_at=started)
        record['wait'] = waited
        record['status'] = ('passed' if waited['status'] == 'exited'
                            and waited['returncode'] == 0 and not record['errors'] else 'failed')
        record['child_may_be_live'] = waited['child_may_be_live']
        record['probe_may_be_live'] = any(row['receipt']['status'] != 'finished'
                                        for row in record['probes'])
        if record['probe_may_be_live']:
            record['status'] = 'failed'
        record['controller_finished_at'] = time.time()
        stdout.flush(); stderr.flush()
        if not waited['child_may_be_live']:
            record['child_finished_at'] = time.time()
            try:
                require(all((output / name).stat().st_size <= 2**20 for name in ('stdout', 'stderr')),
                        'driver output bound exceeded')
                for name in ('stdout', 'stderr'):
                    with (output / name).open('rb') as stream:
                        record[name + '_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
                final = resource_observation(); record['samples'].append(final)
                require(resource_rejection(final) is None, 'final resource observation rejected')
                guard()
            except Exception as error:
                record['errors'].append(dict(operation='final guards', error=repr(error)))
                record['status'] = 'failed'
        # A live driver retains the inherited FD and can still be writing. Do
        # not hash its mutable streams or call this a child completion.
        save()
    return record
