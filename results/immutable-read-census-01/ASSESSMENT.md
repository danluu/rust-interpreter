# Defer immutable-data folding after measuring its current scope

All seven commands passed: two Rust controls in each profile, three exact native
reconstructions and two sample-ownership controls plus attribution. Every emitted
word, entry, resume, assertion and operation count is unchanged; no guest runs or
native code is published. The observer uses explicit memory-source operands,
full-width addresses and complete immutable data bounds.

| Capture | Known Load/Copy sites | Functions | Selected / generated samples |
| --- | ---: | ---: | ---: |
| Block |662|193|0 /1561|
| Exhaustive |973|227|5 /1231|
| Parser |1003|430|3 /85|

These are partial, perturbed self-PC samples, not runtime fractions or proof of
zero benefit. The census does not propagate new constants, but the existing
known-source scope is insufficient to prioritize a new runtime implementation.
Retain the result and do not run a timing screen for this mechanism.

Next examine data-value reuse within existing frame-disjoint guarded ranges.
Current ordinary memory forwarding tracks local-frame values; the adopted range
proofs also identify external offsets and disjoint local writes. A diagnostic
should measure available values under exact register invalidation and overlapping
write rules before extending forwarding. This differs from the parked scalar
path/store-log candidates and requires no added guest guards or code cache.
