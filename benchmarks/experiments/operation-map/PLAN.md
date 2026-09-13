# Post-execution operation attribution

Base: adopted main fd7d06e, VM 99ceabaa from tool e729a493. Both the constant
shift and direct-operand runtime changes remain parked. Their small static
code reductions did not establish a complete-command benefit.

Add an explicit `--jit-operation-map` diagnostic requiring the existing
exclusive `--jit-code-dump` destination. Scope it to ordinary and resumable
execution; reject native trees/stubs before guest execution. Preserve the
original map.json/code.bin interface and write a separate operations.json.
Without this option, do not collect operation spans or retain new per-function
metadata on the execution path.

After successful guest execution, reconstruct each published function in
publication order with the shared emitter and a bounded span collector. Reuse
its original admission, exact byte budget and assertion base. Do not publish
code, entry tables or assertions, and do not mutate the guest or JIT. Accept
labels only after comparing every reconstructed word, block entry, resumable
entry and assertion identity against that process's published values. Reject
incomplete, overlapping or out-of-range coverage. Keep zero-word operations
explicit. Bound span counts and output bytes; a failed diagnostic is retained
as a failure, never treated as a complete sample map.

Separate external entries, budget guards, optional counters, individual
bytecode PCs, fact flushes, region exits, fault/assertion tails, budget fallback
and successor fallbacks. A branch belongs to its actual PC. Initially label
each whole resumable Call/Return emission as a transition, explicitly including
its wrappers, guards and fallbacks. These are native transitions, not VM exits.
Operation names can be joined by function/PC to the exact retained profile;
the map does not infer memory safety from rendered text.

Qualify coverage, byte equality, default-off behavior, multiple functions and
assertion identities, loops/branches, zero-word operations, profiling,
resumable/persistent modes, empty or capacity-declined emissions, corrupt
receipts and invalid options. Run all Rust checks in both profiles, two Cargo
workers under the shared benchmark lock, 45-second lock admission and 8 GiB
free-space floor. Preserve exact exporter/wrapper bytes. Freeze committed
source before the build and retain failed attempts.

Then qualify exact current real-test outcomes and maps before sampling. Reuse
existing exact logical profiles rather than rerunning them for known counts.
Take one fresh three-second normal-entropy owned-process sample of each
dominant token test, with its same-process operation map and pinned artifact/
catalog. No other own benchmark/build/profile overlaps. Freeze the precise
commands and expected counts before execution. Do not retime either parked
candidate or use perturbed samples for a latency verdict.

Report sampled time by actual operation/transition and explicit overhead
categories, with coverage/unassigned samples. Static emitted words and
frequency-weighted expansion remain distinct from sampled time and hardware
retired instructions. Use this evidence to choose a bounded runtime change;
no memory-model or allocator rewrite is preapproved by the hypothesis.
