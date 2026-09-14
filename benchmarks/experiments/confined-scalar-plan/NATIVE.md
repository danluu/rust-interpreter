# First direct native scalar qualification

Compile the qualified scalar IR directly into AArch64 words. No LLVM,
Cranelift, external guest interpreter, guest callbacks or library code generation
participates. Reuse this project's reviewed MAP_JIT publisher and integer
instruction encodings, with distinct ABI probe symbols in the diagnostic binary.
Production bytecode/interpreter/JIT behavior stays unchanged.

Entry receives an immutable, width-checked u128 argument array, the original
logical frame base, a private Output and remaining instruction budget. Before
touching stack/output, require the leaf's maximum acyclic instruction count.
Live computed values/phis use distinct bounded private stack slots; constants,
arguments and Local-derived base values are materialized at use. Full-width
packs, casts, selects, phis and switches retain all 128 bits. Arithmetic and
unary operations support 8/16/32/64 bits; live 128-bit arithmetic declines.
Cap the stack at 32,752 bytes, code at 65,536 words and argument addressing at
2,048 scalar slots. Publication follows complete emission and relocation checks.

The generated leaf makes no host calls and preserves x19–x29, LR and SP. Its
scratch integer registers are x9–x17; CountOnes uses caller-saved v0. It never
dereferences a logical guest address or modifies the input argument array.
Success returns a private value, exact original instruction count and, when
profiled, the original-PC bitset. Acyclic blocks are charged once. Failing
assertions, traps and division return decline; all private output is discarded.
The private bitset/count is not valid on failure. This is not yet the guest Call
transaction: caller preflight, padding and result commit, counters, fallback,
full cursor snapshots and profile publication need separate qualification.

Run six native controls in debug/release alongside the prior 18 controls:
4,374 copy comparisons per profile (2,187 in each instrumentation mode), narrow
integer operations and aliases, all unary forms, wide values/switches and phis,
every-budget decline, bitsets crossing 64-bit boundaries, failure paths,
returned logical addresses, preserved host registers/SP, and code/storage limits.
Native arithmetic executes actual AArch64 instructions and is compared with the
custom scalar reference model. Original project artifacts are only emitted for
coverage metadata; their guest code is not published or executed by this run.

Use the existing owned supervisor and shared workload lock, two Cargo workers,
and max(14 GiB, 8 GiB + twice allocated shared target) build admission, with
the 8 GiB child floor. Preserve source/tool/output identities, setup cost and any
failure. No timing gate or runtime adoption can follow from these controls alone.
