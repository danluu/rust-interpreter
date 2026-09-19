"""Bounded wait policy for a newly owned hash-control child; no process launch.

The caller must provide exact-ownership signal validation and keep the canonical
lock inherited by the child. This module never selects or signals a PID itself.
"""
import math
import signal
import subprocess
import time


def monitor(child, *, heartbeat, stop_owned, publish, timeout=120.0,
            grace=5.0, reap=5.0, interval=5.0, clock=time.monotonic,
            sleep=time.sleep, started_at=None):
    """Return a complete wait history, including an unresolved live child.

    heartbeat returns a resource-stop reason or None. stop_owned(signal, reason)
    must revalidate the original child and its complete owned group, persist the
    proof, and only then signal it. Raising refuses the signal. publish receives
    each event; publication failures remain errors and do not disable deadlines.

    Every child wait is finite. The execution deadline includes supervision time
    after Popen. Supply its monotonic start as started_at so initial identity
    capture and receipt writes consume the same execution budget.
    Blocking callbacks or kernel calls cannot be given a hard real-time bound by
    this in-process policy. An unresolved result is a failed operation, never a
    completed workload; the child-held lock must continue to exclude admission.
    """
    for value in (timeout, grace, reap, interval):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('all wait limits must be positive finite numbers')
    now = clock()
    started = now if started_at is None else started_at
    if isinstance(started, bool) or not isinstance(started, (int, float)) or not math.isfinite(started) or started > now:
        raise ValueError('launch start must be finite and no later than now')
    execution_deadline = started + timeout
    phase = 'running'
    phase_deadline = execution_deadline
    reason = None
    events = []
    errors = []

    def event(kind, **fields):
        row = dict(kind=kind, elapsed=clock()-started, **fields)
        events.append(row)
        try:
            publish(dict(row))
        except Exception as error:
            errors.append(dict(operation='publish', error=repr(error), elapsed=clock()-started))

    def result(returncode, unresolved=False):
        status = ('unresolved-live-child' if unresolved else
                  'stopped' if reason is not None else
                  'supervision-failed' if errors else 'exited')
        event('terminal', status=status, returncode=returncode, reason=reason)
        # Publishing the terminal event can itself fail.
        if status == 'exited' and errors:
            status = 'supervision-failed'
        return dict(status=status, returncode=returncode, reason=reason,
                    elapsed=clock()-started, events=events, errors=errors,
                    child_may_be_live=unresolved)

    def request_stop(signum):
        event('stop-request', signal=signum.name, reason=reason)
        try:
            stop_owned(signum, reason)
        except Exception as error:
            errors.append(dict(operation='stop_owned', error=repr(error), elapsed=clock()-started))
            event('stop-refused', signal=signum.name)
            return False
        event('stop-sent', signal=signum.name)
        return True

    def observed_poll():
        try:
            return child.poll()
        except Exception as error:
            errors.append(dict(operation='poll', error=repr(error), elapsed=clock()-started))
            # Unknown status is conservatively live. It cannot disable the
            # deadline or authorize a signal without the caller's fresh proof.
            return None

    event('started', timeout=timeout, grace=grace, reap=reap, interval=interval)
    while True:
        now = clock()
        returncode = observed_poll()
        if phase == 'running' and now >= execution_deadline:
            reason = 'execution deadline exceeded'
        if returncode is not None:
            return result(returncode)

        try:
            resource_reason = heartbeat()
            if resource_reason is not None and not isinstance(resource_reason, str):
                raise TypeError('heartbeat must return a reason string or None')
            if resource_reason is not None and reason is None:
                reason = resource_reason
        except Exception as error:
            errors.append(dict(operation='heartbeat', error=repr(error), elapsed=clock()-started))

        now = clock()
        if phase == 'running' and now >= execution_deadline and reason is None:
            reason = 'execution deadline exceeded'
        if phase == 'running' and reason is not None:
            if not request_stop(signal.SIGINT):
                returncode = observed_poll()
                return result(returncode, unresolved=returncode is None)
            phase = 'interrupt-grace'
            phase_deadline = clock() + grace
        elif phase == 'interrupt-grace' and now >= phase_deadline:
            if not request_stop(signal.SIGKILL):
                returncode = observed_poll()
                return result(returncode, unresolved=returncode is None)
            phase = 'kill-reap'
            phase_deadline = clock() + reap
        elif phase == 'kill-reap' and now >= phase_deadline:
            returncode = observed_poll()
            return result(returncode, unresolved=returncode is None)

        remaining = phase_deadline - clock()
        if remaining <= 0:
            continue
        wait = min(interval, remaining)
        try:
            child.wait(timeout=wait)
        except subprocess.TimeoutExpired:
            pass
        except Exception as error:
            errors.append(dict(operation='wait', error=repr(error), elapsed=clock()-started))
            # A repeated wait error must not create a busy loop or an unbounded
            # fallback wait. The next iteration still checks the same deadline.
            sleep(min(interval, max(0.0, phase_deadline-clock())))
