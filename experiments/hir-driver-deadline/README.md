# Finite waits for the candidate hash-driver controls

These are source components for the two executions in the
[B3/hash-driver proposal](../hir-options-hash-beta-driver/PROPOSAL.md).
They have no CLI launcher and have not supervised a real driver or sent a signal.
It does not change the already frozen compiler-build helper.

`deadline.monitor` uses a monotonic 120-second execution budget, including
initial identity capture when the caller passes the original `Popen` start.
Resource observations continue at most five seconds apart between bounded
waits. A deadline or resource rejection requests SIGINT, allows five seconds
to exit, requests SIGKILL if needed, and allows five seconds to reap. Each
request requires a new successful ownership proof supplied by the caller.
An identity refusal ends with an explicit unresolved result. A kernel process
that remains live after the final wait is also unresolved; the code does not
claim to guarantee termination or hard real-time behavior of blocking callbacks.

The concrete caller must still provide all of these before any real use:

- A fresh, recorded child/session, exact argv, environment, working directory,
  original identity, source/provider guards, and bounded output retention.
- The already held canonical lock's exact open-file description in `pass_fds`.
  A live child must retain exclusion if its supervisor returns an unresolved
  result. Reopening the lock path is not equivalent.
- A signal callback that revalidates PID, parentage, start time, command,
  working directory, terminal and every current group member, writes the
  complete proof, then signals only that freshly owned group. This module
  neither discovers PIDs nor calls a signal API.
- The existing 9 GiB free-space stop, 14 GiB namespace and 256 MiB evidence
  guards in the heartbeat, with observations retained throughout graceful
  shutdown. The ordinary 24 GiB admission requirement is unchanged.
- Rejection of any result except `exited` with the expected return code and
  no errors. A stopped or unresolved process is not successful cleanup.

Polling, waiting, observation and receipt-publication errors remain in the
returned history and do not disable the finite deadline. The caller must
preserve that complete result, raw output and any earlier failure. A refused
signal never becomes permission to select another process or retry without
proof. Callback execution and operating-system calls themselves can block;
these are finite controller waits, not a kernel termination guarantee.

Twelve pure controls passed with
`/opt/homebrew/bin/python3 -B -m unittest -v test_deadline` from this directory.
They use only a simulated child, clock and callbacks: no subprocess, actual
signal, compiler, benchmark or canonical-lock acquisition. The first ten-test
run passed; review then identified an unhandled polling exception, which was
fixed before the twelve-test run. The added controls cover repeated polling
errors with ownership refusal and the initial identity-capture budget.
Real dispatcher integration and ownership validation remain unqualified.

`owned_driver.py` is a separate, unrun adapter for one future admitted driver
command. It creates a fresh session and passes the already-held canonical lock
descriptor to the driver. It validates recorded PID, parent, start, command,
working directory, terminal and group before a signal. The unchanged small
fixture uses the embedded compiler and stops after expansion, so the adapter
accepts only a singleton group; any extra member causes refusal. A newly
observed exit is recorded as `stop-not-needed`, without claiming a signal.

Identity and group probes use fresh, recorded read-only children with finite
two-second waits. They also inherit the lock. A probe timeout sends no signal:
it retains an unresolved receipt and prevents qualification or subsequent
admission while the process remains live. This avoids the unbounded waits in
the older identity helper and automatic timeout signaling without a proof.
Provider paths, input guards, exact environments and aggregate capacity callbacks
still need binding in the future stage. Operating-system calls can themselves
block; these limits bound explicit controller waits, not kernel behavior.

Raw output is sampled against a 1 MiB per-stream limit and checked before final
reading or hashing. This is an observed stop threshold, not a hard write quota.
A live unresolved driver retains its lock and mutable streams; its receipt has
no false child-finish timestamp or final output digest. Pure ownership and fake
adapter controls are in `test_owned_driver.py`; no actual driver or signal result
is implied by them.

The combined 25 pure controls passed with no failures or skips; their exact
source hashes and raw output are retained in `controls-02.json` and
`controls-02.stderr`. They include the earlier deadline cases, no-signal exit
reporting, reused identities, unexpected group members, lock inheritance,
publication before a mocked signal, launch failure and an unresolved probe.
All process APIs used by these adapter controls are replaced by test doubles.
