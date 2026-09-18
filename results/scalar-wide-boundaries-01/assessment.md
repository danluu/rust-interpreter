# A 64-byte result and 1 KiB frame retain most structural coverage

The exact partition reproduces all 157 candidates and all 11/86 block/exhaustive
samples from the closed broad census. Most functions (148) exceed only the
16-byte result bound. Two exceed both frame and result bounds; their sampled
coverage is 2 block and 62 exhaustive observations. Register-only expansion
contributes 1/4, and frame-only expansion contributes none.

A policy keeping the existing 512-operation, 512-register and 16-byte argument
limits, while allowing 64-byte results and 1,024-byte frames, retains 132
structural candidates and 10/82 samples. This is 7+3 block transition/body
samples and 51+31 exhaustive samples. Every selected opcode family is already
recognized by the scalar IR. All 36 limit combinations and their monotonicity,
empty groups, rejected opcode families and candidate identities are retained.

Proceed to a **bounded aggregate-result proof/model**, using adopted main as its
runtime base. First retain the existing small-result behavior exactly and model
larger local results as ordered byte slices/16-byte lanes. Preserve argument
copy order, result padding and aliases, complete checking, fault behavior and
budgets. Continue rejecting external writes. Re-evaluate actual typed memory,
CFG and scalar-IR eligibility under explicit work bounds before native emission.

These are partial, perturbed samples from the adopted VM, not predicted gains.
Matching opcode families proves neither supported widths nor memory/alias/CFG
eligibility. The larger runtime ABI is not implemented or qualified by this
analysis. No guest run, Rust build or executable publication occurs. Closure
verifies 55 frozen bindings. [Summary](summary.json), [closure](closure.json).
