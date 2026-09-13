# Qualification gates

Require532 workspace tests per debug/release profile (419 bytecode,113 exporter),
11 ignored offline diagnostics. Five candidate tests cover wrapping counters,
alignment/sentinels, repeated entry, fault publication, copy/popcount clobbers,
independent assembly and successor-live branch/join/call values. Existing tests
cover native ABI, frame/return faults, capacity, TLS and all-budget fallback.

The new offline observer reconstructs both complete adopted captures, checks
counter deltas in every operation-map scope (five entry words, one per VM exit,
two removed per counter update), then compares the composed spill removal with
the original typed census. No guest code runs and no executable code is published.

119 strict/cache commands, three exact original profiles including native calls
and returns,12 primary harness tests, then40 fresh changed-source screen commands.
Only a passing wall+CPU A/A screen permits the full five-workload campaign and114
parser tests. Preserve baseline35df4077, compiler/wrapper, bytecode and16 MiB limit.
