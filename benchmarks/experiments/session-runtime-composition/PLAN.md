# Session history with complementary guest execution mechanisms

This is a new experimental composition, not adoption or a retry of either failed
candidate. Preserve the duration-order fre failure and the earlier runtime
composition parser CPU failure. The latter passed726 project commands but its
parser CPU margin1.0502179853 exceeded1.05. The session candidate passed both
parser gates but failed fre wall0.970558296+A/A0.055748790. Gains are not additive.

Apply only the reviewed bytecode delta from2599a193 (indirect transitions,
checked readonly scalar leaves, successor-only spilling) to current session
sources0d6567b2. Keep compiler/exporter/wrapper binaries exactly adopted df4006e0.
Keep16MiB arena, bounded64MiB history per worker, large-function threshold65536,
parameterized literalsv1, shared keys/buffering off, strict checking and2workers.
No benchmark-specific dispatch, shims, entropy replay or altered test assertions.

Interaction review obligations before qualification:
- Indirect code embeds a signature ordinal from the current full program. Key
  the exact current ordinal for each distinct indirect signature, including
  missing metadata/signature and enabled/disabled state. Dynamic layouts/entry
  addresses remain loaded from current owner tables, never retained in templates.
- Preserve current direct-callee zero-initialization and scalar-entry model keys,
  literal relocation, assertion relocation and actual emitted-word verification.
- Extend explicit session request/client/report option transport for indirect
  calls, reject incompatible/partial modes and verify runtime-option agreement.
  Old requests without the new option mean disabled; unsupported servers must
  reject an enabled request before execution. No silent enablement or retry.
- Readonly scalar code must use fresh runtime memory and preserve ordered faults,
  private replay, all budgets, aliased result/source and heap-free entry safety.
- Successor spilling must preserve branch values until exit, join liveness and
  existing tree-call tails; include changed test flags in private template keys.

First run focused interaction controls, then the complete actual composed debug
and release workspace, Python contracts, normal and diagnostic binaries plus
feature-off session/model controls. Record exact counts/binaries/setup time;
reuse only exact bound evidence and distinguish it from new tests. Verify every
history hit by independent emission on saved parser and fre edited histories,
including original assertion failures and resource limits, before timing.

Then run one fresh40-command fre changed-source primary with original edits,
wrong/restored controls, baseline/duplicate/candidate/anchor/ordinary native and
strict unreachable type/borrow rejections. Predeclare session CPU accounting and
option bindings. Require wall ratio+max individual A/A<1 and CPU ratio<=1 with
CPU ratio+A/A<=1.05. Preserve high-variance/failed attempts without unchanged retry.
Only a pass admits full fre/folded/pgrust/private/Nushell histories and both parser
guards. Actual current-main integration requires qualification of merged sources,
preserving the independent compiler session's work, and fresh matched evidence
where the measured path changes. Main remains unchanged on any failed guard.

Resource policy: sole shared target; .work/benchmark.lock with45s admission,
2Cargo/test workers, build floor max(14GiB,8GiB+2*allocated target),12GiB offline
analysis/replay,8GiB child/closure,16GiB fre,24GiB parser plus namespace estimate,
47GiB minimum Nushell. No target cleanup, peer process control or new services.
Freeze all measured source during each run and independently close evidence.
