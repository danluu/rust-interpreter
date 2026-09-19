# Inspect retained native switch sites

Consume the independently closed current-composition captures. Validate exact
operation maps and retained static identities; classify every native Switch span
and every captured Switch self PC as single zero, other small cases (all <=4095),
or general cases. Preserve complete generated-sample accounting. Record code-word
extents, not estimated savings. No guest, profiler, build or timing is run.

If the sampled sites support it, qualify a compact native switch emitter:
single zero uses a whole-128-bit OR comparison; other all-small cases share one
high-half guard and compare low halves with unsigned immediate comparisons.
Retain full-width general comparisons and first-match order. Do not use observed
values or Rust types as proofs. Budget charging, profile PCs, ABI, native links,
fallback and capacity semantics remain the existing contracts. A new changed-
source primary screen must decide performance; these samples cannot.
