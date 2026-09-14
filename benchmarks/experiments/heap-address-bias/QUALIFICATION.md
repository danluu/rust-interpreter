# Heap address bias qualification

The fixed/dynamic oracle executes actual emitted instructions and checks the
whole u64 address/count domain's critical boundaries using u128 arithmetic.
Two controls pass in each profile. Existing all-budget, copy-order, guarded
range, cached-value, native ABI and reentry controls remain mandatory.

Build a matched unchanged main ab6adbe8 VM from Git-bound source and the candidate
with identical toolchain/profile flags and two workers. Retain original strict
exporter/wrapper. Run every workspace test in debug/release, requiring equal
counts, the established minimum and all new named controls; record actual totals.
Retain the existing 11 explicitly ignored diagnostic tests. Original workloads,
source edits/rejections, profiles and protocol controls qualify before timing.

Setup admission is max(14 GiB, 8 GiB + twice the entire shared target's current
allocated size), checked before each compiler child and recorded. It reserves
old plus new outputs and linking space; it never lowers the 8 GiB child floor.
The first focused build completed in 17.12 seconds without substantial growth.
No cleanup of shared targets, installed tools or protected evidence follows.
