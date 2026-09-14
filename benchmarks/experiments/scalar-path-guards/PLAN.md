# Model path guards before direct scalar effects

The two static entry-address policies have closed adopted-sample coverage of
43 and 62 / 1,561 block samples. Both decline useful functions that can fail after
stores. A new path-sensitive guard model must establish the actual successful
path before any external mutation. This is test-only work on the archived
store-log source; main retains the adopted runtime.

Build a bounded dependency slice rooted at every external memory address,
branch/assertion condition and potentially failing division/remainder. Follow
full SSA dependencies including edge-specific phis. Exclude unrelated result
and store-payload computations. Walk the original CFG using this slice, checking
every visited range and write permission and every original fault. Trap or failed
checks decline before guest effects. Do not execute store payloads or mutate
memory during guard evaluation; retain at most sixteen visited write ranges.

When a sliced load executes, its full range must be disjoint from every earlier
visited write range. Otherwise decline. This establishes that the load sees the
same value during subsequent ordinary execution. A later write cannot change a
previously captured SSA value. By induction, branch choices, checked addresses
and fault conditions then remain identical along the certified path. Reads not
needed by the slice still have their complete ranges checked. All ranges refer
to the pre-Call linear prefix or current heap, excluding fresh frame/padding.

The model then runs the existing scalar evaluator with direct Memory reads and
writes in original order, comparing its exact PC sequence to the certificate.
A failure before the first store can replay. A failure after a store is a model
invariant violation and must never replay. The ordinary Call bridge still checks
all argument/result/frame/memory/budget limits, reserves backing before execution,
preserves padding/peak memory and publishes exact logical counters on success.

Caps: existing 512 PCs/blocks and 16,384 nodes, 4,096 sliced nodes, 65,536 closure
visits, 128 memory sites, sixteen visited stores and at most 512 guard PCs. No
calls, allocation, FFI, cycles or partial source checking are admitted. Full
u128 values and low-word guest pointer semantics must match the scalar/VM rules.

Qualify complete active linear/heap memory on success AND error exits, return
values, fault text, instruction counts, per-PC profiles, resource limits, every
budget tail, readonly/null/boundary ranges, aliases, captured inputs, fresh frames,
retained padding, branching/phis, and non-idempotent updates. A dedicated temporal
alias negative control must detect the first divergent read before mutation.
Run debug/release controls under the shared lock and ROOT target with two workers
and test threads. Build admission max(14 GiB,8 GiB+twice allocated target), child
floor8 GiB. Record/close failures as well as successes. No original-project guest
or generated direct-store code is part of this model qualification.

If qualified, census the exact archived native plans for guard-slice size and
saved adopted sample scope before designing emitted guards. Dynamic guard
admission and actual speed require separate original-workload qualification and
a preregistered changed-source primary. Static counts are not a performance claim.

Initial run scalar-path-guard-model-01 executes 31 controls per profile: nine
new path-model controls and all 22 existing Call/private-store/native-reference
controls. Two commands, no saved-workload execution or timing. Existing native
reference tests may publish their already implemented code; the new direct-effect
path uses only this project's scalar evaluator and produces no machine code.
