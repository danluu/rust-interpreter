# Guarded native indirect-call specialization

Implementation follows [the design](../../../docs/INDIRECT-CALL-NEXT.md).
The runtime base is the qualified wide-operation candidate f8713aaa; its failed
folded noise guard stays recorded. Compiler/exporter/wrapper bytes are retained.
Only custom resumable JIT execution gains the new path; strict Rust checking
and the ordinary interpreter remain unchanged.

Each compiled caller with indirect calls owns a separate, fixed-length table
indexed by validated PC. Slots start empty. Code tests a slot and declines to
the original VM when empty. After the VM validates the first target and sets
up the call, the JIT stages a thunk with full128-bit handle equality, the same
deterministic caller register assignment and the existing checked direct-call
emitter. Only then is the internal entry published. Call sites never retarget;
mismatches use the VM. Native entry availability remains independently checked.
All publication occurs on the creating thread between native entries.

Dispatch tables, attempted flags and published code-range descriptors count
against the existing16MiB entry-table budget, including existing resume entries.
The code dump identifies each thunk separately from its preceding region.
Thunks count against the configured
code budget, and their analysis/emission cost enters JIT compile timing.
No code bytes are patched, guest addresses exposed, callback ABI introduced,
borrow checks delayed or argument values specialized.

New correctness tests cover independent Rust arithmetic, both valid targets,
changing targets across prepared invocations, fresh guest storage, invalid and
nonzero-high-word handles, signature mismatch, exact instruction profiles,
every instruction-budget tail, small/far register indices, persistent registers
on/off, zero/full code capacities, exact memory/depth boundaries, bounded
one-target publication and a thunk whose callee is initially unready.
Run full debug/release tests before any new runtime execution outside tests;
then qualify exact saved assertions/entropy, serial/prepared suites and strict
native/cache controls. Provisional expected host count is424 per profile.

The toolchain-lookup benchmark completed all396 expected outcomes against
immutable49746a22 tools before this qualification started. The first host
build found two existing direct-entry test fixtures missing the new cursor
pointer field; compilation stopped before tests ran. Both fixtures now use
the prepared JIT table pointer. Preserve that failed receipt and rerun the
changed source under the shared lock. No runtime performance has been measured.

Before this candidate's timing, freeze its full command driver and tests.
The full twelve-test token selection, including both dominant tests, is primary;
folded and pgrust are mandatory. Compare against f8713aaa and the original fixed
selected-suite anchor with matched Cargo workers and ordinary native libtest.
Retain every original, wrong-edit, valid-edit and restored command.

Use a prospective regression guard that accounts for the observed noise margin:
on each held-out case require paired wall ratio plus wall A/A envelope<=1.05,
and CPU ratio plus CPU A/A envelope<=1.05. This is an engineering acceptance
margin, not a statistical upper confidence bound. It avoids rejecting a large
observed improvement solely because an unrelated absolute noise ceiling was
crossed, while requiring more margin for a near-regression under noisy controls.
Primary component wall gain must exceed its A/A envelope, CPU must not increase,
and the full stack must improve8% against the fixed anchor. Freeze exact
remaining quality rules with the driver before any timing. Historical gates,
including the lookup comparison still running, are not recalculated under this
new rule. No unchanged candidate is retimed to obtain a different decision.
