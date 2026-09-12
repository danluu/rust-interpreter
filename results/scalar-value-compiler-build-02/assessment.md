Typed scalar compiler integration passes 334 workspace tests in both debug and
release, one ignored. The twelve new compiler tests cover all five widths,
entry validation, implicit returns, every caller/callee storage bridge, hot
native transitions, recursion, backedges, initialization, aliases, identity and
extent checks, bounded declines, remaining memory faults and address-proof
rejections. Three existing move-elimination tests also run in the new module.
The original folded/token version-5 artifacts decode/re-encode identically.

Tool key: aa56492e192ef2e87f69ed417b34c8f717b28c31a0fa67f5d63fbb92f313c9cd.
Parent runtime: e651b25cdf50df92a1787d99195803680d52cc25d0e98898f65ddbeb33393ed3.
Implementation: benchmarks/experiments/scalar-value-compiler-v2.

MIR private-use/layout evidence is carried through the validated relocation map
and rechecked after existing optimizers. Direct caller operands and formal
arguments/results become registers only after a bounded final address proof.
Version-6 publication and audit plumbing are opt-in; strict checking remains.
The new proof checks every Local definition, including reused registers and
interior addresses. The old production compiler remains unchanged.

This qualifies library and compiler unit behavior. Real Rust exports, Cargo
publication, original workload assertions and the fixed end-to-end performance
gates are separate outstanding qualifications. No scalar timing or production
runtime publication is claimed. The initial failed harness run is preserved.
